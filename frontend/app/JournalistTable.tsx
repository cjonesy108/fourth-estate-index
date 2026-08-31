"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { JournalistSummary } from "@/lib/types";
import { getDirectoryJournalist } from "@/lib/directory";
import { gradeColor, letterGrade, scoreToPct } from "@/lib/score";

type SortKey = "composite_score" | "pillar_1_score" | "pillar_2_score" | "pillar_3_score" | "pillar_4_score";

const COLUMNS: { key: SortKey; label: string; short: string }[] = [
  { key: "composite_score",  label: "Composite",         short: "Total" },
  { key: "pillar_1_score",   label: "Seek Truth",        short: "P1" },
  { key: "pillar_2_score",   label: "Minimize Harm",     short: "P2" },
  { key: "pillar_3_score",   label: "Act Independently", short: "P3" },
  { key: "pillar_4_score",   label: "Be Accountable",    short: "P4" },
];

function ScoreCell({ score }: { score: number | null }) {
  const pct = scoreToPct(score);
  if (pct === null) return <span className="text-xs italic" style={{ color: "var(--text-faint)" }}>—</span>;
  return (
    <span className="text-sm tabular-nums" style={{ fontFamily: "var(--font-serif)", color: gradeColor(letterGrade(score)), fontWeight: 600 }}>
      {pct}
    </span>
  );
}

function haystack(j: JournalistSummary): string {
  const seeded = getDirectoryJournalist(j.slug);
  return [j.full_name, j.slug, j.primary_outlet, j.beat, ...(seeded?.aliases ?? [])]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

export default function JournalistTable({
  journalists,
  hideOutletFilter = false,
}: {
  journalists: JournalistSummary[];
  hideOutletFilter?: boolean;
}) {
  const outlets = useMemo(() => {
    const set = new Set(journalists.map(j => j.primary_outlet).filter(Boolean) as string[]);
    return Array.from(set).sort();
  }, [journalists]);

  const [query, setQuery] = useState("");
  const [outlet, setOutlet] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("composite_score");
  const [sortDir, setSortDir] = useState<"desc" | "asc">("desc");

  const handleSort = (key: SortKey) => {
    if (key === sortKey) setSortDir(d => d === "desc" ? "asc" : "desc");
    else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = outlet ? journalists.filter(j => j.primary_outlet === outlet) : journalists;
    if (q) list = list.filter(j => haystack(j).includes(q));
    return [...list].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      return sortDir === "desc" ? bv - av : av - bv;
    });
  }, [journalists, outlet, query, sortKey, sortDir]);

  return (
    <div>
      <div className="mb-4">
        <label htmlFor="journalist-search" className="sr-only">Search journalists</label>
        <input
          id="journalist-search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name, outlet, or beat"
          autoComplete="off"
          className="w-full px-3 py-2 text-sm"
          style={{ border: "1px solid var(--border-default)", background: "var(--paper-100)", color: "var(--text-heading)", fontFamily: "var(--font-sans)" }}
        />
      </div>

      {!hideOutletFilter && (
        <div className="flex flex-wrap gap-2 mb-5">
          <button
            onClick={() => setOutlet(null)}
            className="px-3 py-1 text-sm"
            style={outlet === null
              ? { background: "var(--navy-800)", color: "var(--paper-100)" }
              : { background: "var(--paper-300)", color: "var(--text-body)" }}
          >
            All outlets
          </button>
          {outlets.map(o => {
            const slug = o.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
            const on = outlet === o;
            return (
              <div key={o} className="flex items-center gap-1">
                <button
                  onClick={() => setOutlet(on ? null : o)}
                  className="px-3 py-1 text-sm"
                  style={on
                    ? { background: "var(--navy-800)", color: "var(--paper-100)" }
                    : { background: "var(--paper-300)", color: "var(--text-body)" }}
                >
                  {o}
                </button>
                <Link href={`/outlet/${slug}`} className="text-xs" style={{ color: "var(--text-faint)" }} title={`View ${o} outlet page`}>
                  →
                </Link>
              </div>
            );
          })}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr style={{ borderBottom: "2px solid var(--navy-800)" }}>
              <th className="pb-3 pr-4 text-xs uppercase tracking-wide" style={{ color: "var(--text-muted)", fontWeight: 600 }}>Journalist</th>
              {COLUMNS.map(col => (
                <th key={col.key} className="pb-3 px-2 text-right">
                  <button
                    onClick={() => handleSort(col.key)}
                    className="text-xs uppercase tracking-wide flex items-center gap-1 ml-auto"
                    style={{ color: sortKey === col.key ? "var(--navy-800)" : "var(--text-muted)", fontWeight: 600 }}
                  >
                    <span className="hidden sm:inline">{col.label}</span>
                    <span className="sm:hidden">{col.short}</span>
                    {sortKey === col.key && <span>{sortDir === "desc" ? "↓" : "↑"}</span>}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-10 text-center text-sm" style={{ color: "var(--text-faint)" }}>
                  {query.trim() ? `No journalists match “${query.trim()}”.` : "No journalists in this list."}
                </td>
              </tr>
            ) : filtered.map((j) => (
              <tr key={j.id} style={{ borderBottom: "1px solid var(--border-hairline)" }}>
                <td className="py-3 pr-4">
                  <Link href={`/journalist/${j.slug}`} className="block">
                    <p style={{ fontFamily: "var(--font-serif)", fontWeight: 600, color: "var(--text-heading)" }}>{j.full_name}</p>
                    {!outlet && <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{j.primary_outlet}</p>}
                  </Link>
                </td>
                {COLUMNS.map(col => (
                  <td key={col.key} className="py-3 px-2 text-right">
                    {col.key === "composite_score" ? (
                      <Link href={`/journalist/${j.slug}`}>
                        {j.composite_score !== null ? (
                          <span className="tabular-nums" style={{ fontFamily: "var(--font-serif)", fontWeight: 700, fontSize: "1.1rem", color: gradeColor(letterGrade(j.composite_score)) }}>
                            {scoreToPct(j.composite_score)}
                          </span>
                        ) : (
                          <span className="text-xs italic" style={{ color: "var(--text-faint)" }}>pending</span>
                        )}
                      </Link>
                    ) : (
                      <ScoreCell score={j[col.key]} />
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs mt-4" style={{ color: "var(--text-faint)" }}>
        {filtered.length} journalist{filtered.length !== 1 ? "s" : ""}
        {outlet ? ` · ${outlet}` : ""}
        {query.trim() ? ` · matching “${query.trim()}”` : ""}
        {" · "}sorted by {COLUMNS.find(c => c.key === sortKey)?.label} ({sortDir === "desc" ? "highest first" : "lowest first"})
      </p>
    </div>
  );
}
