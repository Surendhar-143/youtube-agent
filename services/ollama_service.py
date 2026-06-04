import json
import urllib.request
import urllib.error
import logging
import time
from typing import List, Optional
from config.settings import settings

logger = logging.getLogger("ollama_service")

class OllamaError(Exception):
    """Base exception for Ollama service."""
    pass

class OllamaConnectionError(OllamaError):
    """Raised when connection to Ollama server fails."""
    pass

class OllamaTimeoutError(OllamaError):
    """Raised when connection to Ollama server times out."""
    pass

class OllamaModelError(OllamaError):
    """Raised when the requested model is invalid or missing."""
    pass

class OllamaService:
    """
    Service layer wrapper for local Ollama LLM execution.
    """
    def __init__(self, base_url: Optional[str] = None, default_model: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_URL).rstrip("/")
        self.default_model = default_model or settings.OLLAMA_MODEL

    def _post(self, path: str, payload: dict, timeout: Optional[float] = None) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        selected_timeout = timeout if timeout is not None else settings.OLLAMA_POST_TIMEOUT
        try:
            logger.info("[TIMING] OllamaService: Before HTTP request")
            start_http = time.time()
            with urllib.request.urlopen(req, timeout=selected_timeout) as response:
                res_data = response.read()
                logger.info(f"[TIMING] OllamaService: After HTTP request (Duration: {time.time() - start_http:.4f}s)")
                return json.loads(res_data.decode("utf-8"))
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                logger.error(f"Ollama request to {url} timed out.")
                raise OllamaTimeoutError(f"Ollama request timed out: {e}")
            logger.error(f"Failed to connect to Ollama at {url}: {e}")
            raise OllamaConnectionError(f"Failed to connect to Ollama: {e}")
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama at {url}: {e}")
            raise OllamaError(f"Ollama call failed: {e}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        json_mode: bool = False,
        timeout: Optional[float] = None
    ) -> str:
        """
        Sends a generation request to the Ollama server.
        """
        selected_model = model or self.default_model
        selected_timeout = timeout if timeout is not None else settings.OLLAMA_GENERATE_TIMEOUT
        
        # Build options dictionary from settings
        options = {
            "temperature": settings.OLLAMA_TEMPERATURE,
            "top_p": settings.OLLAMA_TOP_P,
            "repeat_penalty": settings.OLLAMA_REPEAT_PENALTY,
            "num_predict": settings.OLLAMA_MAX_TOKENS,
            "num_ctx": settings.OLLAMA_NUM_CTX
        }

        payload = {
            "model": selected_model,
            "prompt": prompt,
            "stream": False,
            "options": options
        }
        if system_prompt:
            payload["system"] = system_prompt
        if json_mode:
            payload["format"] = "json"

        # Determine debug name
        debug_name = None
        if system_prompt:
            from prompts.system_prompts import SYSTEM_RESEARCH_AGENT, SYSTEM_SCRIPT_AGENT, SYSTEM_SEO_AGENT, SYSTEM_SCENE_AGENT
            if system_prompt == SYSTEM_RESEARCH_AGENT:
                debug_name = "research"
            elif system_prompt == SYSTEM_SCRIPT_AGENT:
                debug_name = "script"
            elif system_prompt == SYSTEM_SEO_AGENT:
                debug_name = "seo"
            elif system_prompt == SYSTEM_SCENE_AGENT:
                debug_name = "scene"

        if debug_name:
            import os
            os.makedirs("generated/debug", exist_ok=True)
            with open(f"generated/debug/{debug_name}_prompt.txt", "w", encoding="utf-8") as f:
                f.write(prompt)
            words = len(prompt.split())
            chars = len(prompt)
            tokens = int(chars / 4)
            logger.info(f"[DEBUG] Prompt logged to generated/debug/{debug_name}_prompt.txt. Size: {chars} chars, {words} words, ~{tokens} tokens.")

        logger.info(f"Generating content using model '{selected_model}'...")
        response = self._post("/api/generate", payload, timeout=selected_timeout)
        
        logger.info("[TIMING] OllamaService: Before response extraction")
        start_extract = time.time()
        if "response" not in response:
            logger.error("Response body missing 'response' field")
            raise OllamaError("Response body missing 'response' field")
        res_text = response["response"]
        logger.info(f"[TIMING] OllamaService: After response extraction (Duration: {time.time() - start_extract:.4f}s)")
        
        if debug_name:
            with open(f"generated/debug/{debug_name}_response.txt", "w", encoding="utf-8") as f:
                f.write(res_text)
            res_words = len(res_text.split())
            res_chars = len(res_text)
            logger.info(f"[DEBUG] Response logged to generated/debug/{debug_name}_response.txt. Size: {res_chars} chars, {res_words} words.")
            
        return res_text

    def chat(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> str:
        """
        Sends a chat request (multi-message conversation) to the Ollama server.
        """
        selected_model = model or self.default_model
        selected_timeout = timeout if timeout is not None else settings.OLLAMA_CHAT_TIMEOUT
        
        options = {
            "temperature": settings.OLLAMA_TEMPERATURE,
            "top_p": settings.OLLAMA_TOP_P,
            "repeat_penalty": settings.OLLAMA_REPEAT_PENALTY,
            "num_predict": settings.OLLAMA_MAX_TOKENS,
            "num_ctx": settings.OLLAMA_NUM_CTX
        }

        payload = {
            "model": selected_model,
            "messages": messages,
            "stream": False,
            "options": options
        }
        logger.info(f"Starting chat completion using model '{selected_model}'...")
        response = self._post("/api/chat", payload, timeout=selected_timeout)
        
        if "message" not in response or "content" not in response["message"]:
            logger.error("Response body missing expected chat message content")
            raise OllamaError("Response body missing expected chat response format")
            
        return response["message"]["content"]

    def health_check(self) -> bool:
        """
        Returns True if Ollama service is reachable, False otherwise.
        """
        url = f"{self.base_url}/api/tags"
        try:
            with urllib.request.urlopen(url, timeout=5.0) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    def list_models(self) -> List[str]:
        """
        Returns a list of names of models installed on the Ollama instance.
        """
        url = f"{self.base_url}/api/tags"
        try:
            with urllib.request.urlopen(url, timeout=5.0) as response:
                data = json.loads(response.read().decode("utf-8"))
                models = [m["name"] for m in data.get("models", [])]
                return models
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            raise OllamaConnectionError(f"Failed to retrieve models from Ollama: {e}")
