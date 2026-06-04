import unittest
from services.asset_ranker import AssetRanker
from schemas.asset_result import AssetResult

class TestAssetRanker(unittest.TestCase):
    def setUp(self):
        self.ranker = AssetRanker()

    def test_calculate_score_keyword_match(self):
        asset1 = AssetResult(
            url="http://test.com/caesar.jpg",
            thumb_url="http://test.com/caesar_thumb.jpg",
            source="wikimedia",
            width=1920,
            height=1080,
            title="Julius Caesar Rubicon",
            license="CC0",
            query="caesar rubicon"
        )
        
        asset2 = AssetResult(
            url="http://test.com/rome.jpg",
            thumb_url="http://test.com/rome_thumb.jpg",
            source="wikimedia",
            width=1920,
            height=1080,
            title="Random ancient ruins",
            license="CC0",
            query="caesar rubicon"
        )
        
        score1 = self.ranker.calculate_score(asset1)
        score2 = self.ranker.calculate_score(asset2)
        
        self.assertTrue(score1 > score2)
        self.assertAlmostEqual(score1 - score2, 30.0)

    def test_rank(self):
        asset_low = AssetResult(
            url="http://test.com/low.jpg",
            thumb_url="http://test.com/low.jpg",
            source="pexels",
            width=800,
            height=600,
            title="Low quality image",
            license="Free",
            query="caesar"
        )
        
        asset_high = AssetResult(
            url="http://test.com/high.jpg",
            thumb_url="http://test.com/high.jpg",
            source="wikimedia",
            width=1920,
            height=1080,
            title="Julius Caesar",
            license="CC0",
            query="caesar"
        )
        
        ranked = self.ranker.rank([asset_low, asset_high])
        self.assertEqual(ranked[0].url, asset_high.url)
        self.assertEqual(ranked[1].url, asset_low.url)

if __name__ == "__main__":
    unittest.main()
