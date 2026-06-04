import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from database.models import ScenePlan as ScenePlanModel, VisualAsset as VisualAssetModel
from schemas.visual_asset import VisualAsset as VisualAssetSchema
from config.settings import settings

logger = logging.getLogger("scene_parser")

class SceneParserError(Exception):
    """Base exception for SceneParser operations."""
    pass


class SceneParser:
    """
    Parses ScenePlan records to determine and register the required visual assets.
    """
    def map_visual_to_asset_type(self, visual_type: str) -> str:
        """
        Maps a scene's visual type to a valid visual asset type.
        Allowed Asset Types: IMAGE, VIDEO, ICON, CHART, SCREENSHOT
        Allowed Visual Types: BROLL, SCREENSHOT, DIAGRAM, TEXT_OVERLAY, CHART, ANIMATION
        """
        v_type = (visual_type or "").upper().strip()
        if v_type == "BROLL":
            return "VIDEO"
        elif v_type == "SCREENSHOT":
            return "SCREENSHOT"
        elif v_type == "DIAGRAM":
            return "IMAGE"
        elif v_type == "CHART":
            return "CHART"
        elif v_type == "TEXT_OVERLAY":
            return "ICON"
        elif v_type == "ANIMATION":
            return "VIDEO"
        else:
            logger.warning(f"Unknown visual type '{visual_type}'. Defaulting to 'IMAGE' asset type.")
            return "IMAGE"

    def plan_assets_for_scene(self, scene: ScenePlanModel, db: Session) -> List[VisualAssetModel]:
        """
        Generates and saves visual asset plans for a single scene record.
        """
        asset_type = self.map_visual_to_asset_type(scene.visual_type)
        
        # Use scene keywords. Fallback to scene title if keywords are empty.
        search_keywords = scene.keywords if scene.keywords else [scene.title]
        
        # Clean search keywords list
        search_keywords = [k.strip() for k in search_keywords if k and k.strip()]
        if not search_keywords:
            search_keywords = [k.strip() for k in settings.SCENE_FALLBACK_KEYWORDS.split(",") if k.strip()]
            if not search_keywords:
                search_keywords = ["general visual"]

        # Default priority is 1 (can be elevated to 2 for BROLL/intro scenes)
        priority = 2 if scene.scene_number == 1 or asset_type == "VIDEO" else 1

        db_asset = VisualAssetModel(
            scene_id=scene.id,
            asset_type=asset_type,
            search_keywords=search_keywords,
            priority=priority,
            status="PLANNED"
        )
        db.add(db_asset)
        return [db_asset]

    def generate_asset_plan(self, script_id: int, db: Session) -> List[VisualAssetSchema]:
        """
        Retrieves all scenes for the given script_id, clears existing asset plans for those scenes,
        generates new plans, saves them, and returns them as Pydantic schemas.
        """
        logger.info(f"Generating visual asset plans for script_id: {script_id}")
        
        try:
            # 1. Retrieve scenes
            scenes = db.query(ScenePlanModel).filter(ScenePlanModel.script_id == script_id).order_by(ScenePlanModel.scene_number).all()
            if not scenes:
                logger.error(f"No scene plans found for script_id: {script_id}")
                raise SceneParserError(f"No scenes found for script_id: {script_id}. Cannot plan assets.")

            # 2. Clear existing asset plans for these scenes (Idempotency)
            scene_ids = [s.id for s in scenes]
            existing_assets_count = db.query(VisualAssetModel).filter(VisualAssetModel.scene_id.in_(scene_ids)).count()
            if existing_assets_count > 0:
                logger.info(f"Deleting {existing_assets_count} existing visual assets for scenes {scene_ids}")
                db.query(VisualAssetModel).filter(VisualAssetModel.scene_id.in_(scene_ids)).delete(synchronize_session=False)
                db.commit()

            # 3. Create asset requirements for each scene
            logger.info(f"Planning assets for {len(scenes)} scenes...")
            all_assets = []
            for scene in scenes:
                planned = self.plan_assets_for_scene(scene, db)
                all_assets.extend(planned)

            db.commit()

            # 4. Convert saved items to Pydantic schemas
            result = []
            for asset in all_assets:
                db.refresh(asset)
                result.append(VisualAssetSchema.model_validate(asset))

            logger.info(f"Successfully generated and stored {len(result)} asset plans for script {script_id}.")
            return result

        except Exception as e:
            db.rollback()
            if not isinstance(e, SceneParserError):
                logger.error(f"Error occurred during visual asset planning: {e}")
                raise SceneParserError(f"Failed to generate visual asset plan: {e}")
            raise
