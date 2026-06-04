import os
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from database.models import VisualAsset as VisualAssetModel
from config.settings import settings

logger = logging.getLogger("asset_manager")

class AssetManagerError(Exception):
    """Base exception for AssetManager operations."""
    pass


class AssetManager:
    """
    Manages the lifecycle of visual assets requirements, provides metadata operations (CRUD),
    and ensures the local storage directory is initialized.
    """
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or settings.PATH_ASSETS_DIR)
        try:
            os.makedirs(self.base_dir, exist_ok=True)
            logger.info(f"Visual asset storage initialized at: {self.base_dir}")
        except Exception as e:
            logger.critical(f"Failed to create assets storage directory: {e}")
            raise AssetManagerError(f"Initialization failure: {e}")

    def create_asset(
        self,
        db: Session,
        scene_id: int,
        asset_type: str,
        search_keywords: List[str],
        priority: int = 1,
        status: str = "PLANNED"
    ) -> VisualAssetModel:
        """
        Creates and stores a new VisualAsset requirement in the database.
        """
        logger.info(f"Creating visual asset for scene {scene_id} of type '{asset_type}'")
        try:
            asset = VisualAssetModel(
                scene_id=scene_id,
                asset_type=asset_type,
                search_keywords=[k.strip() for k in search_keywords if k and k.strip()],
                priority=priority,
                status=status.upper()
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)
            return asset
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create VisualAsset in database: {e}")
            raise AssetManagerError(f"Database error during creation: {e}")

    def get_asset(self, db: Session, asset_id: int) -> Optional[VisualAssetModel]:
        """
        Retrieves a single VisualAsset metadata by its database ID.
        """
        return db.query(VisualAssetModel).filter(VisualAssetModel.id == asset_id).first()

    def update_asset(self, db: Session, asset_id: int, updates: Dict[str, Any]) -> VisualAssetModel:
        """
        Updates an existing VisualAsset record in the database.
        """
        logger.info(f"Updating visual asset {asset_id} with keys {list(updates.keys())}")
        asset = self.get_asset(db, asset_id)
        if not asset:
            raise AssetManagerError(f"VisualAsset with id {asset_id} not found.")

        allowed_fields = {"asset_type", "search_keywords", "priority", "status"}
        try:
            for field, value in updates.items():
                if field in allowed_fields:
                    if field == "status":
                        value = str(value).upper()
                    elif field == "search_keywords":
                        value = [str(k).strip() for k in value if k and str(k).strip()]
                    setattr(asset, field, value)
            db.commit()
            db.refresh(asset)
            return asset
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update VisualAsset {asset_id}: {e}")
            raise AssetManagerError(f"Database update failed: {e}")

    def list_assets(
        self,
        db: Session,
        scene_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[VisualAssetModel]:
        """
        Lists VisualAsset records, optionally filtering by scene_id and/or status.
        """
        query = db.query(VisualAssetModel)
        if scene_id is not None:
            query = query.filter(VisualAssetModel.scene_id == scene_id)
        if status is not None:
            query = query.filter(VisualAssetModel.status == status.upper())
        return query.all()

    def delete_asset(self, db: Session, asset_id: int) -> bool:
        """
        Deletes the VisualAsset record from the database.
        """
        logger.info(f"Deleting visual asset {asset_id} from database")
        try:
            asset = self.get_asset(db, asset_id)
            if asset:
                db.delete(asset)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete VisualAsset {asset_id}: {e}")
            raise AssetManagerError(f"Database delete failed: {e}")
