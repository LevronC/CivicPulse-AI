export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-lg border border-red-900/50 bg-red-950/30 p-6 text-center">
      <p className="text-sm text-red-300 mb-3">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-md bg-red-900/50 px-4 py-1.5 text-xs font-medium text-red-200 hover:bg-red-900/70 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-8 text-center">
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  );
}
