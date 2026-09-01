(function (root) {
  const SKIP_AUTHORS = new Set([
    "staff", "npr staff", "associated press", "reuters", "editor", "editors", "opinion", "the associated press",
  ]);

  function text(el) {
    return (el && el.textContent ? el.textContent : "").replace(/\s+/g, " ").trim();
  }

  function unique(list) {
    const seen = new Set();
    const out = [];
    for (const item of list) {
      const key = item.toLowerCase();
      if (!item || seen.has(key) || SKIP_AUTHORS.has(key)) continue;
      seen.add(key);
      out.push(item);
    }
    return out;
  }

  function jsonLdArticles() {
    const blocks = [...document.querySelectorAll('script[type="application/ld+json"]')];
    const found = [];
    for (const block of blocks) {
      let data;
      try { data = JSON.parse(block.textContent); } catch { continue; }
      const queue = Array.isArray(data) ? data : [data];
      while (queue.length) {
        const node = queue.shift();
        if (!node || typeof node !== "object") continue;
        if (Array.isArray(node["@graph"])) queue.push(...node["@graph"]);
        const types = [].concat(node["@type"] || []);
        if (types.some((t) => /NewsArticle|Article|ReportageNewsArticle|AudioObject/i.test(String(t)))) {
          found.push(node);
        }
      }
    }
    return found;
  }

  function authorsFromLd(node) {
    const authors = [];
    const raw = node.author;
    const list = Array.isArray(raw) ? raw : raw ? [raw] : [];
    for (const a of list) {
      if (!a) continue;
      if (typeof a === "string") authors.push(a);
      else if (a.name) authors.push(a.name);
    }
    return authors;
  }

  function meta(selector, attr) {
    const el = document.querySelector(selector);
    return el ? el.getAttribute(attr) : null;
  }

  function bylineSelectors() {
    const sels = [
      '[rel="author"]', '[itemprop="author"]', ".byline", ".byline__name", ".author",
      ".author-name", '[data-testid="byline"]', '[data-testid="byline-name"]',
      ".npr-byline", "p.byline", ".ArticlePage-byline", ".c-byline__author",
    ];
    const names = [];
    for (const sel of sels) {
      document.querySelectorAll(sel).forEach((el) => {
        const value = el.getAttribute("content") || text(el);
        value.split(/,|;|\band\b/i).forEach((part) => names.push(part.trim()));
      });
    }
    return names;
  }

  function nprTranscriptByline() {
    const body = text(document.body);
    const m = body.match(/([A-Z][A-Z'\u2019\-]+(?:\s+[A-Z][A-Z'\u2019\-]+)+),\s*BYLINE/i);
    if (!m) return null;
    return m[1].toLowerCase().split(" ").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
  }

  function extract() {
    const ld = jsonLdArticles();
    const primary = ld[0] || {};
    const title = primary.headline || meta('meta[property="og:title"]', "content") || document.querySelector("h1")?.textContent?.trim() || document.title;
    const canonical = document.querySelector('link[rel="canonical"]')?.href || meta('meta[property="og:url"]', "content") || location.href;
    let authors = [];
    ld.forEach((node) => authors.push(...authorsFromLd(node)));
    const metaAuthor = meta('meta[name="author"]', "content") || meta('meta[property="article:author"]', "content");
    if (metaAuthor) authors.push(...metaAuthor.split(/,|;|\band\b/i));
    authors.push(...bylineSelectors());
    const transcript = nprTranscriptByline();
    if (transcript) authors.push(transcript);
    authors = unique(authors.map((a) => a.replace(/^by\s+/i, "").replace(/\s+/g, " ").trim()).filter((a) => a.length > 2 && a.length < 80 && !/https?:/.test(a)));
    return { url: location.href, canonical, host: location.hostname, title, authors, published: primary.datePublished || meta('meta[property="article:published_time"]', "content") || null };
  }

  root.FEIExtract = { extract };
})(globalThis);
