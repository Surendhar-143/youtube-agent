import os
import unittest
from unittest.mock import MagicMock, patch
from services.piper_service import (
    PiperService,
    PiperExecutableNotFoundError,
    PiperModelNotFoundError,
    PiperGenerationError
)

class TestPiperService(unittest.TestCase):
    def setUp(self):
        # Default mock paths
        self.exe_path = ".piper/piper/piper.exe"
        self.model_path = ".piper/en_US-lessac-medium.onnx"
        self.service = PiperService(executable_path=self.exe_path, model_path=self.model_path)

    @patch("os.path.isfile")
    def test_health_check_both_exist(self, mock_isfile):
        # Set both executable and model to exist
        mock_isfile.side_effect = lambda path: True
        self.assertTrue(self.service.health_check())

    @patch("os.path.isfile")
    def test_health_check_executable_missing(self, mock_isfile):
        # Executable does not exist, model exists
        mock_isfile.side_effect = lambda path: path != os.path.abspath(self.exe_path)
        self.assertFalse(self.service.health_check())

    @patch("os.path.isfile")
    def test_health_check_model_missing(self, mock_isfile):
        # Executable exists, model does not exist
        mock_isfile.side_effect = lambda path: path != os.path.abspath(self.model_path)
        self.assertFalse(self.service.health_check())

    @patch("os.path.isfile")
    def test_synthesize_executable_missing_raises(self, mock_isfile):
        mock_isfile.side_effect = lambda path: path != os.path.abspath(self.exe_path)
        with self.assertRaises(PiperExecutableNotFoundError):
            self.service.synthesize("Hello", "out.wav")

    @patch("os.path.isfile")
    def test_synthesize_model_missing_raises(self, mock_isfile):
        # Executable exists, model missing
        mock_isfile.side_effect = lambda path: path != os.path.abspath(self.model_path)
        with self.assertRaises(PiperModelNotFoundError):
            self.service.synthesize("Hello", "out.wav")

    @patch("os.path.isfile")
    @patch("subprocess.Popen")
    def test_synthesize_subprocess_failure(self, mock_popen, mock_isfile):
        # Files exist
        mock_isfile.return_value = True
        
        # Mock Popen instance to simulate non-zero exit code
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("stdout", "some synthesis error")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        with self.assertRaises(PiperGenerationError) as ctx:
            self.service.synthesize("Hello", "out.wav")
        self.assertIn("Piper process failed", str(ctx.exception))

    @patch("os.path.isfile")
    @patch("subprocess.Popen")
    @patch("services.piper_service.os.path.exists")
    @patch("services.piper_service.os.path.getsize")
    def test_synthesize_output_missing_or_empty(self, mock_getsize, mock_exists, mock_popen, mock_isfile):
        # Files exist
        mock_isfile.return_value = True
        
        # Mock Popen instance to simulate success exit code but empty file
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("success", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        mock_exists.return_value = True
        mock_getsize.return_value = 0
            
        with self.assertRaises(PiperGenerationError) as ctx:
            self.service.synthesize("Hello", "out.wav")
        self.assertIn("output file is missing or empty", str(ctx.exception))

    def test_get_voice_info(self):
        info = self.service.get_voice_info()
        self.assertEqual(info["voice_name"], "lessac")
        self.assertEqual(info["language"], "en_US")
        self.assertEqual(info["quality"], "medium")

if __name__ == "__main__":
    unittest.main()
