function pct(value) {
  if (value === null || value === undefined) return null;
  return value <= 1 ? Math.round(value * 100) : Math.round(value);
}

chrome.runtime.onMessage.addListener((message, sender) => {
  if (message?.type !== "FEI_RESULT") return;
  const tabId = sender.tab?.id;
  if (!tabId) return;

  chrome.storage.session.set({
    last: {
      tabId,
      page: message.page,
      data: message.data,
    },
  });

  const article = message.data?.article;
  const journalist = message.data?.journalists?.[0];
  const score = pct(article?.composite_score) ?? pct(journalist?.composite_score);
  chrome.action.setBadgeBackgroundColor({ tabId, color: "#142c47" });
  chrome.action.setBadgeText({ tabId, text: score === null ? "·" : String(score) });
  const name = journalist?.full_name || message.page?.authors?.[0] || "this page";
  chrome.action.setTitle({
    tabId,
    title: score === null ? `Fourth Estate Index · ${name} pending` : `FEI ${score} · ${name}`,
  });
});
