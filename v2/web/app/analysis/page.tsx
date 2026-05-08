"use client";

import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import {
  createGoal,
  createPracticePlan,
  getAnalyticsTrends,
  getRound,
  getRoundAnalytics,
  getRounds,
  requestRoundRecalculation,
  updateInsightStatus,
  type AnalyticsTrend,
  type InsightUnit,
  type RoundDetail,
  type ShotQualitySummary,
} from "@/lib/api";
import { useI18n, type MessageKey } from "@/lib/i18n";

const tabs = ["all", "off_the_tee", "short_game", "control_shot", "iron_shot", "putting", "recovery", "penalty_impact"];

export default function AnalysisPage() {
  const [trend, setTrend] = useState<AnalyticsTrend | null>(null);
  const [activeTab, setActiveTab] = useState("all");
  const [scopeLabel, setScopeLabel] = useState("");
  const [selectedInsightIndex, setSelectedInsightIndex] = useState(0);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const { locale, t } = useI18n();

  async function loadAnalysis() {
    setError("");
    try {
      const params = new URLSearchParams(window.location.search);
      const roundIds = (params.get("roundIds") ?? "").split(",").filter(Boolean);
      if (roundIds.length > 0) {
        setTrend(await selectedRoundTrend(roundIds, locale));
        setScopeLabel(`${t("selectedAnalysis")} (${roundIds.length})`);
        return;
      }
      setTrend(await getAnalyticsTrends(locale));
      setScopeLabel(t("allRounds"));
    } catch (analysisError) {
      setError(analysisError instanceof Error ? analysisError.message : t("loadingAnalysis"));
    }
  }

  useEffect(() => {
    loadAnalysis();
  }, [locale]);

  const visibleCategoryRows = useMemo(() => {
    if (!trend) return [];
    if (activeTab === "all") return trend.category_summary;
    return trend.category_summary.filter((row) => row.category === activeTab);
  }, [trend, activeTab]);

  const visibleInsights = useMemo(() => {
    if (!trend) return [];
    const activeInsights =
      activeTab === "all"
        ? trend.insights
        : trend.insights.filter((insight) => insight.category === activeTab);
    if (activeInsights.length > 0) {
      return compactInsights(activeInsights, activeTab === "all" ? 4 : 2);
    }
    return compactInsights(fallbackInsights(trend, activeTab, t), activeTab === "all" ? 4 : 2);
  }, [trend, activeTab]);
  const selectedInsight = visibleInsights[selectedInsightIndex] ?? visibleInsights[0] ?? null;

  useEffect(() => {
    setSelectedInsightIndex(0);
  }, [activeTab, scopeLabel]);

  useEffect(() => {
    if (selectedInsightIndex >= visibleInsights.length) {
      setSelectedInsightIndex(Math.max(0, visibleInsights.length - 1));
    }
  }, [selectedInsightIndex, visibleInsights.length]);

  async function dismissInsight(insight: InsightUnit) {
    await updateInsightStatus(insight.id, "dismissed", locale);
    await loadAnalysis();
  }

  async function loadShortcut(scope: "all" | "year" | "recent3" | "recent5" | "recent10") {
    setError("");
    try {
      if (scope === "all") {
        setTrend(await getAnalyticsTrends(locale));
        setScopeLabel(t("allRounds"));
        return;
      }
      const currentYear = new Date().getFullYear();
      const limit = scope === "recent3" ? 3 : scope === "recent5" ? 5 : scope === "recent10" ? 10 : 100;
      const rounds = await getRounds({ limit, year: scope === "year" ? String(currentYear) : undefined });
      setTrend(await selectedRoundTrend(rounds.items.map((round) => round.id), locale));
      setScopeLabel(t(scope === "year" ? "thisYear" : scope));
    } catch (shortcutError) {
      setError(shortcutError instanceof Error ? shortcutError.message : t("loadingAnalysis"));
    }
  }

  async function selectPracticeSuggestion(suggestion: PracticeSuggestion) {
    setError("");
    try {
      await createPracticePlan(suggestion.payload);
      setStatus(t("practicePlanCreated"));
    } catch (planError) {
      setError(planError instanceof Error ? planError.message : "Practice plan failed");
    }
  }

  async function createGoalFromSuggestion(suggestion: PracticeSuggestion) {
    setError("");
    try {
      await createGoal({
        source_insight_id: suggestion.payload.source_insight_id,
        title: suggestion.goalTitle,
        description: suggestion.payload.purpose,
        category: suggestion.payload.category,
        metric_key: suggestion.goalMetric,
        target_operator: "<=",
        target_value: suggestion.goalTarget,
        applies_to: "next_round",
      });
      setStatus(t("saved"));
    } catch (goalError) {
      setError(goalError instanceof Error ? goalError.message : "Goal save failed");
    }
  }

  return (
    <AppShell eyebrow={t("analysis")} title={t("analysis")}>
      <div className="mt-5 space-y-5">
        {!trend && !error && (
          <div className="rounded-md border border-line bg-white p-3 text-sm text-muted">
            {t("loadingAnalysis")}
          </div>
        )}
        {error && (
          <div className="rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">
            {error}
          </div>
        )}
        {status && <div className="rounded-md border border-line bg-white p-3 text-sm text-muted">{status}</div>}

        <section className="rounded-md border border-line bg-white p-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm font-semibold">{scopeLabel}</p>
            <div className="flex gap-2 overflow-x-auto">
              {(["all", "year", "recent3", "recent5", "recent10"] as const).map((scope) => (
                <button
                  className="rounded-md border border-line px-3 py-2 text-sm font-semibold"
                  key={scope}
                  onClick={() => loadShortcut(scope)}
                >
                  {scope === "year" ? t("thisYear") : t(scope === "all" ? "allRounds" : scope)}
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className="rounded-md border border-line bg-white p-3">
          <div className="flex gap-2 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                className={
                  activeTab === tab
                    ? "rounded-md bg-green-700 px-3 py-2 text-sm font-semibold text-white"
                    : "rounded-md border border-line px-3 py-2 text-sm font-semibold"
                }
                key={tab}
                onClick={() => setActiveTab(tab)}
              >
                {categoryLabel(tab, t)}
              </button>
            ))}
          </div>
        </section>

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Kpi label={t("rounds")} value={trend?.kpis.round_count ?? "-"} />
          <Kpi label={t("avgScore")} value={trend?.kpis.average_score ?? "-"} />
          <Kpi label={t("bestScore")} value={trend?.kpis.best_score ?? "-"} />
          <Kpi label={t("avgPutts")} value={trend?.kpis.average_putts ?? "-"} />
        </section>

        {trend?.shot_quality_summary && <ShotQualityWidget quality={trend.shot_quality_summary} t={t} />}

        <section className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-md border border-line bg-white">
            <div className="border-b border-line px-4 py-3">
              <h2 className="text-base font-semibold">{t("categorySummary")}</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead className="bg-surface text-muted">
                  <tr>
                    <th className="px-4 py-2 font-medium">{t("category")}</th>
                    <th className="px-4 py-2 font-medium">{t("shots")}</th>
                    <th className="px-4 py-2 font-medium">{t("totalValue")}</th>
                    <th className="px-4 py-2 font-medium">{t("avgValue")}</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleCategoryRows.map((row) => (
                    <tr className="border-t border-line" key={row.category}>
                      <td className="px-4 py-3 font-medium">{categoryLabel(row.category, t)}</td>
                      <td className="px-4 py-3">{row.count}</td>
                      <td className="px-4 py-3">{formatNumber(row.total_shot_value)}</td>
                      <td className="px-4 py-3">{formatNumber(row.avg_shot_value)}</td>
                    </tr>
                  ))}
                  {trend && visibleCategoryRows.length === 0 && (
                    <tr>
                      <td className="px-4 py-6 text-muted" colSpan={4}>
                        {t("noAnalysisRows")}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-md border border-line bg-white">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
              <h2 className="text-base font-semibold">{t("insightUnits")}</h2>
              {visibleInsights.length > 1 && (
                <div className="flex items-center gap-2">
                  <button
                    className="rounded-md border border-line px-2 py-1 text-sm font-semibold"
                    onClick={() => setSelectedInsightIndex((current) => Math.max(0, current - 1))}
                  >
                    {"<"}
                  </button>
                  <span className="min-w-12 text-center text-sm text-muted">
                    {selectedInsightIndex + 1} / {visibleInsights.length}
                  </span>
                  <button
                    className="rounded-md border border-line px-2 py-1 text-sm font-semibold"
                    onClick={() => setSelectedInsightIndex((current) => Math.min(visibleInsights.length - 1, current + 1))}
                  >
                    {">"}
                  </button>
                </div>
              )}
            </div>
            <div>
              {selectedInsight ? (
                <article className="p-4" key={selectedInsight.id}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase text-green-700">
                        {categoryLabel(selectedInsight.category, t)} · {selectedInsight.confidence}
                      </p>
                      <h3 className="mt-1 text-base font-semibold">{selectedInsight.problem}</h3>
                    </div>
                    {!selectedInsight.id.startsWith("suggested-") && (
                      <button
                        className="rounded-md border border-line px-3 py-1.5 text-sm font-semibold"
                        onClick={() => dismissInsight(selectedInsight)}
                      >
                        {t("dismiss")}
                      </button>
                    )}
                  </div>
                  <dl className="mt-3 space-y-2 text-sm leading-6">
                    <InsightLine label={t("evidence")} value={selectedInsight.evidence} />
                    <InsightLine label={t("impact")} value={selectedInsight.impact} />
                    <InsightLine label={t("next")} value={selectedInsight.next_action} />
                  </dl>
                  <PracticeSuggestionList
                    insight={selectedInsight}
                    onCreateGoal={createGoalFromSuggestion}
                    onSelect={selectPracticeSuggestion}
                    t={t}
                  />
                  {visibleInsights.length > 1 && (
                    <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4">
                      {visibleInsights.map((insight, index) => (
                        <button
                          className={
                            index === selectedInsightIndex
                              ? "h-2.5 w-8 rounded-full bg-green-700"
                              : "h-2.5 w-8 rounded-full bg-line"
                          }
                          key={insight.id}
                          onClick={() => setSelectedInsightIndex(index)}
                          title={insight.problem}
                        />
                      ))}
                    </div>
                  )}
                </article>
              ) : trend && trend.category_summary.length === 0 ? (
                <p className="p-4 text-sm text-muted">{t("noActiveInsights")}</p>
              ) : (
                <p className="p-4 text-sm text-muted">{t("noActiveInsights")}</p>
              )}
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function InsightLine({ label, value }: { label: string; value: string }) {
  const displayValue = shortenText(value, 120);
  return (
    <div>
      <dt className="font-semibold">{label}</dt>
      <dd className="text-muted" title={value}>{displayValue}</dd>
    </div>
  );
}

type PracticeSuggestion = {
  id: string;
  title: string;
  summary: string;
  routine: string[];
  goalTitle: string;
  goalMetric: string;
  goalTarget: number;
  payload: {
    source_insight_id?: string;
    title: string;
    purpose: string;
    category: string;
    drill_json: Record<string, unknown>;
    target_json: Record<string, unknown>;
  };
};

function PracticeSuggestionList({
  insight,
  onCreateGoal,
  onSelect,
  t,
}: {
  insight: InsightUnit;
  onCreateGoal: (suggestion: PracticeSuggestion) => void;
  onSelect: (suggestion: PracticeSuggestion) => void;
  t: (key: MessageKey) => string;
}) {
  const suggestions = practiceSuggestionsForInsight(insight, t);

  return (
    <div className="mt-4 border-t border-line pt-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-sm font-semibold">{t("suggestedPracticePlans")}</h4>
        <span className="text-xs font-medium text-muted">{t("choosePracticePlan")}</span>
      </div>
      <div className="mt-3 grid gap-3">
        {suggestions.map((suggestion) => (
          <div className="rounded-md border border-line bg-surface p-3" key={suggestion.id}>
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase text-green-700">
                {categoryLabel(insight.category, t)}
              </p>
              <h5 className="mt-1 text-sm font-semibold">{suggestion.title}</h5>
              <p className="mt-1 text-sm leading-6 text-muted">{suggestion.summary}</p>
            </div>
            <ul className="mt-3 grid gap-1 text-sm text-muted sm:grid-cols-3">
              {suggestion.routine.map((item) => (
                <li className="rounded-md border border-line bg-white px-2 py-1.5" key={item}>
                  {item}
                </li>
              ))}
            </ul>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <button
                className="rounded-md bg-green-700 px-3 py-1.5 text-sm font-semibold text-white"
                onClick={() => onSelect(suggestion)}
              >
                {t("selectPlan")}
              </button>
              <button
                className="rounded-md border border-line bg-white px-3 py-1.5 text-sm font-semibold"
                onClick={() => onCreateGoal(suggestion)}
              >
                {t("createGoalFromPlan")}
              </button>
            </div>
          </div>
        ))}
      </div>
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

function ShotQualityWidget({
  quality,
  t,
}: {
  quality: ShotQualitySummary;
  t: (key: MessageKey) => string;
}) {
  const riskRows = [
    { label: t("technicalMiss"), value: quality.risk.technical_miss_count ?? 0, rate: quality.risk.technical_miss_rate },
    { label: t("strategyIssue"), value: quality.risk.strategy_issue_count ?? 0, rate: quality.risk.strategy_issue_rate },
    { label: t("luckyResult"), value: quality.risk.lucky_result_count ?? 0, rate: quality.risk.lucky_result_rate },
    { label: t("driverResultC"), value: quality.risk.driver_result_c_count ?? 0, rate: quality.risk.driver_result_c_rate },
  ];
  return (
    <section className="rounded-md border border-line bg-white">
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-base font-semibold">{t("shotQuality")}</h2>
      </div>
      <div className="grid gap-4 p-4 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="grid gap-3 sm:grid-cols-2">
          <QualityDistribution title={t("feelDistribution")} distribution={quality.feel_distribution} />
          <QualityDistribution title={t("resultDistribution")} distribution={quality.result_distribution} />
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          {riskRows.map((row) => (
            <div className="rounded-md border border-line bg-surface p-3" key={row.label}>
              <p className="text-sm text-muted">{row.label}</p>
              <p className="mt-1 text-lg font-semibold">
                {row.value} <span className="text-sm font-normal text-muted">({formatPercent(row.rate)})</span>
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function QualityDistribution({ title, distribution }: { title: string; distribution: ShotQualitySummary["feel_distribution"] }) {
  return (
    <div className="rounded-md border border-line p-3">
      <p className="text-sm font-semibold">{title}</p>
      <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
        {(["A", "B", "C"] as const).map((grade) => (
          <div className="rounded-md bg-surface p-2" key={grade}>
            <p className="font-semibold">{grade}</p>
            <p className="text-muted">{distribution.counts[grade]} ({formatPercent(distribution.rates[grade])})</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function categoryLabel(category: string, t: (key: MessageKey) => string) {
  const labels: Record<string, string> = {
    all: t("allRounds"),
    off_the_tee: t("tee"),
    approach: t("approach"),
    short_game: t("shortGame"),
    control_shot: t("controlShot"),
    iron_shot: t("ironShot"),
    putting: t("putting"),
    recovery: t("recovery"),
    penalty_impact: t("penalty"),
  };
  return labels[category] ?? category;
}

async function selectedRoundTrend(roundIds: string[], locale: "ko" | "en"): Promise<AnalyticsTrend> {
  await Promise.all(roundIds.map((roundId) => requestRoundRecalculation(roundId).catch(() => null)));
  const [rounds, analytics] = await Promise.all([
    Promise.all(roundIds.map((roundId) => getRound(roundId))),
    Promise.all(roundIds.map((roundId) => getRoundAnalytics(roundId, locale))),
  ]);
  const shotValues = analytics.flatMap((item) => item.shot_values);
  const byCategory = new Map<string, { category: string; count: number; total_shot_value: number }>();
  for (const value of shotValues) {
    const row = byCategory.get(value.category) ?? {
      category: value.category,
      count: 0,
      total_shot_value: 0,
    };
    row.count += 1;
    row.total_shot_value += value.shot_value ?? 0;
    byCategory.set(value.category, row);
  }
  const category_summary = shotValues.length > 0
    ? [...byCategory.values()].map((row) => ({
      ...row,
      total_shot_value: Math.round(row.total_shot_value * 1000) / 1000,
      avg_shot_value: row.count ? Math.round((row.total_shot_value / row.count) * 1000) / 1000 : 0,
    })).sort((a, b) => a.total_shot_value - b.total_shot_value)
    : fallbackCategorySummaryFromRounds(rounds);
  const scores = rounds.map((round) => round.total_score).filter((score): score is number => score !== null);
  const putts = rounds.map((round) => round.metrics.putts_total).filter((putt): putt is number => typeof putt === "number");
  const trend = {
    kpis: {
      round_count: rounds.length,
      average_score: scores.length ? Math.round((scores.reduce((sum, score) => sum + score, 0) / scores.length) * 10) / 10 : null,
      best_score: scores.length ? Math.min(...scores) : null,
      average_putts: putts.length ? Math.round((putts.reduce((sum, value) => sum + value, 0) / putts.length) * 10) / 10 : null,
    },
    score_trend: rounds.map((round) => ({
      round_id: round.id,
      play_date: round.play_date,
      course_name: round.course_name,
      total_score: round.total_score,
      score_to_par: round.score_to_par,
    })),
    category_summary,
    shot_quality_summary: buildShotQualitySummary(rounds),
    insights: analytics.flatMap((item) => item.insights),
  };
  return trend;
}

function buildShotQualitySummary(rounds: RoundDetail[]): ShotQualitySummary {
  const emptyDistribution = () => ({
    counts: { A: 0, B: 0, C: 0 },
    rates: { A: null, B: null, C: null },
    total: 0,
  });
  const feel = { A: 0, B: 0, C: 0 };
  const result = { A: 0, B: 0, C: 0 };
  const matrix = {
    A: { A: 0, B: 0, C: 0 },
    B: { A: 0, B: 0, C: 0 },
    C: { A: 0, B: 0, C: 0 },
  };
  const risk = {
    reproducible_count: 0,
    technical_miss_count: 0,
    lucky_result_count: 0,
    strategy_issue_count: 0,
    high_risk_count: 0,
    driver_tee_shot_count: 0,
    driver_result_c_count: 0,
  };
  let sampleCount = 0;
  for (const round of rounds) {
    for (const hole of round.holes) {
      for (const shot of hole.shots) {
        if ((shot.club_normalized ?? shot.club) === "P") continue;
        sampleCount += 1;
        const feelGrade = grade(shot.feel_grade);
        const resultGrade = grade(shot.result_grade);
        if (feelGrade) feel[feelGrade] += 1;
        if (resultGrade) result[resultGrade] += 1;
        if (feelGrade && resultGrade) {
          matrix[feelGrade][resultGrade] += 1;
          if ((feelGrade === "A" || feelGrade === "B") && (resultGrade === "A" || resultGrade === "B")) risk.reproducible_count += 1;
          if (feelGrade === "C" && resultGrade === "C") risk.technical_miss_count += 1;
          if (feelGrade === "C" && (resultGrade === "A" || resultGrade === "B")) risk.lucky_result_count += 1;
          if ((feelGrade === "A" || feelGrade === "B") && resultGrade === "C") risk.strategy_issue_count += 1;
        }
        if (resultGrade === "C" || shot.penalty_strokes > 0) risk.high_risk_count += 1;
        if (shot.shot_number === 1 && hole.par >= 4 && (shot.club_normalized ?? shot.club) === "D") {
          risk.driver_tee_shot_count += 1;
          if (resultGrade === "C") risk.driver_result_c_count += 1;
        }
      }
    }
  }
  const distribution = (counts: Record<"A" | "B" | "C", number>) => {
    const total = counts.A + counts.B + counts.C;
    return {
      counts,
      rates: {
        A: total ? counts.A / total : null,
        B: total ? counts.B / total : null,
        C: total ? counts.C / total : null,
      },
      total,
    };
  };
  return {
    sample_count: sampleCount,
    feel_distribution: sampleCount ? distribution(feel) : emptyDistribution(),
    result_distribution: sampleCount ? distribution(result) : emptyDistribution(),
    feel_result_matrix: matrix,
    risk: {
      ...risk,
      driver_result_c_rate: risk.driver_tee_shot_count ? risk.driver_result_c_count / risk.driver_tee_shot_count : null,
      strategy_issue_rate: sampleCount ? risk.strategy_issue_count / sampleCount : null,
      technical_miss_rate: sampleCount ? risk.technical_miss_count / sampleCount : null,
      lucky_result_rate: sampleCount ? risk.lucky_result_count / sampleCount : null,
      high_risk_rate: sampleCount ? risk.high_risk_count / sampleCount : null,
    },
    tee_result_distribution: emptyDistribution(),
    under_90_result_distribution: emptyDistribution(),
    over_90_result_distribution: emptyDistribution(),
    club_groups: [],
  };
}

function grade(value: string | null | undefined): "A" | "B" | "C" | null {
  const normalized = (value ?? "").toUpperCase();
  return normalized === "A" || normalized === "B" || normalized === "C" ? normalized : null;
}

function fallbackCategorySummaryFromRounds(rounds: RoundDetail[]) {
  const byCategory = new Map<string, { category: string; count: number; total_shot_value: number }>();
  for (const round of rounds) {
    for (const hole of round.holes) {
      for (const shot of hole.shots) {
        const category = fallbackShotCategory(shot, hole.hole_number);
        const row = byCategory.get(category) ?? {
          category,
          count: 0,
          total_shot_value: 0,
        };
        row.count += 1;
        row.total_shot_value -= shot.score_cost || 1;
        byCategory.set(category, row);
      }
    }
  }
  return [...byCategory.values()]
    .map((row) => ({
      ...row,
      total_shot_value: Math.round(row.total_shot_value * 1000) / 1000,
      avg_shot_value: row.count ? Math.round((row.total_shot_value / row.count) * 1000) / 1000 : 0,
    }))
    .sort((a, b) => a.total_shot_value - b.total_shot_value);
}

function fallbackShotCategory(shot: RoundDetail["holes"][number]["shots"][number], holeNumber: number) {
  const club = (shot.club_normalized || shot.club || "").toUpperCase();
  if (shot.penalty_strokes > 0) return "penalty_impact";
  if (club === "P" || club === "PT") return "putting";
  if (shot.shot_number === 1 || holeNumber === 1 && club === "D") return "off_the_tee";
  if (shot.start_lie === "R" || shot.end_lie === "R") return "recovery";
  if (typeof shot.distance === "number" && shot.distance < 40) return "short_game";
  if (typeof shot.distance === "number" && shot.distance < 90) return "control_shot";
  if (typeof shot.distance === "number" && shot.distance >= 90) return "iron_shot";
  return "control_shot";
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return value.toFixed(2);
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return `${Math.round(value * 1000) / 10}%`;
}

function goalMetricForInsight(insight: InsightUnit) {
  if (insight.primary_evidence_metric === "driver_result_c_rate") return "driver_result_c_count";
  if (insight.primary_evidence_metric === "strategy_issue_count") return "strategy_issue_count";
  if (insight.primary_evidence_metric === "three_putt_rate") return "three_putt_holes";
  if (insight.primary_evidence_metric === "penalty_strokes") return "penalties_total";
  if (insight.category === "putting") return "three_putt_holes";
  if (insight.category === "penalty_impact") return "penalties_total";
  return "score_to_par";
}

function practiceSuggestionsForInsight(
  insight: InsightUnit,
  t: (key: MessageKey) => string,
): PracticeSuggestion[] {
  const metric = goalMetricForInsight(insight);
  const categoryPlan = categoryPracticePlan(insight.category, t);

  return [
    buildPracticeSuggestion({
      id: "focused",
      insight,
      metric,
      title: categoryPlan.focusTitle,
      summary: insight.next_action || categoryPlan.focusSummary,
      routine: categoryPlan.focusRoutine,
      goalTarget: categoryPlan.goalTarget,
      t,
    }),
    buildPracticeSuggestion({
      id: "pressure",
      insight,
      metric,
      title: categoryPlan.pressureTitle,
      summary: categoryPlan.pressureSummary,
      routine: categoryPlan.pressureRoutine,
      goalTarget: categoryPlan.goalTarget,
      t,
    }),
  ];
}

function buildPracticeSuggestion({
  id,
  insight,
  metric,
  title,
  summary,
  routine,
  goalTarget,
  t,
}: {
  id: string;
  insight: InsightUnit;
  metric: string;
  title: string;
  summary: string;
  routine: string[];
  goalTarget: number;
  t: (key: MessageKey) => string;
}): PracticeSuggestion {
  return {
    id,
    title,
    summary,
    routine,
    goalTitle: `${t("nextRoundGoalPrefix")} ${insight.problem}`,
    goalMetric: metric,
    goalTarget,
    payload: {
      source_insight_id: insight.id.startsWith("suggested-") ? undefined : insight.id,
      title,
      purpose: summary,
      category: insight.category,
      drill_json: {
        source: "insight_suggestion",
        suggestion_id: id,
        routine,
      },
      target_json: {
        metric_key: metric,
        target_operator: "<=",
        target_value: goalTarget,
      },
    },
  };
}

function compactInsights(insights: InsightUnit[], limit: number) {
  const selected: InsightUnit[] = [];
  const seen = new Set<string>();
  for (const insight of [...insights].sort((a, b) => b.priority_score - a.priority_score)) {
    const key = [
      insight.dedupe_key || "",
      insight.category,
      insight.root_cause,
      insight.primary_evidence_metric,
      normalizeInsightText(insight.problem),
    ].join("|");
    if (seen.has(key)) continue;
    seen.add(key);
    selected.push(insight);
    if (selected.length >= limit) break;
  }
  return selected;
}

function normalizeInsightText(value: string) {
  return value.toLowerCase().replace(/\s+/g, " ").trim();
}

function shortenText(value: string, maxLength: number) {
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 1).trim()}…`;
}

function fallbackInsights(
  trend: AnalyticsTrend,
  activeTab: string,
  t: (key: MessageKey) => string,
): InsightUnit[] {
  const rows = activeTab === "all"
    ? trend.category_summary.slice(0, 3)
    : trend.category_summary.filter((row) => row.category === activeTab).slice(0, 1);
  return rows.map((row) => ({
    id: `suggested-${row.category}`,
    round_id: null,
    scope_type: "analysis",
    scope_key: row.category,
    category: row.category,
    root_cause: "category_loss",
    primary_evidence_metric: "shot_value",
    dedupe_key: `suggested-${row.category}`,
    problem: `${categoryLabel(row.category, t)} ${t("suggestedInsight")}`,
    evidence: `${t("generatedFromAnalysis")} ${t("totalValue")}: ${formatNumber(row.total_shot_value)}, ${t("shots")}: ${row.count}.`,
    impact: row.total_shot_value < 0 ? t("categoryLossHint") : t("categoryPracticeHint"),
    next_action: `${categoryLabel(row.category, t)}: ${t("convertToPracticePlan")}`,
    confidence: row.count >= 10 ? "medium" : "low",
    priority_score: Math.abs(row.total_shot_value),
    status: "suggested",
  }));
}

function categoryPracticePlan(category: string, t: (key: MessageKey) => string) {
  const plans: Record<string, {
    focusTitle: string;
    focusSummary: string;
    focusRoutine: string[];
    pressureTitle: string;
    pressureSummary: string;
    pressureRoutine: string[];
    goalTarget: number;
  }> = {
    putting: {
      focusTitle: t("puttingFocusPlan"),
      focusSummary: t("puttingFocusSummary"),
      focusRoutine: [t("puttingRoutineOne"), t("puttingRoutineTwo"), t("puttingRoutineThree")],
      pressureTitle: t("puttingPressurePlan"),
      pressureSummary: t("puttingPressureSummary"),
      pressureRoutine: [t("puttingPressureOne"), t("puttingPressureTwo"), t("puttingPressureThree")],
      goalTarget: 1,
    },
    off_the_tee: {
      focusTitle: t("teeFocusPlan"),
      focusSummary: t("teeFocusSummary"),
      focusRoutine: [t("teeRoutineOne"), t("teeRoutineTwo"), t("teeRoutineThree")],
      pressureTitle: t("teePressurePlan"),
      pressureSummary: t("teePressureSummary"),
      pressureRoutine: [t("teePressureOne"), t("teePressureTwo"), t("teePressureThree")],
      goalTarget: 1,
    },
    penalty_impact: {
      focusTitle: t("penaltyFocusPlan"),
      focusSummary: t("penaltyFocusSummary"),
      focusRoutine: [t("penaltyRoutineOne"), t("penaltyRoutineTwo"), t("penaltyRoutineThree")],
      pressureTitle: t("penaltyPressurePlan"),
      pressureSummary: t("penaltyPressureSummary"),
      pressureRoutine: [t("penaltyPressureOne"), t("penaltyPressureTwo"), t("penaltyPressureThree")],
      goalTarget: 1,
    },
  };

  return plans[category] ?? {
    focusTitle: t("scoreFocusPlan"),
    focusSummary: t("scoreFocusSummary"),
    focusRoutine: [t("scoreRoutineOne"), t("scoreRoutineTwo"), t("scoreRoutineThree")],
    pressureTitle: t("scorePressurePlan"),
    pressureSummary: t("scorePressureSummary"),
    pressureRoutine: [t("scorePressureOne"), t("scorePressureTwo"), t("scorePressureThree")],
    goalTarget: 1,
  };
}
