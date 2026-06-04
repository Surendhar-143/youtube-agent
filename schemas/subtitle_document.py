from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class SubtitleDocument(BaseModel):
    """
    Pydantic schema representing a generated subtitle file.
    """
    script_id: int = Field(..., description="ID of the associated script")
    subtitle_path: str = Field(..., description="File path to the SRT subtitle file")
    line_count: int = Field(..., description="Number of subtitle cues generated")
    created_at: datetime = Field(..., description="Generation timestamp")

    model_config = ConfigDict(from_attributes=True)
