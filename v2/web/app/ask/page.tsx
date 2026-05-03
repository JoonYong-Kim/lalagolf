"use client";

import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import {
  createChatThread,
  getChatThread,
  sendChatMessage,
  type ChatMessage,
  type ChatThread,
} from "@/lib/api";

const suggestions = [
  "최근 10라운드 평균 스코어는?",
  "최근 라운드 퍼팅은 어땠어?",
  "드라이버 페널티율 알려줘",
  "7번 아이언 샷을 요약해줘",
  "어프로치 카테고리 요약해줘",
];

export default function AskPage() {
  const [thread, setThread] = useState<ChatThread | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    createChatThread("Ask LalaGolf")
      .then((created) => {
        setThread(created);
        return getChatThread(created.id);
      })
      .then((detail) => setMessages(detail.messages))
      .catch((threadError) => {
        setError(threadError instanceof Error ? threadError.message : "Ask load failed");
      });
  }, []);

  const latestAssistant = useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant") ?? null,
    [messages],
  );

  async function submitQuestion(nextQuestion = question) {
    if (!thread || !nextQuestion.trim()) return;
    setStatus("Answering...");
    setError("");
    try {
      const pair = await sendChatMessage(thread.id, nextQuestion.trim());
      setMessages((current) => [...current, pair.user_message, pair.assistant_message]);
      setQuestion("");
      setStatus("");
    } catch (askError) {
      setError(askError instanceof Error ? askError.message : "Ask failed");
      setStatus("");
    }
  }

  return (
    <AppShell eyebrow="Ask LalaGolf" title="Ask">
      <div className="mt-5 grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold">Conversation</h2>
          </div>

          <div className="min-h-[360px] space-y-3 p-4">
            {messages.length === 0 && (
              <div className="space-y-3">
                {!thread && !error && (
                  <p className="text-sm text-muted">Starting Ask session...</p>
                )}
                <p className="text-sm leading-6 text-muted">
                  Structured Ask answers use your owned rounds, holes, and shots. Deterministic
                  answers work even when Ollama is unavailable.
                </p>
                <div className="flex flex-wrap gap-2">
                  {suggestions.map((suggestion) => (
                    <button
                      className="rounded-md border border-line px-3 py-2 text-sm font-semibold"
                      disabled={!thread}
                      key={suggestion}
                      onClick={() => submitQuestion(suggestion)}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message) => (
              <article
                className={
                  message.role === "user"
                    ? "ml-auto max-w-[84%] rounded-md bg-green-700 p-3 text-sm leading-6 text-white"
                    : "max-w-[88%] rounded-md border border-line bg-surface p-3 text-sm leading-6"
                }
                key={message.id}
              >
                {message.content}
              </article>
            ))}
          </div>

          <div className="border-t border-line p-4">
            <div className="flex gap-2">
              <input
                className="min-w-0 flex-1 rounded-md border border-line px-3 py-2 text-sm"
                placeholder="최근 10라운드 평균 스코어는?"
                disabled={!thread}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") submitQuestion();
                }}
              />
              <button
                className="rounded-md bg-green-700 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9bb5a6]"
                disabled={!thread || status === "Answering..."}
                onClick={() => submitQuestion()}
              >
                Send
              </button>
            </div>
            {status && <p className="mt-2 text-sm text-muted">{status}</p>}
            {error && <p className="mt-2 text-sm text-[#a34242]">{error}</p>}
          </div>
        </section>

        <section className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold">Evidence</h2>
          </div>
          <div className="space-y-4 p-4 text-sm">
            {latestAssistant ? (
              <Evidence evidence={latestAssistant.evidence} />
            ) : (
              <p className="leading-6 text-muted">
                Ask a supported question to see round count, shot count, and applied filters.
              </p>
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function Evidence({ evidence }: { evidence: Record<string, unknown> }) {
  const filters = evidence.filters as Record<string, unknown> | undefined;
  return (
    <>
      <div className="grid grid-cols-3 gap-2">
        <Metric label="Rounds" value={String(evidence.round_count ?? "-")} />
        <Metric label="Shots" value={String(evidence.shot_count ?? "-")} />
        <Metric label="Holes" value={String(evidence.hole_count ?? "-")} />
      </div>
      <div>
        <h3 className="font-semibold">Applied Filters</h3>
        <dl className="mt-2 grid gap-2">
          {Object.entries(filters ?? {}).map(([key, value]) => (
            <div className="flex justify-between gap-3 border-b border-line pb-2" key={key}>
              <dt className="text-muted">{key}</dt>
              <dd className="text-right font-medium">{formatValue(value)}</dd>
            </div>
          ))}
        </dl>
      </div>
    </>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-surface p-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
