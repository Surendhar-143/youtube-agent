import os
import sys
import json
import time
from sqlalchemy import inspect
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.postgres import Base, engine

def main():
    print("Verifying migrations on database...")
    
    os.makedirs("generated/reports", exist_ok=True)
    report_file = "generated/reports/migration_validation_report.json"
    
    report = {
        "connected": False,
        "alembic_version_exists": False,
        "missing_expected_tables": [],
        "expected_tables_found": [],
        "extra_tables_found": [],
        "schema_matches_models": False,
        "error": None
    }
    
    start_time = time.time()
    
    try:
        inspector = inspect(engine)
        actual_tables = inspector.get_table_names()
        report["connected"] = True
        
        # Verify alembic_version exists
        if "alembic_version" in actual_tables:
            report["alembic_version_exists"] = True
            
        # Expected tables from models
        import database.models  # load models
        model_tables = list(Base.metadata.tables.keys())
        
        # Explicit tables required by specification
        required_tables = [
            "topics", "scripts", "seo_metadata", "audio_assets", 
            "scene_plans", "visual_assets", "subtitle_assets", 
            "video_assets", "analytics"
        ]
        
        expected_tables_found = []
        missing_expected_tables = []
        
        # Check explicit required tables
        for t in required_tables:
            if t in actual_tables:
                expected_tables_found.append(t)
            else:
                missing_expected_tables.append(t)
                
        report["expected_tables_found"] = expected_tables_found
        report["missing_expected_tables"] = missing_expected_tables
        
        # Check additional tables from SQLAlchemy models
        schema_matches = True
        for model_t in model_tables:
            if model_t not in actual_tables:
                schema_matches = False
                if model_t not in missing_expected_tables:
                    missing_expected_tables.append(model_t)
                    
        report["schema_matches_models"] = schema_matches and (len(missing_expected_tables) == 0)
        
        # Extra tables (excluding alembic_version and model tables)
        for t in actual_tables:
            if t != "alembic_version" and t not in model_tables:
                report["extra_tables_found"].append(t)
                
        print(f"Migrations check complete. Alembic Version Exists: {report['alembic_version_exists']}")
        print(f"Expected tables found: {expected_tables_found}")
        print(f"Missing tables: {missing_expected_tables}")
        
    except Exception as e:
        report["connected"] = False
        report["error"] = str(e)
        print(f"Migration verification failed: {e}")
        
    # Save report
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"Migration validation report saved to {report_file}")
    
    # We exit 0 if connected and all expected tables exist
    if report["connected"] and len(report["missing_expected_tables"]) == 0:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
