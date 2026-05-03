"use client";

import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import {
  getAnalyticsTrends,
  updateInsightStatus,
  type AnalyticsTrend,
  type InsightUnit,
} from "@/lib/api";

const tabs = [
  { id: "score", label: "Score" },
  { id: "off_the_tee", label: "Tee" },
  { id: "approach", label: "Approach" },
  { id: "short_game", label: "Short Game" },
  { id: "putting", label: "Putting" },
];

export default function AnalysisPage() {
  const [trend, setTrend] = useState<AnalyticsTrend | null>(null);
  const [activeTab, setActiveTab] = useState("score");
  const [error, setError] = useState("");

  async function loadAnalysis() {
    setError("");
    try {
      setTrend(await getAnalyticsTrends());
    } catch (analysisError) {
      setError(analysisError instanceof Error ? analysisError.message : "Analysis load failed");
    }
  }

  useEffect(() => {
    loadAnalysis();
  }, []);

  const visibleCategoryRows = useMemo(() => {
    if (!trend) return [];
    if (activeTab === "score") return trend.category_summary;
    return trend.category_summary.filter((row) => row.category === activeTab);
  }, [trend, activeTab]);

  const visibleInsights = useMemo(() => {
    if (!trend) return [];
    if (activeTab === "score") return trend.insights;
    return trend.insights.filter((insight) => insight.category === activeTab);
  }, [trend, activeTab]);

  async function dismissInsight(insight: InsightUnit) {
    await updateInsightStatus(insight.id, "dismissed");
    await loadAnalysis();
  }

  return (
    <AppShell eyebrow="Analysis" title="Analysis">
      <div className="mt-5 space-y-5">
        {!trend && !error && (
          <div className="rounded-md border border-line bg-white p-3 text-sm text-muted">
            Loading analysis...
          </div>
        )}
        {error && (
          <div className="rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">
            {error}
          </div>
        )}

        <section className="rounded-md border border-line bg-white p-3">
          <div className="flex gap-2 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                className={
                  activeTab === tab.id
                    ? "rounded-md bg-green-700 px-3 py-2 text-sm font-semibold text-white"
                    : "rounded-md border border-line px-3 py-2 text-sm font-semibold"
                }
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </section>

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Kpi label="Rounds" value={trend?.kpis.round_count ?? "-"} />
          <Kpi label="Avg score" value={trend?.kpis.average_score ?? "-"} />
          <Kpi label="Best score" value={trend?.kpis.best_score ?? "-"} />
          <Kpi label="Avg putts" value={trend?.kpis.average_putts ?? "-"} />
        </section>

        <section className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-md border border-line bg-white">
            <div className="border-b border-line px-4 py-3">
              <h2 className="text-base font-semibold">Category Summary</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead className="bg-surface text-muted">
                  <tr>
                    <th className="px-4 py-2 font-medium">Category</th>
                    <th className="px-4 py-2 font-medium">Shots</th>
                    <th className="px-4 py-2 font-medium">Total value</th>
                    <th className="px-4 py-2 font-medium">Avg value</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleCategoryRows.map((row) => (
                    <tr className="border-t border-line" key={row.category}>
                      <td className="px-4 py-3 font-medium">{categoryLabel(row.category)}</td>
                      <td className="px-4 py-3">{row.count}</td>
                      <td className="px-4 py-3">{formatNumber(row.total_shot_value)}</td>
                      <td className="px-4 py-3">{formatNumber(row.avg_shot_value)}</td>
                    </tr>
                  ))}
                  {trend && visibleCategoryRows.length === 0 && (
                    <tr>
                      <td className="px-4 py-6 text-muted" colSpan={4}>
                        No analysis rows for this tab yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-md border border-line bg-white">
            <div className="border-b border-line px-4 py-3">
              <h2 className="text-base font-semibold">Insight Units</h2>
            </div>
            <div className="divide-y divide-line">
              {visibleInsights.map((insight) => (
                <article className="p-4" key={insight.id}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase text-green-700">
                        {categoryLabel(insight.category)} · {insight.confidence}
                      </p>
                      <h3 className="mt-1 text-base font-semibold">{insight.problem}</h3>
                    </div>
                    <button
                      className="rounded-md border border-line px-3 py-1.5 text-sm font-semibold"
                      onClick={() => dismissInsight(insight)}
                    >
                      Dismiss
                    </button>
                  </div>
                  <dl className="mt-3 space-y-2 text-sm leading-6">
                    <InsightLine label="Evidence" value={insight.evidence} />
                    <InsightLine label="Impact" value={insight.impact} />
                    <InsightLine label="Next" value={insight.next_action} />
                  </dl>
                </article>
              ))}
              {trend && visibleInsights.length === 0 && (
                <p className="p-4 text-sm text-muted">No active insight units for this tab.</p>
              )}
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function InsightLine({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-semibold">{label}</dt>
      <dd className="text-muted">{value}</dd>
    </div>
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

function categoryLabel(category: string) {
  const labels: Record<string, string> = {
    score: "Score",
    off_the_tee: "Tee",
    approach: "Approach",
    short_game: "Short Game",
    putting: "Putting",
    recovery: "Recovery",
    penalty_impact: "Penalty",
  };
  return labels[category] ?? category;
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return value.toFixed(2);
}
