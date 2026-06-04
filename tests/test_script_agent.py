import unittest
from unittest.mock import MagicMock
from database.postgres import SessionLocal
from database.models import Topic, Script
from agents.script_agent import ScriptAgent
from schemas.script_document import ScriptDocument

class TestScriptAgent(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        # Clean existing records
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        
        # Insert a test topic
        self.topic = Topic(
            topic="How to Build a Python Agent",
            score=90.0,
            keywords=["python", "agent"],
            status="pending"
        )
        self.db.add(self.topic)
        self.db.commit()
        
        # Mock OllamaService
        self.mock_ollama = MagicMock()
        self.agent = ScriptAgent(llm_service=self.mock_ollama)

    def tearDown(self):
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        self.db.close()

    def test_generate_script_success(self):
        # Create a mock response with >= 50 words (Shorts minimum)
        word_list = ["word"] * 100
        mock_script_text = " ".join(word_list)
        
        self.mock_ollama.generate.return_value = """{
            "title": "Build a Python Agent in 10 Minutes",
            "hook": "This is the hook",
            "script": "%s",
            "estimated_minutes": 1,
            "word_count": 100
        }""" % mock_script_text

        doc = self.agent.generate_script(topic_id=self.topic.id, db=self.db)
        
        self.assertIsInstance(doc, ScriptDocument)
        self.assertEqual(doc.title, "Build a Python Agent in 10 Minutes")
        self.assertEqual(doc.word_count, 100)
        
        # Verify stored in DB
        script_record = self.db.query(Script).filter(Script.topic_id == self.topic.id).first()
        self.assertIsNotNone(script_record)
        self.assertEqual(script_record.title, "Build a Python Agent in 10 Minutes")
        
        # Verify topic status updated
        updated_topic = self.db.query(Topic).filter(Topic.id == self.topic.id).first()
        self.assertEqual(updated_topic.status, "completed")

    def test_generate_script_under_minimum_words_rejected(self):
        # Mock response with < 50 words
        mock_script_text = "short script text"
        self.mock_ollama.generate.return_value = """{
            "title": "Short Script",
            "hook": "Hook text",
            "script": "%s",
            "estimated_minutes": 1,
            "word_count": 3
        }""" % mock_script_text

        with self.assertRaises(ValueError):
            self.agent.generate_script(topic_id=self.topic.id, db=self.db)

if __name__ == "__main__":
    unittest.main()
