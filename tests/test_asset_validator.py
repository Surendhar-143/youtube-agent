import unittest
from unittest.mock import patch, MagicMock
from PIL import Image
from services.asset_validator import AssetValidator

class TestAssetValidator(unittest.TestCase):
    def setUp(self):
        self.validator = AssetValidator()

    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("PIL.Image.open")
    @patch("services.asset_validator.AssetValidator.calculate_hash")
    def test_validate_success(self, mock_hash, mock_image_open, mock_getsize, mock_exists):
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 100
        mock_hash.return_value = "dummyhash123"
        
        mock_image = MagicMock(spec=Image.Image)
        mock_image.format = "JPEG"
        mock_image.size = (1920, 1080)
        mock_image_open.return_value.__enter__.return_value = mock_image

        res = self.validator.validate("dummy_path.jpg")
        self.assertTrue(res.valid)
        self.assertEqual(res.score, 100.0)

    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("PIL.Image.open")
    @patch("services.asset_validator.AssetValidator.calculate_hash")
    def test_validate_low_resolution(self, mock_hash, mock_image_open, mock_getsize, mock_exists):
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 100
        mock_hash.return_value = "dummyhash123"
        
        mock_image = MagicMock(spec=Image.Image)
        mock_image.format = "JPEG"
        mock_image.size = (400, 300)
        mock_image_open.return_value.__enter__.return_value = mock_image

        res = self.validator.validate("dummy_path.jpg")
        self.assertFalse(res.valid)
        self.assertIn("Resolution too low", res.reason)

if __name__ == "__main__":
    unittest.main()
