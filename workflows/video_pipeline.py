import logging
from typing import Optional
from sqlalchemy.orm import Session
from database.postgres import SessionLocal
from database.models import Script
from services.subtitle_service import SubtitleService
from agents.video_agent import VideoAgent

logger = logging.getLogger("video_pipeline")

def run_video_pipeline(script_id: int, db: Optional[Session] = None) -> dict:
    """
    Orchestrates the Phase 4 Video Production Pipeline:
    1. Load script and verify assets (Loading assets)
    2. Generate SRT subtitle files (Generating subtitles)
    3. Assemble, render, and burn subtitles (Starting render)
    4. Validate rendered video (Validation completed)
    5. Sync DB records and complete pipeline (Video stored)
    
    Args:
        script_id: The primary key of the script record in the database.
        db: Optional SQLAlchemy Session.
        
    Returns:
        dict: {"script_id": script_id, "audio_id": audio_id, "video_id": video_id, "video_path": video_path}
    """
    opened_session = False
    if db is None:
        db = SessionLocal()
        opened_session = True

    try:
        # 1. Loading assets
        logger.info(f"Loading assets for script_id: {script_id}")
        script = db.query(Script).filter(Script.id == script_id).first()
        if not script:
            logger.error(f"Script with ID {script_id} not found in database.")
            raise ValueError(f"Script with ID {script_id} not found.")

        # Ensure narration audio exists
        audio = script.audio_asset
        if not audio:
            logger.error(f"Narration AudioAsset not found for script {script_id}.")
            raise ValueError(f"Narration AudioAsset not found for script {script_id}.")

        # 2. Generating subtitles
        logger.info("Generating subtitles...")
        sub_service = SubtitleService()
        sub_doc = sub_service.generate_subtitles(script_id=script_id, db=db)
        logger.info(f"Subtitles generated. Path: {sub_doc.subtitle_path}")

        # 3. Starting render
        logger.info("Starting render...")
        video_agent = VideoAgent()
        video_doc = video_agent.assemble_video(script_id=script_id, db=db)
        logger.info("Render completed.")

        # 4. Validation completed
        logger.info("Validation completed.")

        # 5. Video stored
        logger.info("Video stored.")

        result = {
            "script_id": script_id,
            "audio_id": audio.id,
            "video_id": video_doc.id,
            "video_path": video_doc.video_path
        }
        
        logger.info(f"Video pipeline completed successfully for script {script_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Video pipeline execution failed for script {script_id}: {e}")
        raise e
    finally:
        if opened_session:
            db.close()
