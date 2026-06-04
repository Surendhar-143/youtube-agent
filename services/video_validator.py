import os
import logging
from typing import Dict, Any, Optional
from services.ffmpeg_service import FFmpegService, FFmpegError

logger = logging.getLogger("video_validator")

class VideoValidationError(Exception):
    """Base exception for VideoValidator checks."""
    pass

class MissingAudioTrackError(VideoValidationError):
    """Raised when video is missing an audio stream."""
    pass

class CorruptVideoError(VideoValidationError):
    """Raised when video file headers/metadata cannot be read."""
    pass


class VideoValidator:
    """
    Validates rendered MP4 files for existence, duration, resolution, size,
    playability, and presence of audio tracks.
    """
    def __init__(self, ffmpeg_service: Optional[FFmpegService] = None):
        self.ffmpeg = ffmpeg_service or FFmpegService()

    def validate_video(self, video_path: str, expected_resolution: str = "1080x1920") -> Dict[str, Any]:
        """
        Validates the properties of the rendered video file.
        
        Args:
            video_path: Relative or absolute path to the MP4 file.
            expected_resolution: Expected resolution string (e.g. '1920x1080').
            
        Returns:
            Dict: {"valid": True, "duration": float, "resolution": str, "size_mb": float}
            
        Raises:
            VideoValidationError: If validation rules fail.
            MissingAudioTrackError: If audio track is missing.
            CorruptVideoError: If file is corrupted or unreadable.
        """
        resolved_path = os.path.abspath(video_path)
        logger.info(f"Validating video file: {resolved_path}")

        # 1. Check file existence
        if not os.path.exists(resolved_path):
            raise VideoValidationError(f"Video file does not exist at: {resolved_path}")
        if not os.path.isfile(resolved_path):
            raise VideoValidationError(f"Video path is not a file: {resolved_path}")

        # 2. Check file size
        size_bytes = os.path.getsize(resolved_path)
        if size_bytes == 0:
            raise VideoValidationError(f"Video file is empty (0 bytes): {resolved_path}")

        size_mb = size_bytes / (1024 * 1024)

        # 3. Probe video metadata
        try:
            info = self.ffmpeg.get_video_info(resolved_path)
        except FFmpegError as e:
            logger.error(f"FFprobe header analysis failed: {e}")
            raise CorruptVideoError(f"Video file header is corrupt or unreadable: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while reading video headers: {e}")
            raise CorruptVideoError(f"Failed to read video format info: {e}")

        duration = info.get("duration", 0.0)
        resolution = info.get("resolution", "unknown")
        has_audio = info.get("has_audio", False)
        codec = info.get("codec", "unknown")

        logger.info(
            f"Probed Video Specs -> Duration: {duration:.2f}s, Resolution: {resolution}, "
            f"Codec: {codec}, Has Audio: {has_audio}, Size: {size_mb:.2f} MB"
        )

        # 4. Apply validation assertions
        if duration <= 0:
            raise VideoValidationError(f"Video duration is invalid: {duration}s")

        if not has_audio:
            raise MissingAudioTrackError("Rendered video is missing an audio track.")

        if resolution != expected_resolution:
            raise VideoValidationError(
                f"Video resolution '{resolution}' does not match expected target '{expected_resolution}'."
            )

        return {
            "valid": True,
            "duration": duration,
            "resolution": resolution,
            "size_mb": size_mb
        }
