"use client";

import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import {
  createChatThread,
  getChatStatus,
  getChatThread,
  sendChatMessage,
  type ChatStatus,
  type ChatMessage,
  type ChatThread,
} from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const suggestions = {
  ko: [
    "최근 10라운드 평균 스코어는?",
    "최근 라운드 퍼팅은 어땠어?",
    "드라이버 페널티율 알려줘",
    "7번 아이언 샷을 요약해줘",
    "어프로치 카테고리 요약해줘",
  ],
  en: [
    "What is my average score over the last 10 rounds?",
    "How was my putting in recent rounds?",
    "What is my driver penalty rate?",
    "Summarize my 7 iron shots.",
    "Summarize my approach category.",
  ],
};

export default function AskPage() {
  const [thread, setThread] = useState<ChatThread | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState("");
  const [chatStatus, setChatStatus] = useState<ChatStatus | null>(null);
  const [error, setError] = useState("");
  const { locale, t } = useI18n();

  useEffect(() => {
    getChatStatus().then(setChatStatus).catch(() => setChatStatus(null));
    createChatThread("Ask GolfRaiders")
      .then((created) => {
        setThread(created);
        return getChatThread(created.id);
      })
      .then((detail) => setMessages(detail.messages))
      .catch((threadError) => {
        setError(threadError instanceof Error ? threadError.message : t("startingAsk"));
      });
  }, []);

  const latestAssistant = useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant") ?? null,
    [messages],
  );

  async function submitQuestion(nextQuestion = question) {
    if (!thread || !nextQuestion.trim()) return;
    setStatus(t("answering"));
    setError("");
    try {
      const pair = await sendChatMessage(thread.id, nextQuestion.trim());
      setMessages((current) => [...current, pair.user_message, pair.assistant_message]);
      setQuestion("");
      setStatus("");
    } catch (askError) {
      setError(askError instanceof Error ? askError.message : t("answering"));
      setStatus("");
    }
  }

  return (
    <AppShell eyebrow={t("askEyebrow")} title={t("navAsk")}>
      <div className="mt-5 grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-md border border-line bg-white">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold">{t("conversation")}</h2>
            <span
              className={
                chatStatus?.mode === "llm"
                  ? "rounded-md bg-[#edf7f1] px-2 py-1 text-xs font-semibold text-green-700"
                  : "rounded-md bg-surface px-2 py-1 text-xs font-semibold text-muted"
              }
            >
              {chatStatus?.mode === "llm"
                ? t("llmConnected")
                : chatStatus?.enabled
                  ? t("llmDisconnected")
                  : t("deterministicMode")}
            </span>
          </div>

          <div className="min-h-[360px] space-y-3 p-4">
            {messages.length === 0 && (
              <div className="space-y-3">
                {!thread && !error && (
                  <p className="text-sm text-muted">{t("startingAsk")}</p>
                )}
                <p className="text-sm leading-6 text-muted">
                  {t("askIntro")}
                </p>
                <div className="flex flex-wrap gap-2">
                  {suggestions[locale].map((suggestion) => (
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
                placeholder={t("askPlaceholder")}
                disabled={!thread}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") submitQuestion();
                }}
              />
              <button
                className="rounded-md bg-green-700 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9bb5a6]"
                disabled={!thread || status === t("answering")}
                onClick={() => submitQuestion()}
              >
                {t("send")}
              </button>
            </div>
            {status && <p className="mt-2 text-sm text-muted">{status}</p>}
            {error && <p className="mt-2 text-sm text-[#a34242]">{error}</p>}
          </div>
        </section>

        <section className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold">{t("evidence")}</h2>
          </div>
          <div className="space-y-4 p-4 text-sm">
            {latestAssistant ? (
              <Evidence
                evidence={latestAssistant.evidence}
                labels={{
                  appliedFilters: t("appliedFilters"),
                  holes: t("holes"),
                  rounds: t("rounds"),
                  shots: t("shots"),
                }}
              />
            ) : (
              <p className="leading-6 text-muted">
                {t("askEvidenceEmpty")}
              </p>
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function Evidence({
  evidence,
  labels,
}: {
  evidence: Record<string, unknown>;
  labels: { appliedFilters: string; holes: string; rounds: string; shots: string };
}) {
  const filters = evidence.filters as Record<string, unknown> | undefined;
  return (
    <>
      <div className="grid grid-cols-3 gap-2">
        <Metric label={labels.rounds} value={String(evidence.round_count ?? "-")} />
        <Metric label={labels.shots} value={String(evidence.shot_count ?? "-")} />
        <Metric label={labels.holes} value={String(evidence.hole_count ?? "-")} />
      </div>
      <div>
        <h3 className="font-semibold">{labels.appliedFilters}</h3>
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
