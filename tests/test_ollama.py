import unittest
from services.ollama_service import OllamaService, OllamaError

class TestOllamaService(unittest.TestCase):
    def setUp(self):
        self.ollama = OllamaService()

    def test_health_check(self):
        is_healthy = self.ollama.health_check()
        self.assertTrue(is_healthy, "Ollama service is not reachable. Is it running?")

    def test_list_models(self):
        models = self.ollama.list_models()
        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 0, "No models installed in local Ollama.")
        print(f"\nInstalled models: {models}")

    def test_generate_hello(self):
        try:
            response = self.ollama.generate("Say Hello")
            self.assertIsInstance(response, str)
            self.assertGreater(len(response.strip()), 0)
            # Encode safely for Windows consoles that don't support all Unicode (e.g. emojis)
            safe_response = response.strip().encode("ascii", errors="backslashreplace").decode("ascii")
            print(f"\nOllama response: {safe_response}")
        except OllamaError as e:
            self.fail(f"Ollama generate failed with error: {e}")

if __name__ == "__main__":
    unittest.main()
