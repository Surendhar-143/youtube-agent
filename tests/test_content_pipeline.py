import json
import unittest
from unittest.mock import patch
from database.postgres import SessionLocal
from database.models import Topic, Script, SEOMetadata
from workflows.content_pipeline import run_content_pipeline

class TestContentPipeline(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.db.query(SEOMetadata).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()

    def tearDown(self):
        self.db.query(SEOMetadata).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        self.db.close()

    @patch('services.llm_service.LLMService.generate')
    def test_pipeline_execution_success(self, mock_generate):
        # 1. Mock ResearchAgent response (topics wrapped in object)
        mock_topics = {
            "topics": [
                {
                    "topic": "Python Agent Tutorial",
                    "score": 95,
                    "audience": "Developers",
                    "keywords": ["python", "agent"],
                    "reasoning": "High CTR potential"
                },
                {
                    "topic": "FastAPI Masterclass",
                    "score": 80,
                    "audience": "Developers",
                    "keywords": ["fastapi", "web"],
                    "reasoning": "Trending topic"
                }
            ]
        }
        
        # 2. Mock ScriptAgent response (script with >= 50 words per Shorts minimum)
        word_list = ["word"] * 100
        mock_script_text = " ".join(word_list)
        mock_script = {
            "title": "Python Agent Tutorial Title",
            "hook": "This is the hook text",
            "script": mock_script_text,
            "estimated_minutes": 1,
            "word_count": 100
        }
        
        # 3. Mock SEOAgent response (tags >= 15, hashtags >= 10)
        mock_tags = [f"tag{i}" for i in range(16)]
        mock_hashes = [f"#hash{i}" for i in range(11)]
        mock_seo = {
            "title": "High CTR Title for Python Agent",
            "description": "Rich description here...",
            "tags": mock_tags,
            "hashtags": mock_hashes
        }
        
        # Configure mock to return these in sequence
        mock_generate.side_effect = [
            json.dumps(mock_topics),
            json.dumps(mock_script),
            json.dumps(mock_seo)
        ]
        
        # Run pipeline
        result = run_content_pipeline(niche="AI Automation", db=self.db)
        
        self.assertIn("topic_id", result)
        self.assertIn("script_id", result)
        self.assertIn("seo_id", result)
        
        # Verify db persistence
        topic = self.db.query(Topic).filter(Topic.id == result["topic_id"]).first()
        self.assertIsNotNone(topic)
        self.assertEqual(topic.topic, "Python Agent Tutorial")
        self.assertEqual(topic.status, "completed")  # Updated by script agent
        
        script = self.db.query(Script).filter(Script.id == result["script_id"]).first()
        self.assertIsNotNone(script)
        self.assertEqual(script.title, "Python Agent Tutorial Title")
        
        seo = self.db.query(SEOMetadata).filter(SEOMetadata.id == result["seo_id"]).first()
        self.assertIsNotNone(seo)
        self.assertEqual(seo.title, "High CTR Title for Python Agent")
        self.assertEqual(len(seo.tags), 16)
        
if __name__ == "__main__":
    unittest.main()
