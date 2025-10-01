from lxml import etree
import os
import re
from bs4 import BeautifulSoup, NavigableString


class TEIGenerator:
    """Generate a richer TEI XML from HTML input.

    html_content may be either a string of HTML or a path to an HTML file.
    """

    def __init__(self, html_content, output_path=None, metadata=None):
        self.input = html_content
        self.output_path = output_path
        self.tei_ns = "http://www.tei-c.org/ns/1.0"
        self.tei_root = etree.Element("TEI", nsmap={None: self.tei_ns})
        self.metadata = metadata or {}
        self._ref_map = {}  # fid -> [ref xml:id]
        self._ref_count = {}  # fid -> n

    def _read_html(self):
        if isinstance(self.input, str) and os.path.isfile(self.input):
            with open(self.input, 'r', encoding='utf-8') as fh:
                return fh.read()
        return str(self.input)

    def _parse_citation(self, citation: str) -> dict:
        """Parse a simple citation like:
        "Wellmann, M. (1895), Die pneumatische Schule bis auf Archigenes, Philologische Untersuchungen, Weidmannsche Buchhandlung."
        Returns dict keys: author, title, date, series, publisher.
        """
        data = {}
        try:
            # Basic pattern: Author, I. (YYYY), Title, Series, Publisher
            m = re.match(r"\s*([^,]+),\s*([^()]+?)\s*\((\d{4})\)\s*,\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^.,]+)", citation)
            if m:
                surname, initials, year, title, series, publisher = m.groups()
                data['author'] = f"{surname.strip()}, {initials.strip().rstrip('.')}"
                data['date'] = year
                data['title'] = title.strip()
                data['series'] = series.strip()
                data['publisher'] = publisher.strip()
        except Exception:
            pass
        return data

    def _author_parts(self, name: str) -> tuple[str, str]:
        # Accept "Surname, Forename" or "Forename Surname"; fallback to whole as surname
        name = name.strip()
        if ',' in name:
            a, b = [x.strip() for x in name.split(',', 1)]
            surname, forename = a, b
        else:
            parts = name.split()
            if len(parts) >= 2:
                forename, surname = ' '.join(parts[:-1]), parts[-1]
            else:
                surname, forename = name, ''
        return forename, surname

    def _make_header(self, soup: BeautifulSoup):
        header = etree.SubElement(self.tei_root, "teiHeader")
        fileDesc = etree.SubElement(header, "fileDesc")

        # Merge citation-derived metadata if provided
        citation = self.metadata.get('citation')
        if citation:
            self.metadata = {**self._parse_citation(citation), **self.metadata}

        # titleStmt
        titleStmt = etree.SubElement(fileDesc, "titleStmt")
        title = self.metadata.get('title')
        if not title:
            title_tag = soup.find(['h1', 'title'])
            title = title_tag.get_text(strip=True) if title_tag else ''
        etree.SubElement(titleStmt, "title").text = title

        author = self.metadata.get('author', '')
        if author:
            forename, surname = self._author_parts(author)
            auth_el = etree.SubElement(titleStmt, "author")
            pn = etree.SubElement(auth_el, "persName")
            if forename:
                etree.SubElement(pn, "forename").text = forename
            etree.SubElement(pn, "surname").text = surname

        # publicationStmt
        pubStmt = etree.SubElement(fileDesc, "publicationStmt")
        publisher = self.metadata.get('publisher')
        if publisher:
            etree.SubElement(pubStmt, "publisher").text = publisher
        place = self.metadata.get('place')
        if place:
            etree.SubElement(pubStmt, "pubPlace").text = place
        date = self.metadata.get('date')
        if date:
            d = etree.SubElement(pubStmt, "date")
            d.text = date
            d.set('when', date)

        # seriesStmt
        series = self.metadata.get('series')
        if series:
            seriesStmt = etree.SubElement(fileDesc, "seriesStmt")
            st = etree.SubElement(seriesStmt, "title")
            st.set('level', 's')
            st.text = series

        # sourceDesc with biblStruct
        sourceDesc = etree.SubElement(fileDesc, "sourceDesc")
        bibl = etree.SubElement(sourceDesc, 'biblStruct')
        monogr = etree.SubElement(bibl, 'monogr')
        # author in monogr
        if author:
            forename, surname = self._author_parts(author)
            a = etree.SubElement(monogr, 'author')
            pn = etree.SubElement(a, 'persName')
            if forename:
                etree.SubElement(pn, 'forename').text = forename
            etree.SubElement(pn, 'surname').text = surname
        # title in monogr
        t = etree.SubElement(monogr, 'title')
        t.set('level', 'm')
        t.text = title
        # imprint
        imp = etree.SubElement(monogr, 'imprint')
        if place:
            etree.SubElement(imp, 'pubPlace').text = place
        if publisher:
            etree.SubElement(imp, 'publisher').text = publisher
        if date:
            d2 = etree.SubElement(imp, 'date')
            d2.text = date
            d2.set('when', date)
        # series block
        if series:
            s = etree.SubElement(bibl, 'series')
            st2 = etree.SubElement(s, 'title')
            st2.set('level', 's')
            st2.text = series

    def convert_html_to_tei(self):
        html = self._read_html()
        soup = BeautifulSoup(html, 'html.parser')

        # Header with enriched metadata
        self._make_header(soup)

        # Prepare text/body
        text_el = etree.SubElement(self.tei_root, "text")
        body_el = etree.SubElement(text_el, "body")

        # collect footnotes present in the document (consolidated or per-page)
        footnote_map = {}
        for fn_ol in soup.select('.footnotes ol'):
            for li in fn_ol.find_all('li'):
                fid = li.get('id')
                if fid:
                    footnote_map[fid] = ''.join(li.strings).strip()

        def add_p_with_inlines(parent_el, p_tag):
            p_el = etree.SubElement(parent_el, 'p')
            for node in p_tag.children:
                if isinstance(node, NavigableString):
                    # Append text nodes
                    if p_el.text is None:
                        p_el.text = str(node)
                    else:
                        p_el.text = (p_el.text or '') + str(node)
                elif getattr(node, 'name', None) == 'a' and ('footnote-ref' in node.get('class', []) or 'fn-ref' in node.get('class', [])):
                    href = node.get('href', '')
                    target = href.lstrip('#')
                    ref_el = etree.SubElement(p_el, 'ref')
                    ref_el.set('target', '#' + target)
                    # assign xml:id to support back pointers
                    if target:
                        idx = (self._ref_count.get(target, 0) + 1)
                        self._ref_count[target] = idx
                        ref_id = f"ref-{target}-{idx}"
                        ref_el.set('{http://www.w3.org/XML/1998/namespace}id', ref_id)
                        self._ref_map.setdefault(target, []).append(ref_id)
                    ref_el.text = node.get_text(strip=True)
                else:
                    # fallback: append inner text
                    txt = node.get_text(strip=True)
                    if txt:
                        if p_el.text is None:
                            p_el.text = txt
                        else:
                            p_el.text = (p_el.text or '') + txt

        def process_flow(container):
            current_div = etree.SubElement(body_el, 'div')
            for child in container.children:
                if isinstance(child, NavigableString):
                    text = str(child).strip()
                    if not text:
                        continue
                    if len(current_div) == 0:
                        p_el = etree.SubElement(current_div, 'p')
                        p_el.text = text
                    else:
                        last = current_div[-1]
                        last.tail = (last.tail or '') + text if last.tail else text
                    continue

                if not hasattr(child, 'name'):
                    continue

                tag = child.name.lower()
                classes = child.get('class', [])
                if tag == 'span' and 'pb' in classes:
                    # page break milestone
                    pb_el = etree.SubElement(body_el, 'pb')
                    pid = child.get('data-n')
                    if pid:
                        # prefer numeric page for @n
                        m = re.search(r"(\d+)$", pid)
                        if m:
                            pb_el.set('n', m.group(1))
                        pb_el.set('{http://www.w3.org/XML/1998/namespace}id', pid)
                    # start a fresh div after page break
                    current_div = etree.SubElement(body_el, 'div')
                elif tag in ['h1', 'h2', 'h3', 'h4']:
                    head = etree.SubElement(current_div, 'head')
                    head.text = child.get_text(strip=True)
                elif tag == 'p':
                    add_p_with_inlines(current_div, child)
                elif tag in ['section', 'div'] and ('columns' in classes or (child.has_attr('style') and 'columns:' in child['style'])):
                    # Columns: encode as a typed div and keep child paragraphs
                    col_div = etree.SubElement(current_div, 'div')
                    col_div.set('type', 'columns')
                    n = child.get('data-cols') or '2'
                    col_div.set('n', str(n))
                    for inner in child.children:
                        if getattr(inner, 'name', None) == 'p':
                            add_p_with_inlines(col_div, inner)
                elif tag == 'img':
                    fig = etree.SubElement(current_div, 'figure')
                    img = etree.SubElement(fig, 'graphic')
                    src = child.get('src')
                    if src:
                        img.set('url', src)
                elif tag == 'figure':
                    # pass-through figure/img
                    fig = etree.SubElement(current_div, 'figure')
                    img = child.find('img')
                    if img and img.get('src'):
                        g = etree.SubElement(fig, 'graphic')
                        g.set('url', img['src'])

        # Prefer cleaned flow with page-break markers if present
        flow_container = soup.select_one('article.work > main') or soup.body
        if flow_container and soup.select('span.pb'):
            process_flow(flow_container)
        else:
            # Fallback: Map per-page divs to <div type="page">
            for page_div in soup.select('div.page'):
                pid = page_div.get('id') or None
                div_el = etree.SubElement(body_el, 'div')
                if pid:
                    div_el.set('{http://www.w3.org/XML/1998/namespace}id', pid)
                    div_el.set('type', 'page')

                # iterate over children to preserve order
                for child in page_div.children:
                    if isinstance(child, NavigableString):
                        text = str(child).strip()
                        if text:
                            # attach as tail of last element or as a paragraph
                            if len(div_el):
                                last = div_el[-1]
                                if last.tail:
                                    last.tail = (last.tail or '') + '\n' + text
                                else:
                                    last.tail = text
                            else:
                                p_el = etree.SubElement(div_el, 'p')
                                p_el.text = text
                        continue

                    if not hasattr(child, 'name'):
                        continue

                    tag = child.name.lower()
                    if tag in ['h1', 'h2', 'h3', 'h4']:
                        head = etree.SubElement(div_el, 'head')
                        head.text = child.get_text(strip=True)
                    elif tag == 'p':
                        add_p_with_inlines(div_el, child)
                    elif tag == 'img':
                        fig = etree.SubElement(div_el, 'figure')
                        img = etree.SubElement(fig, 'graphic')
                        src = child.get('src')
                        if src:
                            img.set('url', src)
                    # skip other markup (hr, etc.)

        # append back matter with footnotes
        if footnote_map:
            back = etree.SubElement(self.tei_root, 'back')
            notes_div = etree.SubElement(back, 'div')
            notes_div.set('type', 'notes')
            for fid, text in footnote_map.items():
                note_el = etree.SubElement(notes_div, 'note')
                note_el.set('{http://www.w3.org/XML/1998/namespace}id', fid)
                note_el.set('place', 'foot')
                note_el.text = text
                # add back pointers to referencing locations if known
                for rid in self._ref_map.get(fid, []):
                    ptr = etree.SubElement(note_el, 'ptr')
                    ptr.set('type', 'back')
                    ptr.set('target', f"#{rid}")

        return self.tei_root

    def save_tei(self, output_path=None):
        out = output_path or self.output_path
        if not out:
            raise ValueError('No output path provided')
        tree = etree.ElementTree(self.tei_root)
        # Add optional browser stylesheet PI for in-browser viewing if the XSL is present alongside the TEI
        try:
            pi = etree.ProcessingInstruction('xml-stylesheet', 'type="text/xsl" href="tei-viewer.xsl"')
            # Insert before root
            self.tei_root.addprevious(pi)
        except Exception:
            pass
        tree.write(out, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    def generate_tei(self, output_path=None):
        self.convert_html_to_tei()
        self.save_tei(output_path or self.output_path)

if __name__ == "__main__":
    # Example usage
    input_html_path = os.path.join('data', 'raw', 'example.html')
    output_tei_path = os.path.join('data', 'processed', 'output.tei.xml')
    template_path = os.path.join('templates', 'pandoc', 'tei_template.xml')

    with open(input_html_path, 'r', encoding='utf-8') as file:
        html_content = file.read()

    tei_generator = TEIGenerator(html_content, template_path)
    tei_generator.generate_tei(output_tei_path)


# Backwards-compatible function used by tests
def generate_tei(html_content: str) -> str:
    # Very small conversion: extract first <h1> as head and first <p> as paragraph
    try:
        parser = etree.HTMLParser()
        root = etree.fromstring(html_content, parser=parser)
        h1 = root.find('.//h1')
        p = root.find('.//p')
        head_text = h1.text if h1 is not None else ''
        p_text = p.text if p is not None else ''
        tei = f"<TEI>\n    <text>\n        <body>\n            <div>\n                <head>{head_text}</head>\n                <p>{p_text}</p>\n            </div>\n        </body>\n    </text>\n</TEI>"
        return tei
    except Exception:
        # Fall back to a minimal TEI wrapper
        return "<TEI><text><body><div><p/></div></body></text></TEI>"
