import type { SentimentLabel, Topic } from "../lib/types";

const TOPIC_COLORS: Record<Topic, string> = {
  politics: "bg-purple-900/60 text-purple-200 border-purple-700/50",
  disaster: "bg-red-900/60 text-red-200 border-red-700/50",
  technology: "bg-blue-900/60 text-blue-200 border-blue-700/50",
  economics: "bg-emerald-900/60 text-emerald-200 border-emerald-700/50",
  conflict: "bg-orange-900/60 text-orange-200 border-orange-700/50",
  other: "bg-gray-800/60 text-gray-300 border-gray-600/50",
};

const SENTIMENT_COLORS: Record<SentimentLabel, string> = {
  positive: "bg-green-900/60 text-green-200 border-green-700/50",
  neutral: "bg-gray-800/60 text-gray-300 border-gray-600/50",
  negative: "bg-red-900/60 text-red-200 border-red-700/50",
};

export function TopicBadge({ topic }: { topic: Topic }) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${TOPIC_COLORS[topic]}`}
    >
      {topic}
    </span>
  );
}

export function SentimentBadge({ sentiment }: { sentiment: SentimentLabel }) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${SENTIMENT_COLORS[sentiment]}`}
    >
      {sentiment}
    </span>
  );
}
