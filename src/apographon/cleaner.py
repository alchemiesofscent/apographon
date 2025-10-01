from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable

from bs4 import BeautifulSoup, Tag


class HTMLCleaner:
    """
    Clean book HTML into a semantically labelled, flowing HTML.

    Goals:
    - Flatten per-page containers into a single flow while inserting page-break markers
      as <span class="pb" data-n="page-000" role="doc-pagebreak"></span>.
    - Preserve headings, paragraphs, figures/images.
    - Preserve footnote references and consolidate footnotes into a single
      <section class="footnotes"><ol>...</ol></section> at the end.
    - Preserve two-column regions semantically by converting
      <div style*="columns: 2"> to <section class="columns" data-cols="2">.
    - Strip presentational inline styles and decorative HRs.
    """

    def __init__(self, input_path: str | Path) -> None:
        self.input_path = Path(input_path)
        raw = self.input_path.read_text(encoding="utf-8")
        self.src_soup = BeautifulSoup(raw, "html.parser")
        self._seen_head_fp: set[str] = set()
        self._kept_title_page: bool = False

    @staticmethod
    def _page_number_from_id(page_id: str | None) -> int:
        if not page_id:
            return 0
        m = re.search(r"(\d+)$", page_id)
        return int(m.group(1)) if m else 0

    @staticmethod
    def _clean_inline_styles(html: str) -> str:
        # Replace column-style DIVs with a semantic section marker first
        html = re.sub(
            r"<div([^>]*?)style=\"[^\"]*?columns\s*:\s*2[^\"]*\"([^>]*)>",
            lambda m: f"<section class=\"columns\" data-cols=\"2\"{m.group(1)}{m.group(2)}>",
            html,
            flags=re.IGNORECASE,
        )
        # Drop all remaining style attributes
        html = re.sub(r"\sstyle=\"[^\"]*\"", "", html)
        # Drop decorative horizontal rules (keep page-breaks by class)
        html = re.sub(r"<hr(?![^>]*class=\"page-break\")[^>]*/?>", "", html, flags=re.IGNORECASE)
        # Compress excessive <br> sequences (keep at most 1)
        html = re.sub(r"(?:<br\s*/?>\s*){2,}", "<br>", html, flags=re.IGNORECASE)
        return html

    def _collect_footnotes(self) -> Dict[str, str]:
        notes: Dict[str, str] = {}
        for li in self.src_soup.select(".footnotes ol li[id]"):
            nid = li.get("id")
            if not nid:
                continue
            # Keep inner HTML of the list item but remove backlink anchors
            li_clone = BeautifulSoup(li.decode(), "html.parser")
            for a in li_clone.select("a.footnote-backlink"):
                a.decompose()
            # Remove wrapping <li>
            inner = li_clone.li.decode_contents() if li_clone.li else li_clone.decode_contents()
            notes[nid] = inner.strip()
        return notes

    def _iter_pages(self) -> Iterable[Tag]:
        pages = list(self.src_soup.select("div.page[id]"))
        pages.sort(key=lambda d: self._page_number_from_id(d.get("id")))
        return pages

    @staticmethod
    def _text_compact(tag: Tag) -> str:
        return " ".join(s.strip() for s in tag.stripped_strings)

    @staticmethod
    def _is_blank_or_bookplate(text: str) -> bool:
        t = text.strip()
        if not t:
            return True
        # Common placeholder
        if t.lower() in {"blank page", "leere seite"}:
            return True
        # Very short call number/bookplate-like content
        if len(t) <= 40:
            if re.search(r"\bHist\.?\b", t) or re.search(r"\b[A-Z]{1,3}\d{2,}[A-Z]*\b", t):
                return True
        # Mostly punctuation/uppercase and digits, very short
        letters = re.sub(r"[^A-Za-z]", "", t)
        if len(t) < 30 and (letters.isupper() or not letters):
            return True
        return False

    @staticmethod
    def _heading_fingerprint(container: Tag) -> str:
        heads = [h.get_text(" ", strip=True) for h in container.find_all(["h1", "h2", "h3"])]
        if not heads:
            return ""
        s = "|".join(heads)[:300]
        s = re.sub(r"\s+", " ", s).strip().lower()
        s = re.sub(r"[^a-z0-9äöüß ]", "", s)
        return s

    def clean(self) -> str:
        # Prepare destination soup
        title_text = ""
        if self.src_soup.title and self.src_soup.title.string:
            title_text = self.src_soup.title.string.strip()

        dest = BeautifulSoup("<!doctype html><html lang=\"de\"><head><meta charset=\"utf-8\"><title></title></head><body><article class=\"work\"><main></main></article></body></html>", "html.parser")
        dest.title.string = title_text or "Cleaned Book"

        main_el = dest.select_one("article.work > main")

        # Collect footnotes globally (they will be consolidated)
        notes = self._collect_footnotes()

        # Flatten page content into a single flow
        for page in self._iter_pages():
            pid = page.get("id", "")
            # Decide if this page should be skipped (bookplate/blank/duplicate title)
            page_text = self._text_compact(page)
            fp = self._heading_fingerprint(page)
            skip = False
            keep_force = False
            # Bookplate/blank detection
            has_bookplate_block = bool(page.select_one('.bookplate'))
            page_text_up = page_text.upper()
            looks_like_bookplate = (
                'YALE' in page_text_up or 'MEDICAL LIBRARY' in page_text_up or 'HISTORICAL LIBRARY' in page_text_up
                or 'EX LIBRIS' in page_text_up or 'BOOKPLATE' in page_text_up
            )
            if self._is_blank_or_bookplate(page_text) or has_bookplate_block or looks_like_bookplate:
                skip = True
            elif fp and fp in self._seen_head_fp:
                # skip duplicate headings early in the book
                pnum = self._page_number_from_id(pid)
                if pnum and pnum < 30:
                    skip = True
            else:
                # Drop very-early series/publisher title pages (tuned heuristics)
                pnum = self._page_number_from_id(pid)
                if pnum and pnum < 30:
                    is_title_like = (
                        bool(re.search(r"philologische\s+untersuchungen", page_text, flags=re.IGNORECASE)) or
                        bool(re.search(r"weidmannsche\s+buchhandlung", page_text, flags=re.IGNORECASE)) or
                        bool(re.search(r"herausgegeben\s+von", page_text, flags=re.IGNORECASE))
                    )
                    if is_title_like:
                        if not self._kept_title_page:
                            keep_force = True  # keep the first title/series page
                        else:
                            skip = True
            if fp and not skip:
                self._seen_head_fp.add(fp)

            if skip and not keep_force:
                continue
            if keep_force:
                self._kept_title_page = True
            # Page-break marker
            pb = dest.new_tag("span")
            pb["class"] = ["pb"]
            pb["data-n"] = pid
            pb["id"] = pid
            pb["role"] = "doc-pagebreak"
            main_el.append(pb)

            # Build cleaned inner HTML for this page excluding footnotes blocks
            chunks: list[str] = []
            for child in page.children:
                if isinstance(child, str):
                    # Skip bare whitespace
                    if child.strip():
                        chunks.append(child)
                    continue
                if not isinstance(child, Tag):
                    continue
                # Skip page-local footnotes (collected globally)
                if "footnotes" in child.get("class", []):
                    continue
                # Append serialized child
                chunks.append(child.decode())

            page_html = "".join(chunks)
            page_html = self._clean_inline_styles(page_html)

            # Append to flow
            if page_html:
                frag = BeautifulSoup(page_html, "html.parser")
                # Normalize footnote reference anchors to class fn-ref
                for a in frag.select("a.footnote-ref"):
                    classes = set(a.get("class", []))
                    classes.discard("footnote-ref")
                    classes.add("fn-ref")
                    a["class"] = sorted(classes)
                main_el.append(frag)

            # Append consolidated footnotes section
        if notes:
            fsec = dest.new_tag("section")
            fsec["class"] = ["footnotes"]
            ol = dest.new_tag("ol")
            for nid, inner in notes.items():
                li = dest.new_tag("li")
                li["id"] = nid
                li_fragment = BeautifulSoup(inner, "html.parser")
                li.append(li_fragment)
                ol.append(li)
            fsec.append(ol)
            main_el.append(fsec)

        # Remove stray page-number-only paragraphs following page breaks (e.g., <p>6</p>)
        # Only act outside the consolidated footnotes block.
        for p in list(main_el.find_all('p')):
            if p.find_parent('section', class_='footnotes'):
                continue
            txt = (p.get_text(strip=True) or '')
            if re.fullmatch(r'\d{1,4}', txt):
                # Remove only when immediately preceded by a page-break marker
                prev = p.previous_sibling
                while prev and getattr(prev, 'name', None) is None and str(prev).strip() == '':
                    prev = prev.previous_sibling
                if getattr(prev, 'name', None) == 'span' and 'pb' in (prev.get('class') or []):
                    p.decompose()

        return dest.prettify()

    def write(self, output_path: str | Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.clean(), encoding="utf-8")
        return output_path


__all__ = ["HTMLCleaner"]
