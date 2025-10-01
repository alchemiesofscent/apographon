<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0"
  xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:xml="http://www.w3.org/XML/1998/namespace"
  exclude-result-prefixes="tei">

  <xsl:output method="html" version="5.0" encoding="UTF-8" omit-xml-declaration="yes"/>

  <xsl:template match="/tei:TEI">
    <html lang="de">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title>
          <xsl:variable name="title" select="normalize-space(.//tei:teiHeader//tei:title[1])"/>
          <xsl:choose>
            <xsl:when test="$title != ''"><xsl:value-of select="$title"/></xsl:when>
            <xsl:otherwise>TEI Viewer</xsl:otherwise>
          </xsl:choose>
        </title>
        <link rel="stylesheet" href="viewer/viewer.css"/>
      </head>
      <body>
        <header class="toolbar">
          <div class="controls"></div>
          <div class="toggles">
            <label><input type="checkbox" id="togglePb" checked="checked"/> Page breaks</label>
            <label><input type="checkbox" id="toggleCols" checked="checked"/> Columns</label>
            <label><input type="checkbox" id="toggleWide"/> Wide layout</label>
            <label><input type="checkbox" id="toggleInlineNotes"/> Inline notes</label>
            <button id="toggleToc" type="button" title="Toggle TOC">TOC</button>
            <span id="currentSection" class="current-section" title="Current section"></span>
            <span class="page-hud">
              Page
              <button id="prevPage" title="Previous page" aria-label="Previous page">◀</button>
              <input id="pageInput" type="text" inputmode="numeric" pattern="[0-9]*" value="1" size="4"/>
              / <span id="pageTotal">0</span>
              <button id="nextPage" title="Next page" aria-label="Next page">▶</button>
            </span>
          </div>
        </header>
        <nav id="toc" class="toc" aria-label="Table of contents"></nav>
        <main id="viewer"><article class="work"><main id="content" class="content">
          <xsl:apply-templates select="tei:text/tei:body"/>
          <xsl:apply-templates select="tei:text/tei:back"/>
        </main></article></main>
        <aside id="notes" class="notes-panel" aria-label="Footnotes">
          <div class="hdr"><strong>Footnote</strong><button id="closeNotes" title="Close">×</button></div>
          <div id="noteBody" class="note-body"></div>
          <div class="note-actions"><button id="backToRef" title="Return to text">Back to text</button></div>
        </aside>
        <footer class="status" id="status">TEI rendered via XSL.</footer>
        <script src="viewer/viewer.js"></script>
      </body>
    </html>
  </xsl:template>

  <!-- Body mapping -->
  <xsl:template match="tei:body">
    <xsl:apply-templates/>
  </xsl:template>

  <!-- Div/head -> headings + flow -->
  <xsl:template match="tei:div">
    <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="tei:head">
    <h2><xsl:value-of select="normalize-space(.)"/></h2>
  </xsl:template>

  <xsl:template match="tei:p">
    <p><xsl:apply-templates/></p>
  </xsl:template>

  <!-- Page break -->
  <xsl:template match="tei:pb">
    <span class="pb" role="doc-pagebreak">
      <xsl:attribute name="data-n">
        <xsl:choose>
          <xsl:when test="@xml:id"><xsl:value-of select="@xml:id"/></xsl:when>
          <xsl:when test="@n"><xsl:text>page-</xsl:text><xsl:value-of select="@n"/></xsl:when>
          <xsl:otherwise>page</xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
    </span>
  </xsl:template>

  <!-- Footnote references in text -->
  <xsl:template match="tei:ref[@target]">
    <a class="fn-ref">
      <xsl:attribute name="href"><xsl:value-of select="@target"/></xsl:attribute>
      <xsl:apply-templates/>
    </a>
  </xsl:template>

  <!-- Back matter footnotes -->
  <xsl:template match="tei:back">
    <xsl:variable name="notes" select=".//tei:div[@type='notes']/tei:note"/>
    <xsl:if test="count($notes) &gt; 0">
      <section class="footnotes"><ol>
        <xsl:for-each select="$notes">
          <li>
            <xsl:if test="@xml:id">
              <xsl:attribute name="id"><xsl:value-of select="@xml:id"/></xsl:attribute>
            </xsl:if>
            <xsl:value-of select="normalize-space(.)"/>
          </li>
        </xsl:for-each>
      </ol></section>
    </xsl:if>
  </xsl:template>

  <!-- Default: drop unmapped TEI elements but render text -->
  <xsl:template match="text()">
    <xsl:value-of select="."/>
  </xsl:template>
  <xsl:template match="@*|node()" priority="-1">
    <xsl:apply-templates/>
  </xsl:template>

</xsl:stylesheet>

