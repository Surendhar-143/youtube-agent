import unittest
from unittest.mock import MagicMock
from agents.asset_search_agent import AssetSearchAgent

class TestAssetSearchAgent(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MagicMock()
        self.agent = AssetSearchAgent(llm_service=self.mock_llm)

    def test_generate_queries_success(self):
        self.mock_llm.generate.return_value = '["roman emperor julius caesar", "crossing the rubicon painting", "ancient rome map"]'
        
        queries = self.agent.generate_queries(
            scene_description="Julius Caesar crossing the Rubicon river with his army",
            scene_keywords=["caesar", "rubicon", "rome"],
            niche="History",
            scene_title="Crossing the Rubicon"
        )
        
        self.assertEqual(len(queries), 3)
        self.assertEqual(queries[0], "roman emperor julius caesar")
        self.assertEqual(queries[1], "crossing the rubicon painting")
        self.assertEqual(queries[2], "ancient rome map")

    def test_generate_queries_fallback(self):
        self.mock_llm.generate.side_effect = Exception("LLM connection error")
        
        queries = self.agent.generate_queries(
            scene_description="Julius Caesar crossing the Rubicon river with his army",
            scene_keywords=["caesar", "rubicon"],
            niche="History",
            scene_title="Crossing the Rubicon"
        )
        
        self.assertTrue(len(queries) >= 2)
        self.assertIn("Crossing the Rubicon", queries)
        self.assertIn("caesar", queries)
        self.assertIn("rubicon", queries)

if __name__ == "__main__":
    unittest.main()
