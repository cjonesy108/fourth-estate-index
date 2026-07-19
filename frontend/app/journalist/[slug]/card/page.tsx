"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { JournalistProfile } from "@/lib/types";
import { api } from "@/lib/api";

function scoreColor(score: number | null) {
  if (score === null) return { text: "text-gray-400", bar: "bg-gray-300" };
  if (score >= 0.8) return { text: "text-emerald-600", bar: "bg-emerald-500" };
  if (score >= 0.7) return { text: "text-amber-500", bar: "bg-amber-400" };
  return { text: "text-red-500", bar: "bg-red-400" };
}

const PILLARS = [
  { label: "Seek Truth & Report It", sub: "Pillar 1 · 30%", key: "pillar_1_score" as const },
  { label: "Minimize Harm",          sub: "Pillar 2 · 20%", key: "pillar_2_score" as const },
  { label: "Act Independently",      sub: "Pillar 3 · 30%", key: "pillar_3_score" as const },
  { label: "Be Accountable",         sub: "Pillar 4 · 20%", key: "pillar_4_score" as const },
];

export default function CardPage() {
  const { slug } = useParams<{ slug: string }>();
  const [profile, setProfile] = useState<JournalistProfile | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.journalists.get(slug).then(setProfile).catch(() => {});
  }, [slug]);

  const handleCopy = () => {
    const url = `${window.location.origin}/journalist/${slug}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (!profile) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-slate-600 border-t-slate-300 rounded-full animate-spin" />
      </div>
    );
  }

  const scores = profile.pillar_scores;
  const composite = scores?.composite_score ?? null;
  const compositeDisplay = composite !== null ? Math.round(composite * 100) : null;
  const { text: compositeText } = scoreColor(composite);

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6">
      {/* Card */}
      <div className="w-full max-w-lg bg-slate-900 rounded-2xl overflow-hidden shadow-2xl">

        {/* Top accent bar */}
        <div className="h-1 bg-gradient-to-r from-slate-700 via-slate-500 to-slate-700" />

        <div className="p-8">
          {/* FEI label */}
          <p className="text-xs text-slate-500 uppercase tracking-widest mb-4">
            Fourth Estate Index
          </p>

          {/* Name + composite */}
          <div className="flex items-start justify-between gap-4 mb-8">
            <div>
              <h1 className="text-2xl font-bold text-slate-100 leading-tight">
                {profile.full_name}
              </h1>
              {profile.primary_outlet && (
                <p className="text-slate-400 text-sm mt-1">{profile.primary_outlet}</p>
              )}
            </div>
            {compositeDisplay !== null && (
              <div className="flex flex-col items-center bg-slate-800 rounded-xl px-5 py-3 flex-shrink-0">
                <span className="text-xs text-slate-500 uppercase tracking-wide mb-0.5">Score</span>
                <span className={`text-4xl font-black tabular-nums ${compositeText}`}>
                  {compositeDisplay}
                </span>
                <span className="text-xs text-slate-600">/ 100</span>
              </div>
            )}
          </div>

          {/* Pillars */}
          {scores ? (
            <div className="space-y-4">
              {PILLARS.map(({ label, sub, key }) => {
                const val = scores[key];
                const pct = val !== null ? Math.round(val * 100) : null;
                const { text, bar } = scoreColor(val);
                return (
                  <div key={key}>
                    <div className="flex items-center justify-between mb-1.5">
                      <div>
                        <span className="text-sm text-slate-300">{label}</span>
                        <span className="text-xs text-slate-600 ml-2">{sub}</span>
                      </div>
                      <span className={`text-sm font-bold tabular-nums ${text}`}>
                        {pct ?? "—"}
                      </span>
                    </div>
                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      {pct !== null && (
                        <div
                          className={`h-full rounded-full ${bar}`}
                          style={{ width: `${pct}%` }}
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-slate-500 text-sm italic">Score data not yet available.</p>
          )}

          {/* Corpus footnote */}
          {profile.corpus_size && (
            <p className="text-xs text-slate-600 mt-6">
              Based on {profile.corpus_size} articles ·{" "}
              {profile.corpus_start?.slice(0, 7)} – {profile.corpus_end?.slice(0, 7)}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-slate-800 px-8 py-4 flex items-center justify-between">
          <span className="text-xs text-slate-600">fourthestateindex.com</span>
          <button
            onClick={handleCopy}
            className="text-xs text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-1.5"
          >
            {copied ? (
              <>
                <svg className="w-3.5 h-3.5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-emerald-500">Copied!</span>
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy link
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
