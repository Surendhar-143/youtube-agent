import json
import logging
import urllib.request
import urllib.parse
from typing import List
from schemas.asset_result import AssetResult
from config.settings import settings

logger = logging.getLogger("wikimedia_service")

class WikimediaService:
    """
    Service to search and retrieve media files from Wikimedia Commons.
    Requires no API key.
    """
    def __init__(self):
        self.base_url = "https://commons.wikimedia.org/w/api.php"

    def search(self, query: str) -> List[AssetResult]:
        logger.info(f"Searching Wikimedia for query: '{query}'")
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,  # Namespace 6 is for files (File: prefix)
            "gsrlimit": settings.ASSET_MAX_RESULTS_PER_QUERY,
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
        }
        
        url_params = urllib.parse.urlencode(params)
        url = f"{self.base_url}?{url_params}"
        
        results = []
        try:
            req = urllib.request.Request(
                url, 
                headers={"User-Agent": "YACEBot/1.0 (contact: surendhar@example.com; github.com/Surendhar-143/youtube-agent)"}
            )
            with urllib.request.urlopen(req, timeout=settings.ASSET_DOWNLOAD_TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
                
            if "query" not in data or "pages" not in data["query"]:
                logger.info(f"No pages found in Wikimedia search for query: '{query}'")
                return results

            pages = data["query"]["pages"]
            for page_id, page_data in pages.items():
                if "imageinfo" not in page_data or not page_data["imageinfo"]:
                    continue
                info = page_data["imageinfo"][0]
                
                # Check mime type
                mime = info.get("mime", "")
                if mime not in ["image/jpeg", "image/png"]:
                    continue
                    
                width = info.get("width", 0)
                height = info.get("height", 0)
                
                if width < settings.ASSET_MIN_WIDTH or height < settings.ASSET_MIN_HEIGHT:
                    logger.debug(f"Skipping Wikimedia asset '{page_data.get('title')}' due to low resolution: {width}x{height}")
                    continue
                    
                img_url = info.get("url", "")
                thumb_url = info.get("thumburl", img_url) # fallback to full image URL if thumbnail doesn't exist
                title = page_data.get("title", "")
                
                # Strip prefix "File:" from title
                if title.lower().startswith("file:"):
                    title = title[5:]
                
                # Extract license info
                extmetadata = info.get("extmetadata", {})
                license_name = extmetadata.get("LicenseShortName", {}).get("value", "Unknown")
                
                results.append(AssetResult(
                    url=img_url,
                    thumb_url=thumb_url,
                    source="wikimedia",
                    width=width,
                    height=height,
                    title=title,
                    license=license_name,
                    query=query
                ))
        except Exception as e:
            logger.error(f"Error searching Wikimedia for '{query}': {e}", exc_info=True)
            
        return results
