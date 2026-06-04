import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from database.postgres import SessionLocal
from database.models import Topic, Script, AudioAsset
from workflows.voice_pipeline import run_voice_pipeline
from schemas.audio_document import AudioDocument

class TestVoicePipeline(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        self.db.query(AudioAsset).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        
        # Setup mock topic and script
        self.topic = Topic(
            topic="Testing Voice Pipeline",
            score=88.8,
            keywords=["pipeline", "test"],
            status="completed"
        )
        self.db.add(self.topic)
        self.db.commit()
        
        self.script = Script(
            title="WAV Pipeline Guide",
            script="This is pipeline text content that will be spoken.",
            topic_id=self.topic.id
        )
        self.db.add(self.script)
        self.db.commit()

    def tearDown(self):
        self.db.query(AudioAsset).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        self.db.close()

    @patch("agents.voice_agent.VoiceAgent.generate_audio")
    def test_run_voice_pipeline_success(self, mock_generate):
        # Configure the mock to return a valid AudioDocument
        mock_doc = AudioDocument(
            id=789,
            script_id=self.script.id,
            audio_path="generated/audio/audio_789.wav",
            duration_seconds=15.5,
            voice_model="lessac",
            created_at=datetime.now(timezone.utc)
        )
        mock_generate.return_value = mock_doc

        # Run pipeline
        result = run_voice_pipeline(script_id=self.script.id, db=self.db)

        # Assert results
        self.assertEqual(result["script_id"], self.script.id)
        self.assertEqual(result["audio_id"], 789)
        self.assertEqual(result["audio_path"], "generated/audio/audio_789.wav")
        
        # Verify VoiceAgent was invoked correctly
        mock_generate.assert_called_once_with(script_id=self.script.id, db=self.db)

if __name__ == "__main__":
    unittest.main()
