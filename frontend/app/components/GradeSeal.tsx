import { gradeColor, letterGrade, scoreToPct } from "@/lib/score";

export default function GradeSeal({
  score,
  size = 88,
}: {
  score: number | null;
  size?: number;
}) {
  const grade = letterGrade(score);
  const pct = scoreToPct(score);
  const color = gradeColor(grade);
  return (
    <div
      className="flex flex-col items-center justify-center text-center"
      style={{
        width: size,
        height: size,
        border: `2px solid ${color}`,
        boxShadow: `inset 0 0 0 3px ${color}`,
        color,
        background: "var(--paper-100)",
      }}
    >
      <span style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: size * 0.38, lineHeight: 1 }}>
        {grade ?? "—"}
      </span>
      <span style={{ fontFamily: "var(--font-sans)", fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase" }}>
        {pct === null ? "pending" : pct}
      </span>
    </div>
  );
}
