import unittest
from unittest.mock import patch, MagicMock
from database.postgres import SessionLocal
from database.models import Topic, Script, ScenePlan, AssetDownload
from workflows.asset_pipeline import AssetPipeline

class TestAssetPipeline(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        # Clean DB
        self.db.query(AssetDownload).delete()
        self.db.query(ScenePlan).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()

        # Add topic, script, scene
        self.topic = Topic(topic="Ancient Egypt", score=85, keywords=["egypt"], status="pending")
        self.db.add(self.topic)
        self.db.commit()

        self.script = Script(title="Secret of Pyramids", script="Narrative text here.", topic_id=self.topic.id)
        self.db.add(self.script)
        self.db.commit()

        self.scene = ScenePlan(
            script_id=self.script.id,
            scene_number=1,
            title="The Great Sphinx",
            description="Visual of the Sphinx in front of Pyramids",
            narration_text="Narrative Sphinx",
            estimated_duration=5.0,
            visual_type="IMAGE",
            keywords=["sphinx", "pyramids"]
        )
        self.db.add(self.scene)
        self.db.commit()

        # Mock LLM
        self.mock_llm = MagicMock()
        self.pipeline = AssetPipeline(db=self.db, llm_service=self.mock_llm)

    def tearDown(self):
        self.db.query(AssetDownload).delete()
        self.db.query(ScenePlan).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        self.db.close()

    @patch("urllib.request.urlopen")
    @patch("services.wikimedia_service.WikimediaService.search")
    @patch("services.asset_validator.AssetValidator.validate")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    def test_pipeline_run_success(self, mock_getsize, mock_exists, mock_validate, mock_search, mock_urlopen):
        mock_exists.return_value = True
        mock_getsize.return_value = 1000
        
        self.mock_llm.generate.return_value = '["sphinx at giza"]'
        
        from schemas.asset_result import AssetResult
        mock_search.return_value = [
            AssetResult(
                url="http://test.com/sphinx.jpg",
                thumb_url="http://test.com/sphinx.jpg",
                source="wikimedia",
                width=1920,
                height=1080,
                title="The Sphinx",
                license="CC0",
                query="sphinx at giza"
            )
        ]
        
        mock_response = MagicMock()
        mock_response.read.return_value = b"image_data_bytes"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        from services.asset_validator import ValidationResult
        mock_validate.return_value = ValidationResult(True, "Valid", 95.0)

        report = self.pipeline.run(script_id=self.script.id, niche="History")
        
        self.assertEqual(report["scene_count"], 1)
        self.assertEqual(report["assets_selected"], 1)
        self.assertEqual(report["placeholder_fallback_count"], 0)
        
        downloads = self.db.query(AssetDownload).filter(AssetDownload.scene_id == self.scene.id).all()
        self.assertEqual(len(downloads), 1)
        self.assertEqual(downloads[0].status, "DOWNLOADED")
        self.assertEqual(downloads[0].source, "wikimedia")
        self.assertEqual(downloads[0].quality_score, 95.0)

if __name__ == "__main__":
    unittest.main()
