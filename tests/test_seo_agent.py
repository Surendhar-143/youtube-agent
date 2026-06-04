import json
import unittest
from unittest.mock import MagicMock
from database.postgres import SessionLocal
from database.models import Topic, Script, SEOMetadata
from agents.seo_agent import SEOAgent
from schemas.seo_metadata import SEOMetadataSchema

class TestSEOAgent(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        # Clean existing records
        self.db.query(SEOMetadata).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        
        # Insert a test topic and script
        self.topic = Topic(
            topic="How to Build a Python Agent",
            score=90.0,
            keywords=["python", "agent"],
            status="completed"
        )
        self.db.add(self.topic)
        self.db.commit()
        
        self.script = Script(
            title="Build a Python Agent in 10 Minutes",
            script="This is a long script narrative details...",
            topic_id=self.topic.id
        )
        self.db.add(self.script)
        self.db.commit()
        
        # Mock OllamaService
        self.mock_ollama = MagicMock()
        self.agent = SEOAgent(llm_service=self.mock_ollama)

    def tearDown(self):
        self.db.query(SEOMetadata).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        self.db.close()

    def test_generate_seo_metadata_success(self):
        mock_tags = [f"tag{i}" for i in range(16)]
        mock_hashes = [f"#hash{i}" for i in range(11)]
        
        self.mock_ollama.generate.return_value = """{{
            "title": "Optimized CTR Video Title",
            "description": "Rich description here containing tags and keywords.",
            "tags": {tags},
            "hashtags": {hashtags}
        }}""".format(tags=json.dumps(mock_tags), hashtags=json.dumps(mock_hashes))

        doc = self.agent.generate_metadata(script_id=self.script.id, db=self.db)
        
        self.assertIsInstance(doc, SEOMetadataSchema)
        self.assertEqual(doc.title, "Optimized CTR Video Title")
        self.assertEqual(len(doc.tags), 16)
        self.assertEqual(len(doc.hashtags), 11)
        
        # Verify stored in DB
        seo_record = self.db.query(SEOMetadata).filter(SEOMetadata.script_id == self.script.id).first()
        self.assertIsNotNone(seo_record)
        self.assertEqual(seo_record.title, "Optimized CTR Video Title")
        self.assertEqual(len(seo_record.tags), 16)

    def test_generate_seo_metadata_insufficient_tags_rejected(self):
        mock_tags = ["tag1", "tag2"]  # < 15
        mock_hashes = [f"#hash{i}" for i in range(11)]
        
        self.mock_ollama.generate.return_value = """{{
            "title": "Too few tags video",
            "description": "Rich description here containing tags.",
            "tags": {tags},
            "hashtags": {hashtags}
        }}""".format(tags=json.dumps(mock_tags), hashtags=json.dumps(mock_hashes))

        with self.assertRaises(ValueError):
            self.agent.generate_metadata(script_id=self.script.id, db=self.db)

if __name__ == "__main__":
    unittest.main()
