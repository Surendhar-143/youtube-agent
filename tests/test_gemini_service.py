import unittest
from unittest.mock import patch, MagicMock
from services.gemini_service import GeminiService
from services.exceptions import LLMAuthenticationError, LLMResponseError

class TestGeminiService(unittest.TestCase):
    @patch('services.gemini_service.settings')
    def test_init_no_api_key(self, mock_settings):
        mock_settings.GEMINI_API_KEY = ""
        with self.assertRaises(LLMAuthenticationError):
            GeminiService()

    @patch('services.gemini_service.genai.Client')
    @patch('services.gemini_service.settings')
    def test_generate_success(self, mock_settings, mock_client):
        mock_settings.GEMINI_API_KEY = "test_key"
        mock_settings.GEMINI_MODEL = "test_model"
        
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        mock_response = MagicMock()
        mock_response.text = "Hello world"
        mock_instance.models.generate_content.return_value = mock_response
        
        service = GeminiService()
        response = service.generate("Hi")
        
        self.assertEqual(response, "Hello world")
        mock_instance.models.generate_content.assert_called_once()

    @patch('services.gemini_service.genai.Client')
    @patch('services.gemini_service.settings')
    def test_generate_json(self, mock_settings, mock_client):
        mock_settings.GEMINI_API_KEY = "test_key"
        
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        mock_response = MagicMock()
        mock_response.text = '```json\n{"score": 10}\n```'
        mock_instance.models.generate_content.return_value = mock_response
        
        service = GeminiService()
        result = service.generate_json("Prompt")
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("score"), 10)

    @patch('services.gemini_service.genai.Client')
    @patch('services.gemini_service.settings')
    def test_generate_json_invalid(self, mock_settings, mock_client):
        mock_settings.GEMINI_API_KEY = "test_key"
        
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        mock_response = MagicMock()
        mock_response.text = 'Invalid JSON'
        mock_instance.models.generate_content.return_value = mock_response
        
        service = GeminiService()
        with self.assertRaises(LLMResponseError):
            service.generate_json("Prompt")

if __name__ == '__main__':
    unittest.main()
