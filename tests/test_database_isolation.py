import unittest
from config.settings import settings
from database.session_factory import validate_database_urls, get_production_session, get_test_session

class TestDatabaseIsolation(unittest.TestCase):
    def test_database_url_equality_checks(self):
        """Verifies that validation throws ValueError if DATABASE_URL equals TEST_DATABASE_URL."""
        # Safety validation should pass with distinct configurations
        try:
            validate_database_urls()
        except ValueError as e:
            self.fail(f"validate_database_urls raised ValueError unexpectedly: {e}")

        # Temporarily mock URLs to be identical and assert exception
        old_prod_url = settings.DATABASE_URL
        try:
            settings.DATABASE_URL = settings.TEST_DATABASE_URL
            with self.assertRaises(ValueError) as context:
                validate_database_urls()
            self.assertIn("cannot be the same", str(context.exception))
        finally:
            settings.DATABASE_URL = old_prod_url

    def test_session_retrieval(self):
        """Checks if session factory retrieves correct session connections."""
        # Ensure we can construct and close production and test sessions
        prod_sess = get_production_session()
        self.assertIsNotNone(prod_sess)
        prod_sess.close()

        test_sess = get_test_session()
        self.assertIsNotNone(test_sess)
        test_sess.close()
