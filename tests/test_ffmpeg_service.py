import os
import json
import unittest
from unittest.mock import MagicMock, patch
from services.ffmpeg_service import FFmpegService, FFmpegNotFound, VideoRenderError, SubtitleRenderError, FFmpegError

class TestFFmpegService(unittest.TestCase):
    def setUp(self):
        self.ffmpeg_path = ".ffmpeg/ffmpeg.exe"
        self.service = FFmpegService(ffmpeg_path=self.ffmpeg_path)

    @patch("os.path.isfile")
    def test_health_check_success(self, mock_isfile):
        # Mock exists both ffmpeg and ffprobe
        mock_isfile.return_value = True
        self.assertTrue(self.service.health_check())

    @patch("os.path.isfile")
    def test_health_check_fail(self, mock_isfile):
        mock_isfile.side_effect = lambda path: "ffprobe" in path
        self.assertFalse(self.service.health_check())

    @patch("services.ffmpeg_service.FFmpegService.health_check")
    @patch("subprocess.Popen")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    def test_create_slideshow_success(self, mock_getsize, mock_exists, mock_popen, mock_health):
        mock_health.return_value = True
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024

        mock_process = MagicMock()
        mock_process.communicate.return_value = ("stdout", "stderr")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        images = ["img1.png", "img2.png"]
        durations = [5.0, 3.5]
        
        # Patch open to avoid writing concat file on disk during unit testing
        with patch("builtins.open", unittest.mock.mock_open()):
            res = self.service.create_slideshow(images, durations, "audio.wav", "output.mp4")
            self.assertEqual(res, os.path.abspath("output.mp4"))

    @patch("services.ffmpeg_service.FFmpegService.health_check")
    @patch("subprocess.Popen")
    def test_create_slideshow_render_failure(self, mock_popen, mock_health):
        mock_health.return_value = True
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("stdout", "render error details")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        with patch("builtins.open", unittest.mock.mock_open()):
            with self.assertRaises(VideoRenderError):
                self.service.create_slideshow(["i.png"], [5.0], "audio.wav", "out.mp4")

    @patch("services.ffmpeg_service.FFmpegService.health_check")
    @patch("subprocess.Popen")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    def test_add_subtitles_success(self, mock_getsize, mock_exists, mock_popen, mock_health):
        mock_health.return_value = True
        mock_exists.return_value = True
        mock_getsize.return_value = 2048 * 1024

        mock_process = MagicMock()
        mock_process.communicate.return_value = ("stdout", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        res = self.service.add_subtitles("in.mp4", "sub.srt", "out.mp4")
        self.assertEqual(res, os.path.abspath("out.mp4"))

    @patch("services.ffmpeg_service.FFmpegService.health_check")
    @patch("subprocess.Popen")
    def test_add_subtitles_failure(self, mock_popen, mock_health):
        mock_health.return_value = True
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("stdout", "burning error details")
        mock_process.returncode = -1
        mock_popen.return_value = mock_process

        with self.assertRaises(SubtitleRenderError):
            self.service.add_subtitles("in.mp4", "sub.srt", "out.mp4")

    @patch("services.ffmpeg_service.FFmpegService.health_check")
    @patch("subprocess.Popen")
    @patch("os.path.exists")
    def test_get_video_info_success(self, mock_exists, mock_popen, mock_health):
        mock_health.return_value = True
        mock_exists.return_value = True

        mock_output = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1080,
                    "height": 1920,
                    "r_frame_rate": "30/1"
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac"
                }
            ],
            "format": {
                "duration": "123.45"
            }
        }

        mock_process = MagicMock()
        mock_process.communicate.return_value = (json.dumps(mock_output), "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        info = self.service.get_video_info("video.mp4")
        self.assertEqual(info["duration"], 123.45)
        self.assertEqual(info["resolution"], "1080x1920")
        self.assertEqual(info["frame_rate"], 30.0)
        self.assertEqual(info["codec"], "h264")
        self.assertTrue(info["has_audio"])

if __name__ == "__main__":
    unittest.main()
