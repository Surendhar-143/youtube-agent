import re
import logging
from typing import List
from schemas.asset_result import AssetResult

logger = logging.getLogger("asset_ranker")

class AssetRanker:
    """
    Ranks AssetResult candidates using a weighted scoring formula.
    """
    def __init__(self):
        self.source_weights = {
            "wikimedia": 100,
            "met_museum": 95,
            "europeana": 90,
            "pexels": 75,
            "ai_generated": 60
        }

    def _clean_words(self, text: str) -> set[str]:
        """Cleans text and extracts unique lowercase alphanumeric words."""
        if not text:
            return set()
        words = re.findall(r'\b\w+\b', text.lower())
        return set(words)

    def calculate_score(self, asset: AssetResult) -> float:
        """
        Calculates a score between 0 and 100 for an AssetResult based on:
        - Keyword Match: 30%
        - Resolution: 25%
        - Source Reliability: 20%
        - Aspect Ratio Fit: 25%
        """
        # 1. Keyword match (30%)
        query_words = self._clean_words(asset.query)
        title_words = self._clean_words(asset.title)
        
        match_score = 0.0
        if query_words:
            overlap = query_words.intersection(title_words)
            match_score = (len(overlap) / len(query_words)) * 30.0

        # 2. Resolution (25%)
        pixels = asset.width * asset.height
        baseline_pixels = 1920 * 1080
        resolution_score = min(pixels / baseline_pixels, 1.0) * 25.0

        # 3. Source reliability (20%)
        source_score = (self.source_weights.get(asset.source.lower(), 50) / 100.0) * 20.0

        # 4. Aspect ratio fit (25%)
        # Landscape bonus (wider >= 16:9 preferred)
        aspect_ratio = asset.width / asset.height if asset.height > 0 else 0.0
        target_aspect = 16.0 / 9.0
        if aspect_ratio >= target_aspect:
            aspect_score = 25.0
        else:
            aspect_score = min(aspect_ratio / target_aspect, 1.0) * 25.0

        total_score = match_score + resolution_score + source_score + aspect_score
        
        logger.debug(
            f"Asset Ranker: '{asset.title[:30]}' from '{asset.source}' scored {total_score:.2f} "
            f"(Keyword: {match_score:.1f}, Res: {resolution_score:.1f}, Source: {source_score:.1f}, Aspect: {aspect_score:.1f})"
        )
        return total_score

    def rank(self, assets: List[AssetResult]) -> List[AssetResult]:
        """
        Sorts the list of AssetResult items by their calculated scores in descending order.
        """
        return sorted(assets, key=lambda a: self.calculate_score(a), reverse=True)
