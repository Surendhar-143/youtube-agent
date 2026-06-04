import json
import logging
import re
from typing import List, Optional
from sqlalchemy.orm import Session
from database.postgres import SessionLocal
from database.models import Script, ScenePlan as ScenePlanModel
from services.llm_service import LLMService
from schemas.scene_plan import ScenePlan as ScenePlanSchema, ScenePlanResponse
from prompts.system_prompts import SYSTEM_SCENE_AGENT
from prompts.scene_prompts import SCENE_PROMPT_TEMPLATE
from config.settings import settings

logger = logging.getLogger("scene_agent")

class SceneAgentError(Exception):
    """Base exception for SceneAgent operations."""
    pass


class SceneAgent:
    """
    Agent responsible for breaking down complete YouTube scripts into chronological visual scenes.
    """
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or LLMService()

    def generate_scenes(self, script_id: int, db: Optional[Session] = None) -> List[ScenePlanSchema]:
        """
        Loads the script from DB, segments it into visual scenes using the LLM in paragraph chunks,
        validates the output format, registers/overwrites scene records in the database,
        and returns the list of validated scene plan schemas.
        """
        logger.info(f"Generating scene plans for script_id: {script_id}")

        opened_session = False
        if db is None:
            db = SessionLocal()
            opened_session = True

        try:
            # 1. Retrieve the script
            script_record = db.query(Script).filter(Script.id == script_id).first()
            if not script_record:
                logger.error(f"Script with id {script_id} not found in database.")
                raise SceneAgentError(f"Script with id {script_id} not found.")

            # Split script into paragraphs and group into chunks of max ~500 words
            paragraphs = [p.strip() for p in script_record.script.split('\n\n') if p.strip()]
            total_words = len(script_record.script.split())
            
            if total_words <= 800:
                chunks = [paragraphs]
            else:
                chunks = []
                current_chunk = []
                current_word_count = 0
                for p in paragraphs:
                    p_words = len(p.split())
                    if current_chunk and current_word_count + p_words > 500:
                        chunks.append(current_chunk)
                        current_chunk = [p]
                        current_word_count = p_words
                    else:
                        current_chunk.append(p)
                        current_word_count += p_words
                if current_chunk:
                    chunks.append(current_chunk)

            all_scenes = []
            start_scene_number = 1
            
            logger.info(f"Processing script in {len(chunks)} chunks...")
            import time
            from services.ai_audit_service import log_generation

            for chunk_idx, chunk_paragraphs in enumerate(chunks):
                chunk_text = "\n\n".join(chunk_paragraphs)
                chunk_word_count = len(chunk_text.split())
                
                # Dynamic scene count bound for this chunk
                min_scenes = max(3, round(chunk_word_count / 150))
                max_scenes = max(5, round(chunk_word_count / 80))
                
                # Adapt prompt template for chunk
                prompt_template = SCENE_PROMPT_TEMPLATE
                prompt_template = prompt_template.replace(
                    "- For a script of this length, you MUST generate between 12 and 25 scenes.\n- Fewer than 12 scenes creates a boring, static video. This is UNACCEPTABLE.\n- More than 25 scenes creates confusion. Stay within the 12–25 range.",
                    f"- For this segment of the script (word count: {chunk_word_count}), you MUST generate between {min_scenes} and {max_scenes} scenes.\n- The scene sequence MUST start numbering from {start_scene_number}."
                )
                prompt_template = prompt_template.replace(
                    "1. scene_number: Sequential integer starting from 1.",
                    f"1. scene_number: Sequential integer starting from {start_scene_number}."
                )
                
                prompt = prompt_template.format(
                    title=f"{script_record.title} (Part {chunk_idx + 1}/{len(chunks)})",
                    script=chunk_text,
                    words_per_second=settings.SPEECH_WORDS_PER_SECOND
                )
                
                logger.info(f"Calling LLM for scene segmentation (Chunk {chunk_idx + 1}/{len(chunks)}, starting scene {start_scene_number})...")
                start_time = time.time()
                try:
                    response_text = self.llm.generate(
                        prompt=prompt,
                        system_prompt=SYSTEM_SCENE_AGENT,
                        json_mode=True
                    )
                except Exception as e:
                    logger.error(f"Failed to generate scene plan for chunk {chunk_idx + 1}: {e}")
                    duration_ms = int((time.time() - start_time) * 1000)
                    try:
                        log_generation(
                            db=db,
                            agent_name=f"SceneAgent_Chunk_{chunk_idx + 1}",
                            model=self.llm.model_name,
                            prompt=prompt,
                            response=str(e),
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
                        agent_name=f"SceneAgent_Chunk_{chunk_idx + 1}",
                        model=self.llm.model_name,
                        prompt=prompt,
                        response=response_text,
                        success=True,
                        duration_ms=duration_ms
                    )
                except Exception as log_err:
                    logger.error(f"Failed to write AI audit log: {log_err}")

                # 3. Parse and Validate Pydantic Schema for this chunk
                try:
                    raw_response = json.loads(response_text)
                    response_doc = ScenePlanResponse(**raw_response)
                except Exception as e:
                    logger.error(f"JSON parsing/validation failed for chunk {chunk_idx + 1}: {e}. Raw response: {response_text}")
                    raise SceneAgentError(f"Invalid visual scene response format for chunk {chunk_idx + 1}: {e}")

                chunk_scenes = response_doc.scenes
                if not chunk_scenes:
                    logger.error(f"No scenes generated for chunk {chunk_idx + 1}.")
                    raise SceneAgentError(f"LLM returned an empty list of scenes for chunk {chunk_idx + 1}.")

                # Enforce chronological ordering and exact starting number offset
                for offset, s in enumerate(chunk_scenes):
                    s.scene_number = start_scene_number + offset

                all_scenes.extend(chunk_scenes)
                start_scene_number += len(chunk_scenes)

            # 4. Clean up any existing scene plans for this script (Idempotency)
            existing_count = db.query(ScenePlanModel).filter(ScenePlanModel.script_id == script_id).count()
            if existing_count > 0:
                logger.info(f"Deleting {existing_count} existing scene plans for script {script_id}")
                db.query(ScenePlanModel).filter(ScenePlanModel.script_id == script_id).delete()
                db.commit()

            # 5. Save to database
            logger.info(f"Saving {len(all_scenes)} new scene plans to database...")
            db_models = []
            for s in all_scenes:
                db_model = ScenePlanModel(
                    script_id=script_id,
                    scene_number=s.scene_number,
                    title=s.title,
                    description=s.description,
                    narration_text=s.narration_text,
                    estimated_duration=s.estimated_duration,
                    visual_type=s.visual_type,
                    keywords=s.keywords
                )
                db.add(db_model)
                db_models.append(db_model)
                
            db.commit()

            # Refresh and map back to Pydantic objects
            result = []
            for db_model in db_models:
                db.refresh(db_model)
                result.append(ScenePlanSchema.model_validate(db_model))

            logger.info(f"Successfully generated and stored {len(result)} scenes for script_id {script_id}.")
            return result

        except Exception as e:
            db.rollback()
            if not isinstance(e, SceneAgentError):
                logger.error(f"Unexpected error in SceneAgent: {e}")
                raise SceneAgentError(f"Failed to generate scene plan: {e}")
            raise
        finally:
            if opened_session:
                db.close()
