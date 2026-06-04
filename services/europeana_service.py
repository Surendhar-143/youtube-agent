import json
import logging
import urllib.request
import urllib.parse
from io import BytesIO
from typing import List, Tuple
from PIL import Image
from schemas.asset_result import AssetResult
from config.settings import settings

logger = logging.getLogger("europeana_service")

class EuropeanaService:
    """
    Service to search and retrieve media files from Europeana API.
    Skipped if EUROPEANA_API_KEY is empty.
    """
    def __init__(self):
        self.api_key = settings.EUROPEANA_API_KEY
        self.base_url = "https://api.europeana.eu/record/v2/search.json"

    def _get_image_dimensions(self, url: str) -> Tuple[int, int]:
        """
        Attempts to read only the image header (first 128 KB) to resolve dimensions
        without downloading the entire file.
        """
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "YACEBot/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                header_data = resp.read(128 * 1024)
                with Image.open(BytesIO(header_data)) as img:
                    return img.width, img.height
        except Exception:
            try:
                # Fallback to downloading full image if partial read fails
                req = urllib.request.Request(url, headers={"User-Agent": "YACEBot/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    with Image.open(resp) as img:
                        return img.width, img.height
            except Exception as e:
                logger.debug(f"Failed to resolve image dimensions for Europeana URL {url}: {e}")
                return 0, 0

    def search(self, query: str) -> List[AssetResult]:
        if not self.api_key:
            logger.info("Europeana key not set; skipping search.")
            return []

        logger.info(f"Searching Europeana for query: '{query}'")
        params = {
            "wskey": self.api_key,
            "query": query,
            "media": "true",
            "reusability": "open",
            "type": "IMAGE",
            "rows": settings.ASSET_MAX_RESULTS_PER_QUERY,
        }
        
        url_params = urllib.parse.urlencode(params)
        url = f"{self.base_url}?{url_params}"
        
        results = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "YACEBot/1.0"})
            with urllib.request.urlopen(req, timeout=settings.ASSET_DOWNLOAD_TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
                
            if "items" not in data:
                logger.info(f"No items found in Europeana search for query: '{query}'")
                return results

            for item in data["items"]:
                # edmIsShownBy contains the direct link to the image/media file
                img_urls = item.get("edmIsShownBy")
                if not img_urls:
                    continue
                
                # edmIsShownBy can be a list or a single string
                img_url = img_urls[0] if isinstance(img_urls, list) else img_urls
                if not img_url.startswith("http"):
                    continue

                title_list = item.get("title", [])
                title = title_list[0] if title_list else "Unknown Europeana Item"
                
                rights_list = item.get("rights", [])
                rights = rights_list[0] if rights_list else "Unknown License"
                
                # Resolve dimensions
                width, height = self._get_image_dimensions(img_url)
                if width < settings.ASSET_MIN_WIDTH or height < settings.ASSET_MIN_HEIGHT:
                    logger.debug(f"Skipping Europeana asset '{title}' due to low resolution: {width}x{height}")
                    continue
                
                # Use same URL for thumbnail for Europeana, or edmPreview if available
                preview_urls = item.get("edmPreview")
                thumb_url = preview_urls[0] if isinstance(preview_urls, list) else (preview_urls or img_url)

                results.append(AssetResult(
                    url=img_url,
                    thumb_url=thumb_url,
                    source="europeana",
                    width=width,
                    height=height,
                    title=title,
                    license=rights,
                    query=query
                ))
        except Exception as e:
            logger.error(f"Error searching Europeana for '{query}': {e}", exc_info=True)
            
        return results
