export interface WorkItem {
  title: string;
  url: string;
  published_at: string | null;
}

const UA = "FourthEstateIndex/0.3 (+https://fourth-estate-index.vercel.app)";

function decode(html: string): string {
  return html
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)))
    .trim();
}

function stripTags(html: string): string {
  return decode(html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim());
}

async function getText(url: string): Promise<string | null> {
  try {
    const res = await fetch(url, {
      headers: { "User-Agent": UA, Accept: "application/rss+xml, text/xml, text/html" },
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  }
}

function parseRss(xml: string, limit: number): WorkItem[] {
  const items: WorkItem[] = [];
  const blocks = xml.split(/<item[\s>]/i).slice(1);
  for (const block of blocks) {
    const title = stripTags((block.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1] || "");
    const link = stripTags((block.match(/<link[^>]*>([\s\S]*?)<\/link>/i) || [])[1] || "");
    const date =
      stripTags((block.match(/<pubDate[^>]*>([\s\S]*?)<\/pubDate>/i) || [])[1] || "") ||
      stripTags((block.match(/<dc:date[^>]*>([\s\S]*?)<\/dc:date>/i) || [])[1] || "") ||
      null;
    if (!title || !link) continue;
    const published = date ? new Date(date) : null;
    items.push({
      title,
      url: link,
      published_at: published && !Number.isNaN(published.getTime()) ? published.toISOString() : null,
    });
    if (items.length >= limit) break;
  }
  return items;
}

function eachMatch(re: RegExp, html: string, fn: (m: RegExpExecArray) => boolean) {
  re.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = re.exec(html)) !== null) {
    if (!fn(match)) break;
    if (!re.global) break;
  }
}

function parseProPublicaPeople(html: string, limit: number): WorkItem[] {
  const items: WorkItem[] = [];
  const seen = new Set<string>();
  const dated =
    /<time[^>]*datetime="([^"]+)"[\s\S]{0,500}?href="(https:\/\/www\.propublica\.org\/article\/[^"]+)"[^>]*>([\s\S]*?)<\/a>/gi;
  eachMatch(dated, html, (match) => {
    const url = match[2].split("?")[0];
    if (seen.has(url)) return true;
    const title = stripTags(match[3]);
    if (!title) return true;
    seen.add(url);
    const published = new Date(match[1]);
    items.push({
      title,
      url,
      published_at: Number.isNaN(published.getTime()) ? null : published.toISOString(),
    });
    return items.length < limit;
  });
  if (items.length) return items;

  const fallback = /href="(https:\/\/www\.propublica\.org\/article\/[^"?]+)"[^>]*>([\s\S]*?)<\/a>/gi;
  eachMatch(fallback, html, (match) => {
    const url = match[1];
    if (seen.has(url)) return true;
    const title = stripTags(match[2]);
    if (!title || title.length < 12) return true;
    seen.add(url);
    items.push({ title, url, published_at: null });
    return items.length < limit;
  });
  return items;
}

export function feedUrlFor(j: {
  feed_url?: string | null;
  guardian_tag?: string | null;
}): string | null {
  if (j.feed_url) return j.feed_url;
  if (j.guardian_tag) return `https://www.theguardian.com/${j.guardian_tag}/rss`;
  return null;
}

export async function fetchRecentWork(
  j: {
    feed_url?: string | null;
    guardian_tag?: string | null;
    author_url?: string | null;
  },
  limit = 8
): Promise<WorkItem[]> {
  const feed = feedUrlFor(j);
  if (feed) {
    const xml = await getText(feed);
    if (xml && xml.includes("<item")) return parseRss(xml, limit);
  }
  if (j.author_url?.includes("propublica.org/people/")) {
    const html = await getText(j.author_url);
    if (html) return parseProPublicaPeople(html, limit);
  }
  return [];
}

export function formatWorkDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
