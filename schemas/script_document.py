from pydantic import BaseModel, Field

class ScriptDocument(BaseModel):
    """
    Pydantic schema representing a full generated YouTube script.
    """
    title: str = Field(..., description="The finalized title of the video script")
    hook: str = Field(..., description="The high-impact first 15 seconds hook")
    script: str = Field(..., description="The complete narration script (hook, intro, body, CTA)")
    estimated_minutes: int = Field(default=1, description="Estimated video duration in minutes based on word count")
    word_count: int = Field(..., description="Total word count of the generated script")
