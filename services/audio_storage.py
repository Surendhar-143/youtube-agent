import os
import shutil
import logging
from pathlib import Path
from typing import Optional, List
from sqlalchemy.orm import Session
from config.settings import settings
from database.models import AudioAsset

logger = logging.getLogger("audio_storage")

class AudioStorageError(Exception):
    """Base exception for AudioStorage operations."""
    pass


class AudioStorage:
    """
    Manages physical WAV audio files and synchronizes metadata state in the PostgreSQL database.
    """
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or settings.PATH_AUDIO_DIR)
        try:
            os.makedirs(self.base_dir, exist_ok=True)
            logger.info(f"Audio storage initialized at: {self.base_dir}")
        except Exception as e:
            logger.critical(f"Failed to create audio storage directory {self.base_dir}: {e}")
            raise AudioStorageError(f"Initialization failed: {e}")

    def get_audio_path(self, script_id: int) -> Path:
        """
        Calculates the expected path for a script's audio file.
        """
        return Path(self.base_dir) / f"audio_{script_id}.wav"

    def store_audio_file(self, script_id: int, temp_file_path: str) -> Path:
        """
        Moves or copies a temporary audio file to the managed storage directory.
        
        Args:
            script_id: The ID of the script.
            temp_file_path: Current path of the synthesized audio file.
            
        Returns:
            Path: The new location of the stored audio file.
            
        Raises:
            AudioStorageError: If moving or copying the file fails.
        """
        temp_abs = os.path.abspath(temp_file_path)
        dest_path = self.get_audio_path(script_id)
        
        if not os.path.exists(temp_abs):
            raise AudioStorageError(f"Temporary source file does not exist: {temp_abs}")
            
        try:
            logger.info(f"Storing audio file for script {script_id}: {temp_abs} -> {dest_path}")
            # If target exists, overwrite it
            shutil.copy2(temp_abs, dest_path)
            return dest_path
        except Exception as e:
            logger.error(f"Failed to store audio file for script {script_id}: {e}")
            raise AudioStorageError(f"Failed to copy file to storage: {e}")

    def delete_audio_file(self, script_id: int) -> bool:
        """
        Deletes the physical audio file for the script if it exists.
        
        Returns:
            bool: True if file was deleted, False if it did not exist.
        """
        file_path = self.get_audio_path(script_id)
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Deleted physical audio file: {file_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete physical audio file {file_path}: {e}")
                raise AudioStorageError(f"Failed to delete file: {e}")
        return False

    def sync_db_asset(
        self,
        db: Session,
        script_id: int,
        audio_path: str,
        duration_seconds: float,
        voice_model: str
    ) -> AudioAsset:
        """
        Synchronizes database state, creating or updating the AudioAsset record.
        
        Args:
            db: SQLAlchemy Session.
            script_id: ID of the script associated with the audio.
            audio_path: Path where the audio file is stored.
            duration_seconds: Validated duration of the audio in seconds.
            voice_model: Name of the model used for synthesis.
            
        Returns:
            AudioAsset: The created or updated SQLAlchemy model instance.
        """
        try:
            # Check if asset already exists
            existing_asset = db.query(AudioAsset).filter(AudioAsset.script_id == script_id).first()
            
            # Normalize path for storage in DB (use relative path to workspace root for portability)
            try:
                rel_path = os.path.relpath(audio_path, os.getcwd()).replace('\\', '/')
            except Exception:
                rel_path = audio_path.replace('\\', '/')
                
            if existing_asset:
                logger.info(f"Updating existing AudioAsset record in database for script {script_id}")
                existing_asset.audio_path = rel_path
                existing_asset.duration_seconds = duration_seconds
                existing_asset.voice_model = voice_model
                db.commit()
                db.refresh(existing_asset)
                return existing_asset
            else:
                logger.info(f"Creating new AudioAsset record in database for script {script_id}")
                new_asset = AudioAsset(
                    script_id=script_id,
                    audio_path=rel_path,
                    duration_seconds=duration_seconds,
                    voice_model=voice_model
                )
                db.add(new_asset)
                db.commit()
                db.refresh(new_asset)
                return new_asset
        except Exception as e:
            db.rollback()
            logger.error(f"Database error while syncing AudioAsset for script {script_id}: {e}")
            raise AudioStorageError(f"Database sync failed: {e}")

    def delete_db_asset(self, db: Session, script_id: int) -> bool:
        """
        Deletes the AudioAsset record from the database.
        
        Returns:
            bool: True if record was deleted, False if it was not found.
        """
        try:
            asset = db.query(AudioAsset).filter(AudioAsset.script_id == script_id).first()
            if asset:
                db.delete(asset)
                db.commit()
                logger.info(f"Deleted AudioAsset DB record for script {script_id}")
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Database error while deleting AudioAsset for script {script_id}: {e}")
            raise AudioStorageError(f"Database delete failed: {e}")
