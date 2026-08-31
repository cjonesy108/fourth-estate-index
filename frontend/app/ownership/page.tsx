import Link from "next/link";
import { Metadata } from "next";
import {
  LAYER_LABEL,
  allContributions,
  controlSnapshot,
  formatPct,
  getContributionsMeta,
  getEntity,
  getGraph,
  institutionHoldings,
  listControllers,
  listInstitutions,
  listOutlets,
  officersOf,
  publicParent,
} from "@/lib/ownership";

export const metadata: Metadata = {
  title: "Who owns the media — Fourth Estate Index",
  description:
    "Voting control, institutional concentration, and entity vs officer political giving.",
};

export default function OwnershipIndex() {
  const graph = getGraph();
  const outlets = listOutlets();
  const institutions = listInstitutions();
  const controllers = listControllers();
  const giving = allContributions();
  const meta = getContributionsMeta();

  return (
    <main className="max-w-4xl mx-auto px-6 py-16">
      <header className="mb-14">
        <p className="text-sm text-gray-400 mb-3">Fourth Estate Index</p>
        <h1 className="text-4xl font-bold tracking-tight mb-4">Who owns the media</h1>
        <p className="text-lg text-gray-600 leading-relaxed mb-4">
          Where there is a controller, we name them and the voting share.
          Where there is not, we show the <strong>1-share-1-vote parent</strong> and the
          top institutional holders — not the word “dispersed.”
        </p>
        <p className="text-gray-600 leading-relaxed">
          Political money is split the same way: firm PAC vs named officer.
          BlackRock PAC is not Larry Fink. Fink is not CNN.
        </p>
      </header>

      <section className="mb-16">
        <h2 className="text-xl font-semibold mb-4">Outlets</h2>
        <p className="text-sm text-gray-500 mb-6">{outlets.length} outlets. Concentration is top 13F holders of the public parent.</p>
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
              {outlets.map((o) => {
                const snap = controlSnapshot(o.slug);
                const parent = publicParent(o.slug);
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
                      {snap.href ? (
                        <Link href={snap.href} className="hover:underline">{snap.label}</Link>
                      ) : (
                        snap.label
                      )}
                      {snap.kind === "controller" && (
                        <div className="text-xs text-gray-400 mt-1">{snap.detail}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs leading-relaxed">
                      {snap.kind === "institutional"
                        ? snap.detail
                        : snap.kind === "closed"
                        ? snap.detail
                        : snap.topHolders.length
                        ? snap.topHolders.map((h) => `${h.entity.name} ${formatPct(h.pct)}`).join(" · ")
                        : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-16">
        <h2 className="text-xl font-semibold mb-4">Institutional economic concentration</h2>
        <p className="text-sm text-gray-500 mb-6">Holdings plus the named officer, when we have one. Economic data as of {graph.as_of_economic}.</p>
        <div className="space-y-8">
          {institutions.map((inst) => {
            const holdings = institutionHoldings(inst.slug);
            const officers = officersOf(inst.slug);
            return (
              <div key={inst.slug} className="border border-gray-100 rounded-lg p-5">
                <div className="flex items-baseline justify-between gap-4 mb-2">
                  <Link href={`/ownership/${inst.slug}`} className="text-lg font-semibold hover:underline">{inst.name}</Link>
                  <span className="text-xs text-gray-400">{holdings.length} issuer{holdings.length === 1 ? "" : "s"}</span>
                </div>
                {officers.length > 0 && (
                  <p className="text-sm text-gray-500 mb-3">
                    {officers.map((off, i) => (
                      <span key={off.person.slug}>
                        {i > 0 && ", "}
                        <Link href={`/ownership/${off.person.slug}`} className="hover:underline">{off.person.name}</Link>
                        <span className="text-gray-400"> · {off.role}</span>
                      </span>
                    ))}
                  </p>
                )}
                {holdings.length === 0 ? (
                  <p className="text-sm text-gray-400">No 13F rows in this seed yet.</p>
                ) : (
                  <ul className="space-y-2">
                    {holdings.map((h) => (
                      <li key={h.issuer.slug} className="text-sm text-gray-700 flex flex-wrap gap-x-2">
                        <span className="tabular-nums text-gray-900 font-medium w-16">{formatPct(h.edge.pct_economic)}</span>
                        <Link href={`/ownership/${h.issuer.slug}`} className="hover:underline">
                          {h.issuer.name}{h.issuer.ticker ? ` (${h.issuer.ticker})` : ""}
                        </Link>
                        {h.outlets.length > 0 && (
                          <span className="text-gray-400">— {h.outlets.map((x) => x.name).join(", ")}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      </section>

      <section className="mb-16">
        <h2 className="text-xl font-semibold mb-4">Controllers</h2>
        <ul className="divide-y divide-gray-100 border border-gray-100 rounded-lg">
          {controllers.map((c) => (
            <li key={c.slug} className="px-4 py-3">
              <Link href={`/ownership/${c.slug}`} className="font-medium hover:underline">{c.name}</Link>
              <p className="text-sm text-gray-500 mt-1">{c.control_summary}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="mb-16">
        <h2 className="text-xl font-semibold mb-4">Political money</h2>
        <p className="text-sm text-gray-500 mb-6">{meta.rule}</p>
        <ul className="space-y-4">
          {giving.map((g) => {
            const ent = getEntity(g.entity);
            return (
              <li key={`${g.entity}-${g.layer}-${g.cycle}`} className="border border-gray-100 rounded-lg p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2 mb-2">
                  <Link href={`/ownership/${g.entity}`} className="font-medium hover:underline">{ent?.name ?? g.entity}</Link>
                  <span className="text-xs text-gray-400">
                    {LAYER_LABEL[g.layer]} · {g.party_lean === "D" ? "leans D" : g.party_lean === "R" ? "leans R" : "mixed"}
                  </span>
                </div>
                <p className="text-sm text-gray-600 mb-2">{g.summary}</p>
                <p className="text-xs text-gray-400">
                  {g.amount_label} · <a href={g.source_url} className="hover:underline" target="_blank" rel="noreferrer">{g.source_label}</a>
                </p>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="text-sm text-gray-500 leading-relaxed">
        <p className="mb-2">{graph.as_of_note}</p>
        <p>Ownership is not a journalist ethics score. <Link href="/methodology" className="underline">Scoring methodology</Link>.</p>
      </section>
    </main>
  );
}
