import os
import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from database.postgres import SessionLocal
from database.models import Topic, Script, AudioAsset
from agents.voice_agent import VoiceAgent, VoiceAgentError
from schemas.audio_document import AudioDocument

class TestVoiceAgent(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        # Clean existing records
        self.db.query(AudioAsset).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        
        # Set up a test topic and script
        self.topic = Topic(
            topic="Testing Audio Automation",
            score=85.0,
            keywords=["audio", "test"],
            status="completed"
        )
        self.db.add(self.topic)
        self.db.commit()
        
        self.script = Script(
            title="WAV Generation Guide",
            script="""# Introduction
            Welcome to the guide! **This is bold text.** [Narrator: Smile] 
            Today, we are going to learn about automation (this should be removed if parenthesized).
            Let's get started.
            """,
            topic_id=self.topic.id
        )
        self.db.add(self.script)
        self.db.commit()
        
        # Initialize VoiceAgent
        self.agent = VoiceAgent()

    def tearDown(self):
        self.db.query(AudioAsset).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        self.db.close()

    def test_clean_text(self):
        raw_text = """
        # Heading 1
        ## Heading 2
        Here is some **bold** text and *italic* text.
        [Narrator Cue: Upbeat energy]
        (Sound effect: wind blowing)
        This is normal text.
        """
        expected = "Heading 1 Heading 2 Here is some bold text and italic text. This is normal text."
        cleaned = self.agent._clean_text(raw_text)
        self.assertEqual(cleaned, expected)

    @patch("services.piper_service.PiperService.synthesize")
    @patch("services.audio_validator.AudioValidator.validate")
    @patch("services.audio_storage.AudioStorage.store_audio_file")
    def test_generate_audio_success(self, mock_store, mock_validate, mock_synthesize):
        # Setup mocks
        mock_synthesize.return_value = "generated/audio/temp_synthesis_1.wav"
        mock_validate.return_value = {"valid": True, "duration": 45.5, "size_bytes": 145600}
        mock_store.return_value = "generated/audio/audio_1.wav"

        # Run agent
        doc = self.agent.generate_audio(script_id=self.script.id, db=self.db)

        # Assertions
        self.assertIsInstance(doc, AudioDocument)
        self.assertEqual(doc.script_id, self.script.id)
        self.assertEqual(doc.duration_seconds, 45.5)
        self.assertEqual(doc.voice_model, "lessac")
        self.assertEqual(doc.audio_path, "generated/audio/audio_1.wav")

        # Verify record exists in DB
        db_record = self.db.query(AudioAsset).filter(AudioAsset.script_id == self.script.id).first()
        self.assertIsNotNone(db_record)
        self.assertEqual(db_record.duration_seconds, 45.5)
        self.assertEqual(db_record.voice_model, "lessac")

        # Verify cleanup of temporary file is attempted
        mock_synthesize.assert_called_once()
        mock_validate.assert_called_once()
        mock_store.assert_called_once()

    def test_generate_audio_missing_script(self):
        # Try to generate for invalid ID
        with self.assertRaises(VoiceAgentError) as ctx:
            self.agent.generate_audio(script_id=99999, db=self.db)
        self.assertIn("not found in database", str(ctx.exception))

    def test_generate_audio_empty_speakable_text(self):
        # Create a script containing only cues (which clean to empty string)
        bad_script = Script(
            title="Empty Cues",
            script="[Intro Music] [Sound effect: wind] (Narrator sighs)",
            topic_id=self.topic.id
        )
        self.db.add(bad_script)
        self.db.commit()

        with self.assertRaises(VoiceAgentError) as ctx:
            self.agent.generate_audio(script_id=bad_script.id, db=self.db)
        self.assertIn("contains no speakable text", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
