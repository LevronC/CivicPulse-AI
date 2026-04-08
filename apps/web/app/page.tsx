"use client";

import { useEffect, useMemo, useState } from "react";

type EventItem = {
  id: string;
  title: string;
  summary: string;
  topic: string;
  sentiment: string;
  impact_score: number;
  latitude: number;
  longitude: number;
};

export default function HomePage() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [topic, setTopic] = useState("");
  const [sentiment, setSentiment] = useState("");

  useEffect(() => {
    const params = new URLSearchParams();
    if (topic) params.set("topic", topic);
    if (sentiment) params.set("sentiment", sentiment);
    fetch(`http://localhost:8000/events?${params.toString()}`)
      .then((r) => r.json())
      .then((d) => setEvents(d.items ?? []))
      .catch(() => setEvents([]));
  }, [topic, sentiment]);

  const top = useMemo(() => events.slice(0, 5), [events]);

  return (
    <main style={{ padding: 20 }}>
      <h1>CivicPulse AI</h1>
      <p>Live intelligence dashboard for global events.</p>
      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <select value={topic} onChange={(e) => setTopic(e.target.value)}>
          <option value="">All topics</option>
          <option value="politics">Politics</option>
          <option value="disaster">Disaster</option>
          <option value="technology">Technology</option>
          <option value="economics">Economics</option>
          <option value="conflict">Conflict</option>
          <option value="other">Other</option>
        </select>
        <select value={sentiment} onChange={(e) => setSentiment(e.target.value)}>
          <option value="">All sentiment</option>
          <option value="positive">Positive</option>
          <option value="neutral">Neutral</option>
          <option value="negative">Negative</option>
        </select>
      </div>

      <section style={{ marginBottom: 20 }}>
        <h2>Global Event Map (coordinates)</h2>
        <div style={{ background: "#111827", padding: 12, borderRadius: 8 }}>
          {events.map((e) => (
            <div key={e.id}>
              {e.title} - ({e.latitude.toFixed(2)}, {e.longitude.toFixed(2)})
            </div>
          ))}
        </div>
      </section>

      <section style={{ marginBottom: 20 }}>
        <h2>Top Impact Events</h2>
        {top.map((e) => (
          <article key={e.id} style={{ background: "#111827", marginBottom: 10, padding: 12, borderRadius: 8 }}>
            <strong>{e.title}</strong> ({e.topic}/{e.sentiment}) - impact {e.impact_score}
            <p>{e.summary}</p>
          </article>
        ))}
      </section>

      <section>
        <h2>Sentiment Snapshot</h2>
        <div style={{ display: "flex", gap: 14 }}>
          <span>Positive: {events.filter((e) => e.sentiment === "positive").length}</span>
          <span>Neutral: {events.filter((e) => e.sentiment === "neutral").length}</span>
          <span>Negative: {events.filter((e) => e.sentiment === "negative").length}</span>
        </div>
      </section>
    </main>
  );
}
