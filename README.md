# German Book Converter

This project is designed to analyze a provided HTML file of a 19th-century German academic book and convert it into two formats: a reflowable EPUB and a TEI XML document. The conversion process utilizes Python and the Pandoc command-line tool to ensure high-quality output.

## Project Structure

The project is organized as follows:

- **src/**: Contains the main source code for the project.
  - **german_book_converter/**: The main package containing all the conversion logic.
    - `__init__.py`: Initializes the package.
    - `cli.py`: Command-line interface for running the conversion.
    - `converter.py`: Core logic for converting HTML to desired formats.
    - `pandoc_wrapper.py`: Wrapper for the Pandoc tool.
    - `tei_generator.py`: Generates the TEI XML document.
    - `epub_generator.py`: Generates the EPUB file.
    - `utils.py`: Utility functions for various tasks.
  - **scripts/**: Contains scripts for environment checks and other utilities.
    - `env_check.py`: Checks for necessary dependencies.

- **data/**: Contains input and output data.
  - **raw/**: Original HTML files to be processed.
  - **processed/**: Directory for cleaned and processed files.

- **templates/**: Contains templates for TEI and EPUB generation.
  - **pandoc/**: Templates for Pandoc conversion.
    - `tei_template.xml`: Template for TEI XML.
    - `epub_metadata.yaml`: Metadata for EPUB.
  - **css/**: CSS styles for EPUB formatting.
    - `epub_styles.css`: Styles for the EPUB output.

- **tests/**: Contains unit tests for the project.
  - `test_converter.py`: Tests for the converter functionality.
  - `test_tei.py`: Tests for TEI generation.
  - **fixtures/**: Sample HTML content for testing.
    - `sample.html`: Sample HTML for tests.

- **docs/**: Documentation for the project.
  - `usage.md`: Instructions on how to use the project.

- **.github/**: Contains GitHub workflows for CI/CD.
  - **workflows/**: CI workflow definitions.
    - `ci.yml`: Continuous integration workflow.

- **scripts/**: Contains automation scripts.
  - `build_epub.sh`: Script to build the EPUB file.
  - `validate_tei.sh`: Script to validate TEI XML.

- **Makefile**: Build instructions and commands.

- **pyproject.toml**: Project metadata and dependencies.

- **requirements.txt**: Required Python packages.

- **.gitignore**: Specifies files to ignore in Git.

- **LICENSE**: Licensing information for the project.

## Installation

To set up the project, clone the repository and install the required dependencies:

```bash
git clone <repository-url>
cd german-book-converter
pip install -r requirements.txt
```

Ensure that Pandoc is installed on your system, as it is required for the conversion process.

## Usage

To convert the HTML file into EPUB and TEI formats, use the command-line interface:

```bash
python src/german_book_converter/cli.py --input data/raw/example.html --output data/processed/
```

This command will process the provided HTML file and generate the corresponding EPUB and TEI XML documents in the specified output directory.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.