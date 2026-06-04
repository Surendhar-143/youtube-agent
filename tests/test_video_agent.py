import os
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from database.postgres import SessionLocal
from database.models import Topic, Script, AudioAsset, SubtitleAsset, ScenePlan, VisualAsset, VideoAsset as VideoAssetModel
from agents.video_agent import VideoAgent, VideoAgentError
from schemas.video_document import VideoDocument

class TestVideoAgent(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        # Clean existing records
        self.db.query(VideoAssetModel).delete()
        self.db.query(VisualAsset).delete()
        self.db.query(ScenePlan).delete()
        self.db.query(SubtitleAsset).delete()
        self.db.query(AudioAsset).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()

        # Create basic records
        self.topic = Topic(topic="Video assembly testing", score=90.0, status="completed")
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
        
        self.subtitle = SubtitleAsset(
            script_id=self.script.id,
            subtitle_path="generated/subtitles/video_1.srt",
            line_count=45
        )
        self.db.add(self.subtitle)
        self.db.commit()

        # Add visual scenes
        self.scene = ScenePlan(
            script_id=self.script.id,
            scene_number=1,
            title="Intro visual",
            description="Details visual",
            narration_text="Script content...",
            estimated_duration=120.0,
            visual_type="BROLL",
            keywords=["dev"]
        )
        self.db.add(self.scene)
        self.db.commit()
        self.db.refresh(self.scene)

        # Planned visual asset requirement
        self.visual_asset = VisualAsset(
            scene_id=self.scene.id,
            asset_type="VIDEO",
            search_keywords=["dev"],
            priority=1,
            status="PLANNED"
        )
        self.db.add(self.visual_asset)
        self.db.commit()

        # Mock dependencies
        self.mock_ffmpeg = MagicMock()
        self.mock_validator = MagicMock()
        self.mock_storage = MagicMock()
        
        # Configure storage mock
        self.mock_storage.base_dir = "generated/videos"
        self.mock_storage.get_video_path.return_value = "generated/videos/video_1.mp4"

        self.agent = VideoAgent(
            ffmpeg_service=self.mock_ffmpeg,
            video_validator=self.mock_validator,
            video_storage=self.mock_storage,
            assets_dir="generated/assets"
        )

    def tearDown(self):
        self.db.query(VideoAssetModel).delete()
        self.db.query(VisualAsset).delete()
        self.db.query(ScenePlan).delete()
        self.db.query(SubtitleAsset).delete()
        self.db.query(AudioAsset).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        self.db.close()

    @patch("os.path.exists")
    @patch("agents.video_agent.VideoAgent._ensure_placeholder_asset")
    def test_assemble_video_success(self, mock_ensure_asset, mock_exists):
        # Setup mocks
        mock_exists.return_value = True  # Pretend physical files (audio, subtitle) exist
        mock_ensure_asset.return_value = "generated/assets/asset_1.png"

        # Mock FFmpeg slideshow and burn commands
        self.mock_ffmpeg.create_slideshow.return_value = "generated/videos/temp_raw_1.mp4"
        self.mock_ffmpeg.add_subtitles.return_value = "generated/videos/video_1.mp4"

        # Mock Validator success
        self.mock_validator.validate_video.return_value = {
            "valid": True,
            "duration": 120.0,
            "resolution": "1080x1920",
            "size_mb": 25.5
        }

        # Mock DB record sync returning valid VideoAssetModel
        mock_db_model = VideoAssetModel(
            id=456,
            script_id=self.script.id,
            audio_id=self.audio.id,
            video_path="generated/videos/video_1.mp4",
            duration_seconds=120.0,
            resolution="1080x1920",
            status="READY",
            created_at=datetime.now(timezone.utc)
        )
        self.mock_storage.sync_db_asset.return_value = mock_db_model

        # Run
        doc = self.agent.assemble_video(script_id=self.script.id, db=self.db)

        # Assertions
        self.assertIsInstance(doc, VideoDocument)
        self.assertEqual(doc.id, 456)
        self.assertEqual(doc.duration_seconds, 120.0)
        self.assertEqual(doc.video_path, "generated/videos/video_1.mp4")

        # Verify DB syncing calls
        self.mock_storage.sync_db_asset.assert_any_call(
            db=self.db,
            script_id=self.script.id,
            audio_id=self.audio.id,
            video_path="generated/videos/video_1.mp4",
            duration_seconds=120.0,
            resolution="1080x1920",
            status="RENDERING"
        )
        self.mock_storage.sync_db_asset.assert_any_call(
            db=self.db,
            script_id=self.script.id,
            audio_id=self.audio.id,
            video_path="generated/videos/video_1.mp4",
            duration_seconds=120.0,
            resolution="1080x1920",
            status="READY"
        )

    @patch("os.path.exists")
    def test_assemble_video_missing_audio_raises(self, mock_exists):
        # Audio file does not exist
        mock_exists.side_effect = lambda path: "audio" not in path
        
        with self.assertRaises(VideoAgentError) as ctx:
            self.agent.assemble_video(script_id=self.script.id, db=self.db)
        self.assertIn("audio file not found", str(ctx.exception).lower())

    @patch("os.path.exists")
    def test_assemble_video_missing_subtitle_raises(self, mock_exists):
        # Subtitle file does not exist
        mock_exists.side_effect = lambda path: "srt" not in path
        
        with self.assertRaises(VideoAgentError) as ctx:
            self.agent.assemble_video(script_id=self.script.id, db=self.db)
        self.assertIn("subtitle file not found", str(ctx.exception).lower())

if __name__ == "__main__":
    unittest.main()
