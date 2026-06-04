import os
import urllib.request
import logging
import time
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from config.settings import settings
from database.models import Script, ScenePlan, AssetDownload
from schemas.asset_result import AssetResult
from agents.asset_search_agent import AssetSearchAgent
from services.wikimedia_service import WikimediaService
from services.europeana_service import EuropeanaService
from services.met_museum_service import MetMuseumService
from services.pexels_service import PexelsService
from services.asset_validator import AssetValidator
from services.asset_ranker import AssetRanker

logger = logging.getLogger("asset_pipeline")

class AssetPipeline:
    """
    Orchestrates the visual asset acquisition pipeline for a given script.
    """
    def __init__(self, db: Session, llm_service: Optional[Any] = None):
        self.db = db
        self.search_agent = AssetSearchAgent(llm_service=llm_service)
        self.wikimedia = WikimediaService()
        self.europeana = EuropeanaService()
        self.met_museum = MetMuseumService()
        self.pexels = PexelsService()
        self.validator = AssetValidator()
        self.ranker = AssetRanker()

    def run(self, script_id: int, niche: str) -> Dict[str, Any]:
        logger.info(f"Starting asset pipeline for script_id: {script_id}, niche: '{niche}'")
        
        script = self.db.query(Script).filter(Script.id == script_id).first()
        if not script:
            raise ValueError(f"Script with ID {script_id} not found.")

        scenes = (
            self.db.query(ScenePlan)
            .filter(ScenePlan.script_id == script_id)
            .order_by(ScenePlan.scene_number)
            .all()
        )
        
        if not scenes:
            logger.warning(f"No scene plans found for script_id {script_id}")
            return {"scene_count": 0, "assets_found": 0, "assets_selected": 0, "placeholder_count": 0}

        self.validator.reset_run()

        assets_found_total = 0
        assets_selected_count = 0
        placeholder_count = 0
        sources_used = {}
        resolutions_used = []

        niche_clean = niche.lower().replace(" ", "_")
        
        if settings.ASSET_NICHE_SUBDIR:
            assets_dir = os.path.join(settings.PATH_ASSETS_DIR, niche_clean)
        else:
            assets_dir = settings.PATH_ASSETS_DIR
        os.makedirs(assets_dir, exist_ok=True)

        for scene in scenes:
            logger.info(f"Processing Scene {scene.scene_number} (ID: {scene.id})")
            
            queries = self.search_agent.generate_queries(
                scene_description=scene.description,
                scene_keywords=scene.keywords or [],
                niche=niche,
                scene_title=scene.title
            )

            candidates: List[AssetResult] = []
            for query in queries:
                # 1. Wikimedia (Primary)
                candidates.extend(self.wikimedia.search(query))
                
                # 2. Europeana (Secondary)
                if settings.EUROPEANA_API_KEY:
                    candidates.extend(self.europeana.search(query))
                
                # 3. Met Museum (Tertiary)
                candidates.extend(self.met_museum.search(query))
                
                # 4. Pexels (Supplementary)
                if settings.PEXELS_API_KEY:
                    candidates.extend(self.pexels.search(query))

            assets_found_total += len(candidates)
            logger.info(f"Scene {scene.scene_number}: Found {len(candidates)} total search candidates.")

            ranked_candidates = self.ranker.rank(candidates)
            
            download_success = False
            for asset in ranked_candidates[:10]:
                logger.info(f"Attempting to acquire asset: '{asset.title[:35]}' from {asset.source}")

                # Caching Check
                cached_download = (
                    self.db.query(AssetDownload)
                    .filter(AssetDownload.url == asset.url, AssetDownload.status == "DOWNLOADED")
                    .first()
                )
                
                if cached_download and os.path.exists(cached_download.local_path) and os.path.getsize(cached_download.local_path) > 0:
                    logger.info(f"Cache hit! Reusing downloaded asset for URL: {asset.url}")
                    new_dl = AssetDownload(
                        scene_id=scene.id,
                        asset_type="IMAGE",
                        source=asset.source,
                        search_query=asset.query,
                        url=asset.url,
                        local_path=cached_download.local_path,
                        width=cached_download.width,
                        height=cached_download.height,
                        file_size=cached_download.file_size,
                        quality_score=cached_download.quality_score,
                        status="DOWNLOADED"
                    )
                    self.db.add(new_dl)
                    self.db.commit()
                    
                    download_success = True
                    assets_selected_count += 1
                    sources_used[asset.source] = sources_used.get(asset.source, 0) + 1
                    resolutions_used.append(f"{cached_download.width}x{cached_download.height}")
                    break

                # Download file
                ext = ".jpg" if "png" not in asset.url.lower() else ".png"
                local_filename = f"scene_{scene.id}_{int(time.time())}{ext}"
                local_path = os.path.join(assets_dir, local_filename)

                try:
                    req = urllib.request.Request(asset.url, headers={"User-Agent": "YACEBot/1.0"})
                    with urllib.request.urlopen(req, timeout=settings.ASSET_DOWNLOAD_TIMEOUT) as response:
                        img_data = response.read()
                    
                    with open(local_path, "wb") as f:
                        f.write(img_data)

                    val_result = self.validator.validate(local_path)
                    if val_result.valid:
                        file_size = os.path.getsize(local_path)
                        new_dl = AssetDownload(
                            scene_id=scene.id,
                            asset_type="IMAGE",
                            source=asset.source,
                            search_query=asset.query,
                            url=asset.url,
                            local_path=local_path,
                            width=asset.width,
                            height=asset.height,
                            file_size=file_size,
                            quality_score=val_result.score,
                            status="DOWNLOADED"
                        )
                        self.db.add(new_dl)
                        self.db.commit()
                        
                        logger.info(f"Successfully downloaded and validated asset: {local_path}")
                        download_success = True
                        assets_selected_count += 1
                        sources_used[asset.source] = sources_used.get(asset.source, 0) + 1
                        resolutions_used.append(f"{asset.width}x{asset.height}")
                        break
                    else:
                        logger.warning(f"Downloaded asset failed validation: {val_result.reason}. Trying next.")
                        if os.path.exists(local_path):
                            os.unlink(local_path)
                except Exception as dl_err:
                    logger.warning(f"Failed to download asset {asset.url}: {dl_err}")
                    if os.path.exists(local_path):
                        try:
                            os.unlink(local_path)
                        except Exception:
                            pass

            if not download_success:
                # AI Fallback hook (disabled)
                if settings.AI_IMAGE_FALLBACK_ENABLED:
                    logger.info(f"AI image fallback triggered for Scene {scene.scene_number} (disabled by default).")
                
                logger.warning(f"No valid assets found or successfully downloaded for Scene {scene.scene_number}. Falling back to color placeholder.")
                placeholder_count += 1

        avg_res = "unknown"
        if resolutions_used:
            widths = []
            heights = []
            for res in resolutions_used:
                try:
                    w, h = map(int, res.split("x"))
                    widths.append(w)
                    heights.append(h)
                except Exception:
                    pass
            if widths and heights:
                avg_res = f"{int(sum(widths)/len(widths))}x{int(sum(heights)/len(heights))}"

        report = {
            "script_id": script_id,
            "scene_count": len(scenes),
            "assets_found": assets_found_total,
            "assets_selected": assets_selected_count,
            "placeholder_fallback_count": placeholder_count,
            "sources_used": sources_used,
            "avg_resolution": avg_res
        }
        
        os.makedirs("generated/reports", exist_ok=True)
        report_path = f"generated/reports/asset_report_{script_id}.json"
        try:
            import json
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            logger.info(f"Asset quality report written to {report_path}")
        except Exception as report_err:
            logger.error(f"Failed to write quality report: {report_err}")

        return report
