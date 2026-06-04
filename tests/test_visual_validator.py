import unittest
from database.postgres import SessionLocal
from database.models import Topic, Script, ScenePlan as ScenePlanModel, VisualAsset as VisualAssetModel, AudioAsset
from services.visual_validator import VisualValidator, SceneValidationError, AssetValidationError

class TestVisualValidator(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        # Clean existing records
        self.db.query(VisualAssetModel).delete()
        self.db.query(ScenePlanModel).delete()
        self.db.query(AudioAsset).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()

        # Create basic records
        self.topic = Topic(topic="Validation test", score=80.0, status="completed")
        self.db.add(self.topic)
        self.db.commit()

        self.script = Script(title="Validation title", script="Validation narration text", topic_id=self.topic.id)
        self.db.add(self.script)
        self.db.commit()

        self.validator = VisualValidator()

    def tearDown(self):
        self.db.query(VisualAssetModel).delete()
        self.db.query(ScenePlanModel).delete()
        self.db.query(AudioAsset).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        self.db.close()

    def test_validation_empty_scenes_raises(self):
        # No scenes in database for this script
        with self.assertRaises(SceneValidationError) as ctx:
            self.validator.validate_visuals(self.script.id, self.db)
        self.assertIn("Scene plan is empty", str(ctx.exception))

    def test_validation_invalid_scene_duration_raises(self):
        # Create invalid scene (estimated_duration = 0)
        scene = ScenePlanModel(
            script_id=self.script.id,
            scene_number=1,
            title="Scene title",
            description="Visual description",
            narration_text="Narration segment",
            estimated_duration=0,
            visual_type="BROLL",
            keywords=["dev"]
        )
        self.db.add(scene)
        self.db.commit()

        with self.assertRaises(SceneValidationError) as ctx:
            self.validator.validate_visuals(self.script.id, self.db)
        self.assertIn("invalid duration", str(ctx.exception))

    def test_validation_invalid_visual_type_raises(self):
        # Create scene with invalid visual type
        scene = ScenePlanModel(
            script_id=self.script.id,
            scene_number=1,
            title="Scene title",
            description="Visual description",
            narration_text="Narration segment",
            estimated_duration=10.0,
            visual_type="INVALID_TYPE",
            keywords=["dev"]
        )
        self.db.add(scene)
        self.db.commit()

        with self.assertRaises(SceneValidationError) as ctx:
            self.validator.validate_visuals(self.script.id, self.db)
        self.assertIn("invalid visual type", str(ctx.exception))

    def test_validation_missing_keywords_raises(self):
        # Create scene with no keywords
        scene = ScenePlanModel(
            script_id=self.script.id,
            scene_number=1,
            title="Scene title",
            description="Visual description",
            narration_text="Narration segment",
            estimated_duration=10.0,
            visual_type="BROLL",
            keywords=[]
        )
        self.db.add(scene)
        self.db.commit()

        with self.assertRaises(SceneValidationError) as ctx:
            self.validator.validate_visuals(self.script.id, self.db)
        self.assertIn("missing search keywords", str(ctx.exception))

    def test_validation_audio_inconsistency_raises(self):
        # Create scene with 10.0s duration
        scene = ScenePlanModel(
            script_id=self.script.id,
            scene_number=1,
            title="Scene title",
            description="Visual description",
            narration_text="Narration segment",
            estimated_duration=10.0,
            visual_type="BROLL",
            keywords=["dev"]
        )
        self.db.add(scene)

        # Create AudioAsset with 50.0s duration (inconsistent: 10s scene vs 50s audio)
        audio = AudioAsset(
            script_id=self.script.id,
            audio_path="generated/audio/audio_1.wav",
            duration_seconds=50.0,
            voice_model="lessac"
        )
        self.db.add(audio)
        self.db.commit()

        with self.assertRaises(SceneValidationError) as ctx:
            self.validator.validate_visuals(self.script.id, self.db)
        self.assertIn("inconsistent with audio narration", str(ctx.exception))

    def test_validation_missing_asset_coverage_raises(self):
        # Create valid scene
        scene = ScenePlanModel(
            script_id=self.script.id,
            scene_number=1,
            title="Scene title",
            description="Visual description",
            narration_text="Narration segment",
            estimated_duration=10.0,
            visual_type="BROLL",
            keywords=["dev"]
        )
        self.db.add(scene)
        self.db.commit()

        # No visual assets planned for this scene -> coverage failure
        with self.assertRaises(AssetValidationError) as ctx:
            self.validator.validate_visuals(self.script.id, self.db)
        self.assertIn("has no planned visual assets", str(ctx.exception))

    def test_validation_success(self):
        # Create valid scene
        scene = ScenePlanModel(
            script_id=self.script.id,
            scene_number=1,
            title="Scene title",
            description="Visual description",
            narration_text="Narration segment",
            estimated_duration=10.0,
            visual_type="BROLL",
            keywords=["dev"]
        )
        self.db.add(scene)
        self.db.commit()
        self.db.refresh(scene)

        # Create valid visual asset for the scene
        asset = VisualAssetModel(
            scene_id=scene.id,
            asset_type="VIDEO",
            search_keywords=["developer"],
            priority=1,
            status="PLANNED"
        )
        self.db.add(asset)
        self.db.commit()

        # Validate
        res = self.validator.validate_visuals(self.script.id, self.db)
        self.assertTrue(res["valid"])
        self.assertEqual(res["scene_count"], 1)
        self.assertEqual(res["asset_count"], 1)

if __name__ == "__main__":
    unittest.main()
