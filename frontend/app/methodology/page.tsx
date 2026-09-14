export default async function MethodologyPage() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-16">
      <header className="mb-12">
        <h1 className="text-4xl font-bold mb-4">Methodology</h1>
        <p className="text-gray-600 leading-relaxed">
          Scores follow the SPJ Code of Ethics. The Code is a guide, not a statute.
          We measure the lines that leave a public trace. Missing checks are blank,
          not 100.
        </p>
      </header>

      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-4">Partial rubric (current)</h2>
        <p className="text-gray-600 leading-relaxed mb-4">
          A pillar publishes only when scored sub-points cover more than half of
          that pillar's weight. A composite publishes only when all four pillars
          clear that bar. Running language patterns alone cannot mint a Minimize
          Harm score of 100. An empty corrections file cannot mint Accountability
          of 100.
        </p>
        <ul className="text-gray-600 text-sm leading-relaxed list-disc pl-5 space-y-2">
          <li>Running now: headline fidelity, attribution, language patterns, source diversity.</li>
          <li>Defined, not yet in the warehouse loop: hedging, sentiment differential, FEC-into-P3, social advocacy.</li>
          <li>Corrections score only after a corrections ingest for that outlet.</li>
        </ul>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-4">Show the work</h2>
        <p className="text-gray-600 leading-relaxed mb-4">
          Each published flag must quote a sentence that exists in the stored
          article body and link that story. The model can propose a flag. The
          citation check drops it if the quote is not in the corpus. No quote,
          no movement.
        </p>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-4">The Standard</h2>
        <p className="text-gray-600 leading-relaxed mb-4">
          The scoring standard is the{" "}
          <a href="https://www.spj.org/ethicscode.asp" className="underline text-blue-600" target="_blank" rel="noopener noreferrer">
            SPJ Code of Ethics
          </a>
          . We did not write it. The profession did.
        </p>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-6">The Four Pillars</h2>
        {[
          { name: "Seek Truth and Report It", weight: "30%", description: "Headline fidelity, attribution, hedging, and (when visible) whether subjects of accusations were given a chance to respond." },
          { name: "Minimize Harm", weight: "20%", description: "Language patterns and sentiment differential across politically opposed subjects." },
          { name: "Act Independently", weight: "30%", description: "FEC records, source diversity, and labeled social-media advocacy. Ownership of the outlet is shown separately." },
          { name: "Be Accountable", weight: "20%", description: "Corrections frequency, velocity, and severity — only after corrections have been ingested." },
        ].map((pillar) => (
          <div key={pillar.name} className="mb-6 border-l-4 border-gray-200 pl-5">
            <div className="flex items-baseline gap-3 mb-2">
              <h3 className="text-lg font-semibold">{pillar.name}</h3>
              <span className="text-sm text-gray-400">{pillar.weight} of composite</span>
            </div>
            <p className="text-gray-600 text-sm leading-relaxed">{pillar.description}</p>
          </div>
        ))}
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-4">Data Sufficiency</h2>
        <p className="text-gray-600 leading-relaxed mb-4">
          No score is published until minimum corpus thresholds are met. Missing
          data is <em>insufficient data</em> — not zero, and not a perfect score.
        </p>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-4">The directory and access levels</h2>
        <p className="text-gray-600 leading-relaxed mb-4">
          A journalist can be listed before we have a full-text corpus. Scores
          overlay from the API when a scored corpus exists.
        </p>
        <ul className="text-gray-600 text-sm leading-relaxed list-disc pl-5 mb-4 space-y-2">
          <li><strong>full</strong> — licensed or openly published body. Eligible for every scoring dimension.</li>
          <li><strong>excerpt</strong> — publisher-provided lede or RSS description. Counts as work product.</li>
          <li><strong>metadata</strong> — headline, URL, date, section, byline. Not used for attribution, language, or source-diversity scoring.</li>
        </ul>
        <p className="text-gray-600 leading-relaxed">
          We do not log into paywalls or use archive mirrors.
        </p>
      </section>

      <section>
        <h2 className="text-2xl font-semibold mb-4">About This Project</h2>
        <p className="text-gray-600 leading-relaxed">
          Built and maintained by one person. The methodology is open. The data
          is sourced. Model output is checked against the stored text.
        </p>
      </section>
    </main>
  );
}
