import Link from "next/link";
import { Metadata } from "next";
import { OutletExplorer } from "./explorer";
import {
  LAYER_LABEL,
  allContributions,
  formatPct,
  getContributionsMeta,
  getEntity,
  getGraph,
  institutionHoldings,
  listControllers,
  listInstitutions,
  listMediaGroups,
  listOutlets,
  officersOf,
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
  const mediaGroups = listMediaGroups();

  return (
    <main className="max-w-4xl mx-auto px-6 py-16">
      <header className="mb-14">
        <p className="text-sm text-gray-400 mb-3">Fourth Estate Index</p>
        <h1 className="text-4xl font-bold tracking-tight mb-4">Who owns the media</h1>
        <p className="text-lg text-gray-600 leading-relaxed mb-4">
          Where there is a controller, we name them and the voting share.
          The public float still shows under <strong>Concentration</strong> — Murdoch votes Fox; Vanguard can still own the Class A.
        </p>
        <p className="text-gray-600 leading-relaxed">
          Political money is split the same way: firm PAC vs named officer.
          BlackRock PAC is not Larry Fink. Fink is not CNN.
        </p>
      </header>

      <section className="mb-16">
        <h2 className="text-xl font-semibold mb-2">Groups</h2>
        <p className="text-sm text-gray-500 mb-6">
          One parent, many newsrooms. Group nodes are not a full FCC census.
        </p>
        <ul className="grid gap-3 sm:grid-cols-2">
          {mediaGroups.map((g) => (
            <li key={g.entity.slug} className="border border-gray-100 rounded-lg p-4">
              <div className="flex items-baseline justify-between gap-2">
                <Link href={`/ownership/${g.entity.slug}`} className="font-semibold hover:underline">
                  {g.entity.name}
                  {g.entity.ticker ? ` (${g.entity.ticker})` : ""}
                </Link>
                <span className="text-xs text-gray-400">{g.outlets.length} title{g.outlets.length === 1 ? "" : "s"}</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">{g.reach}</p>
              <p className="text-sm text-gray-700 mt-2">
                {g.snapshot.href ? (
                  <Link href={g.snapshot.href} className="hover:underline">{g.snapshot.label}</Link>
                ) : (
                  g.snapshot.label
                )}
                {g.snapshot.kind === "controller" && (
                  <span className="text-gray-400"> · {g.snapshot.detail}</span>
                )}
              </p>
              {g.outlets.length > 0 && (
                <p className="text-xs text-gray-400 mt-2">
                  {g.outlets.slice(0, 4).map((o, i) => (
                    <span key={o.slug}>
                      {i > 0 && ", "}
                      <Link href={`/ownership/${o.slug}`} className="hover:underline">{o.name}</Link>
                    </span>
                  ))}
                  {g.outlets.length > 4 ? ` + ${g.outlets.length - 4}` : ""}
                </p>
              )}
            </li>
          ))}
        </ul>
      </section>

      <OutletExplorer outlets={outlets} />

      <section className="mb-16">
        <h2 className="text-xl font-semibold mb-4">Institutional economic concentration</h2>
        <p className="text-sm text-gray-500 mb-6">Same three holders across more issuers. Economic data as of {graph.as_of_economic}.</p>
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
