#!/usr/bin/env python3
"""
Convert cleaned HTML into the Apographon JSON schema, with advanced parsing
for complex layouts like split footnotes and multi-page tables.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "BeautifulSoup4 is required. Install it with `pip install beautifulsoup4`."
    ) from exc

# --- Configuration & Helpers ---
LATIN_KEYWORDS = {"est", "et", "in", "ut", "aut", "nec", "quo", "non", "quae", "eius"}
GREEK_RANGE = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]")
SUPER_MAP = str.maketrans({
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
})


def to_superscript(marker: int) -> str:
    """Convert an index into a 1-based superscript marker string."""
    return str(marker).translate(SUPER_MAP)

# --- Core Functions from Your Original Script ---

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a Wellmann HTML page into the Apographon JSON schema.")
    parser.add_argument("input_html", help="Path to the HTML file.")
    parser.add_argument(
        "output_json",
        nargs="?",
        help="Destination path for the JSON output. Defaults to <output-dir>/<input-stem>.json",
    )
    parser.add_argument(
        "--output-dir",
        default="data/documents",
        help="Directory for generated JSON when no explicit output path is supplied (default: data/documents)",
    )
    return parser.parse_args()

def load_html(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def detect_language(text: str) -> str:
    if GREEK_RANGE.search(text):
        return "grc"
    lowered = text.lower()
    hits = sum(1 for word in LATIN_KEYWORDS if f" {word} " in f" {lowered} ")
    if hits >= 2 or lowered.strip().startswith("qu"):
        return "la"
    return "de"

def gather_metadata(soup: BeautifulSoup) -> Dict[str, str]:
    title = "Untitled"
    if soup.title and soup.title.string:
        title = clean_text(soup.title.string)

    author = "Unknown"
    author_meta = soup.find("meta", attrs={"name": "author"})
    if author_meta and author_meta.get("content"):
        author = clean_text(author_meta["content"])

    # Document-specific heuristics can refine the defaults when present.
    title_tag = soup.find("h2", string=re.compile("PNEUMATISCHE SCHULE", re.IGNORECASE))
    if title_tag:
        title = clean_text(title_tag.get_text(" "))

    def normalise_author(text: str) -> str:
        cleaned = clean_text(text)
        cleaned = re.sub(r"(?i)^von\s+", "", cleaned)
        return cleaned.strip(" .")

    author_tag = soup.find("p", class_="center", string=re.compile("MAX WELLMANN", re.IGNORECASE))
    if author_tag:
        candidate = author_tag.get_text(" ")
        author_candidate = normalise_author(candidate)
        if author_candidate:
            author = author_candidate

    if author == "Unknown":
        inferred = soup.find(string=re.compile(r"MAX WELLMANN", re.IGNORECASE))
        if inferred and inferred.parent:
            candidate = inferred.parent.get_text(" ")
            author_candidate = normalise_author(candidate)
            if author_candidate:
                author = author_candidate

    if author == "Unknown":
        inferred = soup.find(string=re.compile(r"^von ", re.IGNORECASE))
        if inferred:
            author_candidate = normalise_author(str(inferred))
            if author_candidate:
                author = author_candidate

    return {"title": title or "Untitled", "author": author or "Unknown"}

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def inline_note_text(note_payload: Dict[str, Any]) -> str:
    marker = note_payload.get("marker", "")
    text = note_payload.get("text", "")
    if not text:
        return marker
    return f"{marker}Footnote {marker}. {text}"

# --- NEW: Pre-processing Function to Fix Broken HTML ---

def preprocess_html_for_split_footnotes(html_string: str) -> str:
    """Patch the document so that the fn31-3 footnote retains its continuation."""

    try:
        footnote_start = html_string.index('<li id="fn31-3"')
        backlink_index = html_string.index('<a href="#ref31-3"', footnote_start)
        page32_index = html_string.index('<div class="page" id="page-32">', backlink_index)
        footnotes32_index = html_string.index('<div class="footnotes">', page32_index)
    except ValueError:
        return html_string

    table_start = html_string.find('<table', page32_index)
    if table_start == -1 or table_start >= footnotes32_index:
        return html_string

    continuation_html = html_string[table_start:footnotes32_index]
    if not continuation_html.strip():
        return html_string

    without_continuation = html_string[:table_start] + html_string[footnotes32_index:]
    try:
        new_backlink_index = without_continuation.index('<a href="#ref31-3"', footnote_start)
    except ValueError:
        return html_string

    repaired_html = (
        without_continuation[:new_backlink_index]
        + continuation_html
        + without_continuation[new_backlink_index:]
    )
    print("INFO: Successfully pre-processed and repaired split footnote fn31-3.")
    return repaired_html


# --- NEW: Helper for Structured Text Extraction from Footnotes ---

def extract_structured_text_from_note(html_content: str, note_id: str) -> str:
    """Convert footnote HTML into a readable text block."""
    soup = BeautifulSoup(html_content, "html.parser")

    for br in soup.find_all("br"):
        br.replace_with("\n")

    for table in soup.find_all("table"):
        columns: List[List[str]] = []
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            for idx, cell in enumerate(cells):
                while len(columns) <= idx:
                    columns.append([])
                text = clean_text(cell.get_text(" ")).replace(" \n", "\n")
                if text:
                    columns[idx].append(text)
        column_texts = [" ".join(parts).strip() for parts in columns if parts]
        table_text = "\n\n".join(column_texts)
        table.replace_with(table_text)

    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


# --- NEW: Stateful Parsing Logic ---

class ColumnProcessor:
    """A state machine to handle multi-page two-column tables."""
    def __init__(self):
        self.active = False
        self.footnote_map: Dict[str, Dict[str, Any]] = {}
        self.note_lookup: Dict[str, Dict[str, Any]] = {}
        self.note_counters = {'left': 0, 'right': 0}
        self.data: Dict[str, Dict[str, Any]] = {
            'left': {'html_parts': [], 'notes': [], 'pages': []},
            'right': {'html_parts': [], 'notes': [], 'pages': []}
        }
        self.post_table_fragments: List[Dict[str, Any]] = []

    def start_or_continue(self, page_soup: Tag, page_num: int) -> List[Dict[str, Any]]:
        fragments: List[Dict[str, Any]] = []
        if not self.active:
            self.active = True
            print(f"INFO: Starting two-column table processing on page {page_num}.")
        
        if page_num not in self.data['left']['pages']:
            self.data['left']['pages'].append(page_num)
            self.data['right']['pages'].append(page_num)

        table = next(
            (tbl for tbl in page_soup.find_all('table') if not tbl.find_parent(class_='footnotes')),
            None,
        )
        if table:
            left_cells: List[str] = []
            right_cells: List[str] = []
            for row in table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2:
                    left_cells.append(str(cells[0]))
                    right_cells.append(str(cells[1]))

            if left_cells and right_cells:
                prefix = f"[p.{page_num}] " if len(self.data['left']['pages']) > 1 else ""
                self.data['left']['html_parts'].append(prefix + " ".join(left_cells))
                self.data['right']['html_parts'].append(prefix + " ".join(right_cells))

        footnotes_div = page_soup.find('div', class_='footnotes')
        if footnotes_div:
            for note_li in footnotes_div.find_all('li'):
                note_id = note_li.get('id', '')
                if not note_id or note_id in self.note_lookup:
                    continue
                owner = None
                
                if re.match(r'fn\d+-Aet\d+$', note_id) or re.match(r'fn\d+-\w*b$', note_id):
                    owner = 'right'
                elif re.match(r'fn\d+-\d+a?$', note_id):
                    owner = 'left'

                if owner:
                    self.note_counters[owner] += 1
                    marker = to_superscript(self.note_counters[owner])
                else:
                    owner = 'left'
                    self.note_counters[owner] += 1
                    marker = to_superscript(self.note_counters[owner])

                if backlink := note_li.find('a', class_='footnote-backlink'):
                    backlink.decompose()

                note_text_raw = "".join(str(c) for c in note_li.contents).strip()
                clean_text_note = re.sub(r'^\s*([¹²³⁴⁵⁶⁷⁸⁹*]|\d+)\)\s*', '', note_text_raw, 1)
                plain_text = extract_structured_text_from_note(clean_text_note, note_id)

                note_payload = {
                    'id': f"note-{note_id}",
                    'marker': marker,
                    'text': plain_text,
                    'translation': ""
                }

                self.data[owner]['notes'].append(note_payload.copy())
                self.footnote_map[note_id] = {'marker': marker}
                self.note_lookup[note_id] = note_payload

        table_seen = False
        post_table_fragments: List[Dict[str, Any]] = []

        for child in page_soup.children:
            if isinstance(child, NavigableString):
                continue
            if not isinstance(child, Tag):
                continue
            if child.name == 'table' and not child.find_parent(class_='footnotes'):
                table_seen = True
                continue
            if child.name not in {'p', 'h1', 'h2', 'h3', 'h4'}:
                continue
            if child.find_parent('table') or child.find_parent(class_='footnotes'):
                continue

            text_candidate = clean_text(child.get_text(" "))
            if not text_candidate or text_candidate.isdigit():
                continue

            block_soup = BeautifulSoup(str(child), 'html.parser')
            block_notes: List[Dict[str, Any]] = []
            for anchor in block_soup.find_all('a', class_='footnote-ref'):
                href = anchor.get('href', '').lstrip('#')
                note_payload = self.note_lookup.get(href)
                if note_payload:
                    block_notes.append(note_payload.copy())
                    following = anchor.next_sibling
                    if isinstance(following, str) and following.lstrip().startswith(')'):
                        stripped = following.lstrip()
                        remaining = stripped[1:]
                        prefix = following[: len(following) - len(stripped)]
                        anchor.next_sibling.replace_with(prefix + remaining)
                    anchor.replace_with(inline_note_text(note_payload))

            text = clean_text(block_soup.get_text())
            if not text or text.isdigit():
                continue
            lang = detect_language(text)
            fragment_payload = {
                "text": text,
                "notes": block_notes,
                "lang": lang,
                "show_by_default": lang != "grc",
                "page": page_num,
                "pages": [page_num],
                "origin": "prose-block",
            }

            if table_seen:
                post_table_fragments.append(fragment_payload)
            else:
                fragments.append(fragment_payload)

        if post_table_fragments:
            self.post_table_fragments.extend(post_table_fragments)

        return fragments

    def flush(self) -> List[Dict[str, Any]]:
        if not self.active: return []
        print(f"INFO: Flushing column data from pages {self.data['left']['pages']}.")
        
        def process_column(col_data: Dict[str, Any]) -> Dict[str, Any]:
            full_html = ' '.join(col_data['html_parts'])
            soup = BeautifulSoup(full_html, 'html.parser')
            
            for a in soup.find_all('a', class_='footnote-ref'):
                href = a.get('href', '').lstrip('#')
                note_payload = self.note_lookup.get(href)
                if note_payload:
                    following = a.next_sibling
                    if isinstance(following, str):
                        stripped = following.lstrip()
                        if stripped.startswith(')'):
                            prefix = following[: len(following) - len(stripped)]
                            a.next_sibling.replace_with(prefix + stripped[1:])
                    a.replace_with(inline_note_text(note_payload))
            
            text = clean_text(soup.get_text())
            return {
                "text": text, "notes": col_data['notes'], "lang": detect_language(text),
                "show_by_default": False, "page": col_data['pages'][0], "pages": col_data['pages'],
                "origin": "table-cell",
            }

        columns = [process_column(self.data['left']), process_column(self.data['right'])]
        fragments = columns + list(self.post_table_fragments)
        self.reset()
        return fragments

    def reset(self):
        self.__init__()


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


def clone_fragment(fragment: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": fragment["text"],
        "notes": list(fragment.get("notes", [])),
        "lang": fragment["lang"],
        "show_by_default": fragment["show_by_default"],
        "page": fragment.get("page"),
        "pages": list(fragment.get("pages", [])),
        "origin": fragment.get("origin", "prose-block"),
    }


def merge_fragments(fragments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

    for fragment in fragments:
        text = fragment.get("text", "")
        if not text:
            continue

        origin = fragment.get("origin", "prose-block")
        if origin == "table-cell":
            if current is not None:
                current["page"] = current["pages"][0] if current["pages"] else None
                merged.append(current)
                current = None
            merged.append(clone_fragment(fragment))
            continue

        if current is None:
            current = clone_fragment(fragment)
            if not current["pages"]:
                current["pages"] = [current.get("page")]
            continue

        if (
            current["lang"] != fragment["lang"]
            or current["show_by_default"] != fragment["show_by_default"]
            or current.get("origin", "prose-block") != origin
        ):
            current["page"] = current["pages"][0] if current["pages"] else None
            merged.append(current)
            current = clone_fragment(fragment)
            if not current["pages"]:
                current["pages"] = [current.get("page")]
            continue

        if not should_merge(current["text"], text):
            current["page"] = current["pages"][0] if current["pages"] else None
            merged.append(current)
            current = clone_fragment(fragment)
            if not current["pages"]:
                current["pages"] = [current.get("page")]
            continue

        new_pages = fragment.get("pages", []) or [fragment.get("page")]
        for page in new_pages:
            if page is not None and (not current["pages"] or current["pages"][-1] != page):
                current["pages"].append(page)

        current["text"] = clean_text(f"{current['text']} {text}")
        current["notes"].extend(fragment.get("notes", []))

    if current is not None:
        current["page"] = current["pages"][0] if current["pages"] else None
        merged.append(current)

    return merged


def process_pages(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    fragments: List[Dict[str, Any]] = []
    column_processor = ColumnProcessor()
    all_pages = soup.find_all('div', class_='page')

    for page in all_pages:
        page_id = page.get('id', '')
        page_num = int(re.search(r'\d+', page_id).group()) if page_id else 0
        
        is_table_page = page.find('table') and not page.find('table').find_parent(class_='footnotes')
        
        if is_table_page:
            fragments.extend(column_processor.start_or_continue(page, page_num))
        else:
            if column_processor.active:
                fragments.extend(column_processor.flush())

            prose_elements = [p for p in page.find_all(['p', 'h1', 'h2', 'h3', 'h4']) if not p.find_parent(class_='footnotes')]
            if not prose_elements:
                print(f"INFO: Skipping blank/non-prose page {page_num}.")
                continue
                
            print(f"INFO: Processing prose on page {page_num}.")
            
            page_footnotes: List[Dict[str, Any]] = []
            note_map: Dict[str, Dict[str, str]] = {}
            note_counter = 0
            if footnotes_div := page.find('div', class_='footnotes'):
                for note_li in footnotes_div.find_all('li'):
                    if not (note_id := note_li.get('id', '')): continue
                    if backlink := note_li.find('a', class_='footnote-backlink'): backlink.decompose()

                    note_counter += 1
                    marker = to_superscript(note_counter)

                    note_text_html = "".join(str(c) for c in note_li.contents)
                    note_text_cleaned = re.sub(r'^\s*([¹²³⁴⁵⁶⁷⁸⁹*]|\d+)\)\s*', '', note_text_html.strip(), 1)
                    plain_text = extract_structured_text_from_note(note_text_cleaned, note_id)
                    
                    page_footnotes.append({'id_raw': note_id, 'marker': marker, 'text': plain_text})
                    note_map[note_id] = {'marker': marker}

            for element in prose_elements:
                text_content = element.get_text(strip=True)
                if not text_content or text_content.isdigit(): continue

                soup_elem = BeautifulSoup(str(element), 'html.parser')
                elem_notes = []
                for a in soup_elem.find_all('a', class_='footnote-ref'):
                    href = a.get('href', '').lstrip('#')
                    if href in note_map:
                        note_details = next((n for n in page_footnotes if n['id_raw'] == href), None)
                        if note_details:
                            elem_notes.append({
                                'id': f"note-{href}", 'marker': note_details['marker'], 'text': note_details['text'], 'translation': ""
                            })

                        marker_text = note_map[href]['marker']
                        following = a.next_sibling
                        if isinstance(following, str) and following.lstrip().startswith(')'):
                            stripped = following.lstrip()
                            remaining = stripped[1:]
                            prefix = following[: len(following) - len(stripped)]
                            a.next_sibling.replace_with(prefix + remaining)
                        a.replace_with(marker_text)
                
                text = clean_text(soup_elem.get_text())
                lang = detect_language(text)
                
                fragments.append({
                    "text": text, "notes": elem_notes, "lang": lang,
                    "show_by_default": lang != "grc", "page": page_num, "pages": [page_num],
                    "origin": "prose-block",
                })
    
    if column_processor.active:
        fragments.extend(column_processor.flush())

    return fragments

# --- Document Building (from your original script) ---

def build_document(fragments: List[Dict[str, Any]], metadata: Dict[str, str]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    
    paragraphs = []
    for index, frag in enumerate(fragments):
        original = {
            "lang": frag["lang"],
            "text": frag["text"],
            "notes": frag["notes"],
            "page": frag["page"],
            "pages": frag["pages"]
        }
        
        paragraphs.append({
            "id": f"p{index + 1:03d}",
            "original": original,
            "translation": {
                "lang": "en", "text": "", "translator": "translator-agent-v1",
                "vetted_by": "", "confidence": "pending_review",
                "show_by_default": frag["show_by_default"],
                "vetting_notes": "", "vetting_date": "", "timestamp": now
            }
        })
        
    return {
        "document": {
            "id": metadata.get("title", "document").lower().replace(" ", "-")[:40] or "document",
            "title": metadata.get("title", "Untitled"),
            "metadata": {
                "author": metadata.get("author", "Unknown"), "date": "1895",
                "translator": "translator-agent-v1", "vetted_by": ""
            },
            "paragraphs": paragraphs
        }
    }

# --- Main Execution Block ---

def main() -> None:
    args = parse_args()
    input_path = Path(args.input_html)
    output_path = Path(args.output_json) if args.output_json else Path(args.output_dir) / f"{input_path.stem}.json"

    if not input_path.exists():
        raise SystemExit(f"Error: Input file not found at {input_path}")

    html_string = load_html(input_path)
    
    # STEP 1: Apply the pre-processing step to fix broken HTML structure.
    repaired_html = preprocess_html_for_split_footnotes(html_string)
    
    # STEP 2: Parse the now-corrected HTML with BeautifulSoup.
    soup = BeautifulSoup(repaired_html, "html.parser")
    
    # STEP 3: Gather metadata and process pages into logical fragments.
    metadata = gather_metadata(soup)
    fragments = merge_fragments(process_pages(soup))

    # STEP 4: Build the final JSON document from the fragments.
    document = build_document(fragments, metadata)
    
    # STEP 5: Write the output file.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(fragments)} logical paragraphs to {output_path}")

if __name__ == "__main__":
    main()
