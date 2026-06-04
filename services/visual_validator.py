import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from database.models import Script, ScenePlan as ScenePlanModel, VisualAsset as VisualAssetModel
from config.settings import settings

logger = logging.getLogger("visual_validator")

class SceneValidationError(Exception):
    """Exception raised when scene validation fails."""
    pass

class AssetValidationError(Exception):
    """Exception raised when asset validation fails."""
    pass


class VisualValidator:
    """
    Validates visual scenes and asset plans for correctness, coverage, and duration consistency.
    """
    VALID_VISUAL_TYPES = {
        # Legacy / tech channel types (kept for backward compatibility)
        "BROLL", "SCREENSHOT", "DIAGRAM", "TEXT_OVERLAY", "CHART", "ANIMATION",
        # Phase 4.95 – Entertainment / cinematic types
        "HISTORICAL_PAINTING", "ANCIENT_MAP", "ARTIFACT", "AERIAL", "REENACTMENT",
    }

    def validate_visuals(self, script_id: int, db: Session) -> Dict[str, Any]:
        """
        Validates the scene plans and asset plans for a script.
        
        Args:
            script_id: Database script ID.
            db: SQLAlchemy Session.
            
        Returns:
            Dict: {"valid": True, "scene_count": X, "asset_count": Y}
            
        Raises:
            SceneValidationError: If scene structure or consistency check fails.
            AssetValidationError: If asset coverage checks fail.
        """
        logger.info(f"Starting visual validation for script {script_id}")

        # 1. Retrieve the script and scenes
        script = db.query(Script).filter(Script.id == script_id).first()
        if not script:
            raise SceneValidationError(f"Script with id {script_id} not found.")

        scenes = db.query(ScenePlanModel).filter(ScenePlanModel.script_id == script_id).order_by(ScenePlanModel.scene_number).all()
        scene_count = len(scenes)

        if scene_count == 0:
            raise SceneValidationError("Scene plan is empty (0 scenes).")

        total_scene_duration = 0.0
        
        # 2. Validate individual scenes
        for s in scenes:
            if not s.title or not s.title.strip():
                raise SceneValidationError(f"Scene {s.scene_number} has an empty or missing title.")
                
            if s.estimated_duration <= 0:
                raise SceneValidationError(
                    f"Scene {s.scene_number} ('{s.title}') has an invalid duration: {s.estimated_duration}s."
                )

            if not s.visual_type or s.visual_type.upper().strip() not in self.VALID_VISUAL_TYPES:
                raise SceneValidationError(
                    f"Scene {s.scene_number} ('{s.title}') has an invalid visual type: '{s.visual_type}'."
                )

            if not s.keywords:
                raise SceneValidationError(f"Scene {s.scene_number} ('{s.title}') is missing search keywords.")
                
            total_scene_duration += s.estimated_duration

        # 3. Validate duration consistency
        # Cross-reference with the AudioAsset duration if it exists
        if script.audio_asset:
            audio_duration = script.audio_asset.duration_seconds
            diff = abs(total_scene_duration - audio_duration)
            # Threshold: allowed tolerance is base seconds or fraction of the total audio duration, whichever is larger
            tolerance = max(
                settings.SCENE_DURATION_TOLERANCE_BASE_SECONDS,
                settings.SCENE_DURATION_TOLERANCE_FRACTION * audio_duration
            )
            if diff > tolerance:
                raise SceneValidationError(
                    f"Scene plan total duration ({total_scene_duration:.2f}s) is inconsistent with "
                    f"audio narration duration ({audio_duration:.2f}s). Difference: {diff:.2f}s. Max tolerance: {tolerance:.2f}s."
                )
            logger.info(
                f"Duration check passed: Scene duration sum ({total_scene_duration:.2f}s) vs "
                f"Audio narration duration ({audio_duration:.2f}s). Diff: {diff:.2f}s."
            )
        else:
            logger.warning(f"No AudioAsset found for script {script_id}. Skipping duration consistency cross-reference.")

        # 4. Validate asset coverage
        scene_ids = [s.id for s in scenes]
        assets = db.query(VisualAssetModel).filter(VisualAssetModel.scene_id.in_(scene_ids)).all()
        asset_count = len(assets)

        # Build map of scene_id -> list of assets for coverage check
        asset_map: Dict[int, List[VisualAssetModel]] = {sid: [] for sid in scene_ids}
        for asset in assets:
            if asset.scene_id in asset_map:
                asset_map[asset.scene_id].append(asset)

        for s in scenes:
            if not asset_map[s.id]:
                raise AssetValidationError(
                    f"Scene {s.scene_number} ('{s.title}') has no planned visual assets (0 coverage)."
                )

        logger.info(f"Visual validation successful: {scene_count} scenes, {asset_count} assets.")
        return {
            "valid": True,
            "scene_count": scene_count,
            "asset_count": asset_count
        }
