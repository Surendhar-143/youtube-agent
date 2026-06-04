import os
import hashlib
import logging
from PIL import Image
from config.settings import settings

logger = logging.getLogger("asset_validator")

class ValidationResult:
    def __init__(self, valid: bool, reason: str = "", score: float = 0.0):
        self.valid = valid
        self.reason = reason
        self.score = score

class AssetValidator:
    """
    Validates downloaded assets for integrity, resolution, format, and duplication.
    """
    def __init__(self):
        self.min_width = settings.ASSET_MIN_WIDTH
        self.min_height = settings.ASSET_MIN_HEIGHT
        # Set of file hashes seen in the current pipeline run to prevent duplicates
        self.seen_hashes = set()

    def calculate_hash(self, file_path: str) -> str:
        """Calculates the SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return ""

    def validate(self, file_path: str) -> ValidationResult:
        """
        Validates an image file's integrity, resolution, and format.
        """
        if not os.path.exists(file_path):
            return ValidationResult(False, "File does not exist", 0.0)

        # File size check
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return ValidationResult(False, "File size is 0 bytes", 0.0)

        try:
            # 1. Check format & corruption
            with Image.open(file_path) as img:
                # verify() reads headers and verifies integrity, but we must reopen/load to be fully sure
                img.verify()

            # Re-open because verify() closes/invalidates the image object
            with Image.open(file_path) as img:
                img.load()  # This actually decodes the pixel data, catching corrupted frames

                # 2. Check format
                img_format = img.format.upper() if img.format else ""
                if img_format not in ["JPEG", "JPG", "PNG"]:
                    return ValidationResult(False, f"Unsupported format: {img_format}", 0.0)

                # 3. Check resolution
                width, height = img.size
                if width < self.min_width or height < self.min_height:
                    return ValidationResult(
                        False, 
                        f"Resolution too low: {width}x{height} (Min: {self.min_width}x{self.min_height})", 
                        0.0
                    )

                # 4. Check duplicate hash
                file_hash = self.calculate_hash(file_path)
                if not file_hash:
                    return ValidationResult(False, "Could not compute file hash", 0.0)

                if file_hash in self.seen_hashes:
                    return ValidationResult(False, "Duplicate asset (same file content already used in this run)", 0.0)

                self.seen_hashes.add(file_hash)

                # Quality score calculation:
                # 0-100 based on resolution compared to 1920x1080
                pixels = width * height
                target_pixels = 1920 * 1080
                res_ratio = min(pixels / target_pixels, 1.0)
                quality_score = res_ratio * 100.0

                return ValidationResult(True, "Valid asset", quality_score)

        except Exception as e:
            logger.error(f"Image validation exception for {file_path}: {e}")
            return ValidationResult(False, f"Corrupted or invalid image: {str(e)}", 0.0)

    def reset_run(self):
        """Resets the duplicate hash registry for a new run."""
        self.seen_hashes.clear()
