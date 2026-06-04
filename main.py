import os
import sys
import logging
from sqlalchemy import text
from config.settings import settings
from database.postgres import SessionLocal

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join("logs", "bootstrap.log"), encoding="utf-8")
    ]
)
logger = logging.getLogger("bootstrap")

def validate_directories() -> bool:
    """Verifies that all required folders exist. Creates them if missing."""
    required_dirs = [
        "logs",
        settings.PATH_SCRIPTS_DIR,
        settings.PATH_AUDIO_DIR,
        settings.PATH_VIDEOS_DIR,
        "generated/thumbnails",
        settings.PATH_ASSETS_DIR,
        settings.PATH_SUBTITLES_DIR,
        settings.PATH_FONTS_DIR,
        settings.PATH_MUSIC_DIR,
        settings.PATH_TEMPLATES_DIR,
    ]
    for directory in required_dirs:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created missing directory: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
                return False
    return True

def check_database_connection() -> bool:
    """Tests the connection to the PostgreSQL database."""
    try:
        session = SessionLocal()
        # Execute simple query to test connection
        session.execute(text("SELECT 1"))
        session.close()
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def main():
    logger.info("Initializing YACE Bootstrap...")
    
    # 1. Validate settings
    logger.info(f"Loaded Settings for {settings.APP_NAME}")
    
    # 2. Validate directory structure
    if not validate_directories():
        logger.error("Startup validation failed: directory checks failed.")
        sys.exit(1)
        
    # 3. Verify database connectivity
    if not check_database_connection():
        logger.error("Startup validation failed: Database connection is not available.")
        sys.exit(1)
        
    # 4. LLM health check
    from services.llm_service import LLMService
    llm_connected = False
    try:
        llm = LLMService()
        health = llm.health_check()
        if isinstance(health, dict):
            llm_connected = health.get("connected", False)
        else:
            llm_connected = bool(health)
    except Exception as e:
        logger.error(f"LLM provider health check failed during bootstrap: {e}")

    # 5. Success Output
    print("-" * 40)
    print("YACE started successfully")
    print(f"Environment: {settings.APP_ENV}")
    print(f"Database Provider: {settings.DATABASE_PROVIDER}")
    print("Database: Connected")
    print(f"Gemini: {'Connected' if llm_connected else 'Disconnected'}")
    print("-" * 40)

if __name__ == "__main__":
    main()
