import json
import logging
import time
from typing import Optional, Any
from google import genai
from google.genai import types
from google.genai.errors import APIError
from config.settings import settings
from services.exceptions import (
    LLMError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMResponseError
)

logger = logging.getLogger("gemini_service")

class GeminiService:
    """
    Service layer wrapper for Gemini LLM execution using google-genai SDK.
    Supports automatic API key rotation across up to 2 keys to handle
    per-key daily rate limits (free tier: 20 requests/day/key).
    """

    # Class-level: shared across all instances in the same process
    _active_key_index: int = 0

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        # Build ordered key list: primary key first, secondary key second
        primary   = api_key or settings.GEMINI_API_KEY
        secondary = getattr(settings, "GEMINI_API_KEY_2", "") or ""

        self.api_keys: list[str] = [k for k in [primary, secondary] if k]
        if not self.api_keys:
            raise LLMAuthenticationError("No GEMINI_API_KEY configured")

        self.default_model = default_model or settings.GEMINI_MODEL
        self._init_client()

    def _init_client(self) -> None:
        """Create a genai.Client using the currently active API key."""
        key = self.api_keys[GeminiService._active_key_index % len(self.api_keys)]
        self.api_key  = key
        self.client   = genai.Client(api_key=key)
        logger.info(
            f"GeminiService using key #{GeminiService._active_key_index + 1} "
            f"(last 6 chars: ...{key[-6:]})"
        )

    def _rotate_key(self) -> bool:
        """
        Advance to the next API key.  Returns True if a new key is available,
        False if we have already cycled through all keys.
        """
        next_index = GeminiService._active_key_index + 1
        if next_index >= len(self.api_keys):
            logger.error("All Gemini API keys have been exhausted (rate limited).")
            return False
        GeminiService._active_key_index = next_index
        logger.warning(
            f"Rotating to Gemini API key #{next_index + 1} after rate limit on key #{next_index}."
        )
        self._init_client()
        return True

    def _map_error(self, e: Exception) -> Exception:
        """Map google-genai errors to standard LLM exceptions."""
        if isinstance(e, APIError):
            if e.code == 401 or e.code == 403:
                return LLMAuthenticationError(f"Authentication failed: {e.message}")
            elif e.code == 429:
                return LLMRateLimitError(f"Rate limit exceeded: {e.message}")
            elif e.code == 503 or e.code == 504:
                return LLMTimeoutError(f"Service unavailable or timed out: {e.message}")
            else:
                return LLMResponseError(f"API Error ({e.code}): {e.message}")
        
        # Generic fallback
        error_str = str(e).lower()
        if "timeout" in error_str:
            return LLMTimeoutError(f"Request timed out: {e}")
        elif "connection" in error_str or "network" in error_str:
            return LLMConnectionError(f"Connection failed: {e}")
            
        return LLMError(f"Unexpected error: {e}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        json_mode: bool = False,
        timeout: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Sends a generation request to the Gemini API.
        """
        selected_model = model or self.default_model
        
        safety_settings = [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
        ]

        config_kwargs: dict[str, Any] = {
            "temperature": settings.GEMINI_TEMPERATURE,
            "max_output_tokens": max_tokens if max_tokens is not None else settings.GEMINI_MAX_TOKENS,
            "safety_settings": safety_settings,
        }
        
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt
            
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"
            
        config = types.GenerateContentConfig(**config_kwargs)

        logger.info(f"Generating content using model '{selected_model}'...")
        logger.info("[TIMING] GeminiService: Before API call")
        start_api = time.time()

        # Try with current key; rotate once on rate limit
        for attempt in range(len(self.api_keys)):
            try:
                response = self.client.models.generate_content(
                    model=selected_model,
                    contents=prompt,
                    config=config
                )
                logger.info(f"[TIMING] GeminiService: After API call (Duration: {time.time() - start_api:.4f}s)")

                if response.candidates:
                    candidate = response.candidates[0]
                    logger.info(f"Gemini response finish reason: {candidate.finish_reason}")
                    if str(candidate.finish_reason) != "STOP":
                        logger.warning(f"Gemini response did not finish normally. Finish reason: {candidate.finish_reason}")

                if not response.text:
                    raise LLMResponseError("Response body missing text content")

                return response.text

            except Exception as e:
                mapped = self._map_error(e)
                if isinstance(mapped, LLMRateLimitError) and attempt < len(self.api_keys) - 1:
                    logger.warning(f"Rate limit hit on attempt {attempt + 1}. Trying next API key...")
                    if self._rotate_key():
                        start_api = time.time()  # reset timer for new attempt
                        continue
                logger.error(f"Failed to generate content: {e}")
                raise mapped

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> dict | list:
        """
        Sends a generation request specifically for structured JSON output.
        """
        response_text = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            json_mode=True,
            timeout=timeout
        )
        
        # Clean markdown code block if present
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
            
        if text.endswith("```"):
            text = text[:-3]
            
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw text: {response_text}")
            raise LLMResponseError(f"Failed to parse JSON response: {e}")

    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """
        Return estimated token count for the given text.
        """
        selected_model = model or self.default_model
        try:
            response = self.client.models.count_tokens(
                model=selected_model,
                contents=text
            )
            return response.total_tokens
        except Exception as e:
            logger.error(f"Failed to count tokens: {e}")
            raise self._map_error(e)

    def health_check(self) -> dict:
        """
        Returns a status object for the Gemini service.
        """
        start_time = time.time()
        try:
            # Send a minimal prompt to verify connectivity and API key
            self.generate(prompt="Hello", max_tokens=5)
            latency = time.time() - start_time
            return {
                "provider": "gemini",
                "connected": True,
                "model": self.default_model,
                "latency": latency
            }
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return {
                "provider": "gemini",
                "connected": False,
                "model": self.default_model,
                "error": str(e)
            }
