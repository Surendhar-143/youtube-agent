from pydantic import BaseModel, Field

class SEOMetadataSchema(BaseModel):
    """
    Pydantic schema representing the generated YouTube SEO metadata package.
    """
    title: str = Field(..., description="High CTR optimized title")
    description: str = Field(..., description="SEO keyword-rich description")
    tags: list[str] = Field(..., description="Minimum of 15 relevant tags")
    hashtags: list[str] = Field(..., description="Minimum of 10 relevant hashtags")
