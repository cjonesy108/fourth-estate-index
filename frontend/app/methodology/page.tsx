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
          <a
            href="https://www.spj.org/ethicscode.asp"
            className="underline text-blue-600"
            target="_blank"
            rel="noopener noreferrer"
          >
            SPJ Code of Ethics
          </a>
          , published by the Society of Professional Journalists. We didn&apos;t
          write it. The profession did. These are the standards journalists
          themselves have adopted as their ethical framework.
        </p>
        <p className="text-gray-600 leading-relaxed">
          The SPJ Code has four pillars. Our scoring maps directly to them.
        </p>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-6">The Four Pillars</h2>
        {[
          {
            number: 1,
            name: "Seek Truth and Report It",
            weight: "30%",
            description:
              "Accuracy is the cornerstone. We measure headline fidelity (does the headline match the body?), attribution patterns (are claims sourced?), and appropriate hedging language for unconfirmed facts.",
          },
          {
            number: 2,
            name: "Minimize Harm",
            weight: "20%",
            description:
              "We analyze language patterns across the corpus for dehumanizing or inflammatory word choice, and measure whether tone shifts significantly when covering politically opposed subjects.",
          },
          {
            number: 3,
            name: "Act Independently",
            weight: "30%",
            description:
              "Independence means avoiding conflicts of interest. We check FEC records for political contributions and analyze source diversity across the corpus. Social media posts are reviewed for advocacy that may conflict with independent reporting.",
          },
          {
            number: 4,
            name: "Be Accountable and Transparent",
            weight: "20%",
            description:
              "Accountability is demonstrated through the corrections record — how often, how fast, and how serious. This is the most factual dimension we measure.",
          },
        ].map((pillar) => (
          <div key={pillar.number} className="mb-6 border-l-4 border-gray-200 pl-5">
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
          No score is published until minimum corpus thresholds are met. Each
          dimension has a minimum article count before it can be scored. If a
          dimension doesn&apos;t have enough data, it is marked{" "}
          <em>insufficient data</em> — not zero. A zero score means the
          journalist failed the dimension. Insufficient data means we can&apos;t
          say yet.
        </p>
        <p className="text-gray-600 leading-relaxed">
          The composite score is not calculated until all four pillars have at
          least one scored dimension. Partial data produces a partial profile,
          never a composite score.
        </p>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-4">Why The Guardian First</h2>
        <p className="text-gray-600 leading-relaxed">
          The Guardian provides a free, full-text API through their Open
          Platform program. That makes it the right starting point for a solo
          project with no budget. We&apos;re transparent about this constraint
          because transparency is the point. As the project grows, additional
          publications will be added. The methodology doesn&apos;t change —
          only the coverage expands.
        </p>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-4">AI Analysis</h2>
        <p className="text-gray-600 leading-relaxed mb-4">
          Scoring is performed by Claude (Anthropic), version claude-sonnet-4-6.
          Every analysis run is tagged with the model version and prompt version.
          Every citation links to a verbatim sentence in the stored corpus —
          no inference beyond what is written, no hallucinated sources.
        </p>
        <p className="text-gray-600 leading-relaxed">
          The prompts used for each analysis dimension are published in full.
          You can evaluate them. You can disagree with them. That&apos;s the point.
        </p>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-4">Appeals & Context</h2>
        <p className="text-gray-600 leading-relaxed">
          Any journalist scored by this system can submit context or appeal a
          specific dimension. Context submissions are published unedited
          alongside the profile. Appeals citing data errors are investigated —
          if an error is confirmed, the pipeline re-runs. Scores are not changed
          by context submissions, only by confirmed data errors.
        </p>
      </section>

      <section>
        <h2 className="text-2xl font-semibold mb-4">About This Project</h2>
        <p className="text-gray-600 leading-relaxed">
          The Fourth Estate Index is built and maintained by one person — a
          former journalist who started this project because the question
          wouldn&apos;t leave him alone: if the SPJ Code is the profession&apos;s
          standard, why isn&apos;t anyone measuring against it systematically?
          This is that attempt. The methodology is open. The data is sourced.
          The conclusions are the AI&apos;s, not mine.
        </p>
      </section>
    </main>
  );
}
