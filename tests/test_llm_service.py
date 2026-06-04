import unittest
from unittest.mock import MagicMock
from services.llm_service import LLMService

class TestLLMService(unittest.TestCase):
    def test_generate_delegates_to_provider(self):
        mock_provider = MagicMock()
        mock_provider.generate.return_value = "Delegated response"
        
        service = LLMService(provider=mock_provider)
        response = service.generate(prompt="Test prompt")
        
        self.assertEqual(response, "Delegated response")
        mock_provider.generate.assert_called_once_with(
            prompt="Test prompt",
            system_prompt=None,
            model=None,
            json_mode=False,
            timeout=None
        )

    def test_generate_json_delegates(self):
        mock_provider = MagicMock()
        # Mocking that it has generate_json
        mock_provider.generate_json.return_value = {"key": "value"}
        
        service = LLMService(provider=mock_provider)
        response = service.generate_json(prompt="Test prompt")
        
        self.assertEqual(response, {"key": "value"})
        mock_provider.generate_json.assert_called_once_with(
            prompt="Test prompt",
            system_prompt=None,
            model=None,
            timeout=None
        )

    def test_generate_json_fallback(self):
        # When provider doesn't have generate_json (like OllamaService)
        class MockOllama:
            def generate(self, prompt, system_prompt=None, model=None, json_mode=False, timeout=None):
                return '{"fallback": true}'
                
        service = LLMService(provider=MockOllama())
        response = service.generate_json(prompt="Test")
        
        self.assertEqual(response, {"fallback": True})

if __name__ == '__main__':
    unittest.main()
