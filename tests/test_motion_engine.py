import os
import unittest
from unittest.mock import patch, MagicMock
from services.motion_engine import MotionEngine

class TestMotionEngine(unittest.TestCase):
    @patch("subprocess.Popen")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    def test_apply_effect_command_generation(self, mock_getsize, mock_exists, mock_popen):
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("stdout", "stderr")
        mock_popen.return_value = mock_process

        engine = MotionEngine()
        res_path = engine.apply_effect(
            image_path="dummy_image.jpg",
            duration=5.0,
            effect_name="zoom_in",
            output_path="dummy_output.mp4"
        )
        
        self.assertEqual(res_path, os.path.abspath("dummy_output.mp4"))
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        self.assertIn("-vf", args)
        self.assertIn("zoompan", args[args.index("-vf") + 1])

if __name__ == "__main__":
    unittest.main()
