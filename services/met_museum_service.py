import json
import logging
import urllib.request
import urllib.parse
from io import BytesIO
from typing import List, Tuple
from PIL import Image
from schemas.asset_result import AssetResult
from config.settings import settings

logger = logging.getLogger("met_museum_service")

class MetMuseumService:
    """
    Service to search and retrieve public-domain images from the Metropolitan Museum of Art Open Access API.
    Requires no API key.
    """
    def __init__(self):
        self.search_url = "https://collectionapi.metmuseum.org/public/collection/v1/search"
        self.object_url = "https://collectionapi.metmuseum.org/public/collection/v1/objects"

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
                logger.debug(f"Failed to resolve image dimensions for Met Museum URL {url}: {e}")
                return 0, 0

    def search(self, query: str) -> List[AssetResult]:
        logger.info(f"Searching Met Museum for query: '{query}'")
        
        # Build query parameters
        params = {
            "q": query,
            "hasImages": "true",
            "isPublicDomain": "true"
        }
        
        url_params = urllib.parse.urlencode(params)
        search_endpoint = f"{self.search_url}?{url_params}"
        
        results = []
        try:
            # Step 1: Search for object IDs
            req = urllib.request.Request(search_endpoint, headers={"User-Agent": "YACEBot/1.0"})
            with urllib.request.urlopen(req, timeout=settings.ASSET_DOWNLOAD_TIMEOUT) as response:
                search_data = json.loads(response.read().decode("utf-8"))
                
            object_ids = search_data.get("objectIDs")
            if not object_ids:
                logger.info(f"No object IDs found in Met Museum search for query: '{query}'")
                return results

            # Step 2: Fetch details for top N object IDs
            count = 0
            for obj_id in object_ids:
                if count >= settings.ASSET_MAX_RESULTS_PER_QUERY:
                    break
                
                detail_endpoint = f"{self.object_url}/{obj_id}"
                try:
                    req_detail = urllib.request.Request(detail_endpoint, headers={"User-Agent": "YACEBot/1.0"})
                    with urllib.request.urlopen(req_detail, timeout=5) as resp_detail:
                        obj_data = json.loads(resp_detail.read().decode("utf-8"))
                    
                    img_url = obj_data.get("primaryImage")
                    if not img_url:
                        continue
                        
                    # Title and name
                    title = obj_data.get("title", "")
                    object_name = obj_data.get("objectName", "")
                    display_title = title if title else (object_name if object_name else f"Met Object {obj_id}")
                    
                    # Resolve dimensions
                    width, height = self._get_image_dimensions(img_url)
                    if width < settings.ASSET_MIN_WIDTH or height < settings.ASSET_MIN_HEIGHT:
                        logger.debug(f"Skipping Met Museum asset '{display_title}' due to low resolution: {width}x{height}")
                        continue
                    
                    thumb_url = obj_data.get("primaryImageSmall", img_url)
                    
                    results.append(AssetResult(
                        url=img_url,
                        thumb_url=thumb_url,
                        source="met_museum",
                        width=width,
                        height=height,
                        title=display_title,
                        license="CC0 (Public Domain)",
                        query=query
                    ))
                    count += 1
                except Exception as detail_err:
                    logger.debug(f"Error fetching Met Museum object {obj_id} details: {detail_err}")
                    continue
        except Exception as e:
            logger.error(f"Error searching Met Museum for '{query}': {e}", exc_info=True)
            
        return results
