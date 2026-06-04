import os
import re
import logging
from typing import Optional
from sqlalchemy.orm import Session
from database.postgres import SessionLocal
from database.models import Script
from services.piper_service import PiperService
from services.audio_validator import AudioValidator
from services.audio_storage import AudioStorage
from schemas.audio_document import AudioDocument

logger = logging.getLogger("voice_agent")

class VoiceAgentError(Exception):
    """Exception raised by VoiceAgent operations."""
    pass


class VoiceAgent:
    """
    Agent responsible for processing script texts, generating narration audio,
    validating output quality/duration, and managing database assets.
    """
    def __init__(
        self,
        piper_service: Optional[PiperService] = None,
        audio_validator: Optional[AudioValidator] = None,
        audio_storage: Optional[AudioStorage] = None
    ):
        self.piper = piper_service or PiperService()
        self.validator = audio_validator or AudioValidator()
        self.storage = audio_storage or AudioStorage()

    def generate_audio(self, script_id: int, db: Optional[Session] = None) -> AudioDocument:
        """
        Loads the script from database, cleans text, synthesizes voice wav, validates duration,
        saves to managed storage, registers the AudioAsset in DB, and returns AudioDocument.
        """
        logger.info(f"Starting voice synthesis workflow for script_id: {script_id}")

        opened_session = False
        if db is None:
            db = SessionLocal()
            opened_session = True

        temp_wav = None
        try:
            # 1. Retrieve script
            script_record = db.query(Script).filter(Script.id == script_id).first()
            if not script_record:
                logger.error(f"Script with id {script_id} not found in database.")
                raise VoiceAgentError(f"Script with id {script_id} not found in database.")

            # 2. Clean script text
            cleaned_text = self._clean_text(script_record.script)
            if not cleaned_text.strip():
                logger.error(f"Script {script_id} content is empty or resulted in empty text after cleaning.")
                raise VoiceAgentError(f"Script {script_id} contains no speakable text.")

            logger.info(f"Cleaned script text preview (len={len(cleaned_text)}): {cleaned_text[:120]}...")

            # 3. Synthesize to temporary WAV file
            temp_wav = os.path.join(self.storage.base_dir, f"temp_synthesis_{script_id}.wav")
            logger.info(f"Synthesizing audio to temporary file: {temp_wav}")
            self.piper.synthesize(cleaned_text, temp_wav)

            # 4. Validate output
            logger.info("Validating synthesized WAV file...")
            validation_result = self.validator.validate(temp_wav)
            duration = validation_result["duration"]
            logger.info(f"WAV validation successful. Duration: {duration:.2f} seconds.")

            # 5. Move to final managed storage location
            final_path = self.storage.store_audio_file(script_id, temp_wav)

            # 6. Persist AudioAsset in database
            voice_info = self.piper.get_voice_info()
            voice_model_name = voice_info.get("voice_name", "en_US-lessac-medium")

            asset_record = self.storage.sync_db_asset(
                db=db,
                script_id=script_id,
                audio_path=str(final_path),
                duration_seconds=duration,
                voice_model=voice_model_name
            )

            # 7. Convert and return AudioDocument
            audio_doc = AudioDocument.model_validate(asset_record)
            logger.info(f"Voice synthesis workflow completed successfully for script {script_id}.")
            return audio_doc

        except Exception as e:
            if not isinstance(e, VoiceAgentError):
                logger.error(f"Unexpected error in VoiceAgent: {e}")
                raise VoiceAgentError(f"Failed to generate narration audio: {e}")
            raise
        finally:
            # Clean up temp file
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.unlink(temp_wav)
                    logger.debug(f"Temporary synthesis file cleaned up: {temp_wav}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {temp_wav}: {e}")

            if opened_session:
                db.close()

    def _clean_text(self, text: str) -> str:
        """
        Cleans the script text by removing markdown headers, bold/italic markers,
        narrator cues in brackets (e.g. [Narrator], (Intro music)), and extra white spaces.
        """
        if not text:
            return ""

        # Remove markdown headers: e.g. # Title, ## Header
        text = re.sub(r'#+\s+', '', text)

        # Remove bold, italic, and inline markdown: e.g. **bold**, *italic*, _italic_
        text = re.sub(r'\*\*|__', '', text)
        text = re.sub(r'\*|_', '', text)

        # Remove bracketed and parenthesized production cues (e.g., [Host Intro], (sound effect))
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)

        # Replace carriage returns and newlines with spaces
        text = text.replace('\r', ' ').replace('\n', ' ')

        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text)

        return text.strip()
