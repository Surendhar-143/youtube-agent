import logging
from typing import Optional
from sqlalchemy.orm import Session
from database.postgres import SessionLocal
from agents.voice_agent import VoiceAgent

logger = logging.getLogger("voice_pipeline")

def run_voice_pipeline(script_id: int, db: Optional[Session] = None) -> dict:
    """
    Orchestrates the Phase 2 Voice Production Pipeline:
    Retrieve Script -> Synthesize Narration WAV -> Validate Audio -> Save Metadata in DB.
    
    Args:
        script_id: The primary key of the script record in the database.
        db: Optional SQLAlchemy Session.
        
    Returns:
        dict: A dictionary containing execution metadata:
              {"script_id": script_id, "audio_id": audio_id, "audio_path": audio_path}
    """
    logger.info(f"Initiating voice pipeline for script_id: {script_id}")

    opened_session = False
    if db is None:
        db = SessionLocal()
        opened_session = True

    try:
        # Initialize VoiceAgent
        voice_agent = VoiceAgent()

        # Generate audio asset (includes synthesis, validation, storage copy, database record sync)
        audio_doc = voice_agent.generate_audio(script_id=script_id, db=db)

        result = {
            "script_id": script_id,
            "audio_id": audio_doc.id,
            "audio_path": audio_doc.audio_path
        }
        
        logger.info(f"Voice pipeline completed successfully for script {script_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Voice pipeline execution failed for script {script_id}: {e}")
        raise e
    finally:
        if opened_session:
            db.close()
