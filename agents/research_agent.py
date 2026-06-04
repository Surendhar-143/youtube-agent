import json
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from database.postgres import SessionLocal
from database.models import Topic
from services.llm_service import LLMService
from schemas.topic_candidate import TopicCandidate
from prompts.system_prompts import SYSTEM_RESEARCH_AGENT
from prompts.research_prompts import RESEARCH_PROMPT_TEMPLATE
from config.settings import settings

logger = logging.getLogger("research_agent")

class ResearchAgent:
    """
    Agent responsible for content topic discovery and validation.
    """
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or LLMService()

    def generate_topics(self, niche: str, db: Optional[Session] = None) -> List[TopicCandidate]:
        """
        Generates 10 YouTube video ideas for a given niche, validates them,
        persists them to the database, and returns the valid candidates.
        """
        logger.info(f"Generating topics for niche: {niche}")
        
        import time
        logger.info("[TIMING] ResearchAgent: Before prompt creation")
        start_prompt = time.time()
        prompt = RESEARCH_PROMPT_TEMPLATE.format(niche=niche, topics_count=settings.CONTENT_TOPICS_COUNT)
        logger.info(f"[TIMING] ResearchAgent: After prompt creation (Duration: {time.time() - start_prompt:.4f}s)")
        
        from services.ai_audit_service import log_generation

        start_time = time.time()
        success = False
        response_text = ""
        try:
            logger.info("[TIMING] ResearchAgent: Before Ollama call")
            start_ollama = time.time()
            response_text = self.llm.generate(
                prompt=prompt,
                system_prompt=SYSTEM_RESEARCH_AGENT,
                json_mode=True
            )
            logger.info(f"[TIMING] ResearchAgent: After LLM call (Duration: {time.time() - start_ollama:.4f}s)")
            
            logger.info("[TIMING] ResearchAgent: Before JSON parsing")
            start_parse = time.time()
            from services.json_utils import parse_json_robust
            raw_candidates = parse_json_robust(response_text)
            
            logger.info(f"[TIMING] ResearchAgent: After JSON parsing (Duration: {time.time() - start_parse:.4f}s)")
            success = True
        except Exception as e:
            logger.error(f"Failed to generate or parse topics JSON: {e}")
            duration_ms = int((time.time() - start_time) * 1000)
            try:
                log_generation(
                    db=db,
                    agent_name="ResearchAgent",
                    model=self.llm.model_name,
                    prompt=prompt,
                    response=response_text or str(e),
                    success=False,
                    duration_ms=duration_ms
                )
            except Exception as log_err:
                logger.error(f"Failed to write AI audit log: {log_err}")
            raise ValueError(f"Failed to generate or parse topics JSON: {e}")

        duration_ms = int((time.time() - start_time) * 1000)
        try:
            log_generation(
                db=db,
                agent_name="ResearchAgent",
                model=self.llm.model_name,
                prompt=prompt,
                response=response_text,
                success=True,
                duration_ms=duration_ms
            )
        except Exception as log_err:
            logger.error(f"Failed to write AI audit log: {log_err}")
            
        if not isinstance(raw_candidates, list):
            # If the model wrapped the list in an object key, try to extract it
            if isinstance(raw_candidates, dict):
                for val in raw_candidates.values():
                    if isinstance(val, list):
                        raw_candidates = val
                        break
            if not isinstance(raw_candidates, list):
                logger.error("Expected a JSON list of topics but received a different format.")
                raise ValueError("Expected a JSON list of topics.")

        valid_candidates: List[TopicCandidate] = []
        for idx, item in enumerate(raw_candidates):
            try:
                # Standardize keyword formats if necessary
                if "keywords" in item and isinstance(item["keywords"], str):
                    item["keywords"] = [k.strip() for k in item["keywords"].split(",") if k.strip()]
                
                # Parse and validate with Pydantic
                candidate = TopicCandidate(**item)
                
                # Perform required assertions
                if not candidate.topic.strip():
                    raise ValueError("Topic cannot be empty")
                if not candidate.keywords:
                    raise ValueError("Keywords cannot be empty")
                if not (0 <= candidate.score <= 100):
                    raise ValueError("Score must be between 0 and 100")
                if candidate.score < settings.CONTENT_MIN_TOPIC_SCORE:
                    raise ValueError(f"Score ({candidate.score}) is below minimum limit ({settings.CONTENT_MIN_TOPIC_SCORE})")
                    
                valid_candidates.append(candidate)
            except Exception as e:
                logger.warning(f"Rejected invalid candidate at index {idx}: {e}. Data: {item}")
                
        # Persistence
        if valid_candidates:
            opened_session = False
            if db is None:
                db = SessionLocal()
                opened_session = True
                
            try:
                logger.info("[TIMING] ResearchAgent: Before DB insert")
                start_db = time.time()
                for candidate in valid_candidates:
                    topic_record = Topic(
                        topic=candidate.topic,
                        score=float(candidate.score),
                        keywords=candidate.keywords,
                        status="pending"
                    )
                    db.add(topic_record)
                db.commit()
                logger.info(f"[TIMING] ResearchAgent: After DB insert (Duration: {time.time() - start_db:.4f}s)")
                logger.info(f"Saved {len(valid_candidates)} topics to the database.")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to persist topics to database: {e}")
                raise e
            finally:
                if opened_session:
                    db.close()
                    
        return valid_candidates
