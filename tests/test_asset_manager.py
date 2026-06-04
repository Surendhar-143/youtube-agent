import os
import shutil
import tempfile
import unittest
from database.postgres import SessionLocal
from database.models import Topic, Script, ScenePlan, VisualAsset as VisualAssetModel
from services.asset_manager import AssetManager, AssetManagerError

class TestAssetManager(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        # Clean existing records
        self.db.query(VisualAssetModel).delete()
        self.db.query(ScenePlan).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()

        # Set up database records for foreign keys
        self.topic = Topic(topic="Asset Manager test", score=70.0, status="completed")
        self.db.add(self.topic)
        self.db.commit()

        self.script = Script(title="Asset title", script="Narration text", topic_id=self.topic.id)
        self.db.add(self.script)
        self.db.commit()

        self.scene = ScenePlan(
            script_id=self.script.id,
            scene_number=1,
            title="Scene One",
            description="Details",
            narration_text="Text content",
            estimated_duration=10.0,
            visual_type="BROLL",
            keywords=["dev"]
        )
        self.db.add(self.scene)
        self.db.commit()
        self.db.refresh(self.scene)

        # Create temporary assets directory for testing manager init
        self.temp_dir = tempfile.mkdtemp()
        self.manager = AssetManager(base_dir=self.temp_dir)

    def tearDown(self):
        self.db.query(VisualAssetModel).delete()
        self.db.query(ScenePlan).delete()
        self.db.query(Script).delete()
        self.db.query(Topic).delete()
        self.db.commit()
        self.db.close()

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_directory_created_on_init(self):
        self.assertTrue(os.path.isdir(self.temp_dir))
        self.assertTrue(os.path.exists(self.temp_dir))

    def test_create_asset_success(self):
        asset = self.manager.create_asset(
            db=self.db,
            scene_id=self.scene.id,
            asset_type="VIDEO",
            search_keywords=["developer", "desk"],
            priority=2,
            status="PLANNED"
        )
        self.assertIsNotNone(asset.id)
        self.assertEqual(asset.asset_type, "VIDEO")
        self.assertEqual(asset.search_keywords, ["developer", "desk"])
        self.assertEqual(asset.priority, 2)
        self.assertEqual(asset.status, "PLANNED")

    def test_get_asset_success(self):
        # Create
        created = self.manager.create_asset(
            db=self.db,
            scene_id=self.scene.id,
            asset_type="IMAGE",
            search_keywords=["test"],
            priority=1,
            status="PLANNED"
        )
        # Fetch
        fetched = self.manager.get_asset(self.db, created.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, created.id)
        self.assertEqual(fetched.asset_type, "IMAGE")

    def test_update_asset_success(self):
        # Create
        asset = self.manager.create_asset(
            db=self.db,
            scene_id=self.scene.id,
            asset_type="IMAGE",
            search_keywords=["original"],
            priority=1,
            status="PLANNED"
        )
        # Update status and priority
        updated = self.manager.update_asset(
            db=self.db,
            asset_id=asset.id,
            updates={"status": "ready", "priority": 5, "search_keywords": ["updated", "words"]}
        )
        self.assertEqual(updated.status, "READY")
        self.assertEqual(updated.priority, 5)
        self.assertEqual(updated.search_keywords, ["updated", "words"])

    def test_update_asset_not_found_raises(self):
        with self.assertRaises(AssetManagerError):
            self.manager.update_asset(self.db, 99999, {"status": "READY"})

    def test_list_assets_filtering(self):
        # Create assets
        self.manager.create_asset(self.db, self.scene.id, "VIDEO", ["k1"], 1, "PLANNED")
        self.manager.create_asset(self.db, self.scene.id, "IMAGE", ["k2"], 1, "READY")
        
        # List all
        all_assets = self.manager.list_assets(self.db)
        self.assertEqual(len(all_assets), 2)

        # Filter by status
        ready_assets = self.manager.list_assets(self.db, status="ready")
        self.assertEqual(len(ready_assets), 1)
        self.assertEqual(ready_assets[0].asset_type, "IMAGE")

    def test_delete_asset_success(self):
        # Create
        asset = self.manager.create_asset(self.db, self.scene.id, "IMAGE", ["k"], 1, "PLANNED")
        
        # Delete
        success = self.manager.delete_asset(self.db, asset.id)
        self.assertTrue(success)
        
        # Verify not found
        fetched = self.manager.get_asset(self.db, asset.id)
        self.assertIsNone(fetched)

    def test_delete_asset_not_found(self):
        success = self.manager.delete_asset(self.db, 99999)
        self.assertFalse(success)

if __name__ == "__main__":
    unittest.main()
