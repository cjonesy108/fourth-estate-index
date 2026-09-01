function pct(value) {
  if (value === null || value === undefined) return "—";
  return String(value <= 1 ? Math.round(value * 100) : Math.round(value));
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function render(entry) {
  const app = document.getElementById("app");
  if (!entry?.data) {
    app.innerHTML = `<p class="kicker">Fourth Estate Index</p><p class="muted">Open a news article, then click the extension again.</p>`;
    return;
  }
  const { page, data } = entry;
  const article = data.article || {};
  const j = (data.journalists || [])[0];
  app.innerHTML = `
    <p class="kicker">Fourth Estate Index</p>
    <p class="muted">${escapeHtml((data.outlet && data.outlet.name) || page.host || "")}</p>
    <div class="block">
      <p class="label">This article</p>
      <h1>${escapeHtml(page.title || "Untitled")}</h1>
      <p class="big">${pct(article.composite_score)}</p>
      <p class="note">${escapeHtml(article.note || "")}</p>
    </div>
    <div class="block">
      <p class="label">Journalist</p>
      ${
        j
          ? `<h1>${escapeHtml(j.full_name)}</h1>
             <p class="big">${pct(j.composite_score)}</p>
             <p class="note">${escapeHtml([j.outlet_name, j.beat].filter(Boolean).join(" · "))}</p>
             <p><a href="${escapeHtml(j.profile_url)}" target="_blank" rel="noopener">Open profile</a></p>`
          : `<p class="note">${escapeHtml(
              page.authors?.length ? page.authors.join(", ") + " is not listed yet." : "No byline found."
            )}</p>`
      }
    </div>
  `;
}

chrome.storage.session.get("last").then((store) => render(store.last));
