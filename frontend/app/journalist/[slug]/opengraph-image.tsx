import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "FEI Score Card";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

function scoreColor(score: number | null): string {
  if (score === null) return "#94a3b8";
  if (score >= 0.8) return "#4ade80";
  if (score >= 0.7) return "#facc15";
  return "#f87171";
}

export default async function Image({ params }: { params: { slug: string } }) {
  const API_BASE =
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  let profile: Record<string, any> | null = null;
  try {
    const res = await fetch(`${API_BASE}/api/journalists/${params.slug}`);
    if (res.ok) profile = await res.json();
  } catch {}

  const name = profile?.full_name ?? "Journalist";
  const outlet = profile?.primary_outlet ?? "";
  const scores = profile?.pillar_scores;
  const composite: number | null = scores?.composite_score ?? null;
  const compositeDisplay =
    composite !== null ? Math.round(composite * 100) : null;
  const corpusSize = profile?.corpus_size;

  const pillars = [
    { label: "Seek Truth & Report It", key: "pillar_1_score" },
    { label: "Minimize Harm", key: "pillar_2_score" },
    { label: "Act Independently", key: "pillar_3_score" },
    { label: "Be Accountable", key: "pillar_4_score" },
  ];

  return new ImageResponse(
    (
      <div
        style={{
          width: 1200,
          height: 630,
          background: "#0f172a",
          display: "flex",
          flexDirection: "column",
          padding: "56px 80px",
          fontFamily: "system-ui, -apple-system, sans-serif",
        }}
      >
        {/* Header row */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginBottom: 40,
          }}
        >
          {/* Name + outlet */}
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span
              style={{
                fontSize: 13,
                color: "#64748b",
                letterSpacing: "0.15em",
                textTransform: "uppercase",
                marginBottom: 12,
              }}
            >
              Fourth Estate Index
            </span>
            <h1
              style={{
                fontSize: 52,
                fontWeight: 800,
                color: "#f1f5f9",
                margin: 0,
                lineHeight: 1.1,
                maxWidth: 680,
              }}
            >
              {name}
            </h1>
            {outlet && (
              <span
                style={{ fontSize: 22, color: "#94a3b8", marginTop: 10 }}
              >
                {outlet}
              </span>
            )}
          </div>

          {/* Composite score badge */}
          {compositeDisplay !== null && (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                background: "#1e293b",
                borderRadius: 20,
                padding: "20px 44px",
                flexShrink: 0,
              }}
            >
              <span
                style={{
                  fontSize: 13,
                  color: "#64748b",
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  marginBottom: 4,
                }}
              >
                FEI Score
              </span>
              <span
                style={{
                  fontSize: 84,
                  fontWeight: 800,
                  color: scoreColor(composite),
                  lineHeight: 1,
                }}
              >
                {compositeDisplay}
              </span>
              <span style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>
                out of 100
              </span>
            </div>
          )}
        </div>

        {/* Pillar bars */}
        {scores && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 16,
              flex: 1,
            }}
          >
            {pillars.map(({ label, key }) => {
              const val: number | null = scores[key] ?? null;
              const pct = val !== null ? Math.round(val * 100) : null;
              return (
                <div
                  key={key}
                  style={{ display: "flex", alignItems: "center", gap: 18 }}
                >
                  <span
                    style={{
                      fontSize: 15,
                      color: "#94a3b8",
                      width: 230,
                      flexShrink: 0,
                    }}
                  >
                    {label}
                  </span>
                  <div
                    style={{
                      flex: 1,
                      height: 8,
                      background: "#1e293b",
                      borderRadius: 4,
                      display: "flex",
                      overflow: "hidden",
                    }}
                  >
                    {pct !== null && (
                      <div
                        style={{
                          width: `${pct}%`,
                          height: "100%",
                          background: scoreColor(val),
                          borderRadius: 4,
                        }}
                      />
                    )}
                  </div>
                  <span
                    style={{
                      fontSize: 18,
                      fontWeight: 700,
                      color: scoreColor(val),
                      width: 36,
                      textAlign: "right",
                      flexShrink: 0,
                    }}
                  >
                    {pct ?? "—"}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* Footer */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: 32,
            paddingTop: 20,
            borderTop: "1px solid #1e293b",
          }}
        >
          <span style={{ fontSize: 13, color: "#475569" }}>
            {corpusSize
              ? `Based on ${corpusSize} articles · 2023–2024`
              : ""}
          </span>
          <span style={{ fontSize: 13, color: "#475569" }}>
            fourthestateindex.com
          </span>
        </div>
      </div>
    ),
    { ...size }
  );
}
