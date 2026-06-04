"""
YACE Phase 4.95 – Quality Evaluation Script

Reads all generated content from the database and scores it across 6 dimensions:
- Topic quality (curiosity, CTR, emotional impact, story potential, virality)
- Script quality (hook, retention, storytelling, suspense, emotion, value density)
- SEO quality (title curiosity, title emotion, tag coverage, description)
- Scene quality (scene count, visual variety, narrative flow, keyword quality)
- Audio quality (duration, word rate, file health)
- Video quality (duration, resolution, codec, file health)

Writes 6 JSON reports + 1 Markdown summary to generated/reports/

Usage:
  python scripts/evaluate_quality.py
  python scripts/evaluate_quality.py --category History
  python scripts/evaluate_quality.py --limit 10
"""

import os
import sys
import json
import logging
import re
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.postgres import SessionLocal
from database.models import Topic, Script, SEOMetadata, ScenePlan, AudioAsset, VideoAsset

os.makedirs("generated/reports", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("evaluate_quality")

# Load quality standards
STANDARDS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "content_quality_standards.json")
with open(STANDARDS_PATH, "r", encoding="utf-8") as f:
    STANDARDS = json.load(f)

REJECT_PATTERNS = [p.lower() for p in STANDARDS.get("reject_patterns", [])]

# ---------------------------------------------------------------------------
# TOPIC SCORING
# ---------------------------------------------------------------------------

def score_topic(topic_text: str, raw_score: float) -> Dict[str, Any]:
    """
    Scores a topic title on entertainment-channel quality dimensions (1–10 each).
    """
    title = topic_text.strip().lower()

    # Check for reject patterns
    is_generic = any(title.startswith(p) for p in REJECT_PATTERNS) or len(title.split()) < 5
    generic_penalty = -3 if is_generic else 0

    # Curiosity gap: presence of "why", "how", "what", "who", specific emotional words
    curiosity_keywords = ["why", "how", "what", "who", "untold", "secret", "truth", "real", "never",
                          "nobody", "nobody knows", "forgotten", "lost", "disappeared", "cursed", "dark"]
    curiosity_hits = sum(1 for kw in curiosity_keywords if kw in title)
    curiosity_score = min(10, 4 + curiosity_hits * 1.5 + generic_penalty)

    # Emotional impact: shock/mystery words
    emotion_keywords = ["feared", "destroyed", "cursed", "betrayed", "tragic", "darkest", "deadliest",
                        "greatest", "worst", "most powerful", "terror", "collapse", "fall", "rise", "vanished"]
    emotion_hits = sum(1 for kw in emotion_keywords if kw in title)
    emotional_score = min(10, 4 + emotion_hits * 2 + generic_penalty)

    # Story potential: specificity signals
    story_keywords = ["emperor", "king", "warrior", "goddess", "god", "battle", "war", "kingdom",
                      "empire", "civilization", "hero", "legend", "mystery", "prophecy"]
    story_hits = sum(1 for kw in story_keywords if kw in title)
    story_score = min(10, 4 + story_hits * 1.5 + generic_penalty)

    # CTR potential: uses DB score normalised to 1–10
    ctr_score = round(min(10, max(1, (raw_score / 100) * 10)), 1)

    # Virality: length (8–12 words is sweet spot)
    word_count = len(title.split())
    virality_score = 8 if 7 <= word_count <= 14 else 5

    # Weighted composite
    composite = round(
        curiosity_score * 0.25 +
        emotional_score * 0.25 +
        story_score * 0.25 +
        virality_score * 0.15 +
        ctr_score * 0.10, 1
    )

    return {
        "topic": topic_text,
        "raw_db_score": raw_score,
        "is_generic": is_generic,
        "scores": {
            "curiosity_gap": round(curiosity_score, 1),
            "emotional_impact": round(emotional_score, 1),
            "story_potential": round(story_score, 1),
            "virality": virality_score,
            "ctr_potential": ctr_score,
        },
        "composite_score": composite,
        "pass": composite >= STANDARDS["curiosity_score_min"],
        "weaknesses": _detect_topic_weaknesses(curiosity_score, emotional_score, story_score, is_generic),
    }


def _detect_topic_weaknesses(curiosity: float, emotion: float, story: float, generic: bool) -> List[str]:
    issues = []
    if generic:
        issues.append("GENERIC TITLE: Too broad or follows a reject pattern")
    if curiosity < 6:
        issues.append("WEAK CURIOSITY: No curiosity gap or open-loop trigger")
    if emotion < 6:
        issues.append("LOW EMOTIONAL IMPACT: Lacks shock, wonder, fear, or mystery words")
    if story < 6:
        issues.append("LOW STORY POTENTIAL: Missing specific characters, events, or historical specificity")
    return issues


# ---------------------------------------------------------------------------
# SCRIPT SCORING
# ---------------------------------------------------------------------------

def score_script(script_text: str, title: str) -> Dict[str, Any]:
    """
    Scores script quality on 6 dimensions (1–10 each).
    """
    if not script_text:
        return {"composite_score": 0, "pass": False, "error": "Empty script"}

    words = script_text.split()
    word_count = len(words)
    paragraphs = [p.strip() for p in script_text.split("\n\n") if p.strip()]

    # Hook strength: first 200 words — presence of action, tension, specific details
    first_200 = " ".join(words[:200]).lower()
    hook_triggers = ["year was", "it was", "no one", "nobody", "suddenly", "in an instant",
                     "the moment", "just", "only", "silence", "darkness", "stood",
                     "the last", "ancient", "centuries", "thousand", "warriors", "soldiers"]
    hook_hits = sum(1 for kw in hook_triggers if kw in first_200)
    hook_score = min(10, 4 + hook_hits * 0.7)

    # Encyclopedic writing detection (bad)
    encyclopedic_patterns = ["was born in", "is known as", "was founded in", "is considered",
                              "according to historians", "in this video", "today we will", "let's explore",
                              "in today's video", "welcome back", "don't forget to subscribe"]
    enc_hits = sum(1 for p in encyclopedic_patterns if p in script_text.lower())
    encyclopedic_penalty = min(4, enc_hits * 1.5)

    # Retention potential: uses varied sentence lengths, suspense phrases
    suspense_phrases = ["but here", "and then", "what nobody", "what most", "the truth",
                        "dark secret", "until now", "never before", "what happened next",
                        "everything changed", "but that was not"]
    suspense_hits = sum(1 for p in suspense_phrases if p in script_text.lower())
    retention_score = min(10, 4 + suspense_hits * 0.8 - encyclopedic_penalty)

    # Storytelling quality: paragraph variety, no bullet points
    has_bullets = bool(re.search(r"^\s*[-•*]\s", script_text, re.MULTILINE))
    has_numbered = bool(re.search(r"^\s*\d+\.\s", script_text, re.MULTILINE))
    storytelling_score = max(2, 7 - (2 if has_bullets else 0) - (2 if has_numbered else 0) - min(3, enc_hits))

    # Suspense score based on suspense phrase density
    suspense_score = min(10, 3 + (suspense_hits / max(1, word_count / 500)) * 2.5)

    # Emotional impact: emotion vocabulary
    emotion_vocab = ["fear", "terror", "horror", "tragedy", "betrayal", "rage", "grief",
                     "despair", "wonder", "awe", "shock", "astonishment", "curse", "doom"]
    emotion_hits = sum(1 for w in emotion_vocab if w in script_text.lower())
    emotional_score = min(10, 4 + emotion_hits * 0.5)

    # Value density: word count in ideal range
    min_words = STANDARDS.get("script_min_words", 1500)
    max_words = STANDARDS.get("script_max_words", 2500)
    if min_words <= word_count <= max_words:
        value_density_score = 9.0
    elif word_count < min_words:
        value_density_score = max(2, 9 - (min_words - word_count) / 100)
    else:
        value_density_score = max(5, 9 - (word_count - max_words) / 200)

    composite = round(
        hook_score * 0.25 +
        retention_score * 0.20 +
        storytelling_score * 0.20 +
        suspense_score * 0.20 +
        emotional_score * 0.10 +
        value_density_score * 0.05, 1
    )

    return {
        "title": title,
        "word_count": word_count,
        "paragraph_count": len(paragraphs),
        "has_bullet_points": has_bullets,
        "has_numbered_lists": has_numbered,
        "encyclopedic_pattern_hits": enc_hits,
        "scores": {
            "hook_strength": round(hook_score, 1),
            "retention_potential": round(retention_score, 1),
            "storytelling_quality": round(storytelling_score, 1),
            "suspense": round(suspense_score, 1),
            "emotional_impact": round(emotional_score, 1),
            "value_density": round(value_density_score, 1),
        },
        "composite_score": composite,
        "pass": composite >= STANDARDS["script_score_min"],
        "weaknesses": _detect_script_weaknesses(
            hook_score, retention_score, storytelling_score,
            suspense_score, has_bullets, enc_hits, word_count, min_words, max_words
        ),
    }


def _detect_script_weaknesses(hook, retention, storytelling, suspense,
                               has_bullets, enc_hits, word_count, min_w, max_w) -> List[str]:
    issues = []
    if hook < 6:
        issues.append("WEAK HOOK: First 30 seconds lacks immediate tension or curiosity")
    if retention < 6:
        issues.append("LOW RETENTION POTENTIAL: Missing suspense phrases and open loops")
    if storytelling < 6:
        issues.append("POOR STORYTELLING: Script reads like an encyclopedia or list")
    if suspense < 6:
        issues.append("INSUFFICIENT SUSPENSE: Lacks dramatic tension and narrative twists")
    if has_bullets:
        issues.append("BULLET POINTS DETECTED: Script uses list format — must be narrative prose")
    if enc_hits >= 2:
        issues.append(f"ENCYCLOPEDIC WRITING: {enc_hits} encyclopedic phrases detected (e.g., 'in this video', 'let's explore')")
    if word_count < min_w:
        issues.append(f"TOO SHORT: {word_count} words (minimum {min_w})")
    if word_count > max_w:
        issues.append(f"TOO LONG: {word_count} words (maximum {max_w})")
    return issues


# ---------------------------------------------------------------------------
# SEO SCORING
# ---------------------------------------------------------------------------

def score_seo(title: str, description: str, tags: list, hashtags: list) -> Dict[str, Any]:
    """
    Scores SEO metadata quality (1–10 per dimension).
    """
    title_lower = title.lower()

    # Title curiosity gap
    curiosity_words = ["why", "how", "what", "who", "untold", "secret", "truth", "never",
                       "nobody", "forgotten", "lost", "feared", "dark", "deadliest", "greatest"]
    curiosity_hits = sum(1 for w in curiosity_words if w in title_lower)
    title_curiosity_score = min(10, 4 + curiosity_hits * 1.5)

    # Title emotional trigger
    emotion_words = ["feared", "destroyed", "cursed", "betrayed", "tragic", "darkest",
                     "most powerful", "collapse", "vanished", "survived", "changed forever"]
    emotion_hits = sum(1 for w in emotion_words if w in title_lower)
    title_emotion_score = min(10, 4 + emotion_hits * 2)

    # Tag coverage
    tag_count = len(tags)
    min_tags = STANDARDS.get("topic_score_min", 15)
    tag_score = min(10, max(1, (tag_count / 20) * 10))

    # Description quality
    desc_score = min(10, max(1, len(description.split()) / 50))

    composite = round(
        title_curiosity_score * 0.35 +
        title_emotion_score * 0.25 +
        tag_score * 0.20 +
        desc_score * 0.20, 1
    )

    return {
        "title": title,
        "title_length": len(title),
        "tag_count": tag_count,
        "hashtag_count": len(hashtags),
        "description_word_count": len(description.split()),
        "scores": {
            "title_curiosity": round(title_curiosity_score, 1),
            "title_emotion": round(title_emotion_score, 1),
            "tag_coverage": round(tag_score, 1),
            "description_quality": round(desc_score, 1),
        },
        "composite_score": composite,
        "pass": composite >= STANDARDS["seo_score_min"],
        "weaknesses": _detect_seo_weaknesses(title_curiosity_score, title_emotion_score, tag_count, description),
    }


def _detect_seo_weaknesses(curiosity, emotion, tag_count, description) -> List[str]:
    issues = []
    if curiosity < 6:
        issues.append("WEAK TITLE CURIOSITY: Title lacks curiosity gap or question-style hook")
    if emotion < 6:
        issues.append("WEAK TITLE EMOTION: Title doesn't trigger emotional response")
    if tag_count < 15:
        issues.append(f"INSUFFICIENT TAGS: Only {tag_count} tags (minimum 15 required)")
    if len(description.split()) < 100:
        issues.append(f"THIN DESCRIPTION: Only {len(description.split())} words — needs keyword-rich paragraphs")
    return issues


# ---------------------------------------------------------------------------
# SCENE SCORING
# ---------------------------------------------------------------------------

def score_scenes(scenes: list, script_word_count: int = 0) -> Dict[str, Any]:
    """
    Scores scene plan quality (1–10 per dimension).
    """
    count = len(scenes)
    min_scenes = STANDARDS.get("scene_count_min", 12)
    max_scenes = STANDARDS.get("scene_count_max", 25)

    # Scene count score
    if min_scenes <= count <= max_scenes:
        count_score = 10.0
    elif count < min_scenes:
        count_score = max(1, 10 - (min_scenes - count) * 1.5)
    else:
        count_score = max(6, 10 - (count - max_scenes) * 0.5)

    # Visual variety: penalise consecutive same types
    if count > 0:
        visual_types = [s.get("visual_type", "BROLL") if isinstance(s, dict)
                        else getattr(s, "visual_type", "BROLL") for s in scenes]
        consecutive_repeats = sum(
            1 for i in range(1, len(visual_types))
            if visual_types[i] == visual_types[i - 1]
        )
        unique_types = len(set(visual_types))
        variety_score = min(10, max(1, 10 - consecutive_repeats * 1.5 + unique_types * 0.5))
    else:
        variety_score = 0

    # Narrative flow: check scene duration variance (good pacing = varied durations)
    if count > 1:
        durations = [s.get("estimated_duration", 10) if isinstance(s, dict)
                     else getattr(s, "estimated_duration", 10) for s in scenes]
        avg_dur = sum(durations) / len(durations)
        variance = sum(abs(d - avg_dur) for d in durations) / len(durations)
        flow_score = min(10, 4 + variance * 0.3)
    else:
        flow_score = 2

    # Keyword quality: presence of historically specific keywords
    all_keywords = []
    for s in scenes:
        kws = s.get("keywords", []) if isinstance(s, dict) else getattr(s, "keywords", [])
        all_keywords.extend(kws)
    unique_keywords = len(set(all_keywords))
    keyword_score = min(10, max(1, unique_keywords / (count * 2) * 10)) if count > 0 else 0

    composite = round(
        count_score * 0.30 +
        variety_score * 0.30 +
        flow_score * 0.25 +
        keyword_score * 0.15, 1
    )

    return {
        "scene_count": count,
        "unique_visual_types": unique_types if count > 0 else 0,
        "consecutive_type_repeats": consecutive_repeats if count > 0 else 0,
        "scores": {
            "scene_count": round(count_score, 1),
            "visual_variety": round(variety_score, 1),
            "narrative_flow": round(flow_score, 1),
            "keyword_quality": round(keyword_score, 1),
        },
        "composite_score": composite,
        "pass": composite >= STANDARDS["scene_count_min"] / 2.5,  # scaled threshold
        "weaknesses": _detect_scene_weaknesses(count, min_scenes, max_scenes,
                                                consecutive_repeats if count > 0 else 0,
                                                unique_types if count > 0 else 0),
    }


def _detect_scene_weaknesses(count, min_s, max_s, consec, unique) -> List[str]:
    issues = []
    if count < min_s:
        issues.append(f"TOO FEW SCENES: {count} scenes (minimum {min_s} required for dynamic video)")
    if count > max_s:
        issues.append(f"TOO MANY SCENES: {count} scenes (maximum {max_s} for coherent pacing)")
    if consec >= 3:
        issues.append(f"REPETITIVE VISUALS: {consec} consecutive scene pairs with same visual type")
    if unique <= 2:
        issues.append(f"LOW VISUAL VARIETY: Only {unique} unique visual type(s) across all scenes")
    return issues


# ---------------------------------------------------------------------------
# AUDIO SCORING
# ---------------------------------------------------------------------------

def score_audio(audio_record) -> Dict[str, Any]:
    if audio_record is None:
        return {"pass": False, "error": "No audio asset found", "composite_score": 0}

    duration = getattr(audio_record, "duration_seconds", 0) or 0
    path = getattr(audio_record, "audio_path", "") or ""
    file_exists = os.path.exists(path) if path else False
    file_size_mb = os.path.getsize(path) / (1024 * 1024) if file_exists else 0

    issues = []
    duration_score = 10.0
    if duration < 60:
        duration_score = 3.0
        issues.append(f"TOO SHORT: {duration:.0f}s audio (minimum ~60s for a 10min video)")
    elif duration > 1500:
        duration_score = 5.0
        issues.append(f"VERY LONG: {duration:.0f}s audio — check for pacing issues")

    file_health_score = 10.0 if file_exists and file_size_mb > 0 else 0.0
    if not file_exists:
        issues.append("MISSING FILE: Audio file not found on disk")

    composite = round((duration_score * 0.6 + file_health_score * 0.4), 1)

    return {
        "audio_path": path,
        "file_exists": file_exists,
        "duration_seconds": round(duration, 1),
        "file_size_mb": round(file_size_mb, 2),
        "scores": {"duration": round(duration_score, 1), "file_health": round(file_health_score, 1)},
        "composite_score": composite,
        "pass": composite >= 7.0,
        "weaknesses": issues,
    }


# ---------------------------------------------------------------------------
# VIDEO SCORING
# ---------------------------------------------------------------------------

def score_video(video_record) -> Dict[str, Any]:
    if video_record is None:
        return {"pass": False, "error": "No video asset found", "composite_score": 0}

    path = getattr(video_record, "video_path", "") or ""
    status = getattr(video_record, "status", "UNKNOWN") or "UNKNOWN"
    resolution = getattr(video_record, "resolution", "unknown") or "unknown"
    duration = getattr(video_record, "duration_seconds", 0) or 0
    file_exists = os.path.exists(path) if path else False
    file_size_mb = os.path.getsize(path) / (1024 * 1024) if file_exists else 0

    issues = []
    status_score = 10.0 if status == "READY" else 3.0
    if status != "READY":
        issues.append(f"RENDER STATUS: Video status is '{status}' (expected READY)")

    duration_score = 10.0
    if duration < 60:
        duration_score = 3.0
        issues.append(f"SHORT VIDEO: {duration:.0f}s (check if audio/scenes were generated correctly)")

    file_score = 10.0 if file_exists and file_size_mb > 0 else 0.0
    if not file_exists:
        issues.append("MISSING FILE: Rendered video file not found on disk")

    composite = round(status_score * 0.35 + duration_score * 0.35 + file_score * 0.30, 1)

    return {
        "video_path": path,
        "status": status,
        "resolution": resolution,
        "duration_seconds": round(duration, 1),
        "file_exists": file_exists,
        "file_size_mb": round(file_size_mb, 2),
        "scores": {
            "render_status": round(status_score, 1),
            "duration": round(duration_score, 1),
            "file_health": round(file_score, 1),
        },
        "composite_score": composite,
        "pass": composite >= STANDARDS["video_score_min"],
        "weaknesses": issues,
    }


# ---------------------------------------------------------------------------
# MAIN EVALUATOR
# ---------------------------------------------------------------------------

def evaluate_all(category_filter: Optional[str] = None, limit: Optional[int] = None):
    logger.info("="*60)
    logger.info("YACE Quality Evaluation — Phase 4.95")
    logger.info("="*60)

    db = SessionLocal()
    try:
        # Load all scripts (main pivot point)
        query = db.query(Script)
        if limit:
            query = query.limit(limit)
        scripts = query.all()

        logger.info(f"Evaluating {len(scripts)} scripts...")

        topic_report = []
        script_report = []
        seo_report = []
        scene_report = []
        audio_report = []
        video_report = []

        for script in scripts:
            script_id = script.id
            topic = db.query(Topic).filter(Topic.id == script.topic_id).first()

            # --- Topic ---
            if topic:
                t_score = score_topic(topic.topic, float(topic.score or 70))
                t_score["script_id"] = script_id
                t_score["topic_id"] = topic.id
                topic_report.append(t_score)

            # --- Script ---
            s_score = score_script(script.script or "", script.title or "")
            s_score["script_id"] = script_id
            script_report.append(s_score)

            # --- SEO ---
            seo = db.query(SEOMetadata).filter(SEOMetadata.script_id == script_id).first()
            if seo:
                seo_score = score_seo(seo.title or "", seo.description or "",
                                      seo.tags or [], seo.hashtags or [])
                seo_score["script_id"] = script_id
                seo_score["seo_id"] = seo.id
                seo_report.append(seo_score)

            # --- Scenes ---
            scenes = db.query(ScenePlan).filter(ScenePlan.script_id == script_id).all()
            scene_score = score_scenes(scenes, word_count_of_script(script.script))
            scene_score["script_id"] = script_id
            scene_report.append(scene_score)

            # --- Audio ---
            audio = getattr(script, "audio_asset", None)
            audio_score = score_audio(audio)
            audio_score["script_id"] = script_id
            audio_report.append(audio_score)

            # --- Video ---
            video = db.query(VideoAsset).filter(VideoAsset.script_id == script_id).first()
            video_score = score_video(video)
            video_score["script_id"] = script_id
            video_report.append(video_score)

        # Write all reports
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        _write_report(topic_report, f"generated/reports/topic_quality_report.json")
        _write_report(script_report, f"generated/reports/script_quality_report.json")
        _write_report(seo_report, f"generated/reports/seo_quality_report.json")
        _write_report(scene_report, f"generated/reports/scene_quality_report.json")
        _write_report(audio_report, f"generated/reports/audio_quality_report.json")
        _write_report(video_report, f"generated/reports/video_quality_report.json")

        # Write summary
        summary = _build_summary(topic_report, script_report, seo_report,
                                  scene_report, audio_report, video_report)
        _write_markdown_summary(summary, "generated/reports/content_optimization_summary.md")

        logger.info("All reports written to generated/reports/")
        _print_summary(summary)

    finally:
        db.close()


def word_count_of_script(text: Optional[str]) -> int:
    return len(text.split()) if text else 0


def _write_report(data: list, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "count": len(data),
            "items": data
        }, f, indent=2, ensure_ascii=False)
    logger.info(f"Written: {path}")


def _avg(items, key):
    vals = [i[key] for i in items if key in i and i[key] is not None]
    return round(sum(vals) / len(vals), 2) if vals else 0


def _pass_rate(items):
    if not items:
        return "0/0"
    passing = sum(1 for i in items if i.get("pass", False))
    return f"{passing}/{len(items)}"


def _build_summary(topics, scripts, seos, scenes, audios, videos) -> Dict[str, Any]:
    # Collect all weaknesses
    all_topic_weaknesses = [w for t in topics for w in t.get("weaknesses", [])]
    all_script_weaknesses = [w for s in scripts for w in s.get("weaknesses", [])]
    all_seo_weaknesses = [w for s in seos for w in s.get("weaknesses", [])]
    all_scene_weaknesses = [w for s in scenes for w in s.get("weaknesses", [])]

    def count_weaknesses(weakness_list):
        from collections import Counter
        return dict(Counter(weakness_list).most_common(10))

    return {
        "evaluated_at": datetime.now().isoformat(),
        "total_videos_evaluated": len(scripts),
        "averages": {
            "topic_composite": _avg(topics, "composite_score"),
            "script_composite": _avg(scripts, "composite_score"),
            "seo_composite": _avg(seos, "composite_score"),
            "scene_composite": _avg(scenes, "composite_score"),
            "audio_composite": _avg(audios, "composite_score"),
            "video_composite": _avg(videos, "composite_score"),
        },
        "pass_rates": {
            "topics": _pass_rate(topics),
            "scripts": _pass_rate(scripts),
            "seo": _pass_rate(seos),
            "scenes": _pass_rate(scenes),
            "audio": _pass_rate(audios),
            "video": _pass_rate(videos),
        },
        "top_weaknesses": {
            "research": count_weaknesses(all_topic_weaknesses),
            "scripting": count_weaknesses(all_script_weaknesses),
            "seo": count_weaknesses(all_seo_weaknesses),
            "scenes": count_weaknesses(all_scene_weaknesses),
        },
        "thresholds": {
            "topic_min": STANDARDS["topic_score_min"],
            "script_min": STANDARDS["script_score_min"],
            "seo_min": STANDARDS["seo_score_min"],
            "scene_count_min": STANDARDS["scene_count_min"],
            "video_min": STANDARDS["video_score_min"],
        },
    }


def _write_markdown_summary(summary: Dict[str, Any], path: str):
    avgs = summary["averages"]
    passes = summary["pass_rates"]
    weaknesses = summary["top_weaknesses"]
    thresholds = summary["thresholds"]

    def score_emoji(score, threshold):
        if score >= threshold:
            return "✅"
        elif score >= threshold * 0.8:
            return "⚠️"
        return "❌"

    lines = [
        "# YACE Phase 4.95 — Content Quality Optimization Summary",
        "",
        f"**Evaluated:** {summary['evaluated_at']}  ",
        f"**Total Videos:** {summary['total_videos_evaluated']}",
        "",
        "---",
        "",
        "## Quality Scores",
        "",
        "| Dimension | Average Score | Pass Rate | Target | Status |",
        "|-----------|:------------:|:---------:|:------:|:------:|",
        f"| Topic Quality | {avgs['topic_composite']}/10 | {passes['topics']} | {thresholds['topic_min']}/10 | {score_emoji(avgs['topic_composite'], thresholds['topic_min'])} |",
        f"| Script Quality | {avgs['script_composite']}/10 | {passes['scripts']} | {thresholds['script_min']}/10 | {score_emoji(avgs['script_composite'], thresholds['script_min'])} |",
        f"| SEO Quality | {avgs['seo_composite']}/10 | {passes['seo']} | {thresholds['seo_min']}/10 | {score_emoji(avgs['seo_composite'], thresholds['seo_min'])} |",
        f"| Scene Quality | {avgs['scene_composite']}/10 | {passes['scenes']} | based on count | {score_emoji(avgs['scene_composite'], 7)} |",
        f"| Audio Quality | {avgs['audio_composite']}/10 | {passes['audio']} | 7/10 | {score_emoji(avgs['audio_composite'], 7)} |",
        f"| Video Quality | {avgs['video_composite']}/10 | {passes['video']} | {thresholds['video_min']}/10 | {score_emoji(avgs['video_composite'], thresholds['video_min'])} |",
        "",
        "---",
        "",
        "## Identified Weaknesses",
        "",
    ]

    for category, issues in weaknesses.items():
        if issues:
            lines.append(f"### {category.upper()} Weaknesses")
            for issue, count in issues.items():
                lines.append(f"- **{issue}** (found in {count} video(s))")
            lines.append("")

    lines += [
        "---",
        "",
        "## Recommended Actions",
        "",
        "Based on the above weaknesses, update prompt variants targeting the top issues before A/B testing.",
        "",
        "> Run `python scripts/evaluate_quality.py` after generating new content to compare scores.",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"Written: {path}")


def _print_summary(summary: Dict[str, Any]):
    avgs = summary["averages"]
    logger.info("")
    logger.info("=" * 60)
    logger.info("QUALITY EVALUATION COMPLETE")
    logger.info("=" * 60)
    for key, val in avgs.items():
        logger.info(f"  {key.replace('_composite', '').upper():15s}: {val}/10")
    logger.info("")
    logger.info("Pass Rates:")
    for key, val in summary["pass_rates"].items():
        logger.info(f"  {key.upper():10s}: {val}")
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="YACE Phase 4.95 — Quality Evaluator"
    )
    parser.add_argument("--category", type=str, help="Filter by category (not yet used — evaluates all)")
    parser.add_argument("--limit", type=int, help="Limit number of scripts to evaluate")
    args = parser.parse_args()
    evaluate_all(category_filter=args.category, limit=args.limit)


if __name__ == "__main__":
    main()
