import unittest
import json
from unittest.mock import MagicMock
from database.postgres import SessionLocal
from database.models import Topic
from agents.research_agent import ResearchAgent
from schemas.topic_candidate import TopicCandidate

class TestResearchAgent(unittest.TestCase):
    def setUp(self):
        self.mock_ollama = MagicMock()
        self.agent = ResearchAgent(llm_service=self.mock_ollama)
        self.db = SessionLocal()
        # Clean up any test topics
        self.db.query(Topic).delete()
        self.db.commit()

    def tearDown(self):
        self.db.query(Topic).delete()
        self.db.commit()
        self.db.close()

    def test_generate_topics_success(self):
        niche = "AI Automation"
        mock_response = [
            {
                "topic": "Python Agent Tutorial",
                "score": 95.0,
                "audience": "Developers",
                "keywords": ["python", "agent"],
                "reasoning": "High CTR potential"
            }
        ]
        self.mock_ollama.generate.return_value = json.dumps(mock_response)
        candidates = self.agent.generate_topics(niche=niche, db=self.db)
        
        self.assertIsInstance(candidates, list)
        self.assertGreater(len(candidates), 0, "No topics returned by ResearchAgent")
        
        # Verify elements are TopicCandidate objects
        for candidate in candidates:
            self.assertIsInstance(candidate, TopicCandidate)
            self.assertTrue(candidate.topic)
            self.assertTrue(candidate.keywords)
            self.assertTrue(0 <= candidate.score <= 100)
            
        # Verify they are stored in the database
        stored_topics = self.db.query(Topic).all()
        self.assertEqual(len(stored_topics), len(candidates))
        for topic in stored_topics:
            self.assertTrue(topic.topic)
            self.assertTrue(topic.keywords)
            self.assertEqual(topic.status, "pending")

if __name__ == "__main__":
    unittest.main()
