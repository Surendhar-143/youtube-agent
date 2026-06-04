import logging
from typing import Optional
from sqlalchemy.orm import Session
from database.models import AIGeneration

logger = logging.getLogger("ai_audit_service")

def log_generation(
    db: Optional[Session],
    agent_name: str,
    model: str,
    prompt: str,
    response: Optional[str],
    success: bool,
    duration_ms: int
) -> Optional[AIGeneration]:
    """
    Logs an AI generation event (inputs, outputs, model, duration, and success status)
    to the database.
    """
    opened_session = False
    if db is None:
        try:
            from database.postgres import SessionLocal
            db = SessionLocal()
            opened_session = True
        except Exception as e:
            logger.error(f"Failed to open database session for AI audit log: {e}")
            return None

    try:
        audit_record = AIGeneration(
            agent_name=agent_name,
            model=model,
            prompt=prompt,
            response=response,
            success=success,
            duration_ms=duration_ms
        )
        db.add(audit_record)
        db.commit()
        db.refresh(audit_record)
        logger.info(f"Successfully logged AI generation for agent '{agent_name}' (ID: {audit_record.id}, Success: {success})")
        return audit_record
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to write AI audit log to database for agent '{agent_name}': {e}")
        raise e
    finally:
        if opened_session and db is not None:
            db.close()
