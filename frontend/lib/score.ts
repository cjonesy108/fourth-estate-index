export function scoreToPct(score: number | null | undefined): number | null {
  if (score === null || score === undefined) return null;
  return Math.round(score * 100);
}

export function letterGrade(score: number | null | undefined): string | null {
  const pct = scoreToPct(score);
  if (pct === null) return null;
  if (pct >= 90) return "A";
  if (pct >= 80) return "B";
  if (pct >= 70) return "C";
  if (pct >= 60) return "D";
  return "F";
}

export function gradeColor(grade: string | null): string {
  if (grade === "A") return "var(--score-a)";
  if (grade === "B") return "var(--score-b)";
  if (grade === "C") return "var(--score-c)";
  if (grade === "D") return "var(--score-d)";
  if (grade === "F") return "var(--score-f)";
  return "var(--ink-300)";
}
