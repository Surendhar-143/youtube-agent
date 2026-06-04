import unittest
import sys
from config.settings import settings
from database.postgres import db_url, engine

class TestConfig(unittest.TestCase):
    def test_running_under_test_environment(self):
        """Verifies that the test engine connects strictly to the test database url."""
        # Ensure 'unittest' is loaded
        self.assertIn("unittest", sys.modules)
        
        # Verify db_url matches settings.TEST_DATABASE_URL
        self.assertEqual(db_url, settings.TEST_DATABASE_URL)
        
        # Verify the engine url matches TEST_DATABASE_URL (handling URL-encoding differences)
        import urllib.parse
        self.assertEqual(
            urllib.parse.unquote_plus(engine.url.render_as_string(hide_password=False)),
            urllib.parse.unquote_plus(settings.TEST_DATABASE_URL)
        )
        
        # Verify safety validation is working (DATABASE_URL cannot equal TEST_DATABASE_URL)
        from database.session_factory import validate_database_urls
        
        # Temporarily mock settings to be equal and check if it raises ValueError
        old_db_url = settings.DATABASE_URL
        try:
            settings.DATABASE_URL = settings.TEST_DATABASE_URL
            with self.assertRaises(ValueError):
                validate_database_urls()
        finally:
            settings.DATABASE_URL = old_db_url
