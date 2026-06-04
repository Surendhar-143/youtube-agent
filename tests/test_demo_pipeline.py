import unittest
import os
import json
from unittest.mock import patch, MagicMock
from scripts.demo_run import run_demo


# Plain stub classes so isinstance(obj.script, str) works correctly
class _FakeScript:
    def __init__(self, text):
        self.script = text


class _FakeAudio:
    def __init__(self, duration):
        self.duration_seconds = duration


class TestDemoPipeline(unittest.TestCase):
    def setUp(self):
        # Ensure report file does not exist initially
        self.report_path = "generated/reports/demo_report.json"
        if os.path.exists(self.report_path):
            try:
                os.remove(self.report_path)
            except Exception:
                pass

    def tearDown(self):
        if os.path.exists(self.report_path):
            try:
                os.remove(self.report_path)
            except Exception:
                pass

    @patch('scripts.demo_run.run_content_pipeline')
    @patch('scripts.demo_run.run_voice_pipeline')
    @patch('scripts.demo_run.run_visual_pipeline')
    @patch('scripts.demo_run.run_video_pipeline')
    @patch('scripts.demo_run.SessionLocal')        # patch the local reference in demo_run
    def test_demo_run_success(self, mock_session, mock_video, mock_visual, mock_voice, mock_content):
        # Configure pipeline return values
        mock_content.return_value = {"topic_id": 1, "script_id": 2, "seo_id": 3}
        mock_voice.return_value = {"audio_id": 4}
        mock_visual.return_value = {"scene_count": 5, "asset_count": 6}
        mock_video.return_value = {"video_id": 7, "video_path": "path/to/video.mp4"}

        # Create real-attribute stub objects so isinstance checks pass
        fake_script = _FakeScript("This is a test script containing eight words.")
        fake_audio = _FakeAudio(420.0)

        # Set up the DB session mock
        db_mock = MagicMock()
        mock_session.return_value = db_mock

        # Each call to .query(...).filter(...).first() returns the next stub in sequence
        db_mock.query.return_value.filter.return_value.first.side_effect = [
            fake_script,
            fake_audio,
        ]

        # Run demo
        report = run_demo(niche="AI Automation")

        # Assert report contents
        self.assertTrue(report["success"])
        self.assertEqual(report["topic_id"], 1)
        self.assertEqual(report["script_id"], 2)
        self.assertEqual(report["seo_id"], 3)
        self.assertEqual(report["audio_id"], 4)
        self.assertEqual(report["scene_count"], 5)
        self.assertEqual(report["asset_count"], 6)
        self.assertEqual(report["script_words"], 8)
        self.assertEqual(report["audio_duration"], 420)
        self.assertEqual(report["video_id"], 7)
        self.assertEqual(report["video_path"], "path/to/video.mp4")

        # Verify JSON report file is written
        self.assertTrue(os.path.exists(self.report_path))
        with open(self.report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["video_id"], 7)

    @patch('scripts.demo_run.run_content_pipeline')
    @patch('scripts.demo_run.SessionLocal')
    def test_demo_run_failure(self, mock_session, mock_content):
        # Configure content pipeline to raise
        mock_content.side_effect = RuntimeError("Ollama server down")

        db_mock = MagicMock()
        mock_session.return_value = db_mock

        # Run demo
        report = run_demo(niche="AI Automation")

        # Assert report shows failure
        self.assertFalse(report["success"])
        self.assertIn("Ollama server down", report["error"])

        # Verify file is written even on failure
        self.assertTrue(os.path.exists(self.report_path))
        with open(self.report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertFalse(data["success"])


if __name__ == "__main__":
    unittest.main()
