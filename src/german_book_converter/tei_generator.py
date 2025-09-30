from lxml import etree
import os
from bs4 import BeautifulSoup, NavigableString


class TEIGenerator:
    """Generate a richer TEI XML from HTML input.

    html_content may be either a string of HTML or a path to an HTML file.
    """

    def __init__(self, html_content, output_path=None):
        self.input = html_content
        self.output_path = output_path
        self.tei_ns = "http://www.tei-c.org/ns/1.0"
        self.tei_root = etree.Element("TEI", nsmap={None: self.tei_ns})

    def _read_html(self):
        if isinstance(self.input, str) and os.path.isfile(self.input):
            with open(self.input, 'r', encoding='utf-8') as fh:
                return fh.read()
        return str(self.input)

    def _make_header(self, soup: BeautifulSoup):
        fileDesc = etree.SubElement(self.tei_root, "teiHeader")
        # minimal fileDesc structure
        fileDesc_file = etree.SubElement(fileDesc, "fileDesc")
        titleStmt = etree.SubElement(fileDesc_file, "titleStmt")
        title = soup.find(['h1', 'title'])
        ttext = title.get_text(strip=True) if title else ''
        etree.SubElement(titleStmt, "title").text = ttext

        # author guess: find first occurrence of 'VON' or 'von' nearby
        author_name = ''
        # try to find a centered paragraph that contains 'VON' pattern
        for p in soup.find_all('p'):
            txt = p.get_text(separator=' ', strip=True)
            if txt.upper().startswith('VON') or '\nVON' in txt.upper():
                author_name = txt.replace('\n', ' ').strip()
                break
        if not author_name:
            # fallback: look for an h3 after title
            if title:
                nxt = title.find_next(['h2', 'h3', 'p'])
                if nxt:
                    author_name = nxt.get_text(strip=True)

        if author_name:
            nameStmt = etree.SubElement(fileDesc_file, "author")
            nameStmt.text = author_name

        pubStmt = etree.SubElement(fileDesc_file, "publicationStmt")
        pub = soup.find(text=lambda t: t and 'BERLIN' in t.upper())
        if pub:
            etree.SubElement(pubStmt, "publisher").text = pub.strip()

        sourceDesc = etree.SubElement(fileDesc_file, "sourceDesc")
        etree.SubElement(sourceDesc, "biblFull").text = ttext

    def convert_html_to_tei(self):
        html = self._read_html()
        soup = BeautifulSoup(html, 'html.parser')

        # Header with minimal metadata
        self._make_header(soup)

        # Prepare text/body
        text_el = etree.SubElement(self.tei_root, "text")
        body_el = etree.SubElement(text_el, "body")

        # collect footnotes present in the document
        footnote_map = {}
        for fn_ol in soup.select('.footnotes ol'):
            for li in fn_ol.find_all('li'):
                fid = li.get('id')
                if fid:
                    footnote_map[fid] = ''.join(li.strings).strip()

        # Map pages (div.page) into TEI <div type="page" xml:id="..."></div>
        for page_div in soup.select('div.page'):
            pid = page_div.get('id') or None
            div_el = etree.SubElement(body_el, 'div')
            if pid:
                div_el.set('{{http://www.w3.org/XML/1998/namespace}}id', pid)
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
                    p_el = etree.SubElement(div_el, 'p')
                    # build text with inline footnote refs
                    for node in child.children:
                        if isinstance(node, NavigableString):
                            if p_el.text is None:
                                p_el.text = str(node)
                            else:
                                p_el.text = (p_el.text or '') + str(node)
                        elif getattr(node, 'name', None) == 'a' and 'footnote-ref' in node.get('class', []):
                            href = node.get('href', '')
                            target = href.lstrip('#')
                            ref_el = etree.SubElement(p_el, 'ref')
                            ref_el.set('target', '#' + target)
                            ref_el.text = node.get_text(strip=True)
                        else:
                            # fallback: append inner text
                            txt = node.get_text(strip=True)
                            if txt:
                                if p_el.text is None:
                                    p_el.text = txt
                                else:
                                    p_el.text = (p_el.text or '') + txt
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
                note_el.set('{{http://www.w3.org/XML/1998/namespace}}id', fid)
                note_el.set('place', 'foot')
                note_el.text = text

        return self.tei_root

    def save_tei(self, output_path=None):
        out = output_path or self.output_path
        if not out:
            raise ValueError('No output path provided')
        tree = etree.ElementTree(self.tei_root)
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