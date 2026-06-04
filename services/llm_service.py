import os
import logging
from typing import Optional, Any
from services.provider_factory import ProviderFactory

logger = logging.getLogger("llm_service")

class LLMService:
    """
    Unified LLM service interface for all agents.
    Delegates to the configured provider (Gemini or Ollama).
    """
    def __init__(self, provider: Optional[Any] = None):
        # Allow injecting a provider for testing, otherwise use the factory
        self.provider = provider or ProviderFactory.get_provider()

    @property
    def model_name(self) -> str:
        """Returns the configured default model of the underlying provider."""
        return getattr(self.provider, "default_model", "unknown")

    def _log_debug(self, debug_name: str, text: str, prefix: str):
        """Helper to log debug prompts and responses."""
        os.makedirs("generated/debug", exist_ok=True)
        filepath = f"generated/debug/{debug_name}_{prefix}.txt"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        
        words = len(text.split())
        chars = len(text)
        logger.info(f"[DEBUG] {prefix.capitalize()} logged to {filepath}. Size: {chars} chars, {words} words.")

    def _handle_debug(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Determines debug name and logs prompt if applicable."""
        debug_name = None
        if system_prompt:
            try:
                # We do this lazily to avoid circular imports if any
                from prompts.system_prompts import (
                    SYSTEM_RESEARCH_AGENT, 
                    SYSTEM_SCRIPT_AGENT, 
                    SYSTEM_SEO_AGENT, 
                    SYSTEM_SCENE_AGENT
                )
                if system_prompt == SYSTEM_RESEARCH_AGENT:
                    debug_name = "research"
                elif system_prompt == SYSTEM_SCRIPT_AGENT:
                    debug_name = "script"
                elif system_prompt == SYSTEM_SEO_AGENT:
                    debug_name = "seo"
                elif system_prompt == SYSTEM_SCENE_AGENT:
                    debug_name = "scene"
            except ImportError:
                pass
                
        if debug_name:
            self._log_debug(debug_name, prompt, "prompt")
            
        return debug_name

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        json_mode: bool = False,
        timeout: Optional[float] = None
    ) -> str:
        """
        Sends a generation request to the underlying LLM provider.
        """
        debug_name = self._handle_debug(prompt, system_prompt)
        
        # If the provider is Ollama, it doesn't have generate_json as a separate method usually.
        # But wait, the instruction says "Agents should only use LLMService... generate and generate_json".
        # We need to map it accordingly. If the provider is GeminiService, we use generate. 
        # If json_mode is passed directly, we use it.
        
        # We will use the underlying provider's generate method.
        # Wait, if it's gemini, it has generate.
        response_text = self.provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            json_mode=json_mode,
            timeout=timeout
        )
        
        if debug_name:
            self._log_debug(debug_name, response_text, "response")
            
        return response_text

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
        debug_name = self._handle_debug(prompt, system_prompt)
        
        # Check if the provider has a dedicated generate_json method
        if hasattr(self.provider, "generate_json"):
            result = self.provider.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                timeout=timeout
            )
            if debug_name:
                import json
                self._log_debug(debug_name, json.dumps(result, indent=2), "response")
            return result
        else:
            # Fallback for OllamaService
            import json
            response_text = self.provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                json_mode=True,
                timeout=timeout
            )
            if debug_name:
                self._log_debug(debug_name, response_text, "response")
                
            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise ValueError(f"Failed to parse JSON response: {e}")

    def health_check(self) -> dict | bool:
        """
        Checks the health of the underlying LLM provider.
        """
        return self.provider.health_check()
