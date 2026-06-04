import unittest
from unittest.mock import patch
from services.provider_factory import ProviderFactory
from services.gemini_service import GeminiService
from services.ollama_service import OllamaService

class TestProviderFactory(unittest.TestCase):
    @patch('services.provider_factory.settings')
    @patch('services.gemini_service.settings')
    def test_get_gemini_provider(self, mock_gemini_settings, mock_factory_settings):
        mock_factory_settings.LLM_PROVIDER = "gemini"
        mock_gemini_settings.GEMINI_API_KEY = "test"
        
        provider = ProviderFactory.get_provider()
        self.assertIsInstance(provider, GeminiService)

    @patch('services.provider_factory.settings')
    def test_get_ollama_provider(self, mock_settings):
        mock_settings.LLM_PROVIDER = "ollama"
        
        provider = ProviderFactory.get_provider()
        self.assertIsInstance(provider, OllamaService)

    @patch('services.provider_factory.settings')
    def test_get_fallback_provider(self, mock_settings):
        mock_settings.LLM_PROVIDER = "invalid"
        
        provider = ProviderFactory.get_provider()
        self.assertIsInstance(provider, OllamaService)

if __name__ == '__main__':
    unittest.main()
