#!/usr/bin/env python3
"""Convert cleaned HTML into the Apographon JSON schema."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

try:
    from bs4 import BeautifulSoup, NavigableString, Tag  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "BeautifulSoup4 is required. Install it with `pip install beautifulsoup4`."
    ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a Wellmann HTML page (or similar) into the Apographon JSON schema."
    )
    parser.add_argument("input_html", help="Path to the cleaned HTML file.")
    parser.add_argument("output_json", help="Destination path for the JSON output.")
    return parser.parse_args()


def load_html(path: Path) -> BeautifulSoup:
    text = path.read_text(encoding="utf-8")
    return BeautifulSoup(text, "html.parser")


LATIN_KEYWORDS = {
    "est",
    "et",
    "in",
    "ut",
    "aut",
    "nec",
    "quo",
    "non",
    "quae",
    "eius",
}

GREEK_RANGE = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]")
SUPER_MAP = str.maketrans({
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
    "0": "⁰",
})


def detect_language(text: str) -> str:
    if GREEK_RANGE.search(text):
        return "grc"
    lowered = text.lower()
    hits = sum(1 for word in LATIN_KEYWORDS if f" {word} " in f" {lowered} ")
    if hits >= 2 or lowered.strip().startswith("qu"):
        return "la"
    return "de"


def gather_metadata(soup: BeautifulSoup) -> Dict[str, str]:
    title = (soup.title.string.strip() if soup.title and soup.title.string else "Untitled")
    author_meta = soup.find("meta", attrs={"name": "author"})
    author = author_meta.get("content", "") if author_meta else ""
    if not author:
        # Attempt to infer author from centered headings
        author_tag = soup.find(string=re.compile(r"^von ", re.IGNORECASE))
        author = author_tag.strip().replace("VON", "").strip() if author_tag else ""
    return {
        "title": title,
        "author": author or "Unknown",
    }


def build_footnote_map(soup: BeautifulSoup) -> Dict[str, str]:
    notes: Dict[str, str] = {}
    for li in soup.select(".footnotes li[id]"):
        note_id = li.get("id")
        if not note_id:
            continue
        text = li.get_text(" ", strip=True)
        # Remove backlink symbols such as ↩
        text = text.replace("↩", "").strip()
        notes[note_id] = text
    return notes


def normalise_note_id(note_id: str, marker: str) -> str:
    match = re.match(r"fn(\d+)-(\d+)", note_id)
    if match:
        page, number = match.groups()
        return f"page-{page}-note-{number}"
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", note_id).strip("-")
    return f"note-{cleaned or marker}"


def superscript(marker: str) -> str:
    if marker.isdigit():
        return marker.translate(SUPER_MAP)
    return marker


def extract_paragraphs(soup: BeautifulSoup) -> List[Tag]:
    body = soup.body if soup.body else soup
    paragraphs: List[Tag] = []
    for p in body.find_all("p"):
        if p.find_parent(class_="footnotes"):
            continue
        if not p.get_text(strip=True):
            continue
        paragraphs.append(p)
    return paragraphs


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_paragraph_content(
    p: Tag,
    footnotes: Dict[str, str],
) -> Tuple[str, List[Dict[str, str]]]:
    text_fragments: List[str] = []
    notes: List[Dict[str, str]] = []

    for node in p.descendants:
        if isinstance(node, NavigableString):
            text_fragments.append(str(node))
        elif isinstance(node, Tag):
            if node.name == "br":
                text_fragments.append(" ")
            elif node.name == "a" and node.get("href", "").startswith("#fn"):
                href = node.get("href", "").lstrip("#")
                marker = node.get_text(strip=True) or "*"
                marker_sup = superscript(marker)
                note_id = normalise_note_id(href, marker)
                notes.append(
                    {
                        "id": note_id,
                        "marker": marker_sup,
                        "text": clean_text(footnotes.get(href, "")),
                        "translation": ""
                    }
                )
                text_fragments.append(marker_sup)

    text = clean_text("".join(text_fragments))
    return text, notes


def build_document(paragraphs: List[Dict[str, object]], metadata: Dict[str, str]) -> Dict[str, object]:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "document": {
            "id": metadata.get("title", "document").lower().replace(" ", "-")[:40] or "document",
            "title": metadata.get("title", "Untitled"),
            "metadata": {
                "author": metadata.get("author", "Unknown"),
                "date": metadata.get("date", ""),
                "translator": "translator-agent-v1",
                "vetted_by": ""
            },
            "paragraphs": [
                {
                    "id": f"p{index + 1:03d}",
                    "original": paragraph["original"],
                    "translation": {
                        "lang": "en",
                        "text": "",
                        "translator": "translator-agent-v1",
                        "vetted_by": "",
                        "confidence": "pending_review",
                        "show_by_default": paragraph["show_by_default"],
                        "vetting_notes": "",
                        "vetting_date": "",
                        "timestamp": now
                    }
                }
                for index, paragraph in enumerate(paragraphs)
            ]
        }
    }


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_html)
    output_path = Path(args.output_json)

    soup = load_html(input_path)
    metadata = gather_metadata(soup)
    footnotes = build_footnote_map(soup)

    paragraph_nodes = extract_paragraphs(soup)
    paragraph_payload: List[Dict[str, object]] = []

    for node in paragraph_nodes:
        text, notes = extract_paragraph_content(node, footnotes)
        if not text:
            continue
        lang = detect_language(text)
        show_by_default = False if lang == "grc" else True
        paragraph_payload.append(
            {
                "original": {
                    "lang": lang,
                    "text": text,
                    "notes": notes
                },
                "show_by_default": show_by_default,
            }
        )

    document = build_document(paragraph_payload, metadata)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(paragraph_payload)} paragraphs to {output_path}")


if __name__ == "__main__":
    main()
