export default async function MethodologyPage() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-16">
      <p className="uppercase mb-3" style={{ fontFamily: "var(--font-sans)", fontSize: 13, letterSpacing: "var(--tracking-eyebrow)", color: "var(--red-700)", fontWeight: 700 }}>
        The rubric
      </p>
      <h1 className="mb-4" style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "2.6rem", color: "var(--navy-800)" }}>Methodology</h1>
      <p className="leading-relaxed mb-12" style={{ fontFamily: "var(--font-serif)", fontSize: "1.15rem" }}>
        Every score on the Fourth Estate Index is produced by the system described here. Nothing else enters the scoring pipeline. No human editorial judgment. No exceptions.
      </p>

      <section className="mb-10">
        <h2 className="text-2xl mb-4" style={{ fontFamily: "var(--font-serif)", fontWeight: 600, color: "var(--navy-800)" }}>The standard</h2>
        <p className="leading-relaxed" style={{ color: "var(--text-body)" }}>
          The scoring standard is the{" "}
          <a href="https://www.spj.org/ethicscode.asp" style={{ color: "var(--text-link)" }} target="_blank" rel="noopener noreferrer">SPJ Code of Ethics</a>, published by the Society of Professional Journalists. We did not write it. The profession did.
        </p>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl mb-6" style={{ fontFamily: "var(--font-serif)", fontWeight: 600, color: "var(--navy-800)" }}>The four pillars</h2>
        {[
          { name: "Seek Truth and Report It", weight: "30%", description: "Headline fidelity, attribution patterns, and hedging language." },
          { name: "Minimize Harm", weight: "20%", description: "Language patterns and sentiment differential across subjects." },
          { name: "Act Independently", weight: "30%", description: "FEC records, source diversity, and social-media advocacy." },
          { name: "Be Accountable", weight: "20%", description: "Corrections frequency, velocity, and severity." },
        ].map((pillar) => (
          <div key={pillar.name} className="mb-6 pl-5" style={{ borderLeft: "2px solid var(--navy-800)" }}>
            <div className="flex items-baseline gap-3 mb-2">
              <h3 className="text-lg" style={{ fontFamily: "var(--font-serif)", fontWeight: 600 }}>{pillar.name}</h3>
              <span className="text-sm" style={{ color: "var(--text-muted)" }}>{pillar.weight} of composite</span>
            </div>
            <p className="text-sm leading-relaxed" style={{ color: "var(--text-body)" }}>{pillar.description}</p>
          </div>
        ))}
      </section>

      <section className="mb-10">
        <h2 className="text-2xl mb-4" style={{ fontFamily: "var(--font-serif)", fontWeight: 600, color: "var(--navy-800)" }}>Data sufficiency</h2>
        <p className="leading-relaxed">No score is published until minimum corpus thresholds are met. Missing data is insufficient data — not zero.</p>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl mb-4" style={{ fontFamily: "var(--font-serif)", fontWeight: 600, color: "var(--navy-800)" }}>The directory and access levels</h2>
        <p className="leading-relaxed mb-4">A journalist can be listed before we have a full-text corpus. Scores overlay from the API when a scored corpus exists.</p>
        <ul className="text-sm leading-relaxed list-disc pl-5 space-y-2">
          <li><strong>full</strong> — licensed or openly published body. Eligible for every scoring dimension.</li>
          <li><strong>excerpt</strong> — publisher-provided lede or RSS description. Counts as work product.</li>
          <li><strong>metadata</strong> — headline, URL, date, section, byline. Counts toward body of work. Not used for attribution, language, or source-diversity scoring.</li>
        </ul>
      </section>

      <section>
        <h2 className="text-2xl mb-4" style={{ fontFamily: "var(--font-serif)", fontWeight: 600, color: "var(--navy-800)" }}>About this project</h2>
        <p className="leading-relaxed">Built and maintained by one person. The methodology is open. The data is sourced. The conclusions are the system&apos;s, not a newsroom&apos;s.</p>
      </section>
    </main>
  );
}
