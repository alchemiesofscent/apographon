#!/usr/bin/env python3
"""Convert cleaned HTML into the Apographon JSON schema."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Optional

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


def parse_page_identifier(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    match = re.search(r"(\d+)", value)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def is_page_number(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and stripped.isdigit()


def extract_heading_text(tag: Tag) -> str:
    return clean_text(tag.get_text(" "))


def collect_fragments(soup: BeautifulSoup, footnotes: Dict[str, str]) -> List[Dict[str, object]]:
    fragments: List[Dict[str, object]] = []
    body = soup.body if soup.body else soup

    for footnote_section in body.select(".footnotes"):
        footnote_section.decompose()

    for element in body.descendants:
        if isinstance(element, Tag):
            if element.name == "div" and "page" in element.get("class", []):
                page_num = parse_page_identifier(element.get("id"))
                for child in element.descendants:
                    if not isinstance(child, Tag):
                        continue
                    if child.name == "p":
                        text, notes = extract_paragraph_content(child, footnotes)
                        text = clean_text(text)
                        if not text:
                            continue
                        if is_page_number(text):
                            # Update page number if the identifier was missing.
                            if page_num is None:
                                try:
                                    page_num = int(text.strip())
                                except ValueError:
                                    pass
                            continue
                        lang = detect_language(text)
                        fragments.append(
                            {
                                "text": text,
                                "notes": notes,
                                "lang": lang,
                                "show_by_default": lang != "grc",
                                "page": page_num,
                            }
                        )
                    elif child.name in {"h1", "h2", "h3", "h4", "h5"}:
                        heading = extract_heading_text(child)
                        if not heading:
                            continue
                        lang = detect_language(heading)
                        fragments.append(
                            {
                                "text": heading,
                                "notes": [],
                                "lang": lang,
                                "show_by_default": lang != "grc",
                                "page": page_num,
                            }
                        )
            elif element.name == "p":
                # Catch paragraphs outside explicit page containers.
                if element.find_parent(class_="page"):
                    continue
                text, notes = extract_paragraph_content(element, footnotes)
                text = clean_text(text)
                if not text or is_page_number(text):
                    continue
                lang = detect_language(text)
                fragments.append(
                    {
                        "text": text,
                        "notes": notes,
                        "lang": lang,
                        "show_by_default": lang != "grc",
                        "page": None,
                    }
                )
    return fragments


def first_alpha_character(text: str) -> str:
    for char in text:
        if char.isalpha():
            return char
    return ""


def should_merge(prev_text: str, next_text: str) -> bool:
    prev_trimmed = prev_text.rstrip()
    if not prev_trimmed:
        return False
    last_char = prev_trimmed[-1]
    first_alpha = first_alpha_character(next_text.lstrip())
    if last_char in {".", "!", "?"} and (not first_alpha or first_alpha.isupper()):
        return False
    return True


def merge_fragments(fragments: List[Dict[str, object]]) -> List[Dict[str, object]]:
    merged: List[Dict[str, object]] = []
    current: Optional[Dict[str, object]] = None

    for fragment in fragments:
        text = fragment["text"]  # type: ignore[assignment]
        notes = fragment["notes"]  # type: ignore[assignment]
        lang = fragment["lang"]  # type: ignore[assignment]
        show_by_default = fragment["show_by_default"]  # type: ignore[assignment]
        page = fragment["page"]  # type: ignore[assignment]

        if current is None:
            current = {
                "text": text,
                "notes": list(notes),
                "lang": lang,
                "show_by_default": show_by_default,
                "pages": [page] if page is not None else [],
                "page_breaks": [],
            }
            continue

        current_text = current["text"]  # type: ignore[index]
        current_lang = current["lang"]  # type: ignore[index]
        current_show = current["show_by_default"]  # type: ignore[index]

        if current_lang != lang or current_show != show_by_default:
            merged.append(current)
            current = {
                "text": text,
                "notes": list(notes),
                "lang": lang,
                "show_by_default": show_by_default,
                "pages": [page] if page is not None else [],
                "page_breaks": [],
            }
            continue

        if should_merge(current_text, text):
            if page is not None:
                pages: List[int] = current["pages"]  # type: ignore[index]
                if not pages or pages[-1] != page:
                    page_breaks: List[Dict[str, int]] = current["page_breaks"]  # type: ignore[index]
                    page_breaks.append({"page": page, "offset": len(current_text)})
                    pages.append(page)
            combined_text = clean_text(f"{current_text} {text}")
            current["text"] = combined_text
            current_notes = current["notes"]  # type: ignore[index]
            current_notes.extend(notes)
        else:
            merged.append(current)
            current = {
                "text": text,
                "notes": list(notes),
                "lang": lang,
                "show_by_default": show_by_default,
                "pages": [page] if page is not None else [],
                "page_breaks": [],
            }

    if current is not None:
        merged.append(current)

    payload: List[Dict[str, object]] = []
    for entry in merged:
        pages: List[int] = entry["pages"]  # type: ignore[index]
        original: Dict[str, object] = {
            "lang": entry["lang"],
            "text": entry["text"],
            "notes": entry["notes"],
        }
        if pages:
            original["page"] = pages[0]
            original["pages"] = pages
            if len(pages) > 1:
                original["page_breaks"] = entry["page_breaks"]
        else:
            original["page"] = None
        payload.append(
            {
                "original": original,
                "show_by_default": entry["show_by_default"],
            }
        )
    return payload


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

    fragments = collect_fragments(soup, footnotes)
    paragraph_payload = merge_fragments(fragments)

    document = build_document(paragraph_payload, metadata)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(paragraph_payload)} paragraphs to {output_path}")


if __name__ == "__main__":
    main()
