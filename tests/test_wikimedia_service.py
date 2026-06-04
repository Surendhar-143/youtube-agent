import unittest
from unittest.mock import patch, MagicMock
from services.wikimedia_service import WikimediaService
from schemas.asset_result import AssetResult

class TestWikimediaService(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_search_success(self, mock_urlopen):
        mock_response_json = """{
            "query": {
                "pages": {
                    "12345": {
                        "pageid": 12345,
                        "ns": 6,
                        "title": "File:Julius Caesar crossing the Rubicon.jpg",
                        "imageinfo": [
                            {
                                "url": "https://upload.wikimedia.org/wikipedia/commons/1/11/Rubicon.jpg",
                                "descriptionurl": "https://commons.wikimedia.org/wiki/File:Rubicon.jpg",
                                "descriptionshorturl": "https://commons.wikimedia.org/w/index.php?curid=12345",
                                "width": 1200,
                                "height": 800,
                                "mime": "image/jpeg",
                                "extmetadata": {
                                    "LicenseShortName": {
                                        "value": "CC-BY-SA-4.0"
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }"""
        
        mock_response = MagicMock()
        mock_response.read.return_value = mock_response_json.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        service = WikimediaService()
        results = service.search("caesar rubicon")
        
        self.assertEqual(len(results), 1)
        asset = results[0]
        self.assertIsInstance(asset, AssetResult)
        self.assertEqual(asset.url, "https://upload.wikimedia.org/wikipedia/commons/1/11/Rubicon.jpg")
        self.assertEqual(asset.width, 1200)
        self.assertEqual(asset.height, 800)
        self.assertEqual(asset.title, "Julius Caesar crossing the Rubicon.jpg")
        self.assertEqual(asset.license, "CC-BY-SA-4.0")
        self.assertEqual(asset.source, "wikimedia")

if __name__ == "__main__":
    unittest.main()
