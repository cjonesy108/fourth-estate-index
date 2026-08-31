"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MARK_SRC } from "./brandAssets";

const LINKS = [
  { href: "/", label: "Index" },
  { href: "/ownership", label: "Ownership" },
  { href: "/methodology", label: "Methodology" },
];

export default function SiteHeader() {
  const path = usePathname();
  return (
    <header style={{ background: "var(--paper-100)", borderBottom: "2px solid var(--navy-800)" }}>
      <div style={{ borderBottom: "1px solid var(--border-hairline)", background: "var(--paper-200)" }}>
        <div className="max-w-5xl mx-auto px-6 py-1.5 flex justify-between text-[11px] uppercase tracking-wide" style={{ color: "var(--text-muted)", fontFamily: "var(--font-sans)" }}>
          <span>A Democracy Labs project</span>
          <span>Vol. I · 2026</span>
        </div>
      </div>
      <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between gap-6">
        <Link href="/" className="flex items-center gap-3 min-w-0">
          <img src={MARK_SRC} alt="4th Estate Index" width={52} height={55} style={{ height: 52, width: "auto" }} />
          <span className="flex flex-col leading-none">
            <span style={{ fontFamily: "var(--font-masthead)", letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--navy-800)", fontSize: 13, fontWeight: 500 }}>
              Fourth Estate
            </span>
            <span style={{ fontFamily: "var(--font-masthead)", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--navy-800)", fontSize: 28, fontWeight: 500, marginTop: 3 }}>
              Index
            </span>
          </span>
        </Link>
        <nav className="flex items-center gap-6" style={{ fontFamily: "var(--font-sans)" }}>
          {LINKS.map((l) => {
            const active = l.href === "/" ? path === "/" : path.startsWith(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                className="pb-0.5 text-sm"
                style={{
                  color: active ? "var(--navy-800)" : "var(--text-body)",
                  fontWeight: active ? 700 : 500,
                  borderBottom: active ? "2px solid var(--navy-800)" : "2px solid transparent",
                }}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
