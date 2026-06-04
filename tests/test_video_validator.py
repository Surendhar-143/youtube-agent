import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from services.video_validator import VideoValidator, VideoValidationError, MissingAudioTrackError, CorruptVideoError
from services.ffmpeg_service import FFmpegError

class TestVideoValidator(unittest.TestCase):
    def setUp(self):
        self.mock_ffmpeg = MagicMock()
        self.validator = VideoValidator(ffmpeg_service=self.mock_ffmpeg)
        self.temp_files = []

    def tearDown(self):
        for f in self.temp_files:
            if os.path.exists(f):
                try:
                    os.unlink(f)
                except Exception:
                    pass

    def _create_temp_file(self, content=b"fake video data") -> str:
        fd, path = tempfile.mkstemp(suffix=".mp4")
        if content:
            with os.fdopen(fd, 'wb') as f:
                f.write(content)
        else:
            os.close(fd)
        self.temp_files.append(path)
        return path

    def test_file_not_found(self):
        with self.assertRaises(VideoValidationError) as ctx:
            self.validator.validate_video("non_existent_video_file.mp4")
        self.assertIn("does not exist", str(ctx.exception))

    def test_empty_file(self):
        path = self._create_temp_file(content=b"")
        with self.assertRaises(VideoValidationError) as ctx:
            self.validator.validate_video(path)
        self.assertIn("is empty", str(ctx.exception))

    def test_corrupt_video_headers(self):
        path = self._create_temp_file()
        # Mock FFmpeg get_video_info to raise FFmpegError (simulate header read error)
        self.mock_ffmpeg.get_video_info.side_effect = FFmpegError("Corrupt headers")

        with self.assertRaises(CorruptVideoError) as ctx:
            self.validator.validate_video(path)
        self.assertIn("corrupt or unreadable", str(ctx.exception))

    def test_missing_audio_track(self):
        path = self._create_temp_file()
        # Prober output has no audio stream
        self.mock_ffmpeg.get_video_info.return_value = {
            "duration": 60.0,
            "resolution": "1080x1920",
            "frame_rate": 30.0,
            "codec": "h264",
            "has_audio": False
        }

        with self.assertRaises(MissingAudioTrackError) as ctx:
            self.validator.validate_video(path)
        self.assertIn("missing an audio track", str(ctx.exception))

    def test_invalid_resolution(self):
        path = self._create_temp_file()
        # Prober output has incorrect resolution (e.g. 1280x720)
        self.mock_ffmpeg.get_video_info.return_value = {
            "duration": 60.0,
            "resolution": "1280x720",
            "frame_rate": 30.0,
            "codec": "h264",
            "has_audio": True
        }

        with self.assertRaises(VideoValidationError) as ctx:
            self.validator.validate_video(path)
        self.assertIn("resolution '1280x720' does not match", str(ctx.exception))

    def test_invalid_duration(self):
        path = self._create_temp_file()
        self.mock_ffmpeg.get_video_info.return_value = {
            "duration": 0.0,
            "resolution": "1080x1920",
            "frame_rate": 30.0,
            "codec": "h264",
            "has_audio": True
        }

        with self.assertRaises(VideoValidationError) as ctx:
            self.validator.validate_video(path)
        self.assertIn("duration is invalid", str(ctx.exception))

    def test_validation_success(self):
        path = self._create_temp_file()
        self.mock_ffmpeg.get_video_info.return_value = {
            "duration": 45.0,
            "resolution": "1080x1920",
            "frame_rate": 30.0,
            "codec": "h264",
            "has_audio": True
        }

        res = self.validator.validate_video(path)
        self.assertTrue(res["valid"])
        self.assertEqual(res["duration"], 45.0)
        self.assertEqual(res["resolution"], "1080x1920")
        self.assertGreater(res["size_mb"], 0.0)

if __name__ == "__main__":
    unittest.main()
