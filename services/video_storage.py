import os
import shutil
import logging
from pathlib import Path
from typing import Optional, List
from sqlalchemy.orm import Session
from config.settings import settings
from database.models import VideoAsset as VideoAssetModel

logger = logging.getLogger("video_storage")

class VideoStorageError(Exception):
    """Base exception for VideoStorage operations."""
    pass


class VideoStorage:
    """
    Manages final rendered MP4 files and synchronizes metadata state in the PostgreSQL database.
    """
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or settings.PATH_VIDEOS_DIR)
        try:
            os.makedirs(self.base_dir, exist_ok=True)
            logger.info(f"Video storage initialized at: {self.base_dir}")
        except Exception as e:
            logger.critical(f"Failed to create video storage directory {self.base_dir}: {e}")
            raise VideoStorageError(f"Initialization failed: {e}")

    def get_video_path(self, script_id: int) -> Path:
        """
        Calculates the expected path for a script's rendered video file.
        """
        return Path(self.base_dir) / f"video_{script_id}.mp4"

    def store_video_file(self, script_id: int, temp_file_path: str) -> Path:
        """
        Copies a temporary rendered video file to the managed storage directory.
        """
        temp_abs = os.path.abspath(temp_file_path)
        dest_path = self.get_video_path(script_id)
        
        if not os.path.exists(temp_abs):
            raise VideoStorageError(f"Temporary source video file does not exist: {temp_abs}")
            
        try:
            logger.info(f"Storing video file for script {script_id}: {temp_abs} -> {dest_path}")
            shutil.copy2(temp_abs, dest_path)
            return dest_path
        except Exception as e:
            logger.error(f"Failed to store video file for script {script_id}: {e}")
            raise VideoStorageError(f"Failed to copy file to storage: {e}")

    def delete_video_file(self, script_id: int) -> bool:
        """
        Deletes the physical video file for the script if it exists.
        """
        file_path = self.get_video_path(script_id)
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Deleted physical video file: {file_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete physical video file {file_path}: {e}")
                raise VideoStorageError(f"Failed to delete file: {e}")
        return False

    def sync_db_asset(
        self,
        db: Session,
        script_id: int,
        audio_id: int,
        video_path: str,
        duration_seconds: float,
        resolution: str,
        status: str = "READY"
    ) -> VideoAssetModel:
        """
        Synchronizes database state, creating or updating the VideoAsset record.
        """
        try:
            # Check if asset already exists
            existing_asset = db.query(VideoAssetModel).filter(VideoAssetModel.script_id == script_id).first()
            
            # Normalize path for storage in DB (use relative path to workspace root for portability)
            try:
                rel_path = os.path.relpath(video_path, os.getcwd()).replace('\\', '/')
            except Exception:
                rel_path = video_path.replace('\\', '/')
                
            if existing_asset:
                logger.info(f"Updating existing VideoAsset record in database for script {script_id}")
                existing_asset.audio_id = audio_id
                existing_asset.video_path = rel_path
                existing_asset.duration_seconds = duration_seconds
                existing_asset.resolution = resolution
                existing_asset.status = status.upper()
                db.commit()
                db.refresh(existing_asset)
                return existing_asset
            else:
                logger.info(f"Creating new VideoAsset record in database for script {script_id}")
                new_asset = VideoAssetModel(
                    script_id=script_id,
                    audio_id=audio_id,
                    video_path=rel_path,
                    duration_seconds=duration_seconds,
                    resolution=resolution,
                    status=status.upper()
                )
                db.add(new_asset)
                db.commit()
                db.refresh(new_asset)
                return new_asset
        except Exception as e:
            db.rollback()
            logger.error(f"Database error while syncing VideoAsset for script {script_id}: {e}")
            raise VideoStorageError(f"Database sync failed: {e}")

    def get_video(self, db: Session, video_id: int) -> Optional[VideoAssetModel]:
        """
        Retrieves a VideoAsset record by its database ID.
        """
        return db.query(VideoAssetModel).filter(VideoAssetModel.id == video_id).first()

    def list_videos(self, db: Session, script_id: Optional[int] = None) -> List[VideoAssetModel]:
        """
        Lists all VideoAsset records, optionally filtering by script_id.
        """
        query = db.query(VideoAssetModel)
        if script_id is not None:
            query = query.filter(VideoAssetModel.script_id == script_id)
        return query.all()

    def delete_db_asset(self, db: Session, video_id: int) -> bool:
        """
        Deletes the VideoAsset record from the database.
        """
        try:
            asset = self.get_video(db, video_id)
            if asset:
                db.delete(asset)
                db.commit()
                logger.info(f"Deleted VideoAsset DB record with ID {video_id}")
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Database error while deleting VideoAsset {video_id}: {e}")
            raise VideoStorageError(f"Database delete failed: {e}")
