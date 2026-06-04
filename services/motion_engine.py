import os
import subprocess
import logging
from typing import Optional
from config.settings import settings

logger = logging.getLogger("motion_engine")

class MotionEngine:
    """
    Applies cinematic motion effects (Ken Burns pan/zoom) to individual images using FFmpeg filters.
    Produces a temporary MP4 clip per scene.
    """
    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = os.path.abspath(ffmpeg_path or settings.FFMPEG_PATH)

    def apply_effect(self, image_path: str, duration: float, effect_name: str, output_path: str) -> str:
        """
        Takes an image, applies a zoompan motion filter, and creates an MP4 video clip.
        """
        image_abs = os.path.abspath(image_path)
        output_abs = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_abs), exist_ok=True)

        fps = settings.FFMPEG_FRAME_RATE
        total_frames = int(duration * fps)
        if total_frames < 1:
            total_frames = fps  # At least 1 second

        # Base dimensions
        width = settings.VIDEO_RESOLUTION_WIDTH
        height = settings.VIDEO_RESOLUTION_HEIGHT

        # Define FFmpeg zoompan filter strings
        # Note: zoompan requires s=widthxheight and fps=fps.
        effects = {
            "zoom_in": (
                f"zoompan=z='min(zoom+0.0015,1.5)':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={total_frames}:s={width}x{height}:fps={fps}"
            ),
            "zoom_out": (
                f"zoompan=z='if(lte(zoom,1.0),1.5,max(1.0,zoom-0.0015))':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={total_frames}:s={width}x{height}:fps={fps}"
            ),
            "pan_left": (
                f"zoompan=z='1.3':"
                f"x='(iw-iw/zoom)*(1-on/{total_frames})':y='ih/2-(ih/zoom/2)':"
                f"d={total_frames}:s={width}x{height}:fps={fps}"
            ),
            "pan_right": (
                f"zoompan=z='1.3':"
                f"x='(iw-iw/zoom)*(on/{total_frames})':y='ih/2-(ih/zoom/2)':"
                f"d={total_frames}:s={width}x{height}:fps={fps}"
            ),
            "pan_up": (
                f"zoompan=z='1.3':"
                f"x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*(1-on/{total_frames})':"
                f"d={total_frames}:s={width}x{height}:fps={fps}"
            ),
            "pan_down": (
                f"zoompan=z='1.3':"
                f"x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*(on/{total_frames})':"
                f"d={total_frames}:s={width}x{height}:fps={fps}"
            ),
            "slow_push": (
                f"zoompan=z='min(zoom+0.0008,1.3)':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={total_frames}:s={width}x{height}:fps={fps}"
            )
        }

        # Fallback to default if unknown
        zoompan_filter = effects.get(effect_name)
        if not zoompan_filter:
            logger.warning(f"Unknown motion effect '{effect_name}'. Falling back to default '{settings.MOTION_DEFAULT_EFFECT}'.")
            zoompan_filter = list(effects.values())[0]

        # Build a complex filtergraph:
        #  1. Split input into background (bg) and foreground (fg)
        #  2. bg: scale to FILL the 9:16 frame, gaussian blur (looks like a canvas backdrop)
        #  3. fg: scale to FIT inside the frame (no cropping — preserves full image content)
        #  4. Overlay fg centered on top of blurred bg
        #  5. Apply zoompan Ken Burns effect on the composite
        #
        # This ensures a 16:9 historical painting is FULLY visible, not cropped.
        bg_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
            f"gblur=sigma=30"
        )
        fg_filter = (
            f"scale={width}:-2:force_original_aspect_ratio=decrease"
        )
        composite_filter = (
            f"[0:v]split=2[bg][fg];"
            f"[bg]{bg_filter}[blurred];"
            f"[fg]{fg_filter}[clear];"
            f"[blurred][clear]overlay=(W-w)/2:(H-h)/2[composed]"
        )

        if settings.MOTION_EFFECTS_ENABLED:
            full_filter = f"{composite_filter};[composed]{zoompan_filter}"
            map_arg = None  # zoompan outputs unnamed final stream, FFmpeg picks it up
        else:
            full_filter = composite_filter
            map_arg = "[composed]"  # explicitly map the composited output

        # Build command using -filter_complex (required for multi-stream compositing)
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-loop", "1",
            "-i", image_abs,
            "-t", str(duration),
            "-filter_complex", full_filter,
            "-c:v", settings.FFMPEG_VIDEO_CODEC,
            "-pix_fmt", settings.FFMPEG_PIXEL_FORMAT,
            "-r", str(fps),
        ]
        if map_arg:
            cmd += ["-map", map_arg]
        cmd.append(output_abs)

        logger.info(f"Applying motion effect '{effect_name}' to '{os.path.basename(image_path)}' for {duration}s...")
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                logger.error(f"FFmpeg motion render failed for {image_path}: {stderr}")
                raise RuntimeError(f"FFmpeg motion render failed: {stderr.strip()}")

            if not os.path.exists(output_abs) or os.path.getsize(output_abs) == 0:
                raise RuntimeError(f"FFmpeg completed but did not write to {output_abs}")

            return output_abs
        except Exception as e:
            logger.error(f"Failed to apply motion effect: {e}")
            raise e
