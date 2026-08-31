import { notFound } from "next/navigation";
import Link from "next/link";
import { Metadata } from "next";
import { api } from "@/lib/api";
import { JournalistSummary } from "@/lib/types";
import JournalistTable from "@/app/JournalistTable";
import {
  directoryOutletProfile,
  getDirectoryOutlet,
  listDirectoryOutlets,
  mergeJournalistList,
} from "@/lib/directory";

export function generateStaticParams() {
  return listDirectoryOutlets().map((o) => ({ slug: o.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const seeded = getDirectoryOutlet(params.slug);
  try {
    const outlet = await api.outlets.get(params.slug);
    return {
      title: `${outlet.name} — Fourth Estate Index`,
      description: `Journalistic integrity scores for ${outlet.journalist_count} ${outlet.name} reporters, grounded in the SPJ Code of Ethics.`,
    };
  } catch {
    if (seeded) {
      return {
        title: `${seeded.name} — Fourth Estate Index`,
        description: `Journalist directory for ${seeded.name}.`,
      };
    }
    return { title: "Outlet — Fourth Estate Index" };
  }
}

function ScoreBadge({
  label,
  score,
  large,
}: {
  label: string;
  score: number | null;
  large?: boolean;
}) {
  if (score === null) return null;
  const pct = Math.round(score * 100);
  const color =
    score >= 0.8
      ? "text-emerald-600"
      : score >= 0.7
      ? "text-amber-500"
      : "text-red-500";

  return (
    <div className="text-center">
      <div className={`font-black tabular-nums ${large ? "text-4xl" : "text-2xl"} ${color}`}>
        {pct}
      </div>
      <div className="text-xs text-gray-400 uppercase tracking-wide mt-1">{label}</div>
    </div>
  );
}

export default async function OutletPage({
  params,
}: {
  params: { slug: string };
}) {
  let apiRows: JournalistSummary[] | null = null;
  try {
    apiRows = await api.journalists.list();
  } catch {
    apiRows = null;
  }
  const journalists = mergeJournalistList(apiRows);
  const outlet = directoryOutletProfile(params.slug, journalists);
  const seeded = getDirectoryOutlet(params.slug);
  if (!outlet || !seeded) notFound();

  return (
    <main className="max-w-4xl mx-auto px-6 py-16">
      <nav className="mb-8 text-sm text-gray-400">
        <Link href="/" className="hover:text-gray-600 transition-colors">
          Fourth Estate Index
        </Link>
        <span className="mx-2">›</span>
        <span className="text-gray-600">{outlet.name}</span>
      </nav>

      <header className="mb-12">
        <h1 className="text-3xl font-bold tracking-tight mb-1">{outlet.name}</h1>
        <p className="text-gray-400 text-sm mb-3">
          {outlet.journalist_count} journalist{outlet.journalist_count !== 1 ? "s" : ""} in directory
        </p>
        <p className="text-sm text-gray-500 leading-relaxed max-w-2xl">
          {seeded.text_policy}
        </p>
      </header>

      {outlet.avg_composite !== null && (
        <section className="mb-12">
          <div className="border border-gray-100 rounded-xl p-6">
            <h2 className="text-xs font-medium uppercase tracking-wide text-gray-400 mb-6">
              Outlet averages
            </h2>
            <div className="flex gap-8 flex-wrap">
              <ScoreBadge label="Composite" score={outlet.avg_composite} large />
              <div className="w-px bg-gray-100 self-stretch hidden sm:block" />
              <ScoreBadge label="Seek Truth" score={outlet.avg_pillar_1} />
              <ScoreBadge label="Minimize Harm" score={outlet.avg_pillar_2} />
              <ScoreBadge label="Act Independently" score={outlet.avg_pillar_3} />
              <ScoreBadge label="Be Accountable" score={outlet.avg_pillar_4} />
            </div>
          </div>
        </section>
      )}

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-6">Journalists</h2>
        {outlet.journalists.length === 0 ? (
          <p className="text-gray-400 text-sm">
            {seeded.queued
              ? "Queued as a next full-text outlet. No journalists seeded yet."
              : "No journalists in the directory for this outlet yet."}
          </p>
        ) : (
          <JournalistTable journalists={outlet.journalists} hideOutletFilter />
        )}
      </section>

      <footer className="pt-8 border-t border-gray-100 text-sm text-gray-400">
        <p>
          Scoring methodology grounded in the{" "}
          <a
            href="https://www.spj.org/ethicscode.asp"
            className="underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            SPJ Code of Ethics
          </a>
          .{" "}
          <Link href="/methodology" className="underline">
            Full methodology →
          </Link>
        </p>
      </footer>
    </main>
  );
}
