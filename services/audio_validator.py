import os
import wave
import logging
from typing import Dict, Any, Optional
from config.settings import settings

logger = logging.getLogger("audio_validator")

class AudioValidationError(Exception):
    """Exception raised when audio validation fails."""
    pass


class AudioValidator:
    """
    Validates synthesized WAV files for structure, size, duration, and integrity.
    """
    def __init__(self, min_duration: Optional[float] = None, max_duration: Optional[float] = None):
        self.min_duration = min_duration if min_duration is not None else settings.AUDIO_MIN_DURATION_SECONDS
        self.max_duration = max_duration if max_duration is not None else settings.AUDIO_MAX_DURATION_SECONDS

    def validate(self, file_path: str) -> Dict[str, Any]:
        """
        Validates the audio file at the given path.
        
        Args:
            file_path: The file path to the audio file.
            
        Returns:
            Dict: A dictionary containing validation details:
                  {"valid": True, "duration": float, "size_bytes": int}
                  
        Raises:
            AudioValidationError: If the file is invalid, empty, corrupt,
                                  or falls outside duration limits.
        """
        resolved_path = os.path.abspath(file_path)
        
        # 1. Check if file exists
        if not os.path.exists(resolved_path):
            raise AudioValidationError(f"Audio file does not exist at: {resolved_path}")
            
        if not os.path.isfile(resolved_path):
            raise AudioValidationError(f"Path is not a file: {resolved_path}")

        # 2. Check file size
        size_bytes = os.path.getsize(resolved_path)
        if size_bytes == 0:
            raise AudioValidationError(f"Audio file is empty (0 bytes) at: {resolved_path}")

        # 3. Validate WAV header and read duration
        try:
            with wave.open(resolved_path, 'rb') as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                
                if n_frames == 0 or frame_rate == 0:
                    raise AudioValidationError("WAV file has zero frames or invalid frame rate.")
                    
                duration = n_frames / float(frame_rate)
                
                logger.info(
                    f"WAV validation successful. Path: {resolved_path}, "
                    f"Channels: {channels}, Sample Width: {sample_width} bytes, "
                    f"Frame Rate: {frame_rate}Hz, Duration: {duration:.2f}s, Size: {size_bytes} bytes"
                )
        except wave.Error as e:
            logger.error(f"Failed to parse WAV headers for {resolved_path}: {e}")
            raise AudioValidationError(f"Invalid or corrupted WAV file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while reading audio file {resolved_path}: {e}")
            raise AudioValidationError(f"Failed to read audio file: {e}")

        # 4. Check duration boundaries
        if duration < self.min_duration:
            raise AudioValidationError(
                f"Audio duration ({duration:.2f}s) is shorter than minimum limit ({self.min_duration}s)."
            )
            
        if duration > self.max_duration:
            raise AudioValidationError(
                f"Audio duration ({duration:.2f}s) exceeds maximum limit ({self.max_duration}s)."
            )

        return {
            "valid": True,
            "duration": duration,
            "size_bytes": size_bytes
        }
