class MultilingualReader {
  constructor({ containerId, tocListId, dataUrl, pageOffset = 0 }) {
    this.container = document.getElementById(containerId);
    this.tocList = document.getElementById(tocListId);
    this.dataUrl = dataUrl;
    this.pageOffset = typeof pageOffset === 'number' ? pageOffset : 0;

    this.settingsKey = 'apographon:reader:settings';
    this.scrollKey = 'apographon:reader:scroll';
    this.notes = new Map();
    this.paragraphStates = new Map();
    this.paragraphElements = [];

    this.searchInput = document.getElementById('search-input');
    this.searchSummary = document.getElementById('search-summary');
    this.toggleTranslationsBtn = document.getElementById('toggle-translations');
    this.toggleGreekBtn = document.getElementById('toggle-greek');
    this.toggleLayoutBtn = document.getElementById('toggle-layout');
    this.fontSlider = document.getElementById('font-size');
    this.fontValue = document.getElementById('font-size-value');
    this.greekFontSelect = document.getElementById('greek-font');
    this.settingsSummary = document.getElementById('settings-summary');
    this.liveRegion = document.getElementById('live-region');

    this.tooltip = this.createTooltip();
    this.sheet = document.getElementById('footnote-sheet');
    this.sheetBackdrop = document.getElementById('sheet-backdrop');
    this.sheetOriginal = document.getElementById('sheet-original');
    this.sheetTranslation = document.getElementById('sheet-translation');
    this.sheetClose = document.getElementById('sheet-close');

    this.allowedGreekFonts = new Set(['Literata', 'Arial']);

    this.settings = {
      showTranslations: true,
      showGreekTranslations: false,
      layout: 'parallel',
      fontSize: 16,
      greekFont: 'Literata'
    };

    this.restoreSettings();
    this.applySettings();
    this.bindControlEvents();
    this.registerScrollPersistence();
  }

  async loadData(url) {
    const response = await fetch(url, { cache: 'no-cache' });
    if (!response.ok) {
      throw new Error(`Failed to load data from ${url}`);
    }
    this.data = await response.json();
    this.render();
    this.buildTOC();
    this.setupFootnoteTooltips();
    this.observeActiveParagraph();
    this.restoreScroll();
  }

  render() {
    if (!this.data || !this.container) {
      return;
    }

    this.container.innerHTML = '';
    this.paragraphElements = [];
    this.notes.clear();
    this.paragraphStates.clear();

    const { paragraphs } = this.data.document;
    paragraphs.forEach((para, index) => {
      const article = document.createElement('article');
      article.className = 'para';
      article.id = para.id;
      article.dataset.originalLang = para.original.lang;
      article.dataset.index = String(index + 1);

      const header = document.createElement('div');
      header.className = 'para-header';

      const paraTitle = document.createElement('p');
      paraTitle.className = 'para-title';
      paraTitle.textContent = `${this.formatLanguageLabel(para.original.lang)} · ${this.data.document.title}`;
      header.appendChild(paraTitle);

      const pageLabel = this.createPageLabel(para.original);
      if (pageLabel) {
        header.appendChild(pageLabel);
      }

      const status = document.createElement('span');
      status.className = 'status-banner';
      status.dataset.status = para.translation.confidence;
      status.textContent = `Confidence ${this.formatConfidence(para.translation.confidence)}`;
      header.appendChild(status);

      article.appendChild(header);

      const wrapper = document.createElement('div');
      wrapper.className = 'para-container';

      const originalWrap = document.createElement('div');
      originalWrap.className = `para-text lang-${para.original.lang}`;
      originalWrap.lang = this.mapLangCode(para.original.lang);
      const originalBody = document.createElement('p');
      originalBody.appendChild(this.createFootnotedFragment(para));
      originalWrap.appendChild(originalBody);
      wrapper.appendChild(originalWrap);

      const translationWrap = document.createElement('div');
      translationWrap.className = 'para-translation';
      translationWrap.lang = 'en';

      const translationBody = document.createElement('p');
      translationBody.textContent = para.translation.text;
      translationWrap.appendChild(translationBody);

      const translationMeta = document.createElement('div');
      translationMeta.className = 'translation-meta';
      translationMeta.appendChild(this.metaItem(`Translated by ${para.translation.translator}`));
      translationMeta.appendChild(this.metaItem(`Confidence ${this.formatConfidence(para.translation.confidence)}`, `status-${para.translation.confidence}`));

      if (para.translation.vetted_by) {
        const vetted = document.createElement('span');
        vetted.className = 'vetted';
        vetted.innerHTML = `✓ Vetted by ${this.escapeHTML(para.translation.vetted_by)} <span class="tooltip" role="tooltip" tabindex="0">ⓘ</span>`;
        if (para.translation.vetting_notes) {
          vetted.querySelector('.tooltip').setAttribute('title', para.translation.vetting_notes);
        }
        translationMeta.appendChild(vetted);
      } else {
        translationMeta.appendChild(this.metaItem('Not yet vetted'));
      }

      if (para.translation.timestamp) {
        translationMeta.appendChild(
          this.metaItem(`Generated ${new Date(para.translation.timestamp).toLocaleString()}`)
        );
      }

      translationWrap.appendChild(translationMeta);

      if (!para.translation.show_by_default || para.original.lang === 'grc') {
        const toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.className = 'translation-toggle';
        toggleBtn.textContent = 'Show translation';
        toggleBtn.addEventListener('click', () => this.toggleGreekParagraphTranslation(toggleBtn));
        translationWrap.appendChild(toggleBtn);
      }

      wrapper.appendChild(translationWrap);
      article.appendChild(wrapper);

      const backLink = document.createElement('a');
      backLink.href = '#toc';
      backLink.className = 'back-to-index';
      backLink.textContent = 'Back to index';
      backLink.addEventListener('click', () => {
        document.getElementById('toc').focus();
      });
      article.appendChild(backLink);

      this.container.appendChild(article);

      const initialState = {
        visible: true,
        userOverride: false,
        textContent: [para.original.text, para.translation.text].join(' ').toLowerCase()
      };
      const visible = this.computeTranslationVisibility(para, initialState);
      initialState.visible = visible;
      this.paragraphStates.set(para.id, initialState);
      translationWrap.hidden = !visible;
      this.updateParagraphToggleButton(article, visible);

      const greekFontSetting = this.allowedGreekFonts.has(this.settings.greekFont)
        ? this.settings.greekFont
        : 'Literata';
      const greekStack = greekFontSetting === 'Arial' ? 'Arial, sans-serif' : "'Literata', Arial, sans-serif";
      if (para.original.lang === 'grc') {
        originalWrap.style.fontFamily = greekStack;
      }

      this.paragraphElements.push(article);
    });

    this.updateFontSize();
    this.updateLayout();
    this.updateSettingsSummary();
    this.applyGreekFont();
  }

  buildTOC() {
    if (!this.tocList || !this.data) {
      return;
    }

    this.tocList.innerHTML = '';
    this.data.document.paragraphs.forEach((para, index) => {
      const item = document.createElement('li');
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = `${index + 1}. ${this.summariseParagraph(para.original.text)}`;
      button.dataset.targetId = para.id;
      button.addEventListener('click', () => this.navigateToIndexedTerm(para.id));
      item.appendChild(button);
      this.tocList.appendChild(item);
    });
  }

  createTooltip() {
    const tooltip = document.createElement('div');
    tooltip.className = 'footnote-tooltip';
    tooltip.setAttribute('role', 'tooltip');
    tooltip.style.display = 'none';
    document.body.appendChild(tooltip);
    return tooltip;
  }

  setupFootnoteTooltips() {
    const refs = this.container.querySelectorAll('.footnote-ref');
    const isDesktop = () => window.matchMedia('(min-width: 768px)').matches;

    refs.forEach((ref) => {
      const noteId = ref.dataset.noteId;
      const note = this.notes.get(noteId);
      if (!note) {
        return;
      }

      const showTooltip = () => {
        if (!isDesktop()) {
          return;
        }
        this.tooltip.innerHTML = `
          <h4>Note ${this.escapeHTML(note.marker)}</h4>
          <p>${this.escapeHTML(note.text)}</p>
          ${note.translation ? `<p><strong>English:</strong> ${this.escapeHTML(note.translation)}</p>` : ''}
        `;
        this.tooltip.style.display = 'block';
        this.tooltip.style.visibility = 'hidden';
        this.positionTooltip(ref);
        this.tooltip.style.visibility = 'visible';
        this.tooltip.classList.add('visible');
      };

      const hideTooltip = () => {
        this.tooltip.classList.remove('visible');
        this.tooltip.style.display = 'none';
        this.tooltip.style.visibility = 'visible';
      };

      ref.addEventListener('mouseenter', showTooltip);
      ref.addEventListener('mouseleave', hideTooltip);
      ref.addEventListener('focus', showTooltip);
      ref.addEventListener('blur', hideTooltip);

      ref.addEventListener('click', (event) => {
        event.preventDefault();
        this.openFootnoteSheet(note);
      });
    });

    if (this.sheetClose) {
      this.sheetClose.addEventListener('click', () => this.closeFootnoteSheet());
    }
    if (this.sheetBackdrop) {
      this.sheetBackdrop.addEventListener('click', () => this.closeFootnoteSheet());
    }
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        this.closeFootnoteSheet();
      }
    });
  }

  positionTooltip(ref) {
    const rect = ref.getBoundingClientRect();
    const tooltipRect = this.tooltip.getBoundingClientRect();
    let top = rect.bottom + window.scrollY + 8;
    let left = rect.left + window.scrollX - tooltipRect.width / 2 + rect.width / 2;

    const maxLeft = window.scrollX + document.documentElement.clientWidth - tooltipRect.width - 12;
    const minLeft = window.scrollX + 12;
    if (left < minLeft) {
      left = minLeft;
    } else if (left > maxLeft) {
      left = maxLeft;
    }

    if (top + tooltipRect.height > window.scrollY + window.innerHeight) {
      top = rect.top + window.scrollY - tooltipRect.height - 12;
    }

    this.tooltip.style.top = `${top}px`;
    this.tooltip.style.left = `${left}px`;
  }

  openFootnoteSheet(note) {
    if (!this.sheet || !this.sheetBackdrop) {
      return;
    }
    if (this.sheetOriginal) {
      this.sheetOriginal.textContent = note.text;
    }
    if (this.sheetTranslation) {
      this.sheetTranslation.textContent = note.translation || 'No translation available yet.';
    }
    this.sheet.classList.add('visible');
    this.sheetBackdrop.classList.add('visible');
    this.sheetBackdrop.hidden = false;
    document.body.classList.add('lock-scroll');
    this.sheet.focus();
  }

  closeFootnoteSheet() {
    if (!this.sheet || !this.sheetBackdrop) {
      return;
    }
    this.sheet.classList.remove('visible');
    this.sheetBackdrop.classList.remove('visible');
    this.sheetBackdrop.hidden = true;
    document.body.classList.remove('lock-scroll');
  }

  toggleTranslations(show) {
    this.settings.showTranslations = show;
    this.persistSettings();
    this.applyTranslationVisibility();
    this.liveRegion.textContent = show ? 'Translations visible.' : 'Translations hidden.';
  }

  applyTranslationVisibility() {
    this.paragraphElements.forEach((article) => {
      const paraId = article.id;
      const translation = article.querySelector('.para-translation');
      if (!translation) {
        return;
      }
      const paraData = this.getParagraphById(paraId);
      const state = this.paragraphStates.get(paraId) || {};
      const visible = this.computeTranslationVisibility(paraData, state);
      translation.hidden = !visible;
      this.paragraphStates.set(paraId, {
        ...state,
        visible
      });
      this.updateParagraphToggleButton(article, visible);
    });
    this.updateTranslationToggleLabels();
  }

  toggleGreekTranslations(show) {
    this.settings.showGreekTranslations = show;
    this.persistSettings();
    this.applyTranslationVisibility();
    this.liveRegion.textContent = show ? 'Greek translations shown.' : 'Greek translations hidden.';
  }

  toggleGreekParagraphTranslation(button) {
    const article = button.closest('.para');
    if (!article) {
      return;
    }
    const translation = article.querySelector('.para-translation');
    translation.hidden = !translation.hidden;
    const paraState = this.paragraphStates.get(article.id) || {};
    const newVisible = !translation.hidden;
    this.paragraphStates.set(article.id, {
      ...paraState,
      visible: newVisible,
      userOverride: true
    });
    button.textContent = translation.hidden ? 'Show translation' : 'Hide translation';
  }

  toggleColumnView(columns) {
    this.settings.layout = columns ? 'parallel' : 'stacked';
    this.persistSettings();
    this.updateLayout();
    this.liveRegion.textContent = columns ? 'Parallel columns enabled.' : 'Stacked layout enabled.';
  }

  toggleColumnViewFromControl() {
    const isParallel = this.settings.layout === 'parallel';
    this.toggleColumnView(!isParallel);
  }

  toggleTranslationsFromControl() {
    this.toggleTranslations(!this.settings.showTranslations);
  }

  toggleGreekFromControl() {
    this.toggleGreekTranslations(!this.settings.showGreekTranslations);
  }

  updateLayout() {
    if (this.settings.layout === 'parallel') {
      this.container.classList.add('parallel');
      this.container.classList.remove('stacked');
    } else {
      this.container.classList.add('stacked');
      this.container.classList.remove('parallel');
    }
    this.toggleLayoutBtn.setAttribute('aria-pressed', this.settings.layout === 'parallel');
    this.toggleLayoutBtn.textContent = this.settings.layout === 'parallel' ? 'Parallel columns' : 'Stacked view';
  }

  updateTranslationToggleLabels() {
    const show = this.settings.showTranslations;
    this.toggleTranslationsBtn.setAttribute('aria-pressed', show);
    this.toggleTranslationsBtn.textContent = show ? 'Hide translations' : 'Show translations';

    const showGreek = this.settings.showGreekTranslations;
    this.toggleGreekBtn.setAttribute('aria-pressed', showGreek);
    this.toggleGreekBtn.textContent = showGreek ? 'Hide Greek translations' : 'Show Greek translations';
  }

  updateParagraphToggleButton(article, visible) {
    const toggle = article.querySelector('.translation-toggle');
    if (toggle) {
      toggle.textContent = visible ? 'Hide translation' : 'Show translation';
    }
  }

  bindControlEvents() {
    this.toggleTranslationsBtn.addEventListener('click', () => this.toggleTranslationsFromControl());
    this.toggleGreekBtn.addEventListener('click', () => this.toggleGreekFromControl());
    this.toggleLayoutBtn.addEventListener('click', () => this.toggleColumnViewFromControl());

    this.fontSlider.addEventListener('input', (event) => {
      const value = Number(event.target.value);
      this.fontValue.textContent = `${value}px`;
      this.settings.fontSize = value;
      this.updateFontSize();
    });

    this.fontSlider.addEventListener('change', () => {
      this.persistSettings();
      this.updateSettingsSummary();
    });

    this.greekFontSelect.addEventListener('change', (event) => {
      this.settings.greekFont = event.target.value;
      this.persistSettings();
      this.applyGreekFont();
      this.updateSettingsSummary();
      this.liveRegion.textContent = `Greek font set to ${event.target.value}`;
    });

    if (this.searchInput) {
      this.searchInput.addEventListener('input', (event) => this.filterParagraphs(event.target.value));
    }
  }

  filterParagraphs(query) {
    const value = query.trim().toLowerCase();
    let matchCount = 0;

    this.paragraphElements.forEach((article) => {
      const state = this.paragraphStates.get(article.id);
      if (!state) {
        return;
      }
      const match = !value || state.textContent.includes(value);
      article.style.display = match ? '' : 'none';
      if (match) {
        matchCount += 1;
      }
    });

    if (this.searchSummary) {
      this.searchSummary.textContent = value ? `${matchCount} passages match “${query}”.` : '';
    }
  }

  updateFontSize() {
    const size = this.settings.fontSize || 16;
    this.container.style.fontSize = `${size}px`;
    this.fontSlider.value = String(size);
    this.fontValue.textContent = `${size}px`;
    this.updateSettingsSummary();
  }

  applyGreekFont() {
    const font = this.allowedGreekFonts.has(this.settings.greekFont)
      ? this.settings.greekFont
      : 'Literata';
    const stack = font === 'Arial' ? 'Arial, sans-serif' : "'Literata', Arial, sans-serif";
    this.paragraphElements.forEach((article) => {
      if (article.dataset.originalLang === 'grc') {
        const original = article.querySelector('.para-text');
        if (original) {
          original.style.fontFamily = stack;
        }
      }
    });
  }

  updateSettingsSummary() {
    if (!this.settingsSummary) {
      return;
    }
    this.settingsSummary.textContent = `Layout: ${this.settings.layout}, Font: ${this.settings.fontSize}px, Greek font: ${this.settings.greekFont}`;
  }

  persistSettings() {
    try {
      localStorage.setItem(this.settingsKey, JSON.stringify(this.settings));
    } catch (error) {
      console.warn('Unable to persist settings', error);
    }
  }

  restoreSettings() {
    try {
      const stored = localStorage.getItem(this.settingsKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        this.settings = { ...this.settings, ...parsed };
        if (!this.allowedGreekFonts.has(this.settings.greekFont)) {
          this.settings.greekFont = 'Literata';
        }
      }
    } catch (error) {
      console.warn('Unable to restore settings', error);
    }
  }

  registerScrollPersistence() {
    window.addEventListener('beforeunload', () => this.persistScroll());
  }

  persistScroll() {
    try {
      localStorage.setItem(this.scrollKey, String(window.scrollY));
    } catch (error) {
      console.warn('Unable to persist scroll position', error);
    }
  }

  restoreScroll() {
    try {
      const stored = localStorage.getItem(this.scrollKey);
      if (stored) {
        window.scrollTo({ top: Number(stored), behavior: 'auto' });
      }
    } catch (error) {
      console.warn('Unable to restore scroll position', error);
    }
  }

  summariseParagraph(text) {
    const cleaned = text.replace(/\s+/g, ' ').trim();
    return cleaned.length > 80 ? `${cleaned.slice(0, 77)}…` : cleaned;
  }

  createFootnotedFragment(paragraph) {
    const fragment = document.createDocumentFragment();
    const { text, notes, page_breaks: pageBreaksRaw } = paragraph.original;
    const pageBreaks = Array.isArray(pageBreaksRaw)
      ? pageBreaksRaw
          .filter((item) =>
            item && typeof item.page === 'number' && typeof item.offset === 'number'
          )
          .map((item) => ({ ...item }))
          .sort((a, b) => a.offset - b.offset)
      : [];

    if (!notes || notes.length === 0) {
      this.appendTextWithPageBreaks(fragment, text, 0, text.length, pageBreaks);
      return fragment;
    }

    let searchIndex = 0;
    const sortedNotes = notes
      .map((note) => {
        const index = text.indexOf(note.marker, searchIndex);
        if (index !== -1) {
          searchIndex = index + note.marker.length;
        }
        return { ...note, index };
      })
      .filter((note) => note.index !== -1)
      .sort((a, b) => a.index - b.index);

    let lastIndex = 0;
    sortedNotes.forEach((note) => {
      if (note.index > lastIndex) {
        this.appendTextWithPageBreaks(fragment, text, lastIndex, note.index, pageBreaks);
      }
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'footnote-ref';
      button.dataset.noteId = note.id;
      button.textContent = note.marker;
      const descriptionId = `${note.id}-desc`;
      button.setAttribute('aria-describedby', descriptionId);
      const sr = document.createElement('span');
      sr.id = descriptionId;
      sr.className = 'visually-hidden';
      sr.textContent = `Footnote ${note.marker}. ${note.text}`;
      this.notes.set(note.id, {
        marker: note.marker,
        text: note.text,
        translation: note.translation || ''
      });
      fragment.appendChild(button);
      fragment.appendChild(sr);
      lastIndex = note.index + note.marker.length;
    });

    if (lastIndex < text.length) {
      this.appendTextWithPageBreaks(fragment, text, lastIndex, text.length, pageBreaks);
    }

    return fragment;
  }

  appendTextWithPageBreaks(fragment, text, start, end, pageBreaks) {
    let cursor = start;
    while (cursor < end) {
      if (pageBreaks.length && pageBreaks[0].offset >= cursor && pageBreaks[0].offset <= end) {
        const { offset, page } = pageBreaks.shift();
        if (offset > cursor) {
          fragment.appendChild(document.createTextNode(text.slice(cursor, offset)));
        }
        fragment.appendChild(this.createPageBreakMarker(this.applyPageOffset(page)));
        cursor = offset;
      } else {
        fragment.appendChild(document.createTextNode(text.slice(cursor, end)));
        cursor = end;
      }
    }
  }

  createPageBreakMarker(page) {
    const span = document.createElement('span');
    span.className = 'page-break-marker';
    span.dataset.page = String(page);
    span.setAttribute('role', 'separator');
    span.setAttribute('aria-label', `Page ${page}`);
    span.textContent = String(page);
    return span;
  }

  createPageLabel(original) {
    const pages = Array.isArray(original.pages)
      ? original.pages.filter((page) => typeof page === 'number')
      : typeof original.page === 'number'
      ? [original.page]
      : [];

    if (!pages.length) {
      return null;
    }

    const adjustedPages = pages
      .map((page) => this.applyPageOffset(page))
      .filter((page) => typeof page === 'number');

    if (!adjustedPages.length) {
      return null;
    }

    const span = document.createElement('span');
    span.className = 'page-banner';
    span.textContent = this.formatPageRange(adjustedPages);
    return span;
  }

  formatPageRange(pages) {
    if (!pages || pages.length === 0) {
      return '';
    }
    if (pages.length === 1) {
      return `Page ${pages[0]}`;
    }
    const first = pages[0];
    const last = pages[pages.length - 1];
    if (last === first) {
      return `Page ${first}`;
    }
    return `Pages ${first}–${last}`;
  }

  applyPageOffset(page) {
    if (typeof page !== 'number' || Number.isNaN(page)) {
      return page;
    }
    return page + this.pageOffset;
  }

  computeTranslationVisibility(paragraph, state = {}) {
    if (!paragraph) {
      return false;
    }
    if (!this.settings.showTranslations) {
      return false;
    }
    if (state.userOverride) {
      return Boolean(state.visible);
    }
    if (paragraph.original.lang === 'grc') {
      if (this.settings.showGreekTranslations) {
        return true;
      }
      return Boolean(paragraph.translation.show_by_default);
    }
    return paragraph.translation.show_by_default !== false;
  }

  getParagraphById(id) {
    return this.data.document.paragraphs.find((para) => para.id === id);
  }

  metaItem(text, extraClass = '') {
    const span = document.createElement('span');
    span.textContent = text;
    if (extraClass) {
      span.className = extraClass;
    }
    return span;
  }

  formatLanguageLabel(code) {
    const labels = {
      de: 'German',
      la: 'Latin',
      grc: 'Greek'
    };
    return labels[code] || code.toUpperCase();
  }

  mapLangCode(code) {
    if (code === 'grc') {
      return 'grc';
    }
    return code;
  }

  formatConfidence(value) {
    if (!value) {
      return '—';
    }
    return value.replace(/_/g, ' ');
  }

  escapeHTML(input) {
    if (typeof input !== 'string') {
      return '';
    }
    return input
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  navigateToIndexedTerm(id) {
    const element = document.getElementById(id);
    if (!element) {
      return;
    }
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    element.classList.add('highlighted');
    setTimeout(() => element.classList.remove('highlighted'), 2000);
    history.pushState(null, '', `#${id}`);
    this.liveRegion.textContent = `Navigated to ${id}`;
  }

  observeActiveParagraph() {
    if (!('IntersectionObserver' in window)) {
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          this.setActiveTOC(entry.target.id);
        }
      });
    }, {
      threshold: 0.5
    });

    this.paragraphElements.forEach((article) => observer.observe(article));
  }

  setActiveTOC(id) {
    const buttons = this.tocList.querySelectorAll('button');
    buttons.forEach((button) => {
      if (button.dataset.targetId === id) {
        button.classList.add('active-item');
      } else {
        button.classList.remove('active-item');
      }
    });
  }

  applySettings() {
    this.updateLayout();
    this.updateTranslationToggleLabels();
    this.updateFontSize();
    this.applyGreekFont();
    this.updateSettingsSummary();
  }
}
