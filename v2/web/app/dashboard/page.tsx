"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import { getDashboardSummary, type DashboardSummary } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState("");
  const { locale, t } = useI18n();

  useEffect(() => {
    getDashboardSummary(locale)
      .then(setSummary)
      .catch((summaryError) => {
        setError(summaryError instanceof Error ? summaryError.message : t("loadingDashboard"));
      });
  }, [locale]);

  return (
    <AppShell eyebrow={t("privateDashboard")} title={t("dashboard")}>
      <div className="mt-5 space-y-5">
        <section className="flex flex-col gap-2 rounded-md border border-green-700 bg-green-700 p-4 text-white sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide opacity-90">라운드 기록</p>
            <p className="mt-1 text-base font-semibold">한 샷씩 모바일로 기록</p>
            <p className="mt-1 text-xs opacity-90">
              라운드 중에도 자동 저장. 끊겨도 이어쓰기 가능.
            </p>
          </div>
          <div className="flex gap-2">
            <Link
              className="rounded-md bg-white px-4 py-2 text-sm font-semibold text-green-700"
              href="/rounds/log"
            >
              라운드 기록 시작 →
            </Link>
            <Link
              className="rounded-md border border-white px-3 py-2 text-sm font-semibold"
              href="/settings/clubs"
            >
              클럽 가방
            </Link>
          </div>
        </section>

        {!summary && !error && (
          <div className="rounded-md border border-line bg-white p-3 text-sm text-muted">
            {t("loadingDashboard")}
          </div>
        )}
        {error && <div className="rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">{error}</div>}

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Kpi label={t("rounds")} value={summary?.kpis.round_count ?? "-"} />
          <Kpi label={t("avgScore")} value={summary?.kpis.average_score ?? "-"} />
          <Kpi label={t("bestScore")} value={summary?.kpis.best_score ?? "-"} />
          <Kpi label={t("avgPutts")} value={summary?.kpis.average_putts ?? "-"} />
        </section>

        <section className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="min-w-0 rounded-md border border-line bg-white">
            <div className="border-b border-line px-4 py-3">
              <h2 className="text-base font-semibold">{t("scoreTrendGraph")}</h2>
            </div>
            <ScoreTrendChart points={summary?.score_trend ?? []} t={t} />
          </div>

          <div className="rounded-md border border-line bg-white">
            <div className="border-b border-line px-4 py-3">
              <h2 className="text-base font-semibold">{t("priorityInsights")}</h2>
            </div>
            <div className="divide-y divide-line">
              {(summary?.priority_insights ?? []).slice(0, 3).map((insight) => (
                <article className="p-4" key={`${insight.problem}-${insight.evidence}`}>
                  <h3 className="text-sm font-semibold">{insight.problem}</h3>
                  <p className="mt-2 text-sm leading-6 text-muted" title={insight.evidence}>
                    {shortenText(insight.evidence ?? "", 110)}
                  </p>
                  <p className="mt-2 text-sm leading-6" title={insight.next_action}>
                    {shortenText(insight.next_action ?? "", 110)}
                  </p>
                </article>
              ))}
              {summary && summary.priority_insights.length === 0 && (
                <p className="p-4 text-sm text-muted">{t("noPriorityInsights")}</p>
              )}
            </div>
          </div>
        </section>

        <section className="rounded-md border border-line bg-white">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold">{t("recentRounds")}</h2>
            <Link className="text-sm font-semibold text-green-700" href="/rounds">
              {t("viewAll")}
            </Link>
          </div>
          <div className="divide-y divide-line">
            {(summary?.recent_rounds ?? []).map((round) => (
              <Link className="block px-4 py-3 hover:bg-surface" href={`/rounds/${round.id}`} key={round.id}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">{round.course_name}</span>
                  <span className="text-sm text-muted">{round.play_date}</span>
                </div>
                <div className="mt-1 text-sm text-muted">
                  {round.total_score ?? "-"} {t("strokes")} · {formatToPar(round.score_to_par)}
                </div>
              </Link>
            ))}
            {summary && summary.recent_rounds.length === 0 && (
              <p className="px-4 py-6 text-sm text-muted">{t("noRecentRounds")}</p>
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function ScoreTrendChart({
  points,
  t,
}: {
  points: DashboardSummary["score_trend"];
  t: (key: "average" | "bestScore" | "course" | "date" | "max" | "min" | "score" | "toPar") => string;
}) {
  const valid = points.filter((point) => point.total_score !== null);
  if (valid.length === 0) {
    return <p className="px-4 py-6 text-sm text-muted">-</p>;
  }
  const scores = valid.map((point) => point.total_score as number);
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const average = scores.reduce((total, score) => total + score, 0) / scores.length;
  const paddedMin = Math.max(0, min - 2);
  const paddedMax = max + 2;
  const range = Math.max(1, paddedMax - paddedMin);
  const averageY = scoreToY(average, paddedMin, range);
  const chartPoints = valid.map((point, index) => {
    const x = valid.length === 1 ? 51 : 8 + (index / (valid.length - 1)) * 86;
    const y = scoreToY(point.total_score as number, paddedMin, range);
    return { ...point, x, y };
  });
  const path = chartPoints.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
  const gridScores = [paddedMax, Math.round((paddedMax + paddedMin) / 2), paddedMin];
  const labeledPoints = chartPoints.length <= 6 ? chartPoints : chartPoints.filter((_, index) => index % 2 === 0 || index === chartPoints.length - 1);
  const recent = [...valid].slice(-5).reverse();

  return (
    <div className="p-4">
      <div className="mb-3 grid gap-2 text-sm sm:grid-cols-3">
        <div className="rounded-md bg-surface px-3 py-2">
          <p className="text-xs text-muted">{t("average")}</p>
          <p className="font-semibold">{formatDecimal(average)}</p>
        </div>
        <div className="rounded-md bg-surface px-3 py-2">
          <p className="text-xs text-muted">{t("bestScore")}</p>
          <p className="font-semibold">{min}</p>
        </div>
        <div className="rounded-md bg-surface px-3 py-2">
          <p className="text-xs text-muted">{t("min")} - {t("max")}</p>
          <p className="font-semibold">{min} - {max}</p>
        </div>
      </div>
      <svg className="h-80 w-full overflow-visible" viewBox="0 0 100 100">
        <rect fill="#fafafa" height="72" rx="2" width="90" x="6" y="10" />
        {gridScores.map((score) => {
          const y = scoreToY(score, paddedMin, range);
          return (
            <g key={score}>
              <line className="stroke-line" x1="6" x2="96" y1={y} y2={y} vectorEffect="non-scaling-stroke" />
              <text className="fill-muted text-[3px]" dominantBaseline="middle" textAnchor="start" x="1" y={y}>
                {score}
              </text>
            </g>
          );
        })}
        <line stroke="#94a3b8" strokeDasharray="3 3" strokeWidth="1" vectorEffect="non-scaling-stroke" x1="6" x2="96" y1={averageY} y2={averageY} />
        <text className="fill-muted text-[3px]" dominantBaseline="middle" textAnchor="end" x="99" y={averageY}>
          {t("average")} {formatDecimal(average)}
        </text>
        <path d={path} fill="none" stroke="#15803d" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.4" vectorEffect="non-scaling-stroke" />
        {chartPoints.map((point) => (
          <g key={point.round_id}>
            <circle cx={point.x} cy={point.y} fill="#15803d" r="2.2" stroke="white" strokeWidth="1" vectorEffect="non-scaling-stroke" />
            <title>
              {point.course_name}
              {"\n"}{t("date")}: {point.play_date}
              {"\n"}{t("score")}: {point.total_score}
              {"\n"}{t("toPar")}: {formatToPar(point.score_to_par)}
            </title>
          </g>
        ))}
        {labeledPoints.map((point) => (
          <g key={`${point.round_id}-label`}>
            <text className="fill-ink text-[3.4px] font-semibold" textAnchor="middle" x={point.x} y={Math.max(8, point.y - 4)}>
              {point.total_score}
            </text>
            <text className="fill-muted text-[2.7px]" textAnchor="middle" x={point.x} y="90">
              {shortDate(point.play_date)}
            </text>
          </g>
        ))}
      </svg>
      <div className="mt-3 grid gap-2 text-xs text-muted md:grid-cols-5">
        {recent.map((point) => (
          <div className="rounded-md border border-line bg-white px-2 py-1.5" key={point.round_id}>
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold text-ink">{point.total_score}</span>
              <span>{formatToPar(point.score_to_par)}</span>
            </div>
            <p className="mt-1 truncate" title={point.course_name}>{point.course_name}</p>
            <p>{point.play_date}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function scoreToY(score: number, min: number, range: number) {
  return 82 - ((score - min) / range) * 64;
}

function formatDecimal(value: number) {
  return (Math.round(value * 10) / 10).toFixed(1);
}

function shortDate(value: string) {
  const parts = value.split("-");
  if (parts.length !== 3) return value;
  return `${parts[1]}/${parts[2]}`;
}

function shortenText(value: string, maxLength: number) {
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 1).trim()}…`;
}

function Kpi({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-md border border-line bg-white p-4">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function formatToPar(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  if (value > 0) return `+${value}`;
  return String(value);
}
