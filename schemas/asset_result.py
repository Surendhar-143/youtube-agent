from dataclasses import dataclass

@dataclass
class AssetResult:
    url: str
    thumb_url: str
    source: str   # "wikimedia" | "europeana" | "met_museum" | "pexels" | "ai_generated"
    width: int
    height: int
    title: str
    license: str
    query: str
