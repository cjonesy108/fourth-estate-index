import { notFound } from "next/navigation";
import Link from "next/link";
import { Metadata } from "next";
import { api } from "@/lib/api";
import { AnalysisSample, JournalistProfile } from "@/lib/types";
import {
  directoryProfile,
  getDirectoryJournalist,
  listDirectoryJournalists,
  outletName,
} from "@/lib/directory";
import { fetchRecentWork, formatWorkDate } from "@/lib/work";
import ShareButton from "./ShareButton";

function scoreColor(score: number | null): string {
  if (score === null) return "text-gray-400";
  if (score >= 0.80) return "text-green-600";
  if (score >= 0.70) return "text-yellow-600";
  return "text-red-600";
}

function ScoreBar({ score }: { score: number | null }) {
  if (score === null) return <p className="text-sm text-gray-400 italic">Insufficient data</p>;
  const pct = Math.round(score * 100);
  const color = score >= 0.80 ? "bg-green-500" : score >= 0.70 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div>
      <div className="flex items-baseline gap-2 mb-1">
        <span className={`text-2xl font-bold tabular-nums ${scoreColor(score)}`}>{pct}</span>
        <span className="text-xs text-gray-400">/ 100</span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function formatDay(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function sampleLabel(type: string): string {
  const labels: Record<string, string> = {
    headline_fidelity: "Headline fidelity",
    attribution_patterns: "Attribution",
    language_patterns: "Language patterns",
    source_diversity: "Source diversity",
    social_media_independence: "Social posts",
  };
  return labels[type] || type.replace(/_/g, " ");
}

function BodyOfWork({
  profile,
  recentCount,
}: {
  profile: JournalistProfile;
  recentCount: number;
}) {
  const stored = profile.corpus_size ?? 0;
  const full = profile.corpus_full_text ?? null;
  const excerpt = profile.corpus_excerpt ?? null;
  const metadata = profile.corpus_metadata ?? null;
  const samples = profile.analysis_samples ?? [];
  const scoredFrom = samples.length
    ? Math.max(...samples.map((s) => s.corpus_size ?? 0))
    : profile.pillar_scores?.corpus_size ?? null;

  return (
    <section className="mb-12">
      <h2 className="text-xl font-semibold mb-4">Body of work</h2>
      <div className="border border-gray-200 rounded-lg p-5 space-y-4">
        {stored > 0 ? (
          <>
            <p className="text-sm text-gray-700">
              {stored} article{stored === 1 ? "" : "s"} stored in the scoring warehouse
              {profile.corpus_start && profile.corpus_end ? (
                <>
                  {" "}· {formatDay(profile.corpus_start)} to {formatDay(profile.corpus_end)}
                </>
              ) : null}
            </p>
            {full !== null && (
              <p className="text-sm text-gray-500">
                {full} full text
                {excerpt ? ` · ${excerpt} excerpt` : ""}
                {metadata ? ` · ${metadata} metadata only` : ""}
              </p>
            )}
            {profile.composite_score !== null || profile.pillar_scores ? (
              <p className="text-sm text-gray-500">
                {scoredFrom
                  ? `The published score used the most recent ${scoredFrom} full-text stories, not every stored row.`
                  : "The published score used a recent full-text sample, not every stored row."}
              </p>
            ) : (
              <p className="text-sm text-gray-500">
                Articles are stored. No score is published until minimum thresholds are met.
              </p>
            )}
            {samples.length > 0 && (
              <ul className="text-xs text-gray-400 space-y-1 pt-2 border-t border-gray-100">
                {samples.map((s: AnalysisSample) => (
                  <li key={s.analysis_type}>
                    {sampleLabel(s.analysis_type)}
                    {s.corpus_size != null ? ` · ${s.corpus_size} stories` : ""}
                    {s.scored_at ? ` · ${formatDay(s.scored_at)}` : ""}
                  </li>
                ))}
              </ul>
            )}
          </>
        ) : (
          <>
            <p className="text-sm text-gray-700">No full-text corpus in the scoring warehouse yet.</p>
            <p className="text-sm text-gray-500">
              {recentCount > 0
                ? `${recentCount} recent byline${recentCount === 1 ? "" : "s"} below come from the publisher’s public feed. Those links are work product, not scored text.`
                : "This person is listed in the directory. Scoring waits on licensed or openly published full text."}
            </p>
          </>
        )}
        <p className="text-xs text-gray-400">
          Excerpt and metadata rows count as inventory. Only full text enters attribution, language, and source-diversity scoring.{" "}
          <Link href="/methodology" className="text-blue-600 hover:underline">
            Methodology →
          </Link>
        </p>
      </div>
    </section>
  );
}

export function generateStaticParams() {
  return listDirectoryJournalists().map((j) => ({ slug: j.slug }));
}

async function loadProfile(slug: string): Promise<JournalistProfile | null> {
  try {
    return await api.journalists.get(slug);
  } catch {
    return directoryProfile(slug);
  }
}

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const profile = await loadProfile(params.slug);
  if (!profile) return { title: "Fourth Estate Index" };
  const score = profile.pillar_scores?.composite_score ?? profile.composite_score;
  const scoreStr =
    score !== null && score !== undefined
      ? ` · FEI Score: ${Math.round(score * 100)}/100`
      : "";
  return {
    title: `${profile.full_name} | Fourth Estate Index`,
    description: `Journalism standards score for ${profile.full_name} (${profile.primary_outlet})${scoreStr}`,
  };
}

export default async function JournalistPage({
  params,
}: {
  params: { slug: string };
}) {
  const profile = await loadProfile(params.slug);
  if (!profile) notFound();

  const seeded = getDirectoryJournalist(params.slug);
  const work = seeded ? await fetchRecentWork(seeded) : [];
  const { pillar_scores: scores } = profile;
  const narrative = scores?.score_narrative;
  const outletSlug = seeded?.primary_outlet;
  const outletLabel = profile.primary_outlet || (outletSlug ? outletName(outletSlug) : null);

  return (
    <main className="max-w-3xl mx-auto px-6 py-16">
      <header className="mb-10">
        <Link href="/" className="text-sm text-gray-400 hover:text-gray-600 mb-6 inline-block">
          ← Fourth Estate Index
        </Link>
        {outletLabel && outletSlug ? (
          <p className="text-sm text-gray-400 mb-2">
            <Link href={`/outlet/${outletSlug}`} className="hover:text-gray-600">
              {outletLabel}
            </Link>
          </p>
        ) : (
          <p className="text-sm text-gray-400 mb-2">{outletLabel}</p>
        )}
        <h1 className="text-4xl font-bold mb-1">{profile.full_name}</h1>
        {(profile.beat || seeded?.beat) && (
          <p className="text-gray-500 mb-3">{profile.beat || seeded?.beat}</p>
        )}
        <div className="flex flex-wrap items-center gap-4 mb-4">
          <ShareButton slug={params.slug} />
          {seeded?.author_url && (
            <a
              href={seeded.author_url}
              className="text-sm text-blue-600 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              Author page ↗
            </a>
          )}
        </div>
      </header>

      <BodyOfWork profile={profile} recentCount={work.length} />

      {work.length > 0 && (
        <section className="mb-12">
          <h2 className="text-xl font-semibold mb-4">Recent work</h2>
          <ul className="divide-y divide-gray-100 border-t border-gray-100">
            {work.map((item) => (
              <li key={item.url} className="py-3">
                <a
                  href={item.url}
                  className="text-sm text-gray-900 hover:text-blue-600"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {item.title}
                </a>
                {item.published_at && (
                  <p className="text-xs text-gray-400 mt-1">{formatWorkDate(item.published_at)}</p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mb-12">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">FEI Score</h2>
          <Link href="/methodology" className="text-sm text-blue-600 hover:underline">
            How this is scored →
          </Link>
        </div>
        {scores ? (
          <div className="border border-gray-200 rounded-lg p-6">
            {scores.composite_score !== null ? (
              <div className="text-center mb-6 pb-6 border-b border-gray-100">
                <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Composite Score</p>
                <span className={`text-7xl font-bold tabular-nums ${scoreColor(scores.composite_score)}`}>
                  {Math.round(scores.composite_score * 100)}
                </span>
                <p className="text-sm text-gray-400 mt-1">out of 100</p>
                {narrative?.overall && (
                  <p className="text-sm text-gray-500 mt-4 text-left leading-relaxed">{narrative.overall}</p>
                )}
              </div>
            ) : (
              <div className="text-center mb-8 pb-6 border-b border-gray-100">
                <p className="text-sm text-gray-400 italic">
                  Composite score pending — not all pillars have sufficient data yet.
                </p>
              </div>
            )}
            <div className="grid grid-cols-2 gap-8">
              {[
                { label: "Seek Truth & Report It", sublabel: "Pillar 1 · 30%", value: scores.pillar_1_score, narrativeKey: "pillar_1" },
                { label: "Minimize Harm", sublabel: "Pillar 2 · 20%", value: scores.pillar_2_score, narrativeKey: "pillar_2" },
                { label: "Act Independently", sublabel: "Pillar 3 · 30%", value: scores.pillar_3_score, narrativeKey: "pillar_3" },
                { label: "Be Accountable", sublabel: "Pillar 4 · 20%", value: scores.pillar_4_score, narrativeKey: "pillar_4" },
              ].map(({ label, sublabel, value, narrativeKey }) => (
                <div key={label}>
                  <p className="text-sm font-medium mb-0.5">{label}</p>
                  <p className="text-xs text-gray-400 mb-2">{sublabel}</p>
                  <ScoreBar score={value} />
                  {narrative?.[narrativeKey] && (
                    <p className="text-xs text-gray-500 mt-3 leading-relaxed">{narrative[narrativeKey]}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="border border-gray-200 rounded-lg p-6 text-center text-gray-400">
            <p className="font-medium mb-1">Data collection in progress</p>
            <p className="text-sm">
              This journalist is in the public directory. No score is published
              until minimum data thresholds are met.
            </p>
          </div>
        )}
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Financial Disclosures</h2>
        {profile.fec_records.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b">
                <th className="pb-2 font-normal">Recipient</th>
                <th className="pb-2 font-normal">Type</th>
                <th className="pb-2 font-normal">Amount</th>
                <th className="pb-2 font-normal">Date</th>
                <th className="pb-2 font-normal">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {profile.fec_records.map((r) => (
                <tr key={r.id}>
                  <td className="py-2">{r.recipient_name}</td>
                  <td className="py-2 text-gray-500">{r.recipient_type}</td>
                  <td className="py-2">${r.amount.toLocaleString()}</td>
                  <td className="py-2 text-gray-500">{r.contribution_date}</td>
                  <td className="py-2">
                    <a
                      href={`https://www.fec.gov/data/receipts/?contributor_name=${encodeURIComponent(r.contributor_name)}`}
                      className="text-blue-600 underline"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      FEC ↗
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-gray-400">
            No contributions found in FEC records as of{" "}
            {new Date().toLocaleDateString("en-US", { month: "long", year: "numeric" })}.
          </p>
        )}
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Corrections Record</h2>
        {profile.corrections.length > 0 ? (
          <div className="space-y-4">
            {profile.corrections.map((c) => (
              <div key={c.id} className="border-l-2 border-gray-200 pl-4">
                <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                  {c.corrected_at && <span>{c.corrected_at.slice(0, 10)}</span>}
                  {c.correction_type && (
                    <span className="border border-gray-200 rounded px-1">{c.correction_type}</span>
                  )}
                </div>
                <p className="text-sm">{c.correction_text}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">No corrections on record.</p>
        )}
      </section>
    </main>
  );
}
