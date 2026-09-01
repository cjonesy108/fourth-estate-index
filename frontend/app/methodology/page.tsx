export default async function MethodologyPage() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-16">
      <header className="mb-12">
        <h1 className="text-4xl font-bold mb-4">Methodology</h1>
        <p className="text-gray-600 leading-relaxed">
          Every score on the Fourth Estate Index is produced by the system
          described here. Nothing else enters the scoring pipeline. No human
          editorial judgment. No exceptions.
        </p>
      </header>

      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-4">The Standard</h2>
        <p className="text-gray-600 leading-relaxed mb-4">
          The scoring standard is the{" "}
          <a href="https://www.spj.org/ethicscode.asp" className="underline text-blue-600" target="_blank" rel="noopener noreferrer">
            SPJ Code of Ethics
          </a>
          , published by the Society of Professional Journalists. We didn&apos;t
          write it. The profession did.
        </p>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-6">The Four Pillars</h2>
        {[
          { name: "Seek Truth and Report It", weight: "30%", description: "Headline fidelity, attribution patterns, and hedging language." },
          { name: "Minimize Harm", weight: "20%", description: "Language patterns and sentiment differential across subjects." },
          { name: "Act Independently", weight: "30%", description: "FEC records, source diversity, and social-media advocacy." },
          { name: "Be Accountable", weight: "20%", description: "Corrections frequency, velocity, and severity." },
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
          data is <em>insufficient data</em> — not zero.
        </p>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-4">The directory and access levels</h2>
        <p className="text-gray-600 leading-relaxed mb-4">
          A journalist can be listed before we have a full-text corpus. The public
          roster lives in <code className="text-sm bg-gray-50 px-1 rounded">frontend/data/directory.json</code>.
          Scores overlay from the API when a scored corpus exists.
        </p>
        <ul className="text-gray-600 text-sm leading-relaxed list-disc pl-5 mb-4 space-y-2">
          <li><strong>full</strong> — licensed or openly published body. Eligible for every scoring dimension.</li>
          <li><strong>excerpt</strong> — publisher-provided lede or RSS description. Counts as work product.</li>
          <li><strong>metadata</strong> — headline, URL, date, section, byline. Counts toward body of work. Not used for attribution, language, or source-diversity scoring.</li>
        </ul>
        <p className="text-gray-600 leading-relaxed">
          We do not log into paywalls or use archive mirrors. Full-text scoring
          expands through open APIs, public nonprofit newsrooms, and licensed
          databases — not by breaking walls.
        </p>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-4">What a score is computed from</h2>
        <p className="text-gray-600 leading-relaxed mb-4">
          Each profile now separates three things that used to look like one number:
          the journalist listed in the directory, the articles stored in the warehouse,
          and the smaller sample actually sent to the scorer.
        </p>
        <p className="text-gray-600 leading-relaxed mb-4">
          Headline checks use up to the 50 most recent full-text stories. Attribution
          uses up to 25. Language patterns use up to 30. Source diversity uses up to 15.
          If a reporter has 400 Guardian pieces stored, the composite is still a recent
          sample — and the profile says so.
        </p>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-4">Why The Guardian First</h2>
        <p className="text-gray-600 leading-relaxed">
          The Guardian Open Platform gives licensed full text. Next full-text
          outlets are public nonprofit newsrooms (ProPublica, The Texas Tribune,
          The Markup, NPR) before prestige paywalls.
        </p>
      </section>

      <section>
        <h2 className="text-2xl font-semibold mb-4">About This Project</h2>
        <p className="text-gray-600 leading-relaxed">
          Built and maintained by one person. The methodology is open. The data
          is sourced. The conclusions are the AI&apos;s, not mine.
        </p>
      </section>
    </main>
  );
}
