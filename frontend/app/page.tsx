import Link from "next/link";
import { api } from "@/lib/api";
import JournalistTable from "./JournalistTable";

export default async function Home() {
  let journalists: JournalistSummary[] = [];
  try {
    journalists = await api.journalists.list();
    // Sort: scored journalists first (highest score first), unscored last
    journalists.sort((a, b) => {
      if (a.composite_score === null && b.composite_score === null) return 0;
      if (a.composite_score === null) return 1;
      if (b.composite_score === null) return -1;
      return b.composite_score - a.composite_score;
    });
  } catch {
    // API not yet running — show empty state
  }

  return (
    <main className="max-w-4xl mx-auto px-6 py-16">
      <header className="mb-16">
        <h1 className="text-4xl font-bold tracking-tight mb-4">
          Fourth Estate Index
        </h1>
        <p className="text-xl text-gray-600 mb-6 leading-relaxed">
          In 1968, 27 million people watched Walter Cronkite every night to get
          it straight. He was the most trusted man in America.
        </p>
        <p className="text-lg text-gray-600 mb-6 leading-relaxed">
          That feels like an old-timey notion now. But journalists have more
          scale than ever — their voices reach further, their influence runs
          deeper, and the information ecosystem they shape has never mattered
          more.
        </p>
        <p className="text-lg text-gray-600 leading-relaxed">
          What better moment to build transparency into the system?
        </p>
      </header>

      <section className="mb-12">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-semibold">Journalists</h2>
          <Link href="/methodology" className="text-sm text-blue-600 hover:underline">
            How scoring works →
          </Link>
        </div>

        {journalists.length === 0 ? (
          <div className="border border-gray-200 rounded-lg p-8 text-center text-gray-500">
            <p className="mb-2 font-medium">Data collection in progress.</p>
            <p className="text-sm">
              Profiles will appear here as data is gathered and verified.
              No scores are published until they are defensible.
            </p>
          </div>
        ) : (
          <JournalistTable journalists={journalists} />
        )}
      </section>

      <footer className="pt-8 border-t border-gray-100 text-sm text-gray-400">
        <p>
          Scoring methodology grounded in the{" "}
          <a
            href="https://www.spj.org/ethicscode.asp"
            className="underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            SPJ Code of Ethics
          </a>
          . Built and maintained by one person.{" "}
          <Link href="/methodology" className="underline">
            Full methodology →
          </Link>
        </p>
      </footer>
    </main>
  );
}
