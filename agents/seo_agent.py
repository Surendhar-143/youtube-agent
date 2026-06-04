import json
import logging
from typing import Optional
from sqlalchemy.orm import Session
from database.postgres import SessionLocal
from database.models import Script, SEOMetadata
from services.llm_service import LLMService
from schemas.seo_metadata import SEOMetadataSchema
from prompts.system_prompts import SYSTEM_SEO_AGENT
from prompts.seo_prompts import SEO_PROMPT_TEMPLATE
from config.settings import settings

logger = logging.getLogger("seo_agent")

class SEOAgent:
    """
    Agent responsible for generating optimized YouTube SEO metadata.
    """
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or LLMService()

    def generate_metadata(self, script_id: int, db: Optional[Session] = None) -> SEOMetadataSchema:
        """
        Retrieves the script, queries Ollama for metadata, validates
        character and list length constraints, saves to database, and returns the Pydantic schema.
        """
        logger.info(f"Generating SEO metadata for script_id: {script_id}")
        
        opened_session = False
        if db is None:
            db = SessionLocal()
            opened_session = True
            
        try:
            # 1. Load script
            script_record = db.query(Script).filter(Script.id == script_id).first()
            if not script_record:
                logger.error(f"Script with id {script_id} not found in database.")
                raise ValueError(f"Script with id {script_id} not found.")

            # 2. Call Ollama
            prompt = SEO_PROMPT_TEMPLATE.format(
                title=script_record.title,
                script=script_record.script,
                title_max_len=settings.SEO_TITLE_MAX_LEN,
                description_max_len=settings.SEO_DESCRIPTION_MAX_LEN,
                min_tags=settings.SEO_MIN_TAGS_COUNT,
                min_hashtags=settings.SEO_MIN_HASHTAGS_COUNT
            )
            import time
            from services.ai_audit_service import log_generation

            start_time = time.time()
            success = False
            response_text = ""
            try:
                response_text = self.llm.generate(
                    prompt=prompt,
                    system_prompt=SYSTEM_SEO_AGENT,
                    json_mode=True
                )
                from services.json_utils import parse_json_robust
                raw_seo = parse_json_robust(response_text)
                success = True
            except Exception as e:
                logger.error(f"Failed to generate or parse SEO metadata JSON: {e}")
                duration_ms = int((time.time() - start_time) * 1000)
                try:
                    log_generation(
                        db=db,
                        agent_name="SEOAgent",
                        model=self.llm.model_name,
                        prompt=prompt,
                        response=response_text or str(e),
                        success=False,
                        duration_ms=duration_ms
                    )
                except Exception as log_err:
                    logger.error(f"Failed to write AI audit log: {log_err}")
                raise e

            duration_ms = int((time.time() - start_time) * 1000)
            try:
                log_generation(
                    db=db,
                    agent_name="SEOAgent",
                    model=self.llm.model_name,
                    prompt=prompt,
                    response=response_text,
                    success=True,
                    duration_ms=duration_ms
                )
            except Exception as log_err:
                logger.error(f"Failed to write AI audit log: {log_err}")
            
            # 3. Parse and Validate
            seo_doc = SEOMetadataSchema(**raw_seo)
            
            # Clean and deduplicate
            seo_doc.tags = list(dict.fromkeys([t.strip().lower() for t in seo_doc.tags if t.strip()]))
            seo_doc.hashtags = list(dict.fromkeys([h.strip().lower() for h in seo_doc.hashtags if h.strip()]))
            
            # Apply padding to tags if we have at least a few, but less than required
            if 3 <= len(seo_doc.tags) < settings.SEO_MIN_TAGS_COUNT:
                logger.warning(f"SEO tags count ({len(seo_doc.tags)}) is below {settings.SEO_MIN_TAGS_COUNT} minimum. Applying fallback tag padding.")
                fallback_tags = [
                    "history", "ancient history", "mythology", "mystery", "documentary",
                    "historical mysteries", "ancient legends", "untold stories", "lost civilizations",
                    "historical secrets", "archeology", "ancient secrets", "mysterious events",
                    "unsolved mysteries", "educational", "documentary style", "narrative history",
                    "history channel", "mythology stories", "dark history"
                ]
                for tag in fallback_tags:
                    if len(seo_doc.tags) >= settings.SEO_MIN_TAGS_COUNT:
                        break
                    if tag not in seo_doc.tags:
                        seo_doc.tags.append(tag)
                logger.info(f"Padded SEO tags count is now: {len(seo_doc.tags)}")

            # Apply padding to hashtags if we have at least a few, but less than required
            if 3 <= len(seo_doc.hashtags) < settings.SEO_MIN_HASHTAGS_COUNT:
                logger.warning(f"SEO hashtags count ({len(seo_doc.hashtags)}) is below {settings.SEO_MIN_HASHTAGS_COUNT} minimum. Applying fallback hashtag padding.")
                fallback_hashtags = [
                    "#history", "#mythology", "#mystery", "#ancienthistory", "#documentary",
                    "#unsolved", "#ancientmysteries", "#untoldstories", "#lostcivilizations",
                    "#historicalsecrets", "#archeology", "#darkhistory", "#legends", "#myths"
                ]
                for htag in fallback_hashtags:
                    if len(seo_doc.hashtags) >= settings.SEO_MIN_HASHTAGS_COUNT:
                        break
                    if htag not in seo_doc.hashtags:
                        seo_doc.hashtags.append(htag)
                logger.info(f"Padded SEO hashtags count is now: {len(seo_doc.hashtags)}")

            if len(seo_doc.title) > settings.SEO_TITLE_MAX_LEN:
                logger.error(f"SEO title exceeds {settings.SEO_TITLE_MAX_LEN} character limit: {len(seo_doc.title)} characters")
                raise ValueError(f"SEO Title must be less than or equal to {settings.SEO_TITLE_MAX_LEN} characters.")
                
            if len(seo_doc.description) > settings.SEO_DESCRIPTION_MAX_LEN:
                logger.error(f"SEO description exceeds {settings.SEO_DESCRIPTION_MAX_LEN} character limit: {len(seo_doc.description)} characters")
                raise ValueError(f"SEO Description must be less than or equal to {settings.SEO_DESCRIPTION_MAX_LEN} characters.")
                
            if len(seo_doc.tags) < settings.SEO_MIN_TAGS_COUNT:
                logger.error(f"SEO tags count ({len(seo_doc.tags)}) is below {settings.SEO_MIN_TAGS_COUNT} minimum.")
                raise ValueError(f"SEO must generate at least {settings.SEO_MIN_TAGS_COUNT} tags.")
                
            if len(seo_doc.hashtags) < settings.SEO_MIN_HASHTAGS_COUNT:
                logger.error(f"SEO hashtags count ({len(seo_doc.hashtags)}) is below {settings.SEO_MIN_HASHTAGS_COUNT} minimum.")
                raise ValueError(f"SEO must generate at least {settings.SEO_MIN_HASHTAGS_COUNT} hashtags.")
            
            # 4. Save to database
            seo_record = SEOMetadata(
                script_id=script_id,
                title=seo_doc.title,
                description=seo_doc.description,
                tags=seo_doc.tags,
                hashtags=seo_doc.hashtags
            )
            db.add(seo_record)
            db.commit()
            
            logger.info(f"SEO metadata saved successfully for script_id {script_id}.")
            return seo_doc

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to generate SEO metadata: {e}")
            raise e
        finally:
            if opened_session:
                db.close()
