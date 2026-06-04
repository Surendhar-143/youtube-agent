import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from database.postgres import SessionLocal
from database.models import Topic, Script, AudioAsset, SubtitleAsset, VideoAsset as VideoAssetModel
from workflows.video_pipeline import run_video_pipeline
from schemas.subtitle_document import SubtitleDocument
from schemas.video_document import VideoDocument

class TestVideoPipeline(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        # Clean existing records
        self.db.query(VideoAssetModel).delete()
        self.db.query(SubtitleAsset).delete()
        self.db.query(AudioAsset).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()

        # Add records
        self.topic = Topic(topic="Pipeline testing", score=80.0, status="completed")
        self.db.add(self.topic)
        self.db.commit()

        self.script = Script(title="Script Title", script="Script Content text", topic_id=self.topic.id)
        self.db.add(self.script)
        self.db.commit()

        self.audio = AudioAsset(
            script_id=self.script.id,
            audio_path="generated/audio/audio_1.wav",
            duration_seconds=120.0,
            voice_model="lessac"
        )
        self.db.add(self.audio)
        self.db.commit()
        self.db.refresh(self.audio)

    def tearDown(self):
        self.db.query(VideoAssetModel).delete()
        self.db.query(SubtitleAsset).delete()
        self.db.query(AudioAsset).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        self.db.close()

    @patch("services.subtitle_service.SubtitleService.generate_subtitles")
    @patch("agents.video_agent.VideoAgent.assemble_video")
    def test_run_video_pipeline_success(self, mock_assemble, mock_generate):
        # Configure subtitle service mock
        mock_generate.return_value = SubtitleDocument(
            script_id=self.script.id,
            subtitle_path="generated/subtitles/video_1.srt",
            line_count=45,
            created_at=datetime.now(timezone.utc)
        )

        # Configure video agent mock
        mock_assemble.return_value = VideoDocument(
            id=999,
            script_id=self.script.id,
            audio_id=self.audio.id,
            video_path="generated/videos/video_1.mp4",
            duration_seconds=120.0,
            resolution="1080x1920",
            created_at=datetime.now(timezone.utc)
        )

        # Run pipeline
        res = run_video_pipeline(script_id=self.script.id, db=self.db)

        # Assertions
        self.assertEqual(res["script_id"], self.script.id)
        self.assertEqual(res["audio_id"], self.audio.id)
        self.assertEqual(res["video_id"], 999)
        self.assertEqual(res["video_path"], "generated/videos/video_1.mp4")

        # Verify calls
        mock_generate.assert_called_once_with(script_id=self.script.id, db=self.db)
        mock_assemble.assert_called_once_with(script_id=self.script.id, db=self.db)

    def test_run_video_pipeline_missing_script_raises(self):
        with self.assertRaises(ValueError):
            run_video_pipeline(script_id=99999, db=self.db)

if __name__ == "__main__":
    unittest.main()
