import json
import logging
from typing import Optional
from sqlalchemy.orm import Session
from database.postgres import SessionLocal
from database.models import Topic, Script
from services.llm_service import LLMService
from schemas.script_document import ScriptDocument
from prompts.system_prompts import SYSTEM_SCRIPT_AGENT
from prompts.script_prompts import SCRIPT_PROMPT_TEMPLATE
from config.settings import settings

logger = logging.getLogger("script_agent")

def extract_text(val) -> str:
    """Recursively extracts and joins text values from nested list or dict structures."""
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        return "\n\n".join(extract_text(item) for item in val if item)
    if isinstance(val, dict):
        return "\n\n".join(extract_text(v) for v in val.values() if v)
    return str(val)

def parse_json_preserving_duplicates(json_str: str) -> dict:
    """Parses JSON string into a dict, preserving duplicate keys as lists of values."""
    def object_pairs_hook(pairs):
        res = {}
        for k, v in pairs:
            if k in res:
                if isinstance(res[k], list):
                    res[k].append(v)
                else:
                    res[k] = [res[k], v]
            else:
                res[k] = v
        return res
    return json.loads(json_str, object_pairs_hook=object_pairs_hook)

def clean_parsed_dict(d: dict) -> dict:
    """Standardizes parsed fields to match expected Pydantic and database schemas."""
    cleaned = {}
    for k, v in d.items():
        if k == "script":
            cleaned[k] = extract_text(v)
        elif k in ("hook", "title"):
            if isinstance(v, list):
                v_str = [item for item in v if isinstance(item, str)]
                cleaned[k] = v_str[0] if v_str else str(v)
            else:
                cleaned[k] = str(v)
        elif k in ("estimated_minutes", "word_count"):
            if isinstance(v, list):
                try:
                    cleaned[k] = int(v[-1])
                except (ValueError, TypeError):
                    cleaned[k] = 1 if k == "estimated_minutes" else 100
            else:
                try:
                    cleaned[k] = int(v)
                except (ValueError, TypeError):
                    cleaned[k] = 1 if k == "estimated_minutes" else 100
        else:
            cleaned[k] = v
    return cleaned

class ScriptAgent:
    """
    Agent responsible for generating structured YouTube scripts from topics.
    """
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or LLMService()

    def generate_script(self, topic_id: int, db: Optional[Session] = None) -> ScriptDocument:
        """
        Loads the topic from the database, generates a full script using Ollama,
        validates word counts, persists the script, and returns the Pydantic document.
        """
        logger.info(f"Generating script for topic_id: {topic_id}")
        
        opened_session = False
        if db is None:
            db = SessionLocal()
            opened_session = True
            
        try:
            # 1. Load topic
            topic_record = db.query(Topic).filter(Topic.id == topic_id).first()
            if not topic_record:
                logger.error(f"Topic with id {topic_id} not found in database.")
                raise ValueError(f"Topic with id {topic_id} not found.")

            # 2. Call Ollama
            prompt = SCRIPT_PROMPT_TEMPLATE.format(
                topic=topic_record.topic,
                min_words=settings.CONTENT_SCRIPT_MIN_WORDS,
                max_words=settings.CONTENT_SCRIPT_MAX_WORDS
            )
            import time
            from services.ai_audit_service import log_generation

            start_time = time.time()
            success = False
            response_text = ""
            try:
                response_text = self.llm.generate(
                    prompt=prompt,
                    system_prompt=SYSTEM_SCRIPT_AGENT,
                    json_mode=True
                )
                raw_script = parse_json_preserving_duplicates(response_text)
                raw_script = clean_parsed_dict(raw_script)
                success = True
            except Exception as e:
                logger.error(f"Failed to generate or parse script JSON: {e}")
                duration_ms = int((time.time() - start_time) * 1000)
                try:
                    log_generation(
                        db=db,
                        agent_name="ScriptAgent",
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
                    agent_name="ScriptAgent",
                    model=self.llm.model_name,
                    prompt=prompt,
                    response=response_text,
                    success=True,
                    duration_ms=duration_ms
                )
            except Exception as log_err:
                logger.error(f"Failed to write AI audit log: {log_err}")
            
            # 3. Parse and Validate
            script_doc = ScriptDocument(**raw_script)
            
            # Validate word count (between 50 and 150 words)
            actual_word_count = len(script_doc.script.split())
            logger.info(f"Generated script actual word count: {actual_word_count} (Pydantic reported: {script_doc.word_count})")
            
            if actual_word_count < settings.CONTENT_SCRIPT_MIN_WORDS:
                logger.error(f"Script rejected: Word count ({actual_word_count}) is less than {settings.CONTENT_SCRIPT_MIN_WORDS} minimum.")
                raise ValueError(f"Script word count ({actual_word_count}) is below {settings.CONTENT_SCRIPT_MIN_WORDS} words.")
                
            if actual_word_count > settings.CONTENT_SCRIPT_MAX_WORDS:
                logger.error(f"Script rejected: Word count ({actual_word_count}) is more than {settings.CONTENT_SCRIPT_MAX_WORDS} maximum.")
                raise ValueError(f"Script word count ({actual_word_count}) is above {settings.CONTENT_SCRIPT_MAX_WORDS} words.")
            
            # 4. Save to database
            script_record = Script(
                title=script_doc.title,
                script=script_doc.script,
                topic_id=topic_id
            )
            db.add(script_record)
            db.commit()
            
            # Update topic status
            topic_record.status = "completed"
            db.commit()
            
            logger.info(f"Script saved successfully for topic_id {topic_id}.")
            return script_doc

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to generate script: {e}")
            raise e
        finally:
            if opened_session:
                db.close()
