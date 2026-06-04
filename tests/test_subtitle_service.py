import os
import shutil
import tempfile
import unittest
from database.postgres import SessionLocal
from database.models import Topic, Script, ScenePlan, SubtitleAsset
from services.subtitle_service import SubtitleService, SubtitleError
from schemas.subtitle_document import SubtitleDocument

class TestSubtitleService(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        # Clean existing records
        self.db.query(SubtitleAsset).delete()
        self.db.query(ScenePlan).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()

        # Add records
        self.topic = Topic(topic="Subtitle testing", score=80.0, status="completed")
        self.db.add(self.topic)
        self.db.commit()

        self.script = Script(title="Script Title", script="Script Content text", topic_id=self.topic.id)
        self.db.add(self.script)
        self.db.commit()

        self.temp_dir = tempfile.mkdtemp()
        self.service = SubtitleService(output_dir=self.temp_dir)

    def tearDown(self):
        self.db.query(SubtitleAsset).delete()
        self.db.query(ScenePlan).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        self.db.close()

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_format_srt_time(self):
        self.assertEqual(self.service.format_srt_time(0.0), "00:00:00,000")
        self.assertEqual(self.service.format_srt_time(61.5), "00:01:01,500")
        self.assertEqual(self.service.format_srt_time(3665.123), "01:01:05,123")
        # Test overflow boundary
        self.assertEqual(self.service.format_srt_time(1.9999), "00:00:02,000")

    def test_chunk_narration_text_word_lengths(self):
        text = "This is a moderately long sentence designed to test the chunking behavior of subtitle lines. It should wrap nicely into multiple lines."
        # Scene duration 10 seconds, starting at 0.0s
        cues = self.service.chunk_narration_text(text, duration=10.0, start_time=0.0)
        
        self.assertGreater(len(cues), 0)
        for cue in cues:
            lines = cue["text"].split("\n")
            self.assertLessEqual(len(lines), 2)
            for line in lines:
                self.assertLessEqual(len(line), 40)
            self.assertLessEqual(len(cue["text"].replace('\n', ' ')), 80)
            self.assertGreater(cue["end"], cue["start"])

    def test_generate_subtitles_success(self):
        # Create multiple scene plans
        scene1 = ScenePlan(
            script_id=self.script.id,
            scene_number=1,
            title="Scene One",
            description="Visual One",
            narration_text="This is scene one narration.",
            estimated_duration=5.0,
            visual_type="BROLL",
            keywords=["dev"]
        )
        scene2 = ScenePlan(
            script_id=self.script.id,
            scene_number=2,
            title="Scene Two",
            description="Visual Two",
            narration_text="This is scene two narration.",
            estimated_duration=7.0,
            visual_type="DIAGRAM",
            keywords=["chart"]
        )
        self.db.add(scene1)
        self.db.add(scene2)
        self.db.commit()

        doc = self.service.generate_subtitles(script_id=self.script.id, db=self.db)
        
        self.assertIsInstance(doc, SubtitleDocument)
        self.assertEqual(doc.script_id, self.script.id)
        self.assertGreater(doc.line_count, 0)
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, f"video_{self.script.id}.srt")))

        # Check DB persistence
        db_asset = self.db.query(SubtitleAsset).filter(SubtitleAsset.script_id == self.script.id).first()
        self.assertIsNotNone(db_asset)
        self.assertEqual(db_asset.line_count, doc.line_count)

    def test_generate_subtitles_missing_scenes_raises(self):
        # No scene plans exist
        with self.assertRaises(SubtitleError):
            self.service.generate_subtitles(self.script.id, self.db)

if __name__ == "__main__":
    unittest.main()
