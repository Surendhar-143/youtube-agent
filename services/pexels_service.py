import json
import logging
import urllib.request
import urllib.parse
from typing import List
from schemas.asset_result import AssetResult
from config.settings import settings

logger = logging.getLogger("pexels_service")

class PexelsService:
    """
    Service to search and retrieve media files from Pexels API.
    Skipped if PEXELS_API_KEY is empty.
    """
    def __init__(self):
        self.api_key = settings.PEXELS_API_KEY
        self.base_url = "https://api.pexels.com/v1/search"

    def search(self, query: str) -> List[AssetResult]:
        if not self.api_key:
            logger.info("Pexels API key not set; skipping search.")
            return []

        logger.info(f"Searching Pexels for query: '{query}'")
        params = {
            "query": query,
            "per_page": settings.ASSET_MAX_RESULTS_PER_QUERY,
        }
        
        url_params = urllib.parse.urlencode(params)
        url = f"{self.base_url}?{url_params}"
        
        results = []
        try:
            req = urllib.request.Request(
                url, 
                headers={
                    "Authorization": self.api_key,
                    "User-Agent": "YACEBot/1.0"
                }
            )
            with urllib.request.urlopen(req, timeout=settings.ASSET_DOWNLOAD_TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
                
            if "photos" not in data:
                logger.info(f"No photos found in Pexels search for query: '{query}'")
                return results

            for photo in data["photos"]:
                width = photo.get("width", 0)
                height = photo.get("height", 0)
                
                if width < settings.ASSET_MIN_WIDTH or height < settings.ASSET_MIN_HEIGHT:
                    logger.debug(f"Skipping Pexels asset due to low resolution: {width}x{height}")
                    continue
                
                src = photo.get("src", {})
                img_url = src.get("original")
                if not img_url:
                    continue
                
                # Thumb url can be medium or large
                thumb_url = src.get("medium", img_url)
                
                photographer = photo.get("photographer", "Unknown")
                title = f"Photo by {photographer} (ID: {photo.get('id')})"
                
                results.append(AssetResult(
                    url=img_url,
                    thumb_url=thumb_url,
                    source="pexels",
                    width=width,
                    height=height,
                    title=title,
                    license=f"Pexels License (Photographer: {photographer})",
                    query=query
                ))
        except Exception as e:
            logger.error(f"Error searching Pexels for '{query}': {e}", exc_info=True)
            
        return results
