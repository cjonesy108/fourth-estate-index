import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Fourth Estate Index",
  description: "Journalistic integrity scoring grounded in the SPJ Code of Ethics.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-white">
        <nav className="border-b border-gray-100 px-6 py-4">
          <div className="max-w-4xl mx-auto flex items-center justify-between">
            <Link href="/" className="font-semibold tracking-tight hover:opacity-70">
              Fourth Estate Index
            </Link>
            <div className="flex items-center gap-6">
              <Link href="/ownership" className="text-sm text-gray-500 hover:text-gray-900">
                Ownership
              </Link>
              <Link href="/methodology" className="text-sm text-gray-500 hover:text-gray-900">
                Methodology
              </Link>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
