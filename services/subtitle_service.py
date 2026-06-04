import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from database.models import Script, SubtitleAsset as SubtitleAssetModel, ScenePlan as ScenePlanModel
from schemas.subtitle_document import SubtitleDocument
from config.settings import settings

logger = logging.getLogger("subtitle_service")

class SubtitleError(Exception):
    """Base exception for SubtitleService operations."""
    pass


class SubtitleService:
    """
    Service responsible for converting script narration text into timed SRT subtitles.
    Conforms to line length limits (max 80 chars, max 2 lines) and timing boundaries.
    """
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = os.path.abspath(output_dir or settings.PATH_SUBTITLES_DIR)
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except Exception as e:
            logger.critical(f"Failed to create subtitles directory: {e}")
            raise SubtitleError(f"Initialization failed: {e}")

    def format_srt_time(self, seconds: float) -> str:
        """
        Converts seconds into SRT time format: HH:MM:SS,mmm
        """
        if seconds < 0:
            seconds = 0.0
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        if millis == 1000:
            millis = 0
            secs += 1
            if secs == 60:
                secs = 0
                mins += 1
                if mins == 60:
                    mins = 0
                    hrs += 1
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

    def chunk_narration_text(self, text: str, duration: float, start_time: float) -> List[Dict[str, Any]]:
        """
        Chunks narration text of a scene into subtitle entries of max 2 lines and max 80 chars.
        Distributes scene duration proportionally across text character lengths.
        """
        words = text.split()
        if not words:
            return []

        cues = []
        current_word_idx = 0
        while current_word_idx < len(words):
            lines = []
            for _ in range(settings.SUBTITLE_MAX_LINES):
                line = ""
                while current_word_idx < len(words):
                    word = words[current_word_idx]
                    candidate = (line + " " + word).strip()
                    if len(candidate) <= settings.SUBTITLE_CHARS_PER_LINE:
                        line = candidate
                        current_word_idx += 1
                    else:
                        break
                if line:
                    lines.append(line)
                else:
                    break

            if not lines:
                break

            cue_text = "\n".join(lines)

            cues.append({
                "text": cue_text,
                "char_length": len(cue_text.replace('\n', ' '))
            })

        # Distribute timing proportionally
        total_chars = sum(c["char_length"] for c in cues)
        curr_time = start_time
        for c in cues:
            fraction = c["char_length"] / total_chars if total_chars > 0 else 1.0 / len(cues)
            cue_dur = duration * fraction
            c["start"] = curr_time
            c["end"] = curr_time + cue_dur
            curr_time = c["end"]

        return cues

    def generate_subtitles(self, script_id: int, db: Session) -> SubtitleDocument:
        """
        Orchestrates subtitle file generation from database script and scene plans.
        """
        logger.info(f"Generating subtitles for script_id: {script_id}")

        # 1. Retrieve script and scene plans
        script = db.query(Script).filter(Script.id == script_id).first()
        if not script:
            raise SubtitleError(f"Script with id {script_id} not found.")

        scenes = db.query(ScenePlanModel).filter(ScenePlanModel.script_id == script_id).order_by(ScenePlanModel.scene_number).all()
        if not scenes:
            raise SubtitleError(f"No scene plans found for script_id: {script_id}. Cannot generate timing.")

        # 2. Segment and generate timed cues
        all_cues = []
        current_timeline_time = 0.0
        for scene in scenes:
            cues = self.chunk_narration_text(
                text=scene.narration_text,
                duration=scene.estimated_duration,
                start_time=current_timeline_time
            )
            all_cues.extend(cues)
            current_timeline_time += scene.estimated_duration

        # 3. Write SRT file
        srt_filename = f"video_{script_id}.srt"
        srt_path = os.path.join(self.output_dir, srt_filename)
        
        try:
            with open(srt_path, "w", encoding="utf-8") as f:
                for idx, cue in enumerate(all_cues, start=1):
                    start_str = self.format_srt_time(cue["start"])
                    end_str = self.format_srt_time(cue["end"])
                    f.write(f"{idx}\n")
                    f.write(f"{start_str} --> {end_str}\n")
                    f.write(f"{cue['text']}\n\n")
            logger.info(f"Subtitles written successfully to: {srt_path}")
        except Exception as e:
            logger.error(f"Failed to write SRT file: {e}")
            raise SubtitleError(f"File writing failed: {e}")

        # 4. Save metadata in DB (Idempotent update)
        try:
            rel_path = os.path.relpath(srt_path, os.getcwd()).replace('\\', '/')
            existing = db.query(SubtitleAssetModel).filter(SubtitleAssetModel.script_id == script_id).first()
            
            if existing:
                logger.info(f"Updating existing SubtitleAsset record for script {script_id}")
                existing.subtitle_path = rel_path
                existing.line_count = len(all_cues)
                existing.created_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(existing)
                asset_record = existing
            else:
                logger.info(f"Creating new SubtitleAsset record for script {script_id}")
                new_asset = SubtitleAssetModel(
                    script_id=script_id,
                    subtitle_path=rel_path,
                    line_count=len(all_cues)
                )
                db.add(new_asset)
                db.commit()
                db.refresh(new_asset)
                asset_record = new_asset

            # 5. Return document schema
            return SubtitleDocument(
                script_id=asset_record.script_id,
                subtitle_path=asset_record.subtitle_path,
                line_count=asset_record.line_count,
                created_at=asset_record.created_at
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Database error during subtitle registration: {e}")
            raise SubtitleError(f"Database sync failed: {e}")
