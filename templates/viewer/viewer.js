(function() {
  const qs = new URLSearchParams(location.search);
  const el = {
    file: document.getElementById('fileInput'),
    src: document.getElementById('srcInput'),
    load: document.getElementById('loadBtn'),
    status: document.getElementById('status'),
    content: document.getElementById('content'),
    togglePb: document.getElementById('togglePb'),
    toggleCols: document.getElementById('toggleCols'),
    toggleWide: document.getElementById('toggleWide'),
    toggleInline: document.getElementById('toggleInlineNotes'),
    toggleToc: document.getElementById('toggleToc'),
    toc: document.getElementById('toc'),
    currentSection: document.getElementById('currentSection'),
    notesPanel: document.getElementById('notes'),
    noteBody: document.getElementById('noteBody'),
    closeNotes: document.getElementById('closeNotes'),
    backToRef: document.getElementById('backToRef'),
  };
  let originalHTML = null; // snapshot of injected content (innerHTML of main)
  let pageNav = null;
  let sectionNav = null;
  let footnoteRefs = {}; // fid -> [anchorEl]
  let lastRefEl = null; // last in-text anchor clicked

  const setStatus = (msg) => { if (el.status) el.status.textContent = msg; };

  function inject(html) {
    // Try to pull just the <article .work > <main> contents if present
    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      const main = doc.querySelector('article.work > main') || doc.body;
      originalHTML = main.innerHTML;
      renderContent();
    } catch (e) {
      originalHTML = html; // last resort
      renderContent();
    }
  }

  function ensurePbIds(container) {
    container.querySelectorAll('span.pb').forEach(pb => {
      const id = pb.getAttribute('id');
      const dn = pb.getAttribute('data-n');
      if (!id && dn) pb.id = dn;
    });
  }

  function mergeParagraphsAcrossPagebreaks(container) {
    // Helpers to find boundary text nodes
    function lastTextNode(el) {
      for (let node = el.lastChild; node; node = node.previousSibling) {
        if (node.nodeType === Node.TEXT_NODE && node.nodeValue && node.nodeValue.trim() !== '') return node;
        if (node.nodeType === Node.ELEMENT_NODE) {
          const inner = lastTextNode(node);
          if (inner) return inner;
        }
      }
      return null;
    }
    function firstTextNode(el) {
      for (let node = el.firstChild; node; node = node.nextSibling) {
        if (node.nodeType === Node.TEXT_NODE && node.nodeValue && node.nodeValue.trim() !== '') return node;
        if (node.nodeType === Node.ELEMENT_NODE) {
          const inner = firstTextNode(node);
          if (inner) return inner;
        }
      }
      return null;
    }

    // Merge adjacent paragraphs split by a page break marker
    const pbs = Array.from(container.querySelectorAll('span.pb'));
    pbs.forEach(pb => {
      const prev = pb.previousElementSibling;
      const next = pb.nextElementSibling;
      if (prev && prev.tagName === 'P' && next && next.tagName === 'P') {
        const tnPrev = lastTextNode(prev);
        const tnNext = firstTextNode(next);
        const endText = tnPrev ? tnPrev.nodeValue : (prev.textContent || '');
        const startText = tnNext ? tnNext.nodeValue : (next.textContent || '');

        let joiner = '';
        let handledHyphenation = false;

        // Normalize soft hyphen (U+00AD) at boundary
        const SOFT_HYPHEN = /\u00AD$/;
        const NB_HYPHEN = /\u2011$/; // non-breaking hyphen

        const endTrim = endText.replace(/[\s\u00A0]+$/u, '');
        const startTrim = startText.replace(/^[\s\u00A0]+/u, '');

        // Hyphenation detection: prev ends with hyphen (soft/normal) and next starts with lowercase letter
        const endsHyphen = /[A-Za-zÄÖÜäöüß]-$/.test(endTrim) || SOFT_HYPHEN.test(endTrim) || NB_HYPHEN.test(endTrim);
        const startsLower = /^[a-zäöüß]/.test(startTrim);
        if (endsHyphen && startsLower && tnPrev) {
          // Remove trailing hyphen (or soft hyphen) from previous text
          tnPrev.nodeValue = endTrim.replace(/[-\u00AD\u2011]$/u, '');
          // Trim leading spaces in next
          if (tnNext) tnNext.nodeValue = startTrim;
          joiner = '';
          handledHyphenation = true;
        }

        if (!handledHyphenation) {
          // Decide if a space is needed between words
          const endsAlphaNum = /[A-Za-zÄÖÜäöüß0-9)]$/.test(endTrim);
          const startsAlphaNum = /^[A-Za-zÄÖÜäöüß0-9(]/.test(startTrim);
          // If both sides are alphanumeric without clear punctuation separation, add a space
          if (endsAlphaNum && startsAlphaNum) joiner = ' ';
        }

        // Append joiner to prev end if needed
        if (joiner) {
          if (tnPrev) tnPrev.nodeValue = (tnPrev.nodeValue || '') + joiner;
          else prev.appendChild(document.createTextNode(joiner));
        }

        // Move next's children into prev
        while (next.firstChild) prev.appendChild(next.firstChild);
        next.remove();
        // Remove the page break entirely in merged mode to allow true flow
        pb.remove();
      }
    });
  }

  function linkifyIndices(container) {
    // Build map of page numbers to pb ids
    const pageMap = {};
    container.querySelectorAll('span.pb').forEach(pb => {
      const dn = pb.getAttribute('data-n') || '';
      const m = /([0-9]+)$/.exec(dn);
      if (m) pageMap[m[1]] = pb.id || dn;
    });

    // Helper: linkify numbers within a node's text
    function linkifyNodeText(node) {
      const text = node.nodeValue;
      if (!text) return;
      const frag = document.createDocumentFragment();
      let lastIndex = 0;
      const re = /(\b\d{1,4})(?:\s*[-–—]\s*(\d{1,4}))?|\b(\d{1,4})(?=(?:ff?\.?))|\b(\d{1,4})\b/g;
      let m;
      while ((m = re.exec(text)) !== null) {
        const idx = m.index;
        if (idx > lastIndex) frag.appendChild(document.createTextNode(text.slice(lastIndex, idx)));
        const n1 = m[1] || m[3] || m[4];
        const targetId = pageMap[n1];
        if (targetId) {
          const a = document.createElement('a');
          a.href = `#${targetId}`;
          a.textContent = text.slice(idx, re.lastIndex);
          frag.appendChild(a);
        } else {
          frag.appendChild(document.createTextNode(text.slice(idx, re.lastIndex)));
        }
        lastIndex = re.lastIndex;
      }
      if (lastIndex < text.length) frag.appendChild(document.createTextNode(text.slice(lastIndex)));
      node.parentNode.replaceChild(frag, node);
    }

    function processRangeFromHeading(heading) {
      // Process until the next heading of same or higher level
      const level = parseInt(heading.tagName.substring(1), 10) || 6;
      for (let cur = heading.nextElementSibling; cur; cur = cur.nextElementSibling) {
        const isHead = /^H[1-6]$/.test(cur.tagName);
        if (isHead && (parseInt(cur.tagName.substring(1), 10) <= level)) break;
        // Skip within existing links
        Array.from(cur.childNodes).forEach(n => {
          if (n.nodeType === Node.TEXT_NODE) linkifyNodeText(n);
        });
      }
    }

    // Find index headings by text
    const headings = Array.from(container.querySelectorAll('h1, h2, h3'));
    headings.forEach(h => {
      const t = (h.textContent || '').toLowerCase();
      if (t.includes('sachregister') || t.includes('stellenregister') || t.includes('inhalt') || t.includes('inhaltsverzeichnis')) {
        processRangeFromHeading(h);
      }
    });

    // Fix anchors that point to missing ids but look like page references
    container.querySelectorAll('a[href^="#"]').forEach(a => {
      const href = a.getAttribute('href');
      if (!href) return;
      const id = href.slice(1);
      if (id && !container.querySelector(`#${CSS.escape(id)}`)) {
        const n = (/^\d{1,4}$/.test(a.textContent.trim()) ? a.textContent.trim() : null);
        if (n && pageMap[n]) a.setAttribute('href', `#${pageMap[n]}`);
      }
    });
  }

  function addBacklinksInFootnotes(container, refsIndex) {
    // Add ↩ link to the first ref anchor inside consolidated footnotes list
    container.querySelectorAll('section.footnotes ol li[id]').forEach(li => {
      if (li.querySelector('.footnote-backlink')) return;
      const fid = li.getAttribute('id');
      const refs = refsIndex[fid] || [];
      if (!refs.length) return;
      const back = document.createElement('a');
      back.className = 'footnote-backlink';
      back.textContent = '↩';
      back.href = `#${refs[0].id}`;
      // Append with spacing
      li.appendChild(document.createTextNode(' '));
      li.appendChild(back);
    });
  }

  function renderContent() {
    if (!originalHTML) return;
    // Rebuild content from original snapshot to keep operations reversible
    el.content.innerHTML = originalHTML;
    ensurePbIds(el.content);
    // Flow paragraphs across page breaks if page breaks are disabled
    if (el.togglePb && !el.togglePb.checked) {
      mergeParagraphsAcrossPagebreaks(el.content);
    }
    buildTOC();
    setupPagesHUD();
    setupFootnotes();
    linkifyIndices(el.content);
    applyToggles();
    // Open TOC by default
    document.documentElement.classList.add('toc-open');
  }

  async function loadFromURL(url) {
    setStatus(`Loading ${url} …`);
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const html = await res.text();
      inject(html);
      setStatus(`Loaded ${url}`);
    } catch (err) {
      setStatus(`Failed to load: ${err.message}. If using file://, try a local server.`);
    }
  }

  function loadFromFile(file) {
    const reader = new FileReader();
    reader.onload = e => { inject(e.target.result); setStatus(`Loaded ${file.name}`); };
    reader.onerror = () => setStatus('Failed to read file');
    reader.readAsText(file);
  }

  // Wire controls
  el.file.addEventListener('change', () => {
    if (el.file.files && el.file.files[0]) loadFromFile(el.file.files[0]);
  });
  el.load.addEventListener('click', () => {
    const val = el.src.value.trim();
    if (val) loadFromURL(val);
  });

  // Toggles
  const root = document.documentElement;
  const applyToggles = () => {
    root.classList.toggle('hide-pb', !el.togglePb.checked);
    root.classList.toggle('no-cols', !el.toggleCols.checked);
    root.classList.toggle('wide', !!el.toggleWide.checked);
    root.classList.toggle('notes-inline', !!(el.toggleInline && el.toggleInline.checked));
    // TOC display is independent of wide
    // Keep as-is; controlled by .toc-open class below
  };
  [el.togglePb, el.toggleCols, el.toggleWide, el.toggleInline].forEach(input => input && input.addEventListener('change', () => {
    // Re-render if page breaks toggle changed so we can (un)stitch paragraphs
    if (input === el.togglePb) {
      renderContent();
      return;
    }
    applyToggles();
    // If enabling inline notes, close side panel and remove any existing inline notes
    if (input === el.toggleInline && el.toggleInline.checked) {
      closeNote();
      removeAllInlineNotes();
    }
  }));
  applyToggles();
  // TOC toggle button
  el.toggleToc && el.toggleToc.addEventListener('click', () => {
    root.classList.toggle('toc-open');
    // Ensure TOC exists and is built
    if (el.toc && !el.toc.children.length) buildTOC();
  });

  // Autoload via ?src=… or default
  const srcParam = qs.get('src');
  if (srcParam) {
    el.src.value = srcParam;
    loadFromURL(srcParam);
  } else if (window.DEFAULT_SRC) {
    el.src.value = window.DEFAULT_SRC;
    loadFromURL(window.DEFAULT_SRC);
  }

  // ----- TOC -----
  function slugify(text) {
    return text.toLowerCase().trim().replace(/[^a-z0-9\u00c0-\u024f\s-]/g, '').replace(/\s+/g, '-');
  }
  function ensureId(h) {
    if (!h.id) {
      let base = slugify(h.textContent || 'section');
      if (!base) base = 'section';
      let candidate = base, i = 2;
      while (document.getElementById(candidate)) candidate = `${base}-${i++}`;
      h.id = candidate;
    }
    return h.id;
  }
  function buildTOC() {
    const toc = document.getElementById('toc');
    if (!toc) return;
    toc.innerHTML = '';
    const hs = el.content.querySelectorAll('h1, h2, h3');
    if (!hs.length) { toc.style.display = 'none'; return; }
    const frag = document.createDocumentFragment();
    hs.forEach(h => {
      const id = ensureId(h);
      const a = document.createElement('a');
      a.href = `#${id}`;
      a.textContent = h.textContent.trim().replace(/\s+/g, ' ');
      const lvl = h.tagName === 'H1' ? 1 : h.tagName === 'H2' ? 2 : 3;
      a.className = `lvl-${lvl}`;
      frag.appendChild(a);
    });
    toc.appendChild(frag);
    toc.style.display = document.documentElement.classList.contains('toc-open') ? 'block' : 'none';

    // Active section observer
    const links = Array.from(toc.querySelectorAll('a'));
    const map = new Map(links.map(a => [a.getAttribute('href').slice(1), a]));
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          const id = e.target.id;
          links.forEach(l => l.classList.remove('active'));
          const link = map.get(id); if (link) link.classList.add('active');
          if (el.currentSection) {
            const text = e.target.textContent.trim().replace(/\s+/g, ' ');
            el.currentSection.textContent = text;
          }
        }
      });
    }, { rootMargin: '0px 0px -70% 0px', threshold: 0.01 });
    hs.forEach(h => io.observe(h));
    // Initialize current section label
    if (hs[0] && el.currentSection) el.currentSection.textContent = hs[0].textContent.trim().replace(/\s+/g, ' ');

    // Section navigation object
    const arr = Array.from(hs);
    sectionNav = {
      next() {
        const idx = currentIdx();
        const n = Math.min(arr.length - 1, idx + 1);
        arr[n] && arr[n].scrollIntoView({ behavior: 'smooth', block: 'start' });
      },
      prev() {
        const idx = currentIdx();
        const p = Math.max(0, idx - 1);
        arr[p] && arr[p].scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    };
    function currentIdx() {
      // find the first active or the top-most intersecting
      const active = toc.querySelector('a.active');
      if (active) {
        const id = active.getAttribute('href').slice(1);
        const h = document.getElementById(id);
        const i = arr.indexOf(h);
        if (i >= 0) return i;
      }
      // fallback: nearest heading above viewport
      const top = window.scrollY + 10;
      let best = 0;
      for (let i = 0; i < arr.length; i++) {
        const r = arr[i].getBoundingClientRect();
        const y = r.top + window.scrollY;
        if (y <= top) best = i; else break;
      }
      return best;
    }
  }

  // ----- Page HUD -----
  function setupPagesHUD() {
    const pbList = Array.from(el.content.querySelectorAll('.pb'));
    const total = pbList.length || 0;
    const totalEl = document.getElementById('pageTotal');
    const inputEl = document.getElementById('pageInput');
    const prevBtn = document.getElementById('prevPage');
    const nextBtn = document.getElementById('nextPage');
    if (totalEl) totalEl.textContent = String(total);
    if (!pbList.length) {
      if (inputEl) inputEl.value = '1';
      pageNav = null;
      return null;
    }

    // Map label->index and index->label
    const labels = pbList.map(pb => {
      const d = pb.getAttribute('data-n') || '';
      const m = d.match(/(\d+)$/);
      return m ? m[1] : '';
    });

    function scrollToIndex(idx) {
      const clamped = Math.max(0, Math.min(total - 1, idx));
      const target = pbList[clamped];
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function setCurrent(idx) {
      if (!inputEl) return;
      const label = labels[idx] || String(idx + 1);
      inputEl.value = label;
    }

    prevBtn && prevBtn.addEventListener('click', () => pageNav && pageNav.prev());
    nextBtn && nextBtn.addEventListener('click', () => pageNav && pageNav.next());
    inputEl && inputEl.addEventListener('change', () => {
      const val = inputEl.value.trim();
      // try label match first
      let idx = labels.indexOf(val);
      if (idx === -1) {
        const n = parseInt(val, 10);
        if (!Number.isNaN(n)) idx = (n - 1);
      }
      if (idx >= 0) scrollToIndex(idx);
    });

    // Track current page with IO
    let current = 0;
    const currentIndex = () => current;
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          const idx = pbList.indexOf(e.target);
          if (idx >= 0) { current = idx; setCurrent(idx); }
        }
      });
    }, { rootMargin: '-20% 0px -70% 0px', threshold: 0.01 });
    pbList.forEach(pb => io.observe(pb));
    setCurrent(0);

    pageNav = {
      prev() { const cur = currentIndex(); scrollToIndex(cur - 1); },
      next() { const cur = currentIndex(); scrollToIndex(cur + 1); },
      current: currentIndex,
      total: () => total,
    };
    return pageNav;
  }

  // ----- Footnotes panel -----
  function setupFootnotes() {
    footnoteRefs = {};
    lastRefEl = null;
    // Index refs
    const anchors = el.content.querySelectorAll('a.fn-ref, a[href^="#fn"], a[href^="#note"], a[href*="#fn"]');
    let counterMap = {};
    anchors.forEach(a => {
      const href = a.getAttribute('href') || '';
      if (!href.startsWith('#')) return;
      const fid = href.slice(1);
      if (!fid) return;
      (footnoteRefs[fid] || (footnoteRefs[fid] = [])).push(a);
      // Assign a stable id to the ref to enable return
      const idx = (counterMap[fid] = (counterMap[fid] || 0) + 1);
      const rid = `ref-${fid}-${idx}`;
      if (!a.id) a.id = rid;
    });
    // Add ↩ backlinks directly into the consolidated footnote list
    addBacklinksInFootnotes(el.content, footnoteRefs);

    // Delegate clicks to open panel
    el.content.addEventListener('click', (e) => {
      // Click on in-text footnote reference
      const a = e.target.closest('a');
      if (a) {
        const href = a.getAttribute('href') || '';
        if (href.startsWith('#')) {
          const fid = href.slice(1);
          const noteEl = el.content.querySelector(`section.footnotes ol li#${CSS.escape(fid)}`);
          if (noteEl) {
            e.preventDefault();
            if (root.classList.contains('notes-inline')) {
              // Inline mode: toggle inline note near the anchor
              toggleInlineNote(a, fid, noteEl.innerHTML);
            } else {
              lastRefEl = a;
              openNote(fid, noteEl.innerHTML);
            }
            return;
          }
        }
      }
      // Click directly on a footnote list item
      const li = e.target.closest('section.footnotes ol li[id]');
      if (li) {
        e.preventDefault();
        const fid = li.getAttribute('id');
        if (root.classList.contains('notes-inline')) {
          // Use first ref as insertion point if available
          const ref = (footnoteRefs[fid] && footnoteRefs[fid][0]) || null;
          if (ref) toggleInlineNote(ref, fid, li.innerHTML);
        } else {
          lastRefEl = (footnoteRefs[fid] && footnoteRefs[fid][0]) || null;
          openNote(fid, li.innerHTML);
        }
      }
    });

    el.closeNotes && el.closeNotes.addEventListener('click', closeNote);
    el.backToRef && el.backToRef.addEventListener('click', () => {
      if (!lastRefEl) return closeNote();
      closeNote();
      flashAndScroll(lastRefEl);
    });
  }

  function openNote(fid, innerHTML) {
    if (!el.notesPanel || !el.noteBody) return;
    el.noteBody.innerHTML = innerHTML;
    document.documentElement.classList.add('notes-open');
  }
  function closeNote() {
    document.documentElement.classList.remove('notes-open');
  }

  function removeAllInlineNotes() {
    el.content.querySelectorAll('.inline-note').forEach(n => n.remove());
  }

  function toggleInlineNote(anchor, fid, innerHTML) {
    // Remove existing note for this anchor if present
    const existing = anchor.nextElementSibling;
    if (existing && existing.classList.contains('inline-note')) {
      existing.remove();
      return;
    }
    // Remove other inline notes to avoid clutter
    removeAllInlineNotes();
    // Build
    const wrap = document.createElement('span');
    wrap.className = 'inline-note';
    wrap.setAttribute('data-fid', fid);
    // Close button
    const close = document.createElement('button');
    close.className = 'close';
    close.type = 'button';
    close.textContent = '×';
    close.addEventListener('click', () => wrap.remove());
    // Insert content
    wrap.innerHTML = innerHTML;
    wrap.appendChild(close);
    anchor.insertAdjacentElement('afterend', wrap);
    // Scroll to keep anchor + note in view
    anchor.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  function flashAndScroll(elm) {
    elm.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const old = elm.style.backgroundColor;
    elm.style.backgroundColor = 'rgba(140,198,101,.25)';
    setTimeout(() => { elm.style.backgroundColor = old || ''; }, 800);
  }

  // ----- Keyboard shortcuts -----
  function isEditable(target) {
    if (!target) return false;
    const t = target.tagName;
    return t === 'INPUT' || t === 'TEXTAREA' || target.isContentEditable;
  }

  function ensureHelpOverlay() {
    let ov = document.getElementById('helpOverlay');
    if (ov) return ov;
    ov = document.createElement('div');
    ov.id = 'helpOverlay';
    ov.innerHTML = `
      <div class="panel">
        <h2>Keyboard shortcuts</h2>
        <ul>
          <li><kbd>←</kbd> previous page, <kbd>→</kbd> next page</li>
          <li><kbd>↑</kbd> previous section, <kbd>↓</kbd> next section</li>
          <li><kbd>t</kbd> toggle TOC, <kbd>w</kbd> wide layout</li>
          <li><kbd>c</kbd> toggle columns, <kbd>b</kbd> toggle page breaks</li>
          <li><kbd>g</kbd> top, <kbd>Shift+G</kbd> bottom</li>
          <li><kbd>?</kbd> show/hide this help</li>
        </ul>
      </div>`;
    ov.addEventListener('click', (e) => { if (e.target === ov) ov.style.display = 'none'; });
    document.body.appendChild(ov);
    return ov;
  }

  function toggleHelp() {
    const ov = ensureHelpOverlay();
    ov.style.display = (ov.style.display === 'flex') ? 'none' : 'flex';
    if (ov.style.display === '') ov.style.display = 'flex';
  }

  document.addEventListener('keydown', (e) => {
    // Ignore when typing into inputs/textareas
    if (isEditable(e.target)) return;

    switch (e.key) {
      case 'ArrowLeft':
        if (pageNav) { e.preventDefault(); pageNav.prev(); }
        break;
      case 'ArrowRight':
        if (pageNav) { e.preventDefault(); pageNav.next(); }
        break;
      case 'ArrowUp':
        if (sectionNav) { e.preventDefault(); sectionNav.prev(); }
        break;
      case 'ArrowDown':
        if (sectionNav) { e.preventDefault(); sectionNav.next(); }
        break;
      case 't':
        e.preventDefault();
        el.toggleToc && el.toggleToc.click();
        break;
      case 'w':
        e.preventDefault();
        el.toggleWide && (el.toggleWide.checked = !el.toggleWide.checked, applyToggles());
        break;
      case 'c':
        e.preventDefault();
        el.toggleCols && (el.toggleCols.checked = !el.toggleCols.checked, applyToggles());
        break;
      case 'b':
        e.preventDefault();
        el.togglePb && (el.togglePb.checked = !el.togglePb.checked, applyToggles());
        break;
      case 'g':
        e.preventDefault();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        break;
      case 'G':
        e.preventDefault();
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        break;
      case '?':
        e.preventDefault();
        toggleHelp();
        break;
      case 'Escape':
        // Close overlays/panels
        if (document.documentElement.classList.contains('notes-open')) { e.preventDefault(); closeNote(); }
        // Also close any inline note
        if (el.content.querySelector('.inline-note')) { e.preventDefault(); removeAllInlineNotes(); }
        break;
      default:
        break;
    }
  });
})();
