import { NextRequest, NextResponse } from "next/server";
import { api } from "@/lib/api";
import {
  LookupJournalist,
  LookupResponse,
  buildLookupNotes,
  directoryLookup,
  toLookupJournalist,
} from "@/lib/lookup";
import { getDirectoryJournalist } from "@/lib/directory";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Cache-Control": "public, max-age=60",
};

function json(body: unknown, status = 200) {
  return NextResponse.json(body, { status, headers: CORS });
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: CORS });
}

function parseAuthors(raw: string | null): string[] {
  if (!raw) return [];
  return raw.split(/,|;|\band\b/i).map((s) => s.trim()).filter(Boolean);
}

async function overlayScores(base: LookupResponse, backendUrl: string | null): Promise<LookupResponse> {
  const journalists: LookupJournalist[] = [];
  for (const row of base.journalists) {
    try {
      const profile = await api.journalists.get(row.slug);
      const scores = profile.pillar_scores;
      const seeded = getDirectoryJournalist(row.slug);
      journalists.push(
        toLookupJournalist(seeded || (row as any), {
          ...row,
          full_name: profile.full_name,
          beat: profile.beat,
          composite_score: scores?.composite_score ?? profile.composite_score ?? null,
          pillar_1_score: scores?.pillar_1_score ?? null,
          pillar_2_score: scores?.pillar_2_score ?? null,
          pillar_3_score: scores?.pillar_3_score ?? null,
          pillar_4_score: scores?.pillar_4_score ?? null,
          corpus_size: profile.corpus_size,
        })
      );
    } catch {
      journalists.push(row);
    }
  }

  let article = base.article;
  if (backendUrl && base.page.canonical) {
    try {
      const res = await fetch(
        `${backendUrl.replace(/\/$/, "")}/api/lookup?url=${encodeURIComponent(base.page.canonical)}`,
        { next: { revalidate: 120 } }
      );
      if (res.ok) {
        const remote = await res.json();
        if (remote?.article) {
          article = { ...article, ...remote.article, url: remote.article.url ?? article.url, headline: remote.article.headline ?? article.headline };
        }
      }
    } catch {
      /* directory-only fallback */
    }
  }

  return {
    ...base,
    journalists,
    article,
    notes: buildLookupNotes({
      outlet: base.outlet ? { name: base.outlet.name, queued: base.outlet.queued } : undefined,
      journalists,
      authors: base.page.authors,
      article,
    }),
  };
}

export async function GET(req: NextRequest) {
  const url = req.nextUrl.searchParams.get("url");
  const title = req.nextUrl.searchParams.get("title");
  const host = req.nextUrl.searchParams.get("host");
  const authors = parseAuthors(req.nextUrl.searchParams.get("authors"));
  const base = directoryLookup({ url, title, authors, host });
  const payload = await overlayScores(base, process.env.NEXT_PUBLIC_API_URL ?? null);
  return json(payload);
}
