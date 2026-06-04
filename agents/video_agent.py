import os
import subprocess
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from database.postgres import SessionLocal
from database.models import Script, ScenePlan, VisualAsset, AudioAsset
from services.ffmpeg_service import FFmpegService
from services.video_validator import VideoValidator
from services.video_storage import VideoStorage
from schemas.video_document import VideoDocument
from config.settings import settings

logger = logging.getLogger("video_agent")

class VideoAgentError(Exception):
    """Base exception for VideoAgent operations."""
    pass


class VideoAgent:
    """
    Agent responsible for coordinating video production:
    assembling visual/audio/subtitle assets, rendering the MP4, validating the output,
    and persisting video asset metadata.
    """
    def __init__(
        self,
        ffmpeg_service: Optional[FFmpegService] = None,
        video_validator: Optional[VideoValidator] = None,
        video_storage: Optional[VideoStorage] = None,
        assets_dir: Optional[str] = None
    ):
        self.ffmpeg = ffmpeg_service or FFmpegService()
        self.validator = video_validator or VideoValidator(ffmpeg_service=self.ffmpeg)
        self.storage = video_storage or VideoStorage()
        self.assets_dir = os.path.abspath(assets_dir or settings.PATH_ASSETS_DIR)
        os.makedirs(self.assets_dir, exist_ok=True)

    def assemble_video(self, script_id: int, db: Optional[Session] = None) -> VideoDocument:
        """
        Loads project assets, generates placeholder visual frames if missing,
        stitches slideshow with narration, burns subtitles, validates MP4,
        and saves VideoAsset metadata.
        """
        logger.info(f"Assembling video for script_id: {script_id}")

        opened_session = False
        if db is None:
            db = SessionLocal()
            opened_session = True

        temp_raw_mp4 = None
        # Initialize video record in DB with RENDERING status
        video_record = None
        try:
            # 1. Retrieve script record
            script = db.query(Script).filter(Script.id == script_id).first()
            if not script:
                raise VideoAgentError(f"Script with ID {script_id} not found.")

            # 2. Retrieve associated AudioAsset
            audio = script.audio_asset
            if not audio:
                raise VideoAgentError(f"No narration AudioAsset found for script {script_id}.")

            audio_abs_path = os.path.abspath(audio.audio_path)
            if not os.path.exists(audio_abs_path):
                raise VideoAgentError(f"Narration audio file not found at: {audio_abs_path}")

            # 3. Retrieve subtitle asset
            subtitle = script.subtitle_asset
            if not subtitle:
                raise VideoAgentError(f"No SubtitleAsset found for script {script_id}.")

            subtitle_abs_path = os.path.abspath(subtitle.subtitle_path)
            if not os.path.exists(subtitle_abs_path):
                raise VideoAgentError(f"Subtitle file not found at: {subtitle_abs_path}")

            # 4. Retrieve scene plans
            scenes = db.query(ScenePlan).filter(ScenePlan.script_id == script_id).order_by(ScenePlan.scene_number).all()
            if not scenes:
                raise VideoAgentError(f"No scene plans found for script {script_id}.")

            # 5. Build timeline of images and durations
            from services.timeline_builder import TimelineBuilder
            from services.motion_engine import MotionEngine

            timeline_builder = TimelineBuilder()
            motion_engine = MotionEngine(ffmpeg_path=self.ffmpeg.ffmpeg_path)
            timeline = timeline_builder.build(script_id, db)

            clip_paths = []
            temp_clips_dir = os.path.join(self.storage.base_dir, f"temp_clips_{script_id}")
            os.makedirs(temp_clips_dir, exist_ok=True)

            for entry in timeline.entries:
                clip_filename = f"clip_scene_{entry.scene_number}_{entry.scene_id}.mp4"
                clip_path = os.path.join(temp_clips_dir, clip_filename)

                img_path = entry.asset_local_path
                if entry.is_placeholder:
                    # Resolve to local fallback path and ensure it's generated
                    img_path = self._ensure_placeholder_scene(entry.scene_id)

                # Apply motion effect
                motion_engine.apply_effect(
                    image_path=img_path,
                    duration=entry.duration,
                    effect_name=entry.motion_effect,
                    output_path=clip_path
                )
                clip_paths.append(clip_path)

            # Stitch all individual MP4 clips together
            concat_txt_path = os.path.join(temp_clips_dir, "concat.txt")
            with open(concat_txt_path, "w", encoding="utf-8") as f:
                for clip in clip_paths:
                    clip_clean = os.path.abspath(clip).replace('\\', '/')
                    f.write(f"file '{clip_clean}'\n")

            temp_concat_video = os.path.join(temp_clips_dir, "concat_video.mp4")

            cmd_concat = [
                self.ffmpeg.ffmpeg_path,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_txt_path,
                "-c", "copy",
                temp_concat_video
            ]

            logger.info("Stitching motion clips...")
            process = subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode != 0:
                logger.error(f"FFmpeg concat clips failed: {process.stderr.decode('utf-8', errors='ignore')}")
                raise RuntimeError(f"FFmpeg concat clips failed: {process.stderr.decode('utf-8', errors='ignore')}")

            # Pre-register VideoAsset in RENDERING state
            video_record = self.storage.sync_db_asset(
                db=db,
                script_id=script_id,
                audio_id=audio.id,
                video_path=str(self.storage.get_video_path(script_id)),
                duration_seconds=audio.duration_seconds,
                resolution=f"{settings.VIDEO_RESOLUTION_WIDTH}x{settings.VIDEO_RESOLUTION_HEIGHT}",
                status="RENDERING"
            )

            # 6. Merge visuals with narration audio
            temp_raw_mp4 = os.path.join(self.storage.base_dir, f"temp_raw_{script_id}.mp4")
            cmd_merge = [
                self.ffmpeg.ffmpeg_path,
                "-y",
                "-i", temp_concat_video,
                "-i", audio_abs_path,
                "-c:v", "copy",
                "-c:a", settings.FFMPEG_AUDIO_CODEC,
                "-shortest",
                temp_raw_mp4
            ]

            logger.info("Merging visuals with narration audio...")
            process = subprocess.run(cmd_merge, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode != 0:
                logger.error(f"FFmpeg audio merge failed: {process.stderr.decode('utf-8', errors='ignore')}")
                raise RuntimeError(f"FFmpeg audio merge failed: {process.stderr.decode('utf-8', errors='ignore')}")

            # 7. Burn subtitles into final MP4 path
            final_path = self.storage.get_video_path(script_id)
            logger.info("Burning subtitles into the video stream...")
            self.ffmpeg.add_subtitles(temp_raw_mp4, subtitle_abs_path, str(final_path))

            # 8. Validate final output
            logger.info("Validating rendered MP4 video specs...")
            validation = self.validator.validate_video(
                str(final_path),
                expected_resolution=f"{settings.VIDEO_RESOLUTION_WIDTH}x{settings.VIDEO_RESOLUTION_HEIGHT}"
            )
            
            # 9. Sync database state to READY
            logger.info("Updating VideoAsset metadata in database...")
            final_record = self.storage.sync_db_asset(
                db=db,
                script_id=script_id,
                audio_id=audio.id,
                video_path=str(final_path),
                duration_seconds=validation["duration"],
                resolution=validation["resolution"],
                status="READY"
            )

            # Convert to Pydantic document
            doc = VideoDocument.model_validate(final_record)
            logger.info(f"Video assembly pipeline successful for script {script_id}.")
            return doc

        except Exception as e:
            db.rollback()
            logger.error(f"Video agent failed during assembly: {e}")
            if video_record:
                try:
                    # Update status to FAILED in case of crash
                    self.storage.sync_db_asset(
                        db=db,
                        script_id=script_id,
                        audio_id=audio.id if 'audio' in locals() and audio else 0,
                        video_path=str(self.storage.get_video_path(script_id)),
                        duration_seconds=0.0,
                        resolution=f"{settings.VIDEO_RESOLUTION_WIDTH}x{settings.VIDEO_RESOLUTION_HEIGHT}",
                        status="FAILED"
                    )
                except Exception as sync_err:
                    logger.error(f"Failed to set status to FAILED in DB: {sync_err}")
            raise VideoAgentError(f"Video assembly failed: {e}")
        finally:
            # Clean up temporary raw video file
            if temp_raw_mp4 and os.path.exists(temp_raw_mp4):
                try:
                    os.unlink(temp_raw_mp4)
                    logger.debug(f"Temporary raw file cleaned up: {temp_raw_mp4}")
                except Exception as ex:
                    logger.warning(f"Failed to clean up temporary raw video: {ex}")

            # Clean up temp clips directory
            if 'temp_clips_dir' in locals() and os.path.exists(temp_clips_dir):
                import shutil
                try:
                    shutil.rmtree(temp_clips_dir)
                    logger.debug(f"Temporary clips directory cleaned up: {temp_clips_dir}")
                except Exception as ex:
                    logger.warning(f"Failed to clean up temporary clips directory: {ex}")

            if opened_session:
                db.close()

    def _ensure_placeholder_asset(self, asset_id: int) -> str:
        """
        Generates a colored placeholder frame using FFmpeg if the physical file does not exist.
        """
        path = os.path.join(self.assets_dir, f"asset_{asset_id}.png")
        if not os.path.exists(path):
            colors = ["darkblue", "darkgreen", "purple", "darkred", "navy", "olive", "teal"]
            color = colors[asset_id % len(colors)]
            cmd = [
                self.ffmpeg.ffmpeg_path,
                "-y",
                "-f", "lavfi",
                "-i", f"color=c={color}:s={settings.VIDEO_RESOLUTION_WIDTH}x{settings.VIDEO_RESOLUTION_HEIGHT}",
                "-vframes", "1",
                path
            ]
            logger.info(f"Generating placeholder visual asset: {path}")
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode != 0:
                logger.error(f"Failed to generate placeholder frame using FFmpeg: {process.stderr}")
                # Fallback: create empty file if command failed
                with open(path, "w") as f:
                    f.write("")
        return path

    def _ensure_placeholder_scene(self, scene_id: int) -> str:
        """
        Generates a fallback scene colored frame using FFmpeg if no asset plan is attached.
        """
        path = os.path.join(self.assets_dir, f"scene_fallback_{scene_id}.png")
        if not os.path.exists(path):
            cmd = [
                self.ffmpeg.ffmpeg_path,
                "-y",
                "-f", "lavfi",
                "-i", f"color=c={settings.VIDEO_FALLBACK_COLOR}:s={settings.VIDEO_RESOLUTION_WIDTH}x{settings.VIDEO_RESOLUTION_HEIGHT}",
                "-vframes", "1",
                path
            ]
            logger.info(f"Generating fallback scene frame: {path}")
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return path
