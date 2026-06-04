import unittest
from config.settings import settings

class TestSettings(unittest.TestCase):
    def test_settings_fields_resolved(self):
        """Verifies that all Phase 4.9 settings are populated with appropriate values."""
        self.assertEqual(settings.APP_NAME, "YACE")
        self.assertIsNotNone(settings.DATABASE_URL)
        self.assertIsNotNone(settings.TEST_DATABASE_URL)
        
        # Ollama bounds
        self.assertIsNotNone(settings.OLLAMA_URL)
        self.assertIsNotNone(settings.OLLAMA_MODEL)
        self.assertEqual(settings.OLLAMA_TEMPERATURE, 0.7)
        self.assertGreaterEqual(settings.OLLAMA_MAX_TOKENS, 4096)  # Phase 4.95: increased for longer scripts

        # Content Generation bounds
        self.assertEqual(settings.CONTENT_TOPICS_COUNT, 10)
        self.assertEqual(settings.CONTENT_MIN_TOPIC_SCORE, 70.0)
        self.assertEqual(settings.CONTENT_SCRIPT_MIN_WORDS, 50)
        self.assertEqual(settings.CONTENT_SCRIPT_MAX_WORDS, 150)

        # SEO bounds
        self.assertEqual(settings.SEO_TITLE_MAX_LEN, 100)
        self.assertEqual(settings.SEO_MIN_TAGS_COUNT, 15)

        # Media Processing
        self.assertIsNotNone(settings.FFMPEG_PATH)
        self.assertEqual(settings.FFMPEG_VIDEO_CODEC, "libx264")
        self.assertEqual(settings.FFMPEG_AUDIO_CODEC, "aac")

        # Subtitles Settings
        self.assertEqual(settings.SUBTITLE_CHARS_PER_LINE, 20)
        self.assertEqual(settings.SUBTITLE_MAX_LINES, 1)
        self.assertEqual(settings.SUBTITLE_FONT_NAME, "Arial")

        # Storage Paths
        self.assertEqual(settings.PATH_SCRIPTS_DIR, "generated/scripts")
        self.assertEqual(settings.PATH_AUDIO_DIR, "generated/audio")
