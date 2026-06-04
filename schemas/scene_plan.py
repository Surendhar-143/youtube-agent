from pydantic import BaseModel, Field, ConfigDict
from typing import List

class ScenePlan(BaseModel):
    """
    Pydantic schema representing a single scene's visual plan.
    """
    scene_number: int = Field(..., description="Chronological index of the scene")
    title: str = Field(..., description="Concise title for the scene visual")
    description: str = Field(..., description="Description of the visual actions or layout")
    narration_text: str = Field(..., description="The segment of narration text associated with this scene")
    estimated_duration: float = Field(..., description="Estimated scene duration in seconds")
    visual_type: str = Field(..., description="Type of visual (BROLL, SCREENSHOT, etc.)")
    keywords: List[str] = Field(default_factory=list, description="Keywords for asset search and indexing")

    model_config = ConfigDict(from_attributes=True)

class ScenePlanResponse(BaseModel):
    """
    Pydantic schema wrapper for local Ollama list response.
    """
    scenes: List[ScenePlan]
