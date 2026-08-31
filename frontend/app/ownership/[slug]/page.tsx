import Link from "next/link";
import { Metadata } from "next";
import { notFound } from "next/navigation";
import {
  EDGE_LABEL,
  LAYER_LABEL,
  VIA_LABEL,
  clickThrough,
  contributionsFor,
  controlChain,
  controllerHoldings,
  descendantOutlets,
  economicHolders,
  formatPct,
  getEntity,
  getGraph,
  institutionHoldings,
  officersOf,
  orgsOf,
  publicParent,
} from "@/lib/ownership";

export function generateStaticParams() {
  return getGraph().entities.map((e) => ({ slug: e.slug }));
}

export function generateMetadata({ params }: { params: { slug: string } }): Metadata {
  const entity = getEntity(params.slug);
  if (!entity) return { title: "Ownership — Fourth Estate Index" };
  return {
    title: `${entity.name} — ownership — Fourth Estate Index`,
    description: entity.control_summary,
  };
}

export default function OwnershipEntityPage({ params }: { params: { slug: string } }) {
  const entity = getEntity(params.slug);
  if (!entity) notFound();

  const graph = getGraph();
  const chain = entity.is_outlet ? controlChain(entity.slug) : [];
  const parent = entity.is_outlet ? publicParent(entity.slug) : entity.type === "public_issuer" ? entity : undefined;
  const holders = parent ? economicHolders(parent.slug) : economicHolders(entity.slug);
  const instHoldings = entity.type === "institution" ? institutionHoldings(entity.slug) : [];
  const ctrlHoldings = ["family", "individual", "trust"].includes(entity.type)
    ? controllerHoldings(entity.slug)
    : [];
  const kids = descendantOutlets(entity.slug);
  const giving = contributionsFor(entity.slug);
  const power = clickThrough(entity.slug);
  const officers = officersOf(entity.slug);
  const seats = orgsOf(entity.slug);

  return (
    <main className="max-w-4xl mx-auto px-6 py-16">
      <nav className="mb-8 text-sm text-gray-400">
        <Link href="/" className="hover:text-gray-600">Fourth Estate Index</Link>
        <span className="mx-2">›</span>
        <Link href="/ownership" className="hover:text-gray-600">Ownership</Link>
        <span className="mx-2">›</span>
        <span className="text-gray-600">{entity.name}</span>
      </nav>

      <header className="mb-12">
        <p className="text-xs uppercase tracking-wide text-gray-400 mb-2">
          {entity.type.replace("_", " ")}{entity.ticker ? ` · ${entity.ticker}` : ""}
        </p>
        <h1 className="text-3xl font-bold tracking-tight mb-3">{entity.name}</h1>
        <p className="text-gray-600 leading-relaxed">{entity.control_summary}</p>
        {entity.notes && <p className="text-sm text-gray-500 mt-3">{entity.notes}</p>}
        {seats.length > 0 && (
          <p className="text-sm text-gray-500 mt-3">
            {seats.map((s, i) => (
              <span key={s.org.slug}>
                {i > 0 && " · "}
                {s.role} at <Link href={`/ownership/${s.org.slug}`} className="hover:underline">{s.org.name}</Link>
              </span>
            ))}
          </p>
        )}
      </header>

      {chain.length > 1 && (
        <section className="mb-12">
          <h2 className="text-xs font-medium uppercase tracking-wide text-gray-400 mb-4">Control path</h2>
          <ol className="border border-gray-100 rounded-lg divide-y divide-gray-50">
            {chain.map((step, i) => (
              <li key={step.entity.slug} className="px-4 py-3 flex items-baseline gap-3">
                <span className="text-xs text-gray-300 w-4">{i + 1}</span>
                <div>
                  {step.entity.slug === entity.slug ? (
                    <span className="font-medium">{step.entity.name}</span>
                  ) : (
                    <Link href={`/ownership/${step.entity.slug}`} className="font-medium hover:underline">{step.entity.name}</Link>
                  )}
                  {step.via && (
                    <span className="text-sm text-gray-400 ml-2">
                      {EDGE_LABEL[step.via.type]}
                      {step.via.pct_voting != null ? ` · ${formatPct(step.via.pct_voting)} voting` : ""}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}

      {power.length > 0 && (
        <section className="mb-12">
          <h2 className="text-xs font-medium uppercase tracking-wide text-gray-400 mb-2">Click through</h2>
          <p className="text-sm text-gray-500 mb-4">
            People and firms with voting or economic power on this chain. Opening them loads <em>their</em> file — not this page’s FEC.
          </p>
          <ul className="divide-y divide-gray-100 border border-gray-100 rounded-lg">
            {power.map((p) => (
              <li key={p.entity.slug} className="px-4 py-3 flex flex-wrap items-baseline justify-between gap-2">
                <Link href={`/ownership/${p.entity.slug}`} className="font-medium hover:underline">{p.entity.name}</Link>
                <span className="text-xs text-gray-400">{VIA_LABEL[p.via]} · {p.role}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {officers.length > 0 && (
        <section className="mb-12">
          <h2 className="text-xs font-medium uppercase tracking-wide text-gray-400 mb-4">Officers</h2>
          <ul className="divide-y divide-gray-100 border border-gray-100 rounded-lg">
            {officers.map((o) => (
              <li key={o.person.slug} className="px-4 py-3 flex justify-between gap-3">
                <Link href={`/ownership/${o.person.slug}`} className="font-medium hover:underline">{o.person.name}</Link>
                <span className="text-sm text-gray-400">{o.role}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {holders.length > 0 && (
        <section className="mb-12">
          <h2 className="text-xs font-medium uppercase tracking-wide text-gray-400 mb-2">Economic stake</h2>
          <p className="text-sm text-gray-500 mb-4">
            Institutional holders of {parent ? parent.name : entity.name}{parent?.ticker ? ` (${parent.ticker})` : ""}. Not controllers. As of {graph.as_of_economic}. Click a holder to open its officers.
          </p>
          <table className="w-full text-sm border border-gray-100 rounded-lg">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-gray-400 border-b border-gray-100">
                <th className="px-4 py-3 font-medium">Holder</th>
                <th className="px-4 py-3 font-medium">Economic</th>
                <th className="px-4 py-3 font-medium">People</th>
              </tr>
            </thead>
            <tbody>
              {holders.map(({ entity: h, edge }) => {
                const people = officersOf(h.slug);
                return (
                  <tr key={h.slug} className="border-b border-gray-50 last:border-0">
                    <td className="px-4 py-3"><Link href={`/ownership/${h.slug}`} className="hover:underline">{h.name}</Link></td>
                    <td className="px-4 py-3 tabular-nums">{formatPct(edge.pct_economic)}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {people.length === 0
                        ? "—"
                        : people.map((p, i) => (
                            <span key={p.person.slug}>
                              {i > 0 && ", "}
                              <Link href={`/ownership/${p.person.slug}`} className="hover:underline">{p.person.name}</Link>
                            </span>
                          ))}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}

      {instHoldings.length > 0 && (
        <section className="mb-12">
          <h2 className="text-xs font-medium uppercase tracking-wide text-gray-400 mb-2">Media issuers held</h2>
          <ul className="space-y-4">
            {instHoldings.map((h) => (
              <li key={h.issuer.slug} className="border border-gray-100 rounded-lg p-4">
                <div className="flex items-baseline justify-between gap-3">
                  <Link href={`/ownership/${h.issuer.slug}`} className="font-medium hover:underline">
                    {h.issuer.name}{h.issuer.ticker ? ` (${h.issuer.ticker})` : ""}
                  </Link>
                  <span className="tabular-nums font-medium">{formatPct(h.edge.pct_economic)}</span>
                </div>
                {h.outlets.length > 0 && (
                  <p className="text-sm text-gray-500 mt-2">
                    {h.outlets.map((o, i) => (
                      <span key={o.slug}>{i > 0 && ", "}<Link href={`/ownership/${o.slug}`} className="hover:underline">{o.name}</Link></span>
                    ))}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {ctrlHoldings.length > 0 && (
        <section className="mb-12">
          <h2 className="text-xs font-medium uppercase tracking-wide text-gray-400 mb-4">Voting / beneficial control</h2>
          <ul className="space-y-4">
            {ctrlHoldings.map((h) => (
              <li key={h.issuer.slug} className="border border-gray-100 rounded-lg p-4">
                <Link href={`/ownership/${h.issuer.slug}`} className="font-medium hover:underline">
                  {h.issuer.name}{h.issuer.ticker ? ` (${h.issuer.ticker})` : ""}
                </Link>
                <span className="text-sm text-gray-400 ml-2">{EDGE_LABEL[h.edge.type]}</span>
                {h.outlets.length > 0 && (
                  <p className="text-sm text-gray-500 mt-2">
                    {h.outlets.map((o, i) => (
                      <span key={o.slug}>{i > 0 && ", "}<Link href={`/ownership/${o.slug}`} className="hover:underline">{o.name}</Link></span>
                    ))}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {kids.length > 0 && !entity.is_outlet && instHoldings.length === 0 && ctrlHoldings.length === 0 && (
        <section className="mb-12">
          <h2 className="text-xs font-medium uppercase tracking-wide text-gray-400 mb-4">Outlets under this entity</h2>
          <ul className="space-y-2">
            {kids.map((o) => (
              <li key={o.slug}><Link href={`/ownership/${o.slug}`} className="hover:underline">{o.name}</Link></li>
            ))}
          </ul>
        </section>
      )}

      {giving.length > 0 && (
        <section className="mb-12">
          <h2 className="text-xs font-medium uppercase tracking-wide text-gray-400 mb-2">Political money for this entity</h2>
          <p className="text-sm text-gray-500 mb-4">Only the checkbooks that belong here — not every holder on the chain.</p>
          <ul className="space-y-4">
            {giving.map((g) => (
              <li key={`${g.entity}-${g.layer}-${g.cycle}`} className="border border-gray-100 rounded-lg p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2 mb-2">
                  <Link href={`/ownership/${g.entity}`} className="font-medium hover:underline">
                    {getEntity(g.entity)?.name ?? g.entity}
                  </Link>
                  <span className="text-xs text-gray-400">{LAYER_LABEL[g.layer]}</span>
                </div>
                <p className="text-sm text-gray-600 mb-2">{g.summary}</p>
                <p className="text-xs text-gray-400">
                  {g.amount_label} · <a href={g.source_url} className="hover:underline" target="_blank" rel="noreferrer">{g.source_label}</a>
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <footer className="pt-8 border-t border-gray-100 text-sm text-gray-400">
        <p>Ownership is a separate layer from journalist SPJ scores. <Link href="/ownership" className="underline">All ownership →</Link></p>
      </footer>
    </main>
  );
}
