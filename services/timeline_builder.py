import logging
from dataclasses import dataclass
from typing import List
from sqlalchemy.orm import Session
from database.models import ScenePlan, AssetDownload
from config.settings import settings

logger = logging.getLogger("timeline_builder")

@dataclass
class TimelineEntry:
    scene_id: int
    scene_number: int
    asset_local_path: str
    duration: float
    motion_effect: str
    subtitle_start: float
    subtitle_end: float
    is_placeholder: bool

@dataclass  
class VideoTimeline:
    script_id: int
    total_duration: float
    entries: List[TimelineEntry]

class TimelineBuilder:
    """
    Builds the visual/subtitle timeline for a video script based on downloaded assets.
    """
    def __init__(self):
        self.motion_effects = ["zoom_in", "pan_left", "zoom_out", "pan_right", "slow_push", "pan_up", "pan_down"]

    def build(self, script_id: int, db: Session) -> VideoTimeline:
        logger.info(f"Building timeline for script_id: {script_id}")
        
        # Fetch scenes ordered by scene_number
        scenes = (
            db.query(ScenePlan)
            .filter(ScenePlan.script_id == script_id)
            .order_by(ScenePlan.scene_number)
            .all()
        )
        
        entries = []
        cumulative_time = 0.0
        
        # Track previously selected source to apply diversity penalty
        prev_source = None
        prev_effect = None
        
        for i, scene in enumerate(scenes):
            # Fetch all successfully downloaded assets for this scene
            downloads = (
                db.query(AssetDownload)
                .filter(AssetDownload.scene_id == scene.id, AssetDownload.status == "DOWNLOADED")
                .all()
            )
            
            selected_asset = None
            is_placeholder = True
            
            if downloads:
                # Apply diversity penalty: if a candidate source is same as prev_source, reduce its quality score
                scored_downloads = []
                for dl in downloads:
                    score = dl.quality_score
                    if prev_source and dl.source == prev_source:
                        # Penalty of 25 points to encourage source diversity
                        score -= 25.0
                        logger.debug(f"Applying source diversity penalty to asset {dl.id} (source: {dl.source})")
                    scored_downloads.append((score, dl))
                
                # Sort by penalized score descending
                scored_downloads.sort(key=lambda x: x[0], reverse=True)
                selected_asset = scored_downloads[0][1]
                is_placeholder = False
                prev_source = selected_asset.source
            else:
                prev_source = None

            # Determine motion effect (rotate/round-robin while ensuring it doesn't match prev_effect)
            effect_pool = [e for e in self.motion_effects if e != prev_effect]
            if not effect_pool:
                effect_pool = self.motion_effects
            
            # Selection based on scene index
            effect = effect_pool[i % len(effect_pool)]
            prev_effect = effect

            # Paths
            if not is_placeholder and selected_asset:
                asset_path = selected_asset.local_path
            else:
                # Default fallback path
                asset_path = f"assets/scene_fallback_{scene.id}.png"

            duration = scene.estimated_duration
            
            # Subtitle timing maps to cumulative durations
            sub_start = cumulative_time
            sub_end = cumulative_time + duration
            cumulative_time += duration
            
            entry = TimelineEntry(
                scene_id=scene.id,
                scene_number=scene.scene_number,
                asset_local_path=asset_path,
                duration=duration,
                motion_effect=effect,
                subtitle_start=sub_start,
                subtitle_end=sub_end,
                is_placeholder=is_placeholder
            )
            entries.append(entry)
            
        logger.info(f"Timeline built with {len(entries)} entries. Total duration: {cumulative_time:.2f}s")
        return VideoTimeline(
            script_id=script_id,
            total_duration=cumulative_time,
            entries=entries
        )
