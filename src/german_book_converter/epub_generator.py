from pathlib import Path
import subprocess

class EpubGenerator:
    def __init__(self, input_html: str, output_epub: str, metadata_yaml: str):
        self.input_html = input_html
        self.output_epub = output_epub
        self.metadata_yaml = metadata_yaml

    def generate_epub(self):
        # Prepare the command for Pandoc
        command = [
            'pandoc',
            self.input_html,
            '--metadata-file=' + self.metadata_yaml,
            '-o', self.output_epub,
            '--css=templates/css/epub_styles.css',
            '--epub-chapter=section'
        ]

        # Execute the command
        try:
            subprocess.run(command, check=True)
            print(f"EPUB generated successfully: {self.output_epub}")
        except subprocess.CalledProcessError as e:
            print(f"Error generating EPUB: {e}")

if __name__ == "__main__":
    # Example usage
    input_html_path = Path("data/processed/cleaned_book.html")  # Adjust as necessary
    output_epub_path = Path("data/processed/book.epub")
    metadata_yaml_path = Path("templates/pandoc/epub_metadata.yaml")

    epub_generator = EpubGenerator(input_html_path, output_epub_path, metadata_yaml_path)
    epub_generator.generate_epub()