import os
import json
import subprocess
import logging
from typing import List, Dict, Any, Optional
from config.settings import settings

logger = logging.getLogger("ffmpeg_service")

class FFmpegError(Exception):
    """Base exception for FFmpeg service operations."""
    pass

class FFmpegNotFound(FFmpegError):
    """Raised when FFmpeg/FFprobe binaries are missing."""
    pass

class VideoRenderError(FFmpegError):
    """Raised when video rendering/slideshow generation fails."""
    pass

class SubtitleRenderError(FFmpegError):
    """Raised when subtitle burning fails."""
    pass


class FFmpegService:
    """
    Wrapper for FFmpeg and FFprobe executions to build and inspect video assets locally.
    """
    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = os.path.abspath(ffmpeg_path or settings.FFMPEG_PATH)
        # Use settings.FFPROBE_PATH directly or fall back to looking next to ffmpeg
        if settings.FFPROBE_PATH:
            self.ffprobe_path = os.path.abspath(settings.FFPROBE_PATH)
        else:
            bin_dir = os.path.dirname(self.ffmpeg_path)
            self.ffprobe_path = os.path.join(bin_dir, "ffprobe.exe" if os.name == "nt" else "ffprobe")

    def health_check(self) -> bool:
        """
        Verifies that both ffmpeg and ffprobe exist and are executable.
        """
        ffmpeg_exists = os.path.isfile(self.ffmpeg_path)
        ffprobe_exists = os.path.isfile(self.ffprobe_path)
        
        if not ffmpeg_exists:
            logger.warning(f"FFmpeg executable not found at: {self.ffmpeg_path}")
        if not ffprobe_exists:
            logger.warning(f"FFprobe executable not found at: {self.ffprobe_path}")
            
        return ffmpeg_exists and ffprobe_exists

    def create_slideshow(
        self,
        images: List[str],
        durations: List[float],
        audio_path: str,
        output_path: str
    ) -> str:
        """
        Creates a slideshow MP4 video from a list of images and durations, synced with narration audio.
        Uses FFmpeg's concat demuxer.
        """
        if not self.health_check():
            raise FFmpegNotFound("FFmpeg/FFprobe binaries not found. Setup FFmpeg first.")

        if len(images) != len(durations) or not images:
            raise VideoRenderError("Mismatch or empty list in images and durations.")

        audio_abs = os.path.abspath(audio_path)
        output_abs = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_abs), exist_ok=True)

        # Create the concat configuration file
        concat_txt_path = os.path.join(os.path.dirname(output_abs), f"concat_{os.getpid()}.txt")
        try:
            with open(concat_txt_path, "w", encoding="utf-8") as f:
                for img, dur in zip(images, durations):
                    img_clean = os.path.abspath(img).replace('\\', '/')
                    f.write(f"file '{img_clean}'\n")
                    f.write(f"duration {dur}\n")
                # FFmpeg concat demuxer requires repeating the last file
                last_img_clean = os.path.abspath(images[-1]).replace('\\', '/')
                f.write(f"file '{last_img_clean}'\n")

            # Run FFmpeg command:
            # -shortest limits output video length to the audio length
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_txt_path,
                "-i", audio_abs,
                "-c:v", settings.FFMPEG_VIDEO_CODEC,
                "-pix_fmt", settings.FFMPEG_PIXEL_FORMAT,
                "-r", str(settings.FFMPEG_FRAME_RATE),
                "-c:a", settings.FFMPEG_AUDIO_CODEC,
                "-shortest",
                output_abs
            ]

            logger.info(f"Executing FFmpeg slideshow command: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                logger.error(f"FFmpeg slideshow render failed (exit code {process.returncode}): {stderr}")
                raise VideoRenderError(f"FFmpeg slideshow creation failed: {stderr.strip()}")

            if not os.path.exists(output_abs) or os.path.getsize(output_abs) == 0:
                raise VideoRenderError("FFmpeg ran successfully but did not produce a video file.")

            logger.info(f"Slideshow created successfully: {output_abs}")
            return output_abs

        except Exception as e:
            if isinstance(e, FFmpegError):
                raise
            logger.error(f"Error during FFmpeg slideshow generation: {e}")
            raise VideoRenderError(f"Slideshow render failed: {e}")
        finally:
            if os.path.exists(concat_txt_path):
                try:
                    os.unlink(concat_txt_path)
                except Exception:
                    pass

    def add_subtitles(self, video_path: str, subtitle_path: str, output_path: str) -> str:
        """
        Burns subtitles (SRT) directly into the video stream using FFmpeg's subtitle filter.
        """
        if not self.health_check():
            raise FFmpegNotFound("FFmpeg/FFprobe binaries not found. Setup FFmpeg first.")

        video_abs = os.path.abspath(video_path)
        sub_abs = os.path.abspath(subtitle_path)
        output_abs = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_abs), exist_ok=True)

        # Escape paths for FFmpeg filter on Windows
        sub_path_clean = sub_abs.replace('\\', '/')
        if ':' in sub_path_clean:
            sub_path_clean = sub_path_clean.replace(':', '\\:')
        
        # Build force_style options from settings
        force_style_parts = []
        if settings.SUBTITLE_FONT_NAME:
            force_style_parts.append(f"FontName={settings.SUBTITLE_FONT_NAME}")
        if settings.SUBTITLE_FONT_SIZE:
            force_style_parts.append(f"FontSize={settings.SUBTITLE_FONT_SIZE}")
        if settings.SUBTITLE_PRIMARY_COLOR:
            force_style_parts.append(f"PrimaryColour={settings.SUBTITLE_PRIMARY_COLOR}")
        if settings.SUBTITLE_ALIGNMENT is not None:
            force_style_parts.append(f"Alignment={settings.SUBTITLE_ALIGNMENT}")

        force_style_str = ",".join(force_style_parts)
        if force_style_str:
            vf_filter = f"subtitles='{sub_path_clean}':force_style='{force_style_str}'"
        else:
            vf_filter = f"subtitles='{sub_path_clean}'"

        # Burn subtitles, copy audio codec
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", video_abs,
            "-vf", vf_filter,
            "-c:v", settings.FFMPEG_VIDEO_CODEC,  # Re-encode video stream to burn subtitles
            "-pix_fmt", settings.FFMPEG_PIXEL_FORMAT,
            "-c:a", "copy",     # Direct copy audio
            output_abs
        ]

        logger.info(f"Executing FFmpeg subtitle burning command: {' '.join(cmd)}")
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                logger.error(f"FFmpeg subtitle burning failed (exit code {process.returncode}): {stderr}")
                raise SubtitleRenderError(f"FFmpeg subtitle burn failed: {stderr.strip()}")

            if not os.path.exists(output_abs) or os.path.getsize(output_abs) == 0:
                raise SubtitleRenderError("FFmpeg subtitle burn completed but output file is missing/empty.")

            logger.info(f"Subtitles burned successfully: {output_abs}")
            return output_abs
        except Exception as e:
            if isinstance(e, FFmpegError):
                raise
            logger.error(f"Error burning subtitles into video: {e}")
            raise SubtitleRenderError(f"Subtitle burn failed: {e}")

    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        Uses FFprobe to query metadata about the video stream.
        Returns:
            Dict: {"duration": float, "resolution": str, "frame_rate": float, "codec": str, "has_audio": bool}
        """
        if not self.health_check():
            raise FFmpegNotFound("FFmpeg/FFprobe binaries not found. Setup FFmpeg first.")

        video_abs = os.path.abspath(video_path)
        if not os.path.exists(video_abs):
            raise FFmpegError(f"Video file does not exist for metadata check: {video_abs}")

        cmd = [
            self.ffprobe_path,
            "-v", "error",
            "-show_entries", "stream=width,height,r_frame_rate,codec_name,codec_type",
            "-show_entries", "format=duration",
            "-of", "json",
            video_abs
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                logger.error(f"FFprobe metadata query failed (exit code {process.returncode}): {stderr}")
                raise FFmpegError(f"FFprobe failed: {stderr.strip()}")

            metadata = json.loads(stdout)
            
            # Parse streams
            streams = metadata.get("streams", [])
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
            
            if not video_stream:
                raise FFmpegError(f"No valid video stream found in {video_path}")

            # Duration
            duration_str = metadata.get("format", {}).get("duration")
            if not duration_str and video_stream:
                duration_str = video_stream.get("duration")
            
            duration = float(duration_str) if duration_str else 0.0

            # Resolution
            width = video_stream.get("width", 0)
            height = video_stream.get("height", 0)
            resolution = f"{width}x{height}" if width and height else "unknown"

            # Frame rate
            fps_str = video_stream.get("r_frame_rate", "30/1")
            try:
                num, den = map(int, fps_str.split("/"))
                frame_rate = num / den if den != 0 else 30.0
            except Exception:
                frame_rate = 30.0

            codec = video_stream.get("codec_name", "unknown")
            has_audio = audio_stream is not None

            return {
                "duration": duration,
                "resolution": resolution,
                "frame_rate": frame_rate,
                "codec": codec,
                "has_audio": has_audio
            }

        except Exception as e:
            if isinstance(e, FFmpegError):
                raise
            logger.error(f"Failed to query video info for {video_path}: {e}")
            raise FFmpegError(f"Failed to parse video metadata: {e}")
