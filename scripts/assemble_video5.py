"""
Direct video assembly script for script_id=5.
Bypasses DB to avoid Supabase idle-timeout failures.
Uses already-downloaded assets, audio, and subtitles.
"""
import os
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from services.motion_engine import MotionEngine
from services.ffmpeg_service import FFmpegService
from config.settings import settings

# Scene data from the first successful pipeline run
SCENES = [
    {"path": "generated/assets/history/scene_31_1780565289.jpg", "duration": 6.8, "effect": "zoom_in"},
    {"path": "generated/assets/history/scene_32_1780565335.jpg", "duration": 8.4, "effect": "zoom_out"},
    {"path": "generated/assets/history/scene_32_1780565335.jpg", "duration": 9.2, "effect": "pan_right"},
    {"path": "generated/assets/history/scene_34_1780565450.jpg", "duration": 6.8, "effect": "slow_push"},
    {"path": "generated/assets/history/scene_35_1780565902.jpg", "duration": 8.0, "effect": "pan_up"},
    {"path": "generated/assets/history/scene_36_1780566011.jpg", "duration": 2.0, "effect": "pan_down"},
]

AUDIO_PATH    = "generated/audio/audio_5.wav"
SUBTITLE_PATH = "generated/subtitles/video_5.srt"
OUTPUT_PATH   = "generated/videos/video_5.mp4"
CLIPS_DIR     = "generated/temp_clips_v5"

engine = MotionEngine()
ffmpeg = FFmpegService()
os.makedirs(CLIPS_DIR, exist_ok=True)

# Step 1: Render individual motion clips
clip_paths = []
for i, scene in enumerate(SCENES):
    out = os.path.join(CLIPS_DIR, f"clip_{i}.mp4")
    print(f"[{i+1}/{len(SCENES)}] Rendering '{scene['effect']}' on {os.path.basename(scene['path'])}...")
    engine.apply_effect(scene["path"], scene["duration"], scene["effect"], out)
    clip_paths.append(out)

# Step 2: Concatenate clips
print("Concatenating clips...")
concat_txt = os.path.join(CLIPS_DIR, "concat.txt")
with open(concat_txt, "w") as f:
    for cp in clip_paths:
        clean = os.path.abspath(cp).replace("\\", "/")
        f.write(f"file '{clean}'\n")

concat_video = os.path.join(CLIPS_DIR, "concat.mp4")
subprocess.run(
    [ffmpeg.ffmpeg_path, "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", concat_video],
    check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
print("Clips concatenated OK")

# Step 3: Merge with narration audio
print("Merging audio...")
raw_mp4 = os.path.join(CLIPS_DIR, "with_audio.mp4")
subprocess.run(
    [ffmpeg.ffmpeg_path, "-y", "-i", concat_video, "-i", AUDIO_PATH,
     "-c:v", "copy", "-c:a", settings.FFMPEG_AUDIO_CODEC, "-shortest", raw_mp4],
    check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
print("Audio merged OK")

# Step 4: Burn subtitles
print("Burning subtitles...")
ffmpeg.add_subtitles(raw_mp4, SUBTITLE_PATH, OUTPUT_PATH)

size_mb = os.path.getsize(OUTPUT_PATH) / 1024 / 1024
print(f"\nSUCCESS: {OUTPUT_PATH} ({size_mb:.1f} MB)")

# Cleanup temp clips
import shutil
shutil.rmtree(CLIPS_DIR, ignore_errors=True)
print("Temp clips cleaned up.")
