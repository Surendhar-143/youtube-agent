"""
YACE Phase 4.95 – Batch Video Generation Script

Generates a configurable number of complete videos per content category.
Each video goes through the full pipeline: Content → Voice → Scene Planning → Video Assembly.

Usage:
  python scripts/batch_generate.py --category History --count 3
  python scripts/batch_generate.py --category Mythology --count 3
  python scripts/batch_generate.py --category Mystery --count 3
  python scripts/batch_generate.py --all --count 3   (runs all 3 categories)

Reports are written to: generated/reports/batch_{category}_{timestamp}.json
"""

import os
import sys
import json
import logging
import argparse
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.settings import settings
from database.postgres import SessionLocal
from workflows.content_pipeline import run_content_pipeline
from workflows.voice_pipeline import run_voice_pipeline
from workflows.visual_pipeline import run_visual_pipeline
from workflows.video_pipeline import run_video_pipeline

# Ensure directories exist
os.makedirs("logs", exist_ok=True)
os.makedirs("generated/reports", exist_ok=True)
os.makedirs("generated/videos", exist_ok=True)

# Configure logging
log_file_path = os.path.join("logs", "batch_generate.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file_path, encoding="utf-8")
    ]
)
logger = logging.getLogger("batch_generate")

# ---------------------------------------------------------------------------
# PREDEFINED TOPIC SEEDS
# These are used as niche prompts fed to the ResearchAgent.
# The agent will generate fresh topics from each seed on each run.
# ---------------------------------------------------------------------------
CATEGORY_NICHES = {
    "History": [
        "The Darkest Emperors and Rulers Who Terrorised the Ancient World",
        "The Greatest Military Defeats and Collapses in Human History",
        "Lost Civilisations and Forgotten Empires of the Ancient World",
    ],
    "Mythology": [
        "The Most Powerful and Feared Gods in Ancient Mythology",
        "Ancient Curses, Prophecies, and Dark Mythology Stories",
        "The Untold Stories of Mythological Heroes and Their Tragic Fates",
    ],
    "Mystery": [
        "Lost Cities, Buried Secrets, and Unexplained Ancient Discoveries",
        "Historical Conspiracies and Cover-Ups That Changed the World",
    ],
    "Horror": [
        "The Real Story Behind Annabelle and Other Cursed Artifacts",
        "The Most Terrifying Japanese Urban Legends and Creepypastas",
        "Horrifying Unexplained Paranormal Cases That Shocked Investigators",
    ],
}

# ---------------------------------------------------------------------------
# SINGLE VIDEO PIPELINE
# ---------------------------------------------------------------------------

def generate_single_video(niche: str, category: str, video_index: int) -> Dict[str, Any]:
    """
    Runs the complete pipeline for a single video and returns a result dict.
    """
    result: Dict[str, Any] = {
        "category": category,
        "video_index": video_index,
        "niche_prompt": niche,
        "topic_id": None,
        "script_id": None,
        "seo_id": None,
        "audio_id": None,
        "scene_count": 0,
        "asset_count": 0,
        "video_id": None,
        "video_path": None,
        "script_words": 0,
        "audio_duration_seconds": 0,
        "success": False,
        "error": None,
        "duration_seconds": 0,
    }

    start_time = time.time()
    db = SessionLocal()

    try:
        logger.info(f"[{category}] Video {video_index}: Starting content pipeline — niche: '{niche}'")

        # Stage 1: Content Generation (Topics → Script → SEO)
        content_res = run_content_pipeline(niche=niche, db=db)
        result["topic_id"] = content_res["topic_id"]
        result["script_id"] = content_res["script_id"]
        result["seo_id"] = content_res["seo_id"]
        script_id = content_res["script_id"]
        logger.info(f"[{category}] Video {video_index}: Content pipeline complete. script_id={script_id}")

        # Capture script word count
        from database.models import Script
        script_record = db.query(Script).filter(Script.id == script_id).first()
        if script_record and isinstance(script_record.script, str):
            result["script_words"] = len(script_record.script.split())

        # Stage 2: Voice Production (Script → WAV audio)
        logger.info(f"[{category}] Video {video_index}: Starting voice pipeline...")
        voice_res = run_voice_pipeline(script_id=script_id, db=db)
        result["audio_id"] = voice_res["audio_id"]
        logger.info(f"[{category}] Video {video_index}: Voice pipeline complete. audio_id={voice_res['audio_id']}")

        # Capture audio duration
        from database.models import AudioAsset
        audio_record = db.query(AudioAsset).filter(AudioAsset.id == voice_res["audio_id"]).first()
        if audio_record and isinstance(audio_record.duration_seconds, (int, float)):
            result["audio_duration_seconds"] = round(audio_record.duration_seconds, 2)

        # Stage 3: Visual Scene Planning (Script → Scenes → Asset Plan)
        logger.info(f"[{category}] Video {video_index}: Starting visual pipeline...")
        visual_res = run_visual_pipeline(script_id=script_id, db=db)
        result["scene_count"] = visual_res["scene_count"]
        result["asset_count"] = visual_res["asset_count"]
        logger.info(f"[{category}] Video {video_index}: Visual pipeline complete. scenes={visual_res['scene_count']}")

        # Stage 4: Video Assembly (Audio + Scenes → MP4)
        logger.info(f"[{category}] Video {video_index}: Starting video pipeline...")
        video_res = run_video_pipeline(script_id=script_id, db=db)
        result["video_id"] = video_res["video_id"]
        result["video_path"] = video_res["video_path"]
        logger.info(f"[{category}] Video {video_index}: Video pipeline complete. video_id={video_res['video_id']}")

        result["success"] = True
        logger.info(f"[{category}] Video {video_index}: SUCCESS - {result['script_words']} words, "
                    f"{result['scene_count']} scenes, {result['audio_duration_seconds']:.0f}s audio")

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        logger.error(f"[{category}] Video {video_index}: FAILED - {e}")
    finally:
        result["duration_seconds"] = round(time.time() - start_time, 2)
        db.close()

    return result


# ---------------------------------------------------------------------------
# BATCH RUNNER
# ---------------------------------------------------------------------------

def run_batch(category: str, count: int) -> Dict[str, Any]:
    """
    Generates `count` videos for a given category and returns a batch report.
    """
    logger.info(f"{'='*60}")
    logger.info(f"BATCH GENERATION: {category.upper()} - {count} videos")
    logger.info(f"{'='*60}")

    niches = CATEGORY_NICHES.get(category, [])
    if not niches:
        raise ValueError(f"Unknown category: '{category}'. Valid: {list(CATEGORY_NICHES.keys())}")

    results: List[Dict[str, Any]] = []
    batch_start = time.time()

    for i in range(count):
        # Cycle through the available niche prompts
        niche = niches[i % len(niches)]
        video_result = generate_single_video(niche=niche, category=category, video_index=i + 1)
        results.append(video_result)

        # Brief pause between videos to avoid overwhelming the LLM
        if i < count - 1:
            logger.info(f"[{category}] Pausing 5 seconds before next video...")
            time.sleep(5)

    # Compile batch summary
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    batch_report = {
        "category": category,
        "count_requested": count,
        "count_success": len(successes),
        "count_failed": len(failures),
        "success_rate": f"{len(successes)}/{count}",
        "total_batch_duration_seconds": round(time.time() - batch_start, 2),
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "avg_script_words": round(
                sum(r["script_words"] for r in successes) / len(successes), 0
            ) if successes else 0,
            "avg_scene_count": round(
                sum(r["scene_count"] for r in successes) / len(successes), 1
            ) if successes else 0,
            "avg_audio_duration_seconds": round(
                sum(r["audio_duration_seconds"] for r in successes) / len(successes), 1
            ) if successes else 0,
        },
        "videos": results,
        "failures": [{"video_index": r["video_index"], "error": r["error"]} for r in failures],
    }

    # Write report to disk
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"generated/reports/batch_{category.lower()}_{timestamp}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(batch_report, f, indent=2, ensure_ascii=False)

    logger.info(f"{'='*60}")
    logger.info(f"BATCH COMPLETE: {category.upper()} - {len(successes)}/{count} succeeded")
    logger.info(f"Report saved to: {report_path}")
    logger.info(f"{'='*60}")

    return batch_report


# ---------------------------------------------------------------------------
# MAIN CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="YACE Phase 4.95 — Batch Video Generator for Entertainment Channel"
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=["History", "Mythology", "Mystery", "Horror"],
        help="Content category to generate videos for."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all 4 categories (History, Mythology, Mystery, Horror)."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=3,
        help="Number of videos per category (default: 3 for baseline validation)."
    )
    args = parser.parse_args()

    if not args.category and not args.all:
        parser.print_help()
        sys.exit(1)

    categories = ["History", "Mythology", "Mystery", "Horror"] if args.all else [args.category]
    all_reports = {}

    for category in categories:
        try:
            report = run_batch(category=category, count=args.count)
            all_reports[category] = report
        except Exception as e:
            logger.error(f"Batch failed for category '{category}': {e}")
            all_reports[category] = {"category": category, "error": str(e), "success": False}

    # Write combined summary
    if args.all:
        total_success = sum(r.get("count_success", 0) for r in all_reports.values())
        total_requested = sum(r.get("count_requested", args.count) for r in all_reports.values())
        summary = {
            "run_type": "full_baseline",
            "categories": categories,
            "total_success": total_success,
            "total_requested": total_requested,
            "generated_at": datetime.now().isoformat(),
            "category_reports": all_reports,
        }
        summary_path = f"generated/reports/batch_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logger.info(f"Combined report saved to: {summary_path}")
        logger.info(f"TOTAL: {total_success}/{total_requested} videos generated successfully.")


if __name__ == "__main__":
    main()
