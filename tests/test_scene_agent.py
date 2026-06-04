import json
import unittest
from unittest.mock import MagicMock, patch
from database.postgres import SessionLocal
from database.models import Topic, Script, ScenePlan as ScenePlanModel
from agents.scene_agent import SceneAgent, SceneAgentError
from schemas.scene_plan import ScenePlan as ScenePlanSchema

class TestSceneAgent(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        # Clean existing records
        self.db.query(ScenePlanModel).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        
        # Add test records
        self.topic = Topic(
            topic="Building a Scene Segmentation Agent",
            score=95.0,
            status="completed"
        )
        self.db.add(self.topic)
        self.db.commit()
        
        self.script = Script(
            title="Automated Scene Breaks",
            script="This is the script narrative. We will test formatting and segmenting.",
            topic_id=self.topic.id
        )
        self.db.add(self.script)
        self.db.commit()
        
        # Initialize Agent with Mock Ollama
        self.mock_ollama = MagicMock()
        self.agent = SceneAgent(llm_service=self.mock_ollama)

    def tearDown(self):
        self.db.query(ScenePlanModel).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        self.db.close()

    def test_generate_scenes_success(self):
        # Mock JSON response from Ollama
        mock_response = {
            "scenes": [
                {
                    "scene_number": 1,
                    "title": "Introduction Scene",
                    "description": "Show a developer coding at their desk.",
                    "narration_text": "This is the script narrative.",
                    "estimated_duration": 8.5,
                    "visual_type": "BROLL",
                    "keywords": ["developer", "desk"]
                },
                {
                    "scene_number": 2,
                    "title": "Visualizing segmentation",
                    "description": "Show diagram of pipeline splits.",
                    "narration_text": "We will test formatting and segmenting.",
                    "estimated_duration": 12.0,
                    "visual_type": "DIAGRAM",
                    "keywords": ["diagram", "pipeline"]
                }
            ]
        }
        self.mock_ollama.generate.return_value = json.dumps(mock_response)

        # Execute
        docs = self.agent.generate_scenes(script_id=self.script.id, db=self.db)

        # Assert returns Pydantic models
        self.assertEqual(len(docs), 2)
        self.assertIsInstance(docs[0], ScenePlanSchema)
        self.assertEqual(docs[0].title, "Introduction Scene")
        self.assertEqual(docs[1].visual_type, "DIAGRAM")

        # Verify DB entries
        db_records = self.db.query(ScenePlanModel).filter(ScenePlanModel.script_id == self.script.id).order_by(ScenePlanModel.scene_number).all()
        self.assertEqual(len(db_records), 2)
        self.assertEqual(db_records[0].title, "Introduction Scene")
        self.assertEqual(db_records[0].estimated_duration, 8.5)
        self.assertEqual(db_records[1].keywords, ["diagram", "pipeline"])

    def test_generate_scenes_idempotency(self):
        # Insert a pre-existing scene plan for this script
        pre_scene = ScenePlanModel(
            script_id=self.script.id,
            scene_number=1,
            title="Old Scene",
            description="Should be deleted",
            narration_text="Spoken content",
            estimated_duration=5.0,
            visual_type="TEXT_OVERLAY",
            keywords=["old"]
        )
        self.db.add(pre_scene)
        self.db.commit()

        # Mock JSON response
        mock_response = {
            "scenes": [
                {
                    "scene_number": 1,
                    "title": "New Scene",
                    "description": "Instructions",
                    "narration_text": "Text content",
                    "estimated_duration": 10.0,
                    "visual_type": "BROLL",
                    "keywords": ["new"]
                }
            ]
        }
        self.mock_ollama.generate.return_value = json.dumps(mock_response)

        # Execute
        docs = self.agent.generate_scenes(script_id=self.script.id, db=self.db)
        
        # Verify old scene was replaced
        db_records = self.db.query(ScenePlanModel).filter(ScenePlanModel.script_id == self.script.id).all()
        self.assertEqual(len(db_records), 1)
        self.assertEqual(db_records[0].title, "New Scene")

    def test_generate_scenes_invalid_format_raises(self):
        # Return invalid JSON structure (missing 'scenes')
        self.mock_ollama.generate.return_value = json.dumps({"invalid_field": "data"})

        with self.assertRaises(SceneAgentError):
            self.agent.generate_scenes(script_id=self.script.id, db=self.db)

    def test_generate_scenes_missing_script_raises(self):
        with self.assertRaises(SceneAgentError):
            self.agent.generate_scenes(script_id=99999, db=self.db)

if __name__ == "__main__":
    unittest.main()
