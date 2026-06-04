from pydantic import BaseModel, Field

class TopicCandidate(BaseModel):
    """
    Pydantic schema representing a generated YouTube video topic candidate.
    """
    topic: str = Field(..., description="The high-potential title/topic for the YouTube video")
    score: int = Field(..., description="Quality score between 0 and 100", ge=0, le=100)
    audience: str = Field(..., description="Target audience description")
    keywords: list[str] = Field(..., description="List of target search keywords for SEO")
    reasoning: str = Field(..., description="Strategic reasoning for generating this topic")
