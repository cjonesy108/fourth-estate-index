import {
  DirectoryJournalist,
  listDirectoryJournalists,
  listDirectoryOutlets,
  outletName,
} from "./directory";

export type LookupRequest = {
  url?: string | null;
  title?: string | null;
  authors?: string[] | null;
  host?: string | null;
};

export type LookupJournalist = {
  slug: string;
  full_name: string;
  aliases: string[];
  primary_outlet: string;
  outlet_name: string;
  beat: string | null;
  directory_status: string;
  author_url: string | null;
  profile_url: string;
  composite_score: number | null;
  pillar_1_score: number | null;
  pillar_2_score: number | null;
  pillar_3_score: number | null;
  pillar_4_score: number | null;
  corpus_size: number | null;
  score_source: "api" | "directory";
};

export type LookupArticle = {
  found: boolean;
  url: string | null;
  headline: string | null;
  published_at: string | null;
  in_corpus: boolean;
  composite_score: number | null;
  pillar_1_score: number | null;
  pillar_2_score: number | null;
  note: string;
};

export type LookupResponse = {
  page: { url: string | null; canonical: string | null; host: string | null; title: string | null; authors: string[] };
  outlet: { slug: string; name: string; domain: string; queued: boolean; access: string } | null;
  journalists: LookupJournalist[];
  article: LookupArticle;
  notes: string[];
};

const SITE = "https://fourth-estate-index.vercel.app";

export function normalizeHost(input: string | null | undefined): string | null {
  if (!input) return null;
  let host = input.trim().toLowerCase();
  try { if (host.includes("://")) host = new URL(host).hostname; } catch { /* keep */ }
  return host.replace(/^www\./, "") || null;
}

export function canonicalizeArticleUrl(raw: string | null | undefined): string | null {
  if (!raw) return null;
  try {
    const u = new URL(raw);
    u.hash = "";
    [...u.searchParams.keys()].forEach((k) => {
      if (k.toLowerCase().startsWith("utm_") || k.toLowerCase() === "fbclid" || k.toLowerCase() === "gclid") {
        u.searchParams.delete(k);
      }
    });
    u.hostname = u.hostname.replace(/^www\./, "");
    let href = u.toString();
    if (href.endsWith("/") && u.pathname !== "/") href = href.slice(0, -1);
    return href;
  } catch {
    return raw;
  }
}

function foldName(name: string): string {
  return name.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

export function findOutletByHost(hostOrUrl: string | null | undefined) {
  const host = normalizeHost(hostOrUrl);
  if (!host) return undefined;
  return listDirectoryOutlets().find((o) => {
    const domain = o.domain.replace(/^www\./, "").toLowerCase();
    return host === domain || host.endsWith(`.${domain}`);
  });
}

export function findJournalistsByNames(names: string[], outletSlug?: string | null): DirectoryJournalist[] {
  const folded = names.map(foldName).filter(Boolean);
  if (!folded.length) return [];
  const pool = listDirectoryJournalists().filter((j) => (outletSlug ? j.primary_outlet === outletSlug : true));
  return pool.filter((j) => {
    const aliases = [j.full_name, ...(j.aliases ?? [])].map(foldName);
    return folded.some((n) => aliases.some((a) => a === n || a.includes(n) || n.includes(a)));
  });
}

export function emptyArticle(url: string | null, title: string | null): LookupArticle {
  return {
    found: false,
    url,
    headline: title,
    published_at: null,
    in_corpus: false,
    composite_score: null,
    pillar_1_score: null,
    pillar_2_score: null,
    note: "No published article score. FEI scores a journalist across a corpus. A single URL is only scored after it is ingested and analyzed.",
  };
}

export function toLookupJournalist(j: DirectoryJournalist, scores?: Partial<LookupJournalist> | null): LookupJournalist {
  return {
    slug: j.slug,
    full_name: scores?.full_name || j.full_name,
    aliases: j.aliases ?? [],
    primary_outlet: j.primary_outlet,
    outlet_name: outletName(j.primary_outlet),
    beat: scores?.beat ?? j.beat,
    directory_status: j.directory_status,
    author_url: j.author_url ?? null,
    profile_url: `${SITE}/journalist/${j.slug}`,
    composite_score: scores?.composite_score ?? null,
    pillar_1_score: scores?.pillar_1_score ?? null,
    pillar_2_score: scores?.pillar_2_score ?? null,
    pillar_3_score: scores?.pillar_3_score ?? null,
    pillar_4_score: scores?.pillar_4_score ?? null,
    corpus_size: scores?.corpus_size ?? null,
    score_source: scores?.composite_score != null ? "api" : "directory",
  };
}

export function buildLookupNotes(opts: {
  outlet: { name: string; queued?: boolean } | undefined;
  journalists: LookupJournalist[];
  authors: string[];
  article: LookupArticle;
}): string[] {
  const notes: string[] = [];
  if (!opts.outlet) notes.push("This site is not in the Fourth Estate Index directory yet.");
  else if (opts.outlet.queued && opts.journalists.length === 0) {
    notes.push(`${opts.outlet.name} is queued. Staff are not scored until a public-text cohort is ingested.`);
  }
  if (opts.authors.length && opts.journalists.length === 0) {
    notes.push(`No directory match for ${opts.authors.join(", ")}. Listed journalists still appear before a corpus score exists.`);
  }
  for (const j of opts.journalists) {
    if (j.composite_score == null) {
      notes.push(`${j.full_name} is listed. No composite score until every pillar has enough data — pending is not a zero.`);
    }
  }
  if (!opts.article.in_corpus) notes.push(opts.article.note);
  return notes;
}

export function directoryLookup(req: LookupRequest): LookupResponse {
  const canonical = canonicalizeArticleUrl(req.url ?? null);
  const host = normalizeHost(req.host || req.url || null);
  const authors = (req.authors ?? []).map((a) => a.trim()).filter(Boolean);
  const outlet = findOutletByHost(host);
  const journalists = findJournalistsByNames(authors, outlet?.slug).map((j) => toLookupJournalist(j));
  const article = emptyArticle(canonical, req.title ?? null);
  return {
    page: { url: req.url ?? null, canonical, host, title: req.title ?? null, authors },
    outlet: outlet ? { slug: outlet.slug, name: outlet.name, domain: outlet.domain, queued: Boolean(outlet.queued), access: String(outlet.access) } : null,
    journalists,
    article,
    notes: buildLookupNotes({ outlet, journalists, authors, article }),
  };
}
