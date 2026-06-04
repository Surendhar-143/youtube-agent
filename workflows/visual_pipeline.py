import logging
from typing import Optional
from sqlalchemy.orm import Session
from database.postgres import SessionLocal
from database.models import Script
from agents.scene_agent import SceneAgent
from services.scene_parser import SceneParser
from services.visual_validator import VisualValidator

logger = logging.getLogger("visual_pipeline")

def run_visual_pipeline(script_id: int, db: Optional[Session] = None) -> dict:
    """
    Orchestrates the Phase 3 visual planning engine workflow:
    1. Load Script
    2. Generate Scene Plan (SceneAgent)
    3. Validate Scene Plan & Assets (VisualValidator)
    4. Generate Asset Plan (SceneParser)
    5. Save metadata to database.
    
    Args:
        script_id: The primary key of the script record in the database.
        db: Optional SQLAlchemy Session.
        
    Returns:
        dict: A dictionary containing execution metadata:
              {"script_id": script_id, "scene_count": X, "asset_count": Y}
    """
    opened_session = False
    if db is None:
        db = SessionLocal()
        opened_session = True

    try:
        # 1. Loading script
        logger.info(f"Loading script with ID: {script_id}")
        script = db.query(Script).filter(Script.id == script_id).first()
        if not script:
            logger.error(f"Script with ID {script_id} not found in database.")
            raise ValueError(f"Script with ID {script_id} not found.")

        # Initialize core components
        scene_agent = SceneAgent()
        scene_parser = SceneParser()
        validator = VisualValidator()

        # 2. Generating scenes
        logger.info("Generating scenes...")
        scene_plans = scene_agent.generate_scenes(script_id=script_id, db=db)
        logger.info("Scene plan saved.")

        # 3. Generating assets
        logger.info("Generating assets...")
        assets = scene_parser.generate_asset_plan(script_id=script_id, db=db)
        logger.info("Assets saved.")

        # 4. Validating visual plan
        logger.info("Validating visual plan...")
        validation_result = validator.validate_visuals(script_id=script_id, db=db)
        logger.info("Validation successful.")

        result = {
            "script_id": script_id,
            "scene_count": validation_result["scene_count"],
            "asset_count": validation_result["asset_count"]
        }
        
        logger.info(f"Visual pipeline completed successfully for script {script_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Visual pipeline execution failed for script {script_id}: {e}")
        raise e
    finally:
        if opened_session:
            db.close()
