"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  controlSnapshot,
  formatPct,
  outletKind,
  publicParent,
  type OwnershipEntity,
} from "@/lib/ownership";

type Filter = "all" | "family" | "institutional" | "closed";

export function OutletExplorer({ outlets }: { outlets: OwnershipEntity[] }) {
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<Filter>("all");

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return outlets.filter((o) => {
      const kind = outletKind(o.slug);
      if (filter !== "all" && kind !== filter) return false;
      if (!needle) return true;
      const parent = publicParent(o.slug);
      const snap = controlSnapshot(o.slug);
      const hay = [o.name, parent?.name, parent?.ticker, snap.label, snap.detail]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(needle);
    });
  }, [outlets, q, filter]);

  return (
    <section className="mb-16">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-4">
        <div>
          <h2 className="text-xl font-semibold">Outlets</h2>
          <p className="text-sm text-gray-500 mt-1">
            {rows.length} of {outlets.length}. Concentration is residual 13F of the public parent — including under a family vote.
          </p>
        </div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search outlet, parent, controller…"
          className="border border-gray-200 rounded-md px-3 py-2 text-sm w-64 max-w-full"
        />
      </div>
      <div className="flex flex-wrap gap-2 mb-4">
        {(
          [
            ["all", "All"],
            ["family", "Family / person"],
            ["institutional", "1-share-1-vote"],
            ["closed", "Trust / private"],
          ] as [Filter, string][]
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setFilter(id)}
            className={`text-xs px-3 py-1 rounded-full border ${
              filter === id ? "bg-gray-900 text-white border-gray-900" : "border-gray-200 text-gray-600"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="overflow-x-auto border border-gray-100 rounded-lg">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-gray-400 border-b border-gray-100">
              <th className="px-4 py-3 font-medium">Outlet</th>
              <th className="px-4 py-3 font-medium">Control</th>
              <th className="px-4 py-3 font-medium">Concentration</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((o) => {
              const snap = controlSnapshot(o.slug);
              const parent = publicParent(o.slug);
              const conc =
                snap.topHolders.length > 0
                  ? snap.topHolders.map((h) => `${h.entity.name} ${formatPct(h.pct)}`).join(" · ") +
                    (snap.top3Economic != null ? ` · top 3 ${formatPct(snap.top3Economic)}` : "")
                  : snap.kind === "closed"
                  ? snap.detail
                  : snap.kind === "institutional"
                  ? snap.detail
                  : "—";
              return (
                <tr key={o.slug} className="border-b border-gray-50 last:border-0 align-top">
                  <td className="px-4 py-3">
                    <Link href={`/ownership/${o.slug}`} className="font-medium hover:underline">{o.name}</Link>
                    {parent && (
                      <div className="text-xs text-gray-400 mt-1">
                        <Link href={`/ownership/${parent.slug}`} className="hover:underline">
                          {parent.ticker ?? parent.name}
                        </Link>
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-700">
                    {snap.href ? <Link href={snap.href} className="hover:underline">{snap.label}</Link> : snap.label}
                    {snap.kind === "controller" && (
                      <div className="text-xs text-gray-400 mt-1">{snap.detail}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs leading-relaxed">{conc}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
