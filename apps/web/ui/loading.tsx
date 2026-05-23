export function LoadingSpinner({ text = "Loading..." }: { text?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-gray-400">
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-600 border-t-blue-400" />
      <span className="text-sm">{text}</span>
    </div>
  );
}

export function LoadingSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-3 animate-pulse">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-4 rounded bg-gray-800"
          style={{ width: `${85 - i * 15}%` }}
        />
      ))}
    </div>
  );
}
