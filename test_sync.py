import unittest
from sync_novels import slugify

class TestSyncNovels(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Golden Experience"), "golden-experience")
        self.assertEqual(slugify("10,000 Years In A Cultivation Sect"), "10000-years-in-a-cultivation-sect")
        self.assertEqual(slugify("Novel Title.epub"), "novel-title")
        self.assertEqual(slugify("  Spaces  And-Dashes  "), "spaces-and-dashes")

if __name__ == "__main__":
    unittest.main()
