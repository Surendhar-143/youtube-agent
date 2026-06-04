from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class AudioDocument(BaseModel):
    """
    Pydantic schema representing a synthesized narration audio asset.
    """
    id: int = Field(..., description="Unique database ID of the audio asset")
    script_id: int = Field(..., description="The ID of the associated script")
    audio_path: str = Field(..., description="The relative file path of the WAV audio asset")
    duration_seconds: float = Field(..., description="The validated duration of the audio in seconds")
    voice_model: str = Field(..., description="The voice model used for synthesis")
    created_at: datetime = Field(..., description="Timestamp when the audio was generated")

    model_config = ConfigDict(from_attributes=True)
