export function ImpactBar({ score }: { score: number }) {
  const width = Math.min(score, 100);
  const color =
    score >= 70
      ? "bg-red-500"
      : score >= 40
      ? "bg-amber-500"
      : "bg-emerald-500";

  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 rounded-full bg-gray-800">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="text-xs font-mono text-gray-400 w-8 text-right">
        {score.toFixed(0)}
      </span>
    </div>
  );
}
