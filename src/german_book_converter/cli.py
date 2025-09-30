import argparse
from german_book_converter.converter import Converter

def main():
    parser = argparse.ArgumentParser(description="Convert a 19th-century German academic book from HTML to EPUB and TEI XML.")
    parser.add_argument('input_file', type=str, help='Path to the input HTML file.')
    parser.add_argument('--output-dir', type=str, default='data/processed', help='Directory to store the output files.')
    
    args = parser.parse_args()
    
    converter = Converter(args.input_file, args.output_dir)
    converter.convert()

if __name__ == "__main__":
    main()