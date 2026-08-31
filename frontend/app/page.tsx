import Link from "next/link";
import { api } from "@/lib/api";
import { JournalistSummary } from "@/lib/types";
import { directoryMeta, mergeJournalistList } from "@/lib/directory";
import { letterGrade, scoreToPct } from "@/lib/score";
import JournalistTable from "./JournalistTable";
import GradeSeal from "./components/GradeSeal";
import Rule from "./components/Rule";

const PILLARS = [
  { n: "01", name: "Seek Truth & Report It", blurb: "Accuracy, verification, and sourcing. Does the reporting hold up to the record?" },
  { n: "02", name: "Minimize Harm", blurb: "Compassion in coverage. Are subjects and the vulnerable treated with care?" },
  { n: "03", name: "Act Independently", blurb: "Freedom from conflict — no favors, no undisclosed ties, no paid influence." },
  { n: "04", name: "Be Accountable", blurb: "Corrections, transparency of method, and answering for mistakes in public." },
];

export default async function Home() {
  let apiRows: JournalistSummary[] | null = null;
  try {
    apiRows = await api.journalists.list();
  } catch {
    apiRows = null;
  }

  const journalists = mergeJournalistList(apiRows);
  const meta = directoryMeta();
  const leaders = journalists.filter((j) => j.composite_score !== null).slice(0, 3);

  return (
    <main>
      <section style={{ background: "var(--paper-100)", borderBottom: "1px solid var(--border-hairline)" }}>
        <div className="max-w-5xl mx-auto px-6 py-16 text-center">
          <p className="uppercase mb-5" style={{ fontFamily: "var(--font-sans)", fontSize: 13, letterSpacing: "var(--tracking-eyebrow)", color: "var(--red-700)", fontWeight: 700 }}>
            The free press, held to its own code
          </p>
          <h1 className="mx-auto max-w-3xl" style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "clamp(2.4rem, 6vw, 4.4rem)", lineHeight: 0.98, color: "var(--navy-800)" }}>
            Every byline, graded against the code it swore to uphold.
          </h1>
          <p className="mx-auto max-w-xl mt-6" style={{ fontFamily: "var(--font-serif)", fontSize: "1.2rem", lineHeight: 1.6 }}>
            The Fourth Estate Index scores journalists against the four pillars of the Society of Professional Journalists Code of Ethics.
          </p>
          <div className="flex gap-3 justify-center mt-8">
            <a href="#index" className="px-5 py-2.5 text-sm font-medium" style={{ background: "var(--navy-800)", color: "var(--paper-100)" }}>
              View the index
            </a>
            <Link href="/methodology" className="px-5 py-2.5 text-sm font-medium" style={{ border: "1px solid var(--navy-800)", color: "var(--navy-800)" }}>
              How scoring works
            </Link>
          </div>
          <div className="max-w-sm mx-auto mt-12">
            <Rule />
          </div>
        </div>
      </section>

      {leaders.length > 0 && (
        <section className="max-w-5xl mx-auto px-6 py-14">
          <p className="uppercase mb-2" style={{ fontFamily: "var(--font-sans)", fontSize: 13, letterSpacing: "var(--tracking-eyebrow)", color: "var(--red-700)", fontWeight: 700 }}>
            Highest integrity on record
          </p>
          <h2 className="mb-8" style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "2rem", color: "var(--navy-800)" }}>
            Leaders
          </h2>
          <div className="grid gap-5 md:grid-cols-3">
            {leaders.map((j) => (
              <Link key={j.slug} href={`/journalist/${j.slug}`} className="block p-5" style={{ background: "var(--surface-card)", border: "1px solid var(--border-default)", boxShadow: "var(--shadow-sm)" }}>
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <p style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: "1.25rem", color: "var(--text-heading)" }}>{j.full_name}</p>
                    <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>{j.primary_outlet}{j.beat ? ` · ${j.beat}` : ""}</p>
                  </div>
                  <GradeSeal score={j.composite_score} size={72} />
                </div>
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                  Composite {scoreToPct(j.composite_score)} · Grade {letterGrade(j.composite_score)}
                </p>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section style={{ background: "var(--navy-900)", color: "var(--paper-100)" }}>
        <div className="max-w-5xl mx-auto px-6 py-14">
          <p className="text-center uppercase mb-3" style={{ letterSpacing: "var(--tracking-eyebrow)", color: "var(--navy-300)", fontSize: 13, fontWeight: 700 }}>The rubric</p>
          <h2 className="text-center mb-6" style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "2.2rem" }}>Four pillars of the SPJ Code</h2>
          <div className="max-w-xs mx-auto mb-10">
            <Rule faint />
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {PILLARS.map((p) => (
              <div key={p.n} style={{ borderTop: "2px solid var(--navy-400)", paddingTop: 16 }}>
                <p className="mb-2" style={{ fontFamily: "var(--font-serif)", fontWeight: 700, fontSize: "1.6rem", color: "var(--navy-300)" }}>{p.n}</p>
                <p className="mb-2" style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: "1.05rem" }}>{p.name}</p>
                <p className="text-sm leading-relaxed" style={{ color: "var(--navy-200)" }}>{p.blurb}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="index" className="max-w-5xl mx-auto px-6 py-14">
        <div className="flex items-end justify-between mb-6">
          <div>
            <p className="uppercase mb-2" style={{ fontFamily: "var(--font-sans)", fontSize: 13, letterSpacing: "var(--tracking-eyebrow)", color: "var(--red-700)", fontWeight: 700 }}>
              Full standings
            </p>
            <h2 style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "2rem", color: "var(--navy-800)" }}>The Index</h2>
          </div>
          <Link href="/methodology" className="text-sm" style={{ color: "var(--text-link)" }}>
            How scoring works →
          </Link>
        </div>
        <div style={{ background: "var(--surface-card)", border: "1px solid var(--border-default)" }}>
          <div className="p-5">
            <JournalistTable journalists={journalists} />
          </div>
        </div>
        <p className="text-xs mt-6" style={{ color: "var(--text-faint)" }}>
          Directory v{meta.version} · {meta.as_of}. Pending rows are listed journalists whose corpus is still being collected — not a score of zero.
        </p>
      </section>
    </main>
  );
}
