import unittest
from database.postgres import SessionLocal
from database.models import AIGeneration
from services.ai_audit_service import log_generation

class TestAIAuditService(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        # Clean existing audit records
        self.db.query(AIGeneration).delete()
        self.db.commit()

    def tearDown(self):
        self.db.query(AIGeneration).delete()
        self.db.commit()
        self.db.close()

    def test_log_generation_success(self):
        """Verifies logging successful AI model outputs."""
        agent_name = "TestAgent"
        model = "test-model"
        prompt = "Hello model"
        response = "Hello user"
        success = True
        duration_ms = 150

        # Execute
        audit_record = log_generation(
            db=self.db,
            agent_name=agent_name,
            model=model,
            prompt=prompt,
            response=response,
            success=success,
            duration_ms=duration_ms
        )

        self.assertIsNotNone(audit_record)
        self.assertEqual(audit_record.agent_name, agent_name)
        self.assertEqual(audit_record.model, model)
        self.assertEqual(audit_record.prompt, prompt)
        self.assertEqual(audit_record.response, response)
        self.assertTrue(audit_record.success)
        self.assertEqual(audit_record.duration_ms, duration_ms)

        # Retrieve from DB to verify persistence
        db_record = self.db.query(AIGeneration).filter(AIGeneration.id == audit_record.id).first()
        self.assertIsNotNone(db_record)
        self.assertEqual(db_record.agent_name, agent_name)
        self.assertEqual(db_record.success, True)

    def test_log_generation_failure(self):
        """Verifies logging failed AI model queries (exceptions or connection errors)."""
        agent_name = "ScriptAgent"
        model = "qwen3:14b"
        prompt = "Create script for tech topic"
        response = "OllamaTimeoutError: Connection timed out"
        success = False
        duration_ms = 120000

        # Execute
        audit_record = log_generation(
            db=self.db,
            agent_name=agent_name,
            model=model,
            prompt=prompt,
            response=response,
            success=success,
            duration_ms=duration_ms
        )

        self.assertIsNotNone(audit_record)
        self.assertEqual(audit_record.agent_name, agent_name)
        self.assertFalse(audit_record.success)
        self.assertEqual(audit_record.duration_ms, duration_ms)

        # Query and assert
        db_record = self.db.query(AIGeneration).filter(AIGeneration.id == audit_record.id).first()
        self.assertIsNotNone(db_record)
        self.assertEqual(db_record.success, False)
        self.assertEqual(db_record.response, response)
