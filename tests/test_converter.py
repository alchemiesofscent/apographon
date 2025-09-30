import unittest
from german_book_converter.converter import Converter

class TestConverter(unittest.TestCase):

    def setUp(self):
        self.converter = Converter()

    def test_cleanup_html(self):
        raw_html = "<html><body><h1>Title</h1><p>Content</p></body></html>"
        cleaned_html = self.converter.cleanup_html(raw_html)
        self.assertIn("<h1>Title</h1>", cleaned_html)
        self.assertIn("<p>Content</p>", cleaned_html)

    def test_convert_to_tei(self):
        cleaned_html = "<html><body><h1>Title</h1><p>Content</p></body></html>"
        tei_output = self.converter.convert_to_tei(cleaned_html)
        self.assertIn("<teiHeader>", tei_output)
        self.assertIn("<title>Title</title>", tei_output)

    def test_convert_to_epub(self):
        cleaned_html = "<html><body><h1>Title</h1><p>Content</p></body></html>"
        epub_output = self.converter.convert_to_epub(cleaned_html)
        self.assertIn("EPUB", epub_output)

if __name__ == '__main__':
    unittest.main()