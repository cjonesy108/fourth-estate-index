import { Citation, JournalistProfile, JournalistSummary } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 300 } });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export const api = {
  journalists: {
    list: (params?: { outlet?: string; beat?: string; scored_only?: boolean }) => {
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      return get<JournalistSummary[]>(`/api/journalists${qs ? `?${qs}` : ""}`);
    },
    get: (slug: string) => get<JournalistProfile>(`/api/journalists/${slug}`),
    citations: (slug: string, dimension?: string) => {
      const qs = dimension ? `?dimension=${dimension}` : "";
      return get<Citation[]>(`/api/journalists/${slug}/citations${qs}`);
    },
  },
  methodology: {
    get: () => get<Record<string, unknown>>("/api/methodology"),
  },
};
