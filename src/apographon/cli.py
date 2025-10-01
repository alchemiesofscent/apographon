import argparse
from apographon.converter import GermanBookConverter


def main():
    parser = argparse.ArgumentParser(
        description="Convert a 19th-century German academic book from HTML to EPUB and TEI XML."
    )
    parser.add_argument("--input", dest="input_file", required=True, help="Path to the input HTML file.")
    parser.add_argument(
        "--output",
        dest="output_dir",
        default="data/processed",
        help="Directory to store the output files.",
    )
    parser.add_argument(
        "--skip-epub",
        action="store_true",
        help="Skip EPUB generation (useful if Pandoc is unavailable).",
    )
    parser.add_argument(
        "--with-viewer",
        action="store_true",
        help="Copy a minimal web viewer and emit view.html in the output directory.",
    )
    meta = parser.add_argument_group('metadata (optional, TEI header)')
    meta.add_argument("--meta-title", help="Work title for TEI header")
    meta.add_argument("--meta-author", help="Author name (e.g., 'Wellmann, M.')")
    meta.add_argument("--meta-date", help="Publication year (e.g., 1895)")
    meta.add_argument("--meta-publisher", help="Publisher (e.g., 'Weidmannsche Buchhandlung')")
    meta.add_argument("--meta-place", help="Place of publication (e.g., 'Berlin')")
    meta.add_argument("--meta-series", help="Series title (e.g., 'Philologische Untersuchungen')")
    meta.add_argument("--meta-citation", help="Full citation string to parse (optional)")

    args = parser.parse_args()

    metadata = {
        k: v for k, v in dict(
            title=args.meta_title,
            author=args.meta_author,
            date=args.meta_date,
            publisher=args.meta_publisher,
            place=args.meta_place,
            series=args.meta_series,
            citation=args.meta_citation,
        ).items() if v
    }
    converter = GermanBookConverter(args.input_file, args.output_dir, metadata=metadata or None)
    converter.clean_html()
    converter.generate_tei()
    if not args.skip_epub:
        converter.generate_epub()
    if args.with_viewer:
        converter.emit_viewer()


if __name__ == "__main__":
    main()
