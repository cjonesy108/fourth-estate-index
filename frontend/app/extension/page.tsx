import Link from "next/link";

const ZIP =
  "https://github.com/cjonesy108/fourth-estate-index/archive/refs/heads/main.zip";
const SOURCE =
  "https://github.com/cjonesy108/fourth-estate-index/tree/main/extension";

export const metadata = {
  title: "Browser extension — Fourth Estate Index",
  description:
    "See the Fourth Estate Index article and journalist scores on the page you are reading.",
};

export default function ExtensionPage() {
  return (
    <main className="max-w-4xl mx-auto px-6 py-16">
      <p className="text-sm uppercase tracking-widest text-gray-400 mb-3">
        Browser extension
      </p>
      <h1 className="text-4xl font-bold tracking-tight mb-4">
        Scores on the article you are reading
      </h1>
      <p className="text-lg text-gray-600 leading-relaxed mb-6">
        The chip shows two things and will not invent either of them: a score
        for this URL if it is in the corpus, and the journalist&apos;s corpus
        score if that byline is in the directory. Pending is not a zero.
      </p>
      <p className="text-gray-600 leading-relaxed mb-10">
        Chrome and Edge do not allow a website to install an extension with one
        click. Until this is on the Chrome Web Store, you load it unpacked from
        the download below. That is the same method we used to test it.
      </p>

      <section className="border border-gray-200 rounded-lg p-6 mb-12">
        <h2 className="text-xl font-semibold mb-4">Install in Chrome or Edge</h2>
        <ol className="list-decimal pl-5 space-y-3 text-gray-700 leading-relaxed">
          <li>
            <a href={ZIP} className="text-blue-600 hover:underline">
              Download the repository ZIP
            </a>
            . Unzip it. Open the inner folder named{" "}
            <code className="text-sm bg-gray-100 px-1 rounded">extension</code>
            — the one that contains{" "}
            <code className="text-sm bg-gray-100 px-1 rounded">manifest.json</code>.
          </li>
          <li>
            Go to{" "}
            <code className="text-sm bg-gray-100 px-1 rounded">chrome://extensions</code>{" "}
            (or{" "}
            <code className="text-sm bg-gray-100 px-1 rounded">edge://extensions</code>).
          </li>
          <li>Turn on Developer mode (top right).</li>
          <li>
            Click <strong>Load unpacked</strong> and select that{" "}
            <code className="text-sm bg-gray-100 px-1 rounded">extension</code> folder.
          </li>
          <li>
            Open any news article. A small FEI chip appears lower-right. Click
            it.
          </li>
        </ol>
        <p className="mt-6">
          <a
            href={ZIP}
            className="inline-block bg-gray-900 text-white text-sm font-medium px-4 py-2 rounded hover:bg-gray-700"
          >
            Download ZIP
          </a>
          <a
            href={SOURCE}
            className="inline-block ml-4 text-sm text-gray-500 hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            View source on GitHub →
          </a>
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-3">What it will and will not show</h2>
        <ul className="list-disc pl-5 space-y-2 text-gray-700 leading-relaxed">
          <li>
            Article score only after that URL is ingested and scored. Otherwise
            an em dash.
          </li>
          <li>
            Journalist score only when the byline matches a listed person with a
            published corpus composite. Otherwise listed-and-pending, or not in
            the directory.
          </li>
          <li>
            It reads the page title, byline, and URL. It does not send article
            body text to a model and it does not log into paywalls.
          </li>
        </ul>
      </section>

      <p className="text-sm text-gray-500">
        Chrome Web Store listing is not live yet. When it is, this page will
        point at the store instead of Developer mode.{" "}
        <Link href="/methodology" className="underline">
          Scoring methodology →
        </Link>
      </p>
    </main>
  );
}
