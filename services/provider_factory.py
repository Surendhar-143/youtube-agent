from typing import Any
from config.settings import settings
from services.gemini_service import GeminiService
from services.ollama_service import OllamaService

class ProviderFactory:
    """
    Instantiates and returns the appropriate LLM service provider
    based on the application configuration.
    """
    @staticmethod
    def get_provider() -> Any:
        provider_name = settings.LLM_PROVIDER.lower()
        if provider_name == "gemini":
            return GeminiService()
        elif provider_name == "ollama":
            return OllamaService()
        else:
            # Fallback to ollama if invalid provider is specified
            return OllamaService()
