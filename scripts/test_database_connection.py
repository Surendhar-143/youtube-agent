import os
import sys
import json
import time
from sqlalchemy import text, inspect
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from database.postgres import SessionLocal, engine

def main():
    print("Starting Database Health Check...")
    
    os.makedirs("generated/reports", exist_ok=True)
    report_file = "generated/reports/database_health_report.json"
    
    report = {
        "provider": settings.DATABASE_PROVIDER,
        "connected": False,
        "database": None,
        "user": None,
        "tables_found": 0,
        "latency_ms": 0,
        "error": None
    }
    
    start_time = time.time()
    
    try:
        session = SessionLocal()
        
        # 1. Test version()
        version_res = session.execute(text("SELECT version();")).scalar()
        print(f"PostgreSQL Version: {version_res}")
        
        # 2. Test current_database()
        db_res = session.scalar(text("SELECT current_database();"))
        print(f"Current Database: {db_res}")
        report["database"] = db_res
        
        # 3. Test current_user
        user_res = session.scalar(text("SELECT current_user;"))
        print(f"Current User: {user_res}")
        report["user"] = user_res
        
        # 4. Verify table visibility using SQLAlchemy inspector
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"Tables found in database: {tables}")
        report["tables_found"] = len(tables)
        
        # 5. Verify ORM access (make a light query on Topic to see if ORM mapping is fine)
        # Import models inside to avoid issues if database isn't fully migrated yet
        from database.models import Topic
        try:
            topic_count = session.query(Topic).count()
            print(f"ORM Access OK. Topic table count: {topic_count}")
            report["orm_check"] = "SUCCESS"
        except Exception as orm_err:
            print(f"ORM Query failed (this is expected if tables are not migrated yet): {orm_err}")
            report["orm_check"] = f"FAILED: {str(orm_err)}"
            
        session.close()
        
        latency = int((time.time() - start_time) * 1000)
        report["latency_ms"] = latency
        report["connected"] = True
        print(f"Database connection verified in {latency}ms.")
        
    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        report["latency_ms"] = latency
        report["connected"] = False
        report["error"] = str(e)
        print(f"Database health check failed: {e}")
        
    # Save report
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"Report saved to {report_file}")
    
    if report["connected"]:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
