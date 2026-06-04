import json
import logging
from typing import List, Optional
from services.llm_service import LLMService
from prompts.system_prompts import SYSTEM_ASSET_SEARCH_AGENT

logger = logging.getLogger("asset_search_agent")

class AssetSearchAgent:
    """
    Agent to convert scene descriptions, keywords, and niche into optimized image search query strings.
    """
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or LLMService()

    def generate_queries(
        self, 
        scene_description: str, 
        scene_keywords: List[str], 
        niche: str,
        scene_title: str = ""
    ) -> List[str]:
        logger.info(f"Generating asset search queries for scene: '{scene_title or scene_description[:40]}...'")
        
        prompt = (
            f"Video Niche: {niche}\n"
            f"Scene Title: {scene_title}\n"
            f"Scene Description: {scene_description}\n"
            f"Keywords: {', '.join(scene_keywords) if scene_keywords else 'None'}\n\n"
            "Based on the above, generate a list of 3 to 6 search terms optimized for search engines (e.g. Wikimedia, Met Museum, Pexels) to fetch relevant images."
        )

        try:
            response_text = self.llm.generate(
                prompt=prompt,
                system_prompt=SYSTEM_ASSET_SEARCH_AGENT,
                json_mode=True
            )
            # Parse the response as JSON list
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
                
            queries = json.loads(text.strip())
            if isinstance(queries, list):
                # Filter out empty or non-string queries
                queries = [q.strip() for q in queries if q and isinstance(q, str)]
                if queries:
                    logger.info(f"LLM generated {len(queries)} search queries: {queries}")
                    return queries
        except Exception as e:
            logger.error(f"Failed to generate asset search queries using LLM: {e}")

        # Fallback logic: build queries from keywords and description
        logger.info("Falling back to raw keywords for asset search.")
        fallback_queries = []
        
        if scene_title:
            fallback_queries.append(scene_title)
        
        for kw in scene_keywords:
            if kw and kw not in fallback_queries:
                fallback_queries.append(kw)
                
        if niche and len(fallback_queries) < 3:
            fallback_queries.append(f"{niche} theme")

        fallback_queries = fallback_queries[:5]
        
        if not fallback_queries:
            fallback_queries = ["historical event"]
            
        logger.info(f"Fallback queries built: {fallback_queries}")
        return fallback_queries
