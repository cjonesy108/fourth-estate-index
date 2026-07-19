"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { JournalistSummary } from "@/lib/types";

type SortKey = "composite_score" | "pillar_1_score" | "pillar_2_score" | "pillar_3_score" | "pillar_4_score";

const COLUMNS: { key: SortKey; label: string; short: string }[] = [
  { key: "composite_score",  label: "Composite",         short: "Total" },
  { key: "pillar_1_score",   label: "Seek Truth",        short: "P1" },
  { key: "pillar_2_score",   label: "Minimize Harm",     short: "P2" },
  { key: "pillar_3_score",   label: "Act Independently", short: "P3" },
  { key: "pillar_4_score",   label: "Be Accountable",    short: "P4" },
];

function scoreColor(score: number | null) {
  if (score === null) return "text-gray-300";
  if (score >= 0.8) return "text-emerald-600";
  if (score >= 0.7) return "text-amber-500";
  return "text-red-500";
}

function ScoreCell({ score }: { score: number | null }) {
  if (score === null) return <span className="text-xs text-gray-300 italic">—</span>;
  return (
    <span className={`text-sm font-bold tabular-nums ${scoreColor(score)}`}>
      {Math.round(score * 100)}
    </span>
  );
}

export default function JournalistTable({ journalists }: { journalists: JournalistSummary[] }) {
  const outlets = useMemo(() => {
    const set = new Set(journalists.map(j => j.primary_outlet).filter(Boolean) as string[]);
    return Array.from(set).sort();
  }, [journalists]);

  const [outlet, setOutlet] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("composite_score");
  const [sortDir, setSortDir] = useState<"desc" | "asc">("desc");

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir(d => d === "desc" ? "asc" : "desc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const filtered = useMemo(() => {
    let list = outlet ? journalists.filter(j => j.primary_outlet === outlet) : journalists;
    return [...list].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      return sortDir === "desc" ? bv - av : av - bv;
    });
  }, [journalists, outlet, sortKey, sortDir]);

  return (
    <div>
      {/* Outlet filter pills */}
      <div className="flex flex-wrap gap-2 mb-5">
        <button
          onClick={() => setOutlet(null)}
          className={`px-3 py-1 rounded-full text-sm transition-colors ${
            outlet === null
              ? "bg-gray-900 text-white"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          All outlets
        </button>
        {outlets.map(o => (
          <button
            key={o}
            onClick={() => setOutlet(o === outlet ? null : o)}
            className={`px-3 py-1 rounded-full text-sm transition-colors ${
              outlet === o
                ? "bg-gray-900 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {o}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="pb-3 pr-4 text-xs font-medium text-gray-400 uppercase tracking-wide">
                Journalist
              </th>
              {COLUMNS.map(col => (
                <th key={col.key} className="pb-3 px-2 text-right">
                  <button
                    onClick={() => handleSort(col.key)}
                    className={`text-xs font-medium uppercase tracking-wide transition-colors flex items-center gap-1 ml-auto ${
                      sortKey === col.key ? "text-gray-900" : "text-gray-400 hover:text-gray-600"
                    }`}
                  >
                    <span className="hidden sm:inline">{col.label}</span>
                    <span className="sm:hidden">{col.short}</span>
                    {sortKey === col.key && (
                      <span className="text-gray-400">{sortDir === "desc" ? "↓" : "↑"}</span>
                    )}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {filtered.map((j, i) => (
              <tr key={j.id} className="hover:bg-gray-50 transition-colors group">
                <td className="py-3 pr-4">
                  <Link href={`/journalist/${j.slug}`} className="block">
                    <p className="font-medium text-gray-900 group-hover:text-blue-600 transition-colors">
                      {j.full_name}
                    </p>
                    {!outlet && (
                      <p className="text-xs text-gray-400 mt-0.5">{j.primary_outlet}</p>
                    )}
                  </Link>
                </td>
                {COLUMNS.map(col => (
                  <td key={col.key} className={`py-3 px-2 text-right ${col.key === sortKey ? "bg-gray-50/50" : ""}`}>
                    {col.key === "composite_score" ? (
                      <Link href={`/journalist/${j.slug}`}>
                        {j.composite_score !== null ? (
                          <span className={`text-base font-black tabular-nums ${scoreColor(j.composite_score)}`}>
                            {Math.round(j.composite_score * 100)}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-300 italic">pending</span>
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

      <p className="text-xs text-gray-400 mt-4">
        {filtered.length} journalist{filtered.length !== 1 ? "s" : ""}
        {outlet ? ` · ${outlet}` : ""}
        {" · "}sorted by {COLUMNS.find(c => c.key === sortKey)?.label} ({sortDir === "desc" ? "highest first" : "lowest first"})
      </p>
    </div>
  );
}
