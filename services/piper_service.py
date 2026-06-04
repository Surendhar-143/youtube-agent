import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict
from config.settings import settings

logger = logging.getLogger("piper_service")

class PiperError(Exception):
    """Base exception for Piper service."""
    pass

class PiperExecutableNotFoundError(PiperError):
    """Raised when the piper.exe binary is not found."""
    pass

class PiperModelNotFoundError(PiperError):
    """Raised when the ONNX voice model is not found."""
    pass

class PiperGenerationError(PiperError):
    """Raised when audio synthesis fails."""
    pass


class PiperService:
    """
    Service layer wrapper for local Piper Text-To-Speech (TTS) synthesis.
    """
    def __init__(
        self,
        executable_path: Optional[str] = None,
        model_path: Optional[str] = None
    ):
        # Resolve paths relative to workspace root if they are relative
        self.executable_path = os.path.abspath(executable_path or settings.PIPER_EXECUTABLE)
        self.model_path = os.path.abspath(model_path or settings.PIPER_MODEL)

    def health_check(self) -> bool:
        """
        Verifies that both the piper.exe binary and the ONNX voice model exist.
        """
        exe_exists = os.path.isfile(self.executable_path)
        model_exists = os.path.isfile(self.model_path)
        
        if not exe_exists:
            logger.warning(f"Piper executable not found at: {self.executable_path}")
        if not model_exists:
            logger.warning(f"Piper model not found at: {self.model_path}")
            
        return exe_exists and model_exists

    def synthesize(self, text: str, output_path: str) -> Path:
        """
        Executes the standalone piper.exe binary to synthesize text into a WAV file.
        
        Args:
            text: The cleaned narration text to synthesize.
            output_path: The file path where the output WAV should be written.
            
        Returns:
            Path: The resolved output file Path on success.
            
        Raises:
            PiperExecutableNotFoundError: If the piper binary does not exist.
            PiperModelNotFoundError: If the model file does not exist.
            PiperGenerationError: If process execution fails or outputs nothing.
        """
        if not os.path.isfile(self.executable_path):
            raise PiperExecutableNotFoundError(
                f"Piper executable not found at: {self.executable_path}. Please run setup_piper.py."
            )
        if not os.path.isfile(self.model_path):
            raise PiperModelNotFoundError(
                f"ONNX voice model not found at: {self.model_path}. Please run setup_piper.py."
            )

        # Ensure the destination directory exists
        out_path_obj = Path(os.path.abspath(output_path))
        out_path_obj.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.executable_path,
            "--model", self.model_path,
            "--output_file", str(out_path_obj)
        ]
        if settings.PIPER_SPEAKER_ID is not None and str(settings.PIPER_SPEAKER_ID).strip() != "":
            cmd.extend(["--speaker", str(settings.PIPER_SPEAKER_ID)])

        logger.info(f"Running Piper speech synthesis. Command: {' '.join(cmd)}")
        try:
            # Run the process and write the text to stdin
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8"
            )
            
            stdout, stderr = process.communicate(input=text)
            
            if process.returncode != 0:
                logger.error(f"Piper process failed with exit code {process.returncode}. Stderr: {stderr}")
                raise PiperGenerationError(
                    f"Piper process failed (exit code {process.returncode}): {stderr.strip()}"
                )
                
            # Verify file was generated and has non-zero size
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                logger.error("Piper run finished but output file is missing or empty.")
                raise PiperGenerationError("Piper speech synthesis failed: output file is missing or empty.")
                
            logger.info(f"Piper synthesis completed successfully. File saved at: {out_path_obj}")
            return out_path_obj
            
        except Exception as e:
            if isinstance(e, PiperError):
                raise
            logger.error(f"Subprocess execution error during Piper synthesis: {e}")
            raise PiperGenerationError(f"Piper process execution failed: {e}")

    def get_voice_info(self) -> Dict[str, str]:
        """
        Returns basic metadata about the loaded voice model.
        """
        model_filename = os.path.basename(self.model_path)
        # Parse language/voice name from model filename if standard name is used
        # e.g., en_US-lessac-medium.onnx
        parts = model_filename.replace(".onnx", "").split("-")
        lang = parts[0] if len(parts) > 0 else "unknown"
        name = parts[1] if len(parts) > 1 else "unknown"
        quality = parts[2] if len(parts) > 2 else "unknown"
        
        return {
            "model_path": self.model_path,
            "voice_name": name,
            "language": lang,
            "quality": quality
        }
