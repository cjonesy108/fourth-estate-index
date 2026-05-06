import { notFound } from "next/navigation";
import { api } from "@/lib/api";

export default async function JournalistPage({
  params,
}: {
  params: { slug: string };
}) {
  let profile;
  try {
    profile = await api.journalists.get(params.slug);
  } catch {
    notFound();
  }

  const { pillar_scores: scores } = profile;

  return (
    <main className="max-w-3xl mx-auto px-6 py-16">
      {/* 1. Header */}
      <header className="mb-12">
        <p className="text-sm text-gray-400 mb-2">{profile.primary_outlet}</p>
        <h1 className="text-4xl font-bold mb-1">{profile.full_name}</h1>
        {profile.beat && <p className="text-gray-500 mb-4">{profile.beat}</p>}
        <div className="text-xs text-gray-400 space-y-1">
          {profile.corpus_size && (
            <p>
              {profile.corpus_size} articles analyzed ·{" "}
              {profile.corpus_start?.slice(0, 10)} to{" "}
              {profile.corpus_end?.slice(0, 10)}
            </p>
          )}
          {profile.methodology_version && (
            <p>Methodology v{profile.methodology_version}</p>
          )}
        </div>
      </header>

      {/* 2. Scorecard */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">FEI Score</h2>
        {scores ? (
          <div className="border border-gray-200 rounded-lg p-6">
            <div className="grid grid-cols-2 gap-4 mb-6">
              {[
                { label: "Seek Truth & Report It", value: scores.pillar_1_score },
                { label: "Minimize Harm", value: scores.pillar_2_score },
                { label: "Act Independently", value: scores.pillar_3_score },
                { label: "Be Accountable", value: scores.pillar_4_score },
              ].map(({ label, value }) => (
                <div key={label} className="border border-gray-100 rounded p-3">
                  <p className="text-xs text-gray-500 mb-1">{label}</p>
                  {value !== null ? (
                    <p className="text-2xl font-bold">{value.toFixed(1)}</p>
                  ) : (
                    <p className="text-sm text-gray-400 italic">Insufficient data</p>
                  )}
                </div>
              ))}
            </div>
            {scores.composite_score !== null ? (
              <div className="text-center">
                <p className="text-xs text-gray-400 mb-1">Composite Score</p>
                <p className="text-5xl font-bold">{scores.composite_score.toFixed(1)}</p>
              </div>
            ) : (
              <p className="text-sm text-gray-400 italic text-center">
                Composite score pending — not all pillars have sufficient data yet.
              </p>
            )}
          </div>
        ) : (
          <div className="border border-gray-200 rounded-lg p-6 text-center text-gray-400">
            <p className="font-medium mb-1">Data collection in progress</p>
            <p className="text-sm">
              No score is published until minimum data thresholds are met.
            </p>
          </div>
        )}
      </section>

      {/* 3. Financial Disclosures */}
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

      {/* 4. Corrections Record */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Corrections Record</h2>
        {profile.corrections.length > 0 ? (
          <div className="space-y-4">
            {profile.corrections.map((c) => (
              <div key={c.id} className="border-l-2 border-gray-200 pl-4">
                <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                  {c.corrected_at && <span>{c.corrected_at.slice(0, 10)}</span>}
                  {c.correction_type && (
                    <span className="border border-gray-200 rounded px-1">
                      {c.correction_type}
                    </span>
                  )}
                  {c.days_to_correction && (
                    <span>{c.days_to_correction}d to correction</span>
                  )}
                </div>
                <p className="text-sm">{c.correction_text}</p>
                {c.correction_url && (
                  <a
                    href={c.correction_url}
                    className="text-xs text-blue-600 underline"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Source ↗
                  </a>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">No corrections on record.</p>
        )}
      </section>

      {/* 5. Context & Appeals */}
      {profile.appeals.filter((a) => a.published).length > 0 && (
        <section className="mb-12">
          <h2 className="text-xl font-semibold mb-4">Context & Appeals</h2>
          <div className="space-y-4">
            {profile.appeals
              .filter((a) => a.published)
              .map((a) => (
                <div key={a.id} className="bg-gray-50 rounded-lg p-4">
                  <div className="text-xs text-gray-400 mb-2">
                    Submitted {a.submitted_at.slice(0, 10)}
                    {a.outcome && ` · Outcome: ${a.outcome}`}
                  </div>
                  <p className="text-sm">{a.submission_text}</p>
                  {a.outcome_notes && (
                    <p className="text-xs text-gray-500 mt-2">{a.outcome_notes}</p>
                  )}
                </div>
              ))}
          </div>
        </section>
      )}
    </main>
  );
}
