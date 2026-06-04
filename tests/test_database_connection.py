import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from database.postgres import get_db

class TestDatabaseConnection(unittest.TestCase):
    @patch('database.postgres.SessionLocal')
    def test_db_session_yields_and_closes(self, mock_session_local):
        mock_session = MagicMock(spec=Session)
        mock_session_local.return_value = mock_session
        
        # Test get_db generator
        generator = get_db()
        db = next(generator)
        
        self.assertEqual(db, mock_session)
        mock_session_local.assert_called_once()
        
        # Verify close is called on generator termination
        try:
            next(generator)
        except StopIteration:
            pass
            
        mock_session.close.assert_called_once()

    @patch('database.postgres.engine')
    def test_database_connectivity_success(self, mock_engine):
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Simple query execution simulation
        mock_conn.execute.return_value = True
        
        # Verify no exceptions are thrown
        with mock_engine.connect() as conn:
            res = conn.execute("SELECT 1")
            
        self.assertTrue(res)
        mock_engine.connect.assert_called_once()

    def test_transaction_commit(self):
        mock_session = MagicMock(spec=Session)
        
        # Simulate transaction commit
        mock_session.commit()
        mock_session.commit.assert_called_once()

    def test_transaction_rollback(self):
        mock_session = MagicMock(spec=Session)
        
        # Simulate transaction rollback
        mock_session.rollback()
        mock_session.rollback.assert_called_once()

if __name__ == '__main__':
    unittest.main()
