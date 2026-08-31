export default function Rule({ faint = false }: { faint?: boolean }) {
  const color = faint ? "var(--navy-400)" : "var(--navy-800)";
  return (
    <div className="flex items-center gap-3" aria-hidden="true">
      <span className="flex-1 h-px" style={{ background: color }} />
      <span style={{ color, fontSize: 10 }}>◆</span>
      <span className="flex-1 h-px" style={{ background: color }} />
    </div>
  );
}
