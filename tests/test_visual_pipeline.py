import unittest
from unittest.mock import patch, MagicMock
from database.postgres import SessionLocal
from database.models import Topic, Script, ScenePlan, VisualAsset
from workflows.visual_pipeline import run_visual_pipeline
from schemas.scene_plan import ScenePlan as ScenePlanSchema
from schemas.visual_asset import VisualAsset as VisualAssetSchema

class TestVisualPipeline(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        # Clean existing records
        self.db.query(VisualAsset).delete()
        self.db.query(ScenePlan).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()

        # Create basic records
        self.topic = Topic(topic="Pipeline test", score=90.0, status="completed")
        self.db.add(self.topic)
        self.db.commit()

        self.script = Script(title="Pipeline Title", script="Script text content", topic_id=self.topic.id)
        self.db.add(self.script)
        self.db.commit()

    def tearDown(self):
        self.db.query(VisualAsset).delete()
        self.db.query(ScenePlan).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        self.db.close()

    @patch("agents.scene_agent.SceneAgent.generate_scenes")
    @patch("services.scene_parser.SceneParser.generate_asset_plan")
    @patch("services.visual_validator.VisualValidator.validate_visuals")
    def test_run_visual_pipeline_success(self, mock_validate, mock_parser, mock_generate):
        # Configure mocks
        mock_generate.return_value = [
            ScenePlanSchema(
                scene_number=1,
                title="Scene title",
                description="desc",
                narration_text="spoken",
                estimated_duration=10.0,
                visual_type="BROLL",
                keywords=["developer"]
            )
        ]
        mock_parser.return_value = [
            VisualAssetSchema(
                scene_id=1,
                asset_type="VIDEO",
                search_keywords=["developer"],
                priority=1,
                status="PLANNED"
            )
        ]
        mock_validate.return_value = {
            "valid": True,
            "scene_count": 1,
            "asset_count": 1
        }

        # Run pipeline
        res = run_visual_pipeline(script_id=self.script.id, db=self.db)

        # Assertions
        self.assertEqual(res["script_id"], self.script.id)
        self.assertEqual(res["scene_count"], 1)
        self.assertEqual(res["asset_count"], 1)

        # Verify calls
        mock_generate.assert_called_once_with(script_id=self.script.id, db=self.db)
        mock_parser.assert_called_once_with(script_id=self.script.id, db=self.db)
        mock_validate.assert_called_once_with(script_id=self.script.id, db=self.db)

    def test_run_visual_pipeline_missing_script_raises(self):
        with self.assertRaises(ValueError):
            run_visual_pipeline(script_id=99999, db=self.db)

if __name__ == "__main__":
    unittest.main()
