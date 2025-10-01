import unittest
from apographon.tei_generator import generate_tei

class TestTEIGenerator(unittest.TestCase):
    def setUp(self):
        self.html_content = "<html><body><h1>Title</h1><p>Some content.</p></body></html>"
        self.expected_tei_output = """<TEI>
    <text>
        <body>
            <div>
                <head>Title</head>
                <p>Some content.</p>
            </div>
        </body>
    </text>
</TEI>"""

    def test_generate_tei(self):
        tei_output = generate_tei(self.html_content)
        self.assertEqual(tei_output.strip(), self.expected_tei_output.strip())

if __name__ == '__main__':
    unittest.main()