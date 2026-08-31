import Link from "next/link";
import { Metadata } from "next";
import {
  LAYER_LABEL,
  allContributions,
  controlChain,
  formatPct,
  getContributionsMeta,
  getEntity,
  getGraph,
  institutionHoldings,
  listControllers,
  listInstitutions,
  listOutlets,
  publicParent,
} from "@/lib/ownership";

export const metadata: Metadata = {
  title: "Who owns the media — Fourth Estate Index",
  description:
    "Voting control, economic stakes, and controller political giving across major news outlets.",
};

function ControllerLabel({ slug }: { slug: string }) {
  const chain = controlChain(slug);
  const controller = [...chain].reverse().find((c) =>
    ["family", "individual", "trust"].includes(c.entity.type)
  );
  const parent = publicParent(slug);
  if (controller) return <>{controller.entity.name}</>;
  if (parent) return <>Dispersed ({parent.ticker})</>;
  return <>—</>;
}

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
          Two facts, kept apart on purpose. <strong>Voting control</strong> is
          who can fire the editor. <strong>Economic stake</strong> is who has
          capital sitting in the parent company — usually index funds, usually
          without a board seat.
        </p>
        <p className="text-gray-600 leading-relaxed">
          Political money is a third column, attached only to the entity that
          wrote the check — a controller or a parent PAC, never an index fund
          and never “CNN donated.”
        </p>
      </header>

      <section className="mb-16">
        <h2 className="text-xl font-semibold mb-4">Outlets</h2>
        <p className="text-sm text-gray-500 mb-6">
          {outlets.length} outlets in the seed. Control path is the default.
        </p>
        <div className="overflow-x-auto border border-gray-100 rounded-lg">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-gray-400 border-b border-gray-100">
                <th className="px-4 py-3 font-medium">Outlet</th>
                <th className="px-4 py-3 font-medium">Voting control</th>
                <th className="px-4 py-3 font-medium">Public parent</th>
              </tr>
            </thead>
            <tbody>
              {outlets.map((o) => {
                const parent = publicParent(o.slug);
                return (
                  <tr key={o.slug} className="border-b border-gray-50 last:border-0">
                    <td className="px-4 py-3">
                      <Link href={`/ownership/${o.slug}`} className="font-medium hover:underline">{o.name}</Link>
                    </td>
                    <td className="px-4 py-3 text-gray-600"><ControllerLabel slug={o.slug} /></td>
                    <td className="px-4 py-3 text-gray-500">
                      {parent ? (
                        <Link href={`/ownership/${parent.slug}`} className="hover:underline">
                          {parent.name}{parent.ticker ? ` (${parent.ticker})` : ""}
                        </Link>
                      ) : (
                        "Private / trust / nonprofit"
                      )}
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
        <p className="text-sm text-gray-500 mb-6">
          Same holders, many issuers. No recursion into who owns the funds. Economic data as of {graph.as_of_economic}.
        </p>
        <div className="space-y-8">
          {institutions.map((inst) => {
            const holdings = institutionHoldings(inst.slug);
            return (
              <div key={inst.slug} className="border border-gray-100 rounded-lg p-5">
                <div className="flex items-baseline justify-between gap-4 mb-4">
                  <Link href={`/ownership/${inst.slug}`} className="text-lg font-semibold hover:underline">{inst.name}</Link>
                  <span className="text-xs text-gray-400">{holdings.length} media issuer{holdings.length === 1 ? "" : "s"} in seed</span>
                </div>
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
                          <span className="text-gray-400">— {h.outlets.map((o) => o.name).join(", ")}</span>
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
        <p className="text-sm text-gray-500 mb-6">Families, individuals, and trusts with voting or beneficial control. Not index funds.</p>
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
              <li key={`${g.entity}-${g.cycle}`} className="border border-gray-100 rounded-lg p-4">
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
