"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import { getDashboardSummary, type DashboardSummary } from "@/lib/api";

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getDashboardSummary()
      .then(setSummary)
      .catch((summaryError) => {
        setError(summaryError instanceof Error ? summaryError.message : "Dashboard load failed");
      });
  }, []);

  return (
    <AppShell eyebrow="Private Dashboard" title="Dashboard">
      <div className="mt-5 space-y-5">
        {!summary && !error && (
          <div className="rounded-md border border-line bg-white p-3 text-sm text-muted">
            Loading dashboard...
          </div>
        )}
        {error && <div className="rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">{error}</div>}

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Kpi label="Rounds" value={summary?.kpis.round_count ?? "-"} />
          <Kpi label="Avg score" value={summary?.kpis.average_score ?? "-"} />
          <Kpi label="Best score" value={summary?.kpis.best_score ?? "-"} />
          <Kpi label="Avg putts" value={summary?.kpis.average_putts ?? "-"} />
        </section>

        <section className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="min-w-0 rounded-md border border-line bg-white">
            <div className="border-b border-line px-4 py-3">
              <h2 className="text-base font-semibold">Score Trend</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead className="bg-surface text-muted">
                  <tr>
                    <th className="px-4 py-2 font-medium">Date</th>
                    <th className="px-4 py-2 font-medium">Course</th>
                    <th className="px-4 py-2 font-medium">Score</th>
                    <th className="px-4 py-2 font-medium">To par</th>
                  </tr>
                </thead>
                <tbody>
                  {(summary?.score_trend ?? []).map((point) => (
                    <tr className="border-t border-line" key={point.round_id}>
                      <td className="px-4 py-3">{point.play_date}</td>
                      <td className="px-4 py-3">{point.course_name}</td>
                      <td className="px-4 py-3 font-semibold">{point.total_score ?? "-"}</td>
                      <td className="px-4 py-3">{formatToPar(point.score_to_par)}</td>
                    </tr>
                  ))}
                  {summary && summary.score_trend.length === 0 && (
                    <tr>
                      <td className="px-4 py-6 text-muted" colSpan={4}>No committed rounds yet.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-md border border-line bg-white">
            <div className="border-b border-line px-4 py-3">
              <h2 className="text-base font-semibold">Priority Insights</h2>
            </div>
            <div className="divide-y divide-line">
              {(summary?.priority_insights ?? []).map((insight) => (
                <article className="p-4" key={`${insight.problem}-${insight.evidence}`}>
                  <h3 className="text-sm font-semibold">{insight.problem}</h3>
                  <p className="mt-2 text-sm leading-6 text-muted">{insight.evidence}</p>
                  <p className="mt-2 text-sm leading-6">{insight.next_action}</p>
                </article>
              ))}
              {summary && summary.priority_insights.length === 0 && (
                <p className="p-4 text-sm text-muted">No priority insights yet.</p>
              )}
            </div>
          </div>
        </section>

        <section className="rounded-md border border-line bg-white">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold">Recent Rounds</h2>
            <Link className="text-sm font-semibold text-green-700" href="/rounds">
              View all
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
                  {round.total_score ?? "-"} strokes · {formatToPar(round.score_to_par)}
                </div>
              </Link>
            ))}
            {summary && summary.recent_rounds.length === 0 && (
              <p className="px-4 py-6 text-sm text-muted">No recent rounds yet.</p>
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
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
