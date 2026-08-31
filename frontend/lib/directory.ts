import raw from "@/data/directory.json";
import { JournalistProfile, JournalistSummary, OutletProfile, OutletSummary } from "./types";

export type AccessKind = "full_api" | "soft_scrape" | "full_public" | "rss" | "licensed" | "queued";
export type DirectoryStatus = "listed" | "collecting" | "scored";
export type ArticleAccessLevel = "full" | "excerpt" | "metadata";

export interface DirectoryOutlet {
  slug: string;
  name: string;
  domain: string;
  api_source: string;
  access: AccessKind | string;
  text_policy: string;
  author_url_template?: string;
  corrections_url?: string;
  queued?: boolean;
}

export interface DirectoryJournalist {
  slug: string;
  full_name: string;
  aliases: string[];
  primary_outlet: string;
  beat: string | null;
  directory_status: DirectoryStatus;
  guardian_tag?: string | null;
  author_slug?: string | null;
  author_url?: string | null;
  x_handle?: string | null;
}

interface DirectoryFile {
  version: string;
  as_of: string;
  note: string;
  access_levels: Record<string, string>;
  outlets: DirectoryOutlet[];
  journalists: DirectoryJournalist[];
}

const data = raw as DirectoryFile;

const outletsBySlug = new Map(data.outlets.map((o) => [o.slug, o]));
const journalistsBySlug = new Map(data.journalists.map((j) => [j.slug, j]));

export function directoryMeta() {
  return {
    version: data.version,
    as_of: data.as_of,
    note: data.note,
    access_levels: data.access_levels,
  };
}

export function listDirectoryOutlets(): DirectoryOutlet[] {
  return data.outlets;
}

export function getDirectoryOutlet(slug: string): DirectoryOutlet | undefined {
  return outletsBySlug.get(slug);
}

export function listDirectoryJournalists(): DirectoryJournalist[] {
  return data.journalists;
}

export function getDirectoryJournalist(slug: string): DirectoryJournalist | undefined {
  return journalistsBySlug.get(slug);
}

export function outletName(slug: string): string {
  return outletsBySlug.get(slug)?.name ?? slug;
}

export function journalistsForOutlet(outletSlug: string): DirectoryJournalist[] {
  return data.journalists.filter((j) => j.primary_outlet === outletSlug);
}

function emptySummary(j: DirectoryJournalist): JournalistSummary {
  return {
    id: `dir:${j.slug}`,
    full_name: j.full_name,
    slug: j.slug,
    primary_outlet: outletName(j.primary_outlet),
    beat: j.beat,
    data_status: j.directory_status === "scored" ? "scored" : "collecting",
    composite_score: null,
    pillar_1_score: null,
    pillar_2_score: null,
    pillar_3_score: null,
    pillar_4_score: null,
    scored_at: null,
  };
}

export function mergeJournalistList(apiRows: JournalistSummary[] | null): JournalistSummary[] {
  const bySlug = new Map((apiRows ?? []).map((row) => [row.slug, row]));
  const merged = data.journalists.map((j) => {
    const api = bySlug.get(j.slug);
    if (!api) return emptySummary(j);
    return {
      ...emptySummary(j),
      ...api,
      full_name: api.full_name || j.full_name,
      primary_outlet: api.primary_outlet || outletName(j.primary_outlet),
      beat: api.beat ?? j.beat,
    };
  });

  return merged.sort((a, b) => {
    if (a.composite_score === null && b.composite_score === null) {
      return a.full_name.localeCompare(b.full_name);
    }
    if (a.composite_score === null) return 1;
    if (b.composite_score === null) return -1;
    return b.composite_score - a.composite_score;
  });
}

export function directoryProfile(slug: string): JournalistProfile | null {
  const j = journalistsBySlug.get(slug);
  if (!j) return null;
  const summary = emptySummary(j);
  return {
    ...summary,
    bio: null,
    pillar_scores: null,
    fec_records: [],
    corrections: [],
    appeals: [],
    corpus_size: null,
    corpus_start: null,
    corpus_end: null,
    methodology_version: null,
  };
}

export function mergeOutletList(apiRows: OutletSummary[] | null): OutletSummary[] {
  const bySlug = new Map((apiRows ?? []).map((row) => [row.slug, row]));
  return data.outlets
    .filter((o) => !o.queued || journalistsForOutlet(o.slug).length > 0 || bySlug.has(o.slug))
    .map((o) => {
      const api = bySlug.get(o.slug);
      const listed = journalistsForOutlet(o.slug).length;
      return {
        name: o.name,
        slug: o.slug,
        journalist_count: api?.journalist_count ?? listed,
        avg_composite: api?.avg_composite ?? null,
        avg_pillar_1: api?.avg_pillar_1 ?? null,
        avg_pillar_2: api?.avg_pillar_2 ?? null,
        avg_pillar_3: api?.avg_pillar_3 ?? null,
        avg_pillar_4: api?.avg_pillar_4 ?? null,
      };
    });
}

export function directoryOutletProfile(slug: string, journalists: JournalistSummary[]): OutletProfile | null {
  const outlet = outletsBySlug.get(slug);
  if (!outlet) return null;
  const rows = journalists.filter((j) => {
    const dir = journalistsBySlug.get(j.slug);
    return dir?.primary_outlet === slug || j.primary_outlet === outlet.name;
  });
  const scored = rows.filter((j) => j.composite_score !== null);
  const avg = (key: keyof JournalistSummary) => {
    const vals = scored.map((j) => j[key]).filter((v): v is number => typeof v === "number");
    if (!vals.length) return null;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  };
  return {
    name: outlet.name,
    slug: outlet.slug,
    journalist_count: rows.length,
    avg_composite: avg("composite_score"),
    avg_pillar_1: avg("pillar_1_score"),
    avg_pillar_2: avg("pillar_2_score"),
    avg_pillar_3: avg("pillar_3_score"),
    avg_pillar_4: avg("pillar_4_score"),
    journalists: rows,
  };
}
