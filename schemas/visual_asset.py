from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

class VisualAsset(BaseModel):
    """
    Pydantic schema representing a planned visual asset requirement.
    """
    id: Optional[int] = Field(None, description="Unique database ID of the asset requirement")
    scene_id: int = Field(..., description="ID of the scene this asset is mapped to")
    asset_type: str = Field(..., description="Type of asset (IMAGE, VIDEO, ICON, CHART, SCREENSHOT)")
    search_keywords: List[str] = Field(default_factory=list, description="Keywords for media downloader")
    priority: int = Field(default=1, description="Download/Search priority")
    status: str = Field(default="PLANNED", description="Status (PLANNED, READY, MISSING, REJECTED)")
    created_at: Optional[datetime] = Field(None, description="Timestamp when the asset plan was created")

    model_config = ConfigDict(from_attributes=True)
