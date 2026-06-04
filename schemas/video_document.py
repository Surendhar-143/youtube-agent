from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class VideoDocument(BaseModel):
    """
    Pydantic schema representing a rendered final video asset.
    """
    id: int = Field(..., description="Unique database ID of the video asset")
    script_id: int = Field(..., description="Associated script ID")
    audio_id: int = Field(..., description="Associated narration audio ID")
    video_path: str = Field(..., description="Relative path to final rendered video file")
    duration_seconds: float = Field(..., description="Length of video in seconds")
    resolution: str = Field(..., description="Video resolution e.g. 1920x1080")
    created_at: datetime = Field(..., description="Rendering timestamp")

    model_config = ConfigDict(from_attributes=True)
