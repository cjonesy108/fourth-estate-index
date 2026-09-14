const API_CANDIDATES = [
  "https://fourth-estate-index.vercel.app/ext/lookup",
  "http://localhost:3000/ext/lookup",
];

function scoreLabel(value) {
  if (value === null || value === undefined) return "\u2014";
  const n = value <= 1 ? Math.round(value * 100) : Math.round(value);
  return String(n);
}

function grade(value) {
  if (value === null || value === undefined) return null;
  const n = value <= 1 ? Math.round(value * 100) : Math.round(value);
  if (n >= 90) return "A";
  if (n >= 80) return "B";
  if (n >= 70) return "C";
  if (n >= 60) return "D";
  return "F";
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function pillarRow(label, value) {
  const n = value === null || value === undefined ? null : value <= 1 ? Math.round(value * 100) : Math.round(value);
  const width = n === null ? 0 : n;
  const shown = n === null ? "pending" : String(n);
  return `<div class="fei-pillar"><div class="fei-pillar-meta"><span>${escapeHtml(label)}</span><span>${shown}</span></div><div class="fei-bar"><div class="fei-bar-fill" style="width:${width}%"></div></div></div>`;
}

function render(page, data) {
  let root = document.getElementById("fei-root");
  if (!root) {
    root = document.createElement("aside");
    root.id = "fei-root";
    document.documentElement.appendChild(root);
  }
  const article = data.article || {};
  const journalists = data.journalists || [];
  const first = journalists[0];
  const articleScore = article.composite_score;
  const journalistScore = first ? first.composite_score : null;
  const g = grade(articleScore ?? journalistScore);
  root.innerHTML = `
    <button type="button" class="fei-chip" id="fei-chip" aria-expanded="false">
      <span class="fei-chip-kicker">FEI</span>
      <span class="fei-chip-score">${g || scoreLabel(journalistScore)}</span>
    </button>
    <div class="fei-panel" id="fei-panel" hidden>
      <header class="fei-head">
        <p class="fei-kicker">Fourth Estate Index</p>
        <p class="fei-outlet">${escapeHtml((data.outlet && data.outlet.name) || page.host || "")}</p>
      </header>
      <section class="fei-block">
        <p class="fei-label">This article</p>
        <p class="fei-title">${escapeHtml(page.title || article.headline || "Untitled")}</p>
        <p class="fei-big">${scoreLabel(articleScore)}</p>
        <p class="fei-note">${escapeHtml(article.note || "No published article score yet.")}</p>
      </section>
      <section class="fei-block">
        <p class="fei-label">Journalist</p>
        ${
          first
            ? `<p class="fei-name">${escapeHtml(first.full_name)}</p>
               <p class="fei-beat">${escapeHtml([first.outlet_name, first.beat].filter(Boolean).join(" \u00b7 "))}</p>
               <p class="fei-big">${scoreLabel(journalistScore)}</p>
               ${pillarRow("Seek Truth", first.pillar_1_score)}
               ${pillarRow("Minimize Harm", first.pillar_2_score)}
               ${pillarRow("Act Independently", first.pillar_3_score)}
               ${pillarRow("Be Accountable", first.pillar_4_score)}
               <a class="fei-link" href="${escapeHtml(first.profile_url)}" target="_blank" rel="noopener">Open profile</a>`
            : `<p class="fei-note">${escapeHtml(page.authors.length ? page.authors.join(", ") + " is not in the directory yet." : "No byline detected on this page.")}</p>`
        }
      </section>
    </div>`;
  const chip = root.querySelector("#fei-chip");
  const panel = root.querySelector("#fei-panel");
  chip.addEventListener("click", () => {
    const open = panel.hasAttribute("hidden");
    if (open) panel.removeAttribute("hidden");
    else panel.setAttribute("hidden", "");
    chip.setAttribute("aria-expanded", open ? "true" : "false");
  });
}

async function fetchLookup(page) {
  const params = new URLSearchParams();
  if (page.canonical || page.url) params.set("url", page.canonical || page.url);
  if (page.title) params.set("title", page.title);
  if (page.host) params.set("host", page.host);
  if (page.authors.length) params.set("authors", page.authors.join(", "));
  let lastError = null;
  for (const base of API_CANDIDATES) {
    try {
      const res = await fetch(`${base}?${params.toString()}`);
      if (!res.ok) throw new Error(String(res.status));
      return await res.json();
    } catch (err) {
      lastError = err;
    }
  }
  return {
    outlet: null,
    journalists: [],
    article: { found: false, composite_score: null, note: "Lookup API unreachable. Load this branch on Vercel, then reload the article." },
    notes: [String(lastError || "lookup failed")],
  };
}

async function run() {
  if (!globalThis.FEIExtract) return;
  const page = globalThis.FEIExtract.extract();
  const looksLikeArticle =
    Boolean(document.querySelector('script[type="application/ld+json"]')) ||
    Boolean(document.querySelector('meta[property="og:type"][content*="article"]')) ||
    Boolean(document.querySelector("article")) ||
    /\/\d{4}\/\d{2}\//.test(location.pathname) ||
    /nx-s1-/.test(location.pathname);
  if (!looksLikeArticle && page.authors.length === 0) return;
  const data = await fetchLookup(page);
  render(page, data);
  chrome.runtime.sendMessage({ type: "FEI_RESULT", page, data });
}

run();
