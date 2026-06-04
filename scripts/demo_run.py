import os
import sys
import json
import logging
import time
from typing import Dict, Any

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.settings import settings
from database.postgres import SessionLocal
from database.models import Script, AudioAsset, ScenePlan, VisualAsset, VideoAsset
from workflows.content_pipeline import run_content_pipeline
from workflows.voice_pipeline import run_voice_pipeline
from workflows.visual_pipeline import run_visual_pipeline
from workflows.video_pipeline import run_video_pipeline

# Ensure folders exist
os.makedirs("logs", exist_ok=True)
os.makedirs("generated/reports", exist_ok=True)

# Configure logging to console and logs/demo_run.log
log_file_path = os.path.join("logs", "demo_run.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file_path, encoding="utf-8")
    ]
)
logger = logging.getLogger("demo_run")

def run_demo(niche: str) -> Dict[str, Any]:
    logger.info(f"===== Initiating End-to-End Demo Run for Niche: '{niche}' =====")
    
    report: Dict[str, Any] = {
        "topic_id": None,
        "script_id": None,
        "seo_id": None,
        "audio_id": None,
        "video_id": None,
        "script_words": 0,
        "audio_duration": 0,
        "scene_count": 0,
        "asset_count": 0,
        "video_path": None,
        "success": False
    }

    db = SessionLocal()
    try:
        # 1. Content Generation Pipeline
        logger.info("Executing Phase 1: Content Generation Pipeline...")
        content_res = run_content_pipeline(niche=niche, db=db)
        
        topic_id = content_res["topic_id"]
        script_id = content_res["script_id"]
        seo_id = content_res["seo_id"]
        
        report["topic_id"] = topic_id
        report["script_id"] = script_id
        report["seo_id"] = seo_id
        
        script_record = db.query(Script).filter(Script.id == script_id).first()
        if script_record and hasattr(script_record, "script") and isinstance(script_record.script, str):
            report["script_words"] = len(script_record.script.split())

        # 2. Voice Narration Production Pipeline
        logger.info("Executing Phase 2: Voice Production Pipeline...")
        voice_res = run_voice_pipeline(script_id=script_id, db=db)
        audio_id = voice_res["audio_id"]
        report["audio_id"] = audio_id
        
        audio_record = db.query(AudioAsset).filter(AudioAsset.id == audio_id).first()
        if audio_record and hasattr(audio_record, "duration_seconds") and isinstance(audio_record.duration_seconds, (int, float)):
            report["audio_duration"] = int(audio_record.duration_seconds)

        # 3. Visual Scene Planning Pipeline
        logger.info("Executing Phase 3: Visual Scene Planning Pipeline...")
        visual_res = run_visual_pipeline(script_id=script_id, db=db)
        scene_count = visual_res["scene_count"]
        asset_count = visual_res["asset_count"]
        report["scene_count"] = scene_count
        report["asset_count"] = asset_count

        # 4. Video Rendering Pipeline
        logger.info("Executing Phase 4: Video Assembly Pipeline...")
        video_res = run_video_pipeline(script_id=script_id, db=db)
        video_id = video_res["video_id"]
        video_path = video_res["video_path"]
        
        report["video_id"] = video_id
        report["video_path"] = video_path
        report["success"] = True
        
        logger.info("===== End-to-End Demo Run Completed Successfully! =====")

    except Exception as e:
        logger.error(f"===== Demo Run Execution Failed! Error: {e} =====")
        report["success"] = False
        report["error"] = str(e)
    finally:
        db.close()

    # Write report json to generated/reports/demo_report.json
    report_path = "generated/reports/demo_report.json"
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Demo run report successfully saved to: {report_path}")
    except Exception as e:
        logger.error(f"Failed to write demo run report: {e}")

    return report

if __name__ == "__main__":
    niche_arg = "AI Automation"
    if len(sys.argv) > 1:
        niche_arg = sys.argv[1]
    run_demo(niche_arg)
