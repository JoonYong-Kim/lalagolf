"use client";

import { useEffect, useMemo, useState } from "react";

import Link from "next/link";

import { AppShell } from "@/app/components/AppShell";
import { EmptyState } from "@/app/components/EmptyState";
import {
  createGoal,
  createPracticePlan,
  getAnalyticsTrends,
  getRound,
  getRoundAnalytics,
  getRounds,
  updateInsightStatus,
  type AnalyticsTrend,
  type AnalysisItemSummary,
  type InsightUnit,
  type RoundAnalytics,
  type RoundDetail,
  type ShotQualitySummary,
} from "@/lib/api";
import { useI18n, type MessageKey } from "@/lib/i18n";

const tabs = ["all", "off_the_tee", "short_game", "control_shot", "iron_shot", "putting", "recovery", "penalty_impact", "shot_quality"];

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
  const visibleItemRows = useMemo(() => {
    if (!trend || activeTab === "all") return [];
    return (trend.item_summary ?? []).filter((row) => row.group === activeTab);
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

        {trend && trend.kpis.round_count === 0 && (
          <EmptyState
            action={
              <Link
                className="rounded-md bg-green-700 px-4 py-2 text-sm font-semibold text-white"
                href="/rounds"
              >
                {t("goToRounds")}
              </Link>
            }
            description={t("noAnalysisYetHint")}
            title={t("noAnalysisYet")}
          />
        )}

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
              <h2 className="text-base font-semibold">
                {activeTab === "all" ? t("categorySummary") : t("itemSummary")}
              </h2>
            </div>
            <div className="overflow-x-auto">
              {activeTab === "all" ? (
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
              ) : (
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="bg-surface text-muted">
                    <tr>
                      <th className="px-4 py-2 font-medium">{t("item")}</th>
                      <th className="px-4 py-2 font-medium">{t("shots")}</th>
                      <th className="px-4 py-2 font-medium">{t("avgValue")}</th>
                      <th className="px-4 py-2 font-medium">{itemMetricLabels(activeTab, t)[0]}</th>
                      <th className="px-4 py-2 font-medium">{itemMetricLabels(activeTab, t)[1]}</th>
                      {activeTab === "penalty_impact" && (
                        <th className="px-4 py-2 font-medium">{t("goodFeelPenalty")}</th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {visibleItemRows.map((row) => (
                      <tr className="border-t border-line" key={`${row.group}-${row.item}`}>
                        <td className="px-4 py-3 font-medium">{itemLabel(row.item, t)}</td>
                        <td className="px-4 py-3">{row.count}</td>
                        <td className="px-4 py-3">{formatNumber(row.avg_shot_value)}</td>
                        {itemMetricCells(row, activeTab, t)}
                      </tr>
                    ))}
                    {trend && visibleItemRows.length === 0 && (
                      <tr>
                        <td className="px-4 py-6 text-muted" colSpan={activeTab === "penalty_impact" ? 6 : 5}>
                          {t("noAnalysisRows")}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              )}
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
    shot_quality: t("shotQuality"),
  };
  return labels[category] ?? category;
}

function itemLabel(item: string, t: (key: MessageKey) => string) {
  const keys: Record<string, MessageKey> = {
    putt_0_2: "putt_0_2",
    putt_2_7: "putt_2_7",
    putt_7_10: "putt_7_10",
    putt_10_20: "putt_10_20",
    putt_20_plus: "putt_20_plus",
    putt_unknown: "putt_unknown",
    short_0_10: "short_0_10",
    short_10_20: "short_10_20",
    short_20_30: "short_20_30",
    short_30_40: "short_30_40",
    short_chip: "short_chip",
    mid_approach: "mid_approach",
    long_approach: "long_approach",
    control_40_60: "control_40_60",
    control_60_75: "control_60_75",
    control_75_90: "control_75_90",
    long_iron: "long_iron",
    pitching_wedge: "pitching_wedge",
    other_iron: "other_iron",
    driver: "driver",
    wood_utility: "wood_utility",
    iron_tee: "iron_tee",
    other_tee: "other_tee",
    rough: "rough",
    bunker: "bunker",
    hazard: "hazard",
    trouble: "trouble",
    other_recovery: "other_recovery",
    greenside_bunker: "greenside_bunker",
    fairway_bunker: "fairway_bunker",
    ob: "ob",
    hazard_penalty: "hazard_penalty",
    unplayable: "unplayable",
    tee_penalty: "tee_penalty",
    other_penalty: "other_penalty",
    tee_ob: "tee_ob",
    tee_hazard: "tee_hazard",
    tee_other_penalty: "tee_other_penalty",
    non_tee_ob: "non_tee_ob",
    non_tee_hazard: "non_tee_hazard",
    non_tee_other_penalty: "non_tee_other_penalty",
    strategy_issue: "strategyIssue",
    technical_miss: "technicalMiss",
    lucky_result: "luckyResult",
    reproducible_shot: "reproducibleShot",
    high_risk_shot: "high_risk_shot",
  };
  if (item in keys) return t(keys[item]);
  return item.replaceAll("_", " ");
}

function itemMetricLabels(activeTab: string, t: (key: MessageKey) => string) {
  if (activeTab === "putting") return [t("made"), t("conceded")];
  if (activeTab === "recovery") return [t("recovered"), t("failedRecovery")];
  if (activeTab === "penalty_impact") return [t("obPenalty"), t("hazardPenalty")];
  if (activeTab === "shot_quality") return [t("rate"), t("primaryClub")];
  if (activeTab === "short_game") return [t("upAndDownChance"), t("upAndDownSuccess")];
  return [t("resultC"), t("penalty")];
}

function itemMetricCells(row: AnalysisItemSummary, activeTab: string, t: (key: MessageKey) => string) {
  if (activeTab === "putting") {
    return (
      <>
        <td className="px-4 py-3">{row.made_count ?? 0} ({formatPercent(row.made_rate)})</td>
        <td className="px-4 py-3">{row.ok_count ?? 0} ({formatPercent(row.ok_rate)})</td>
      </>
    );
  }
  if (activeTab === "recovery") {
    return (
      <>
        <td className="px-4 py-3">{row.recovered_count ?? 0} ({formatPercent(row.recovered_rate)})</td>
        <td className="px-4 py-3">{row.failed_recovery_count ?? 0} ({formatPercent(row.failed_recovery_rate)})</td>
      </>
    );
  }
  if (activeTab === "penalty_impact") {
    return (
      <>
        <td className="px-4 py-3">
          {row.ob_count ?? 0} ({formatPercent(row.ob_rate)})
        </td>
        <td className="px-4 py-3">
          {row.hazard_count ?? 0} ({formatPercent(row.hazard_rate)})
        </td>
        <td className="px-4 py-3">
          {row.good_feel_penalty_count ?? 0} ({formatPercent(row.good_feel_penalty_rate)})
        </td>
      </>
    );
  }
  if (activeTab === "shot_quality") {
    return (
      <>
        <td className="px-4 py-3">{formatPercent(row.item_rate)}</td>
        <td className="px-4 py-3">{row.primary_club_group ?? "-"}</td>
      </>
    );
  }
  if (activeTab === "short_game") {
    return (
      <>
        <td className="px-4 py-3">{row.up_and_down_chance_count ?? 0}</td>
        <td className="px-4 py-3">
          {row.up_and_down_success_count ?? 0} ({formatPercent(row.up_and_down_success_rate)})
        </td>
      </>
    );
  }
  return (
    <>
      <td className="px-4 py-3">{row.result_c_count} ({formatPercent(row.result_c_rate)})</td>
      <td className="px-4 py-3">{row.penalty_count} ({formatPercent(row.penalty_rate)})</td>
    </>
  );
}

async function selectedRoundTrend(roundIds: string[], locale: "ko" | "en"): Promise<AnalyticsTrend> {
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
    item_summary: buildItemSummary(rounds, analytics.flatMap((item) => item.shot_values)),
    shot_quality_summary: buildShotQualitySummary(rounds),
    insights: analytics.flatMap((item) => item.insights),
  };
  return trend;
}

function buildItemSummary(rounds: RoundDetail[], shotValues: RoundAnalytics["shot_values"]): AnalysisItemSummary[] {
  const shotValueById = new Map(shotValues.map((value) => [value.shot_id, value]));
  const buckets = new Map<string, AnalysisItemSummary>();
  for (const round of rounds) {
    for (const hole of round.holes) {
      for (const shot of hole.shots) {
        for (const [group, item] of analysisItemsForShot(shot, hole.par)) {
          const key = `${group}:${item}`;
          const bucket = buckets.get(key) ?? {
            group,
            item,
            count: 0,
            total_shot_value: 0,
            avg_shot_value: 0,
            result_c_count: 0,
            feel_c_count: 0,
            penalty_count: 0,
            made_count: 0,
            ok_count: 0,
            recovered_count: 0,
            failed_recovery_count: 0,
            ob_count: 0,
            hazard_count: 0,
            good_feel_penalty_count: 0,
            item_rate: null,
            primary_club_group: null,
            up_and_down_chance_count: 0,
            up_and_down_success_count: 0,
            result_c_rate: null,
            feel_c_rate: null,
            penalty_rate: null,
            made_rate: null,
            ok_rate: null,
            recovered_rate: null,
            failed_recovery_rate: null,
            ob_rate: null,
            hazard_rate: null,
            good_feel_penalty_rate: null,
            up_and_down_success_rate: null,
          };
          bucket.count += 1;
          bucket.total_shot_value += shotValueById.get(shot.id)?.shot_value ?? 0;
          if (grade(shot.result_grade) === "C") bucket.result_c_count += 1;
          if (grade(shot.feel_grade) === "C") bucket.feel_c_count += 1;
          if (shot.penalty_strokes > 0) bucket.penalty_count += 1;
          if (group === "putting") {
            if (puttOk(shot)) bucket.ok_count = (bucket.ok_count ?? 0) + 1;
            else if (puttMade(shot, hole.shots)) bucket.made_count = (bucket.made_count ?? 0) + 1;
          }
          if (group === "recovery") {
            if (recoverySuccess(shot)) bucket.recovered_count = (bucket.recovered_count ?? 0) + 1;
            else bucket.failed_recovery_count = (bucket.failed_recovery_count ?? 0) + 1;
          }
          if (group === "penalty_impact") {
            const penaltyType = (shot.penalty_type ?? "").toUpperCase();
            if (penaltyType === "OB") bucket.ob_count = (bucket.ob_count ?? 0) + 1;
            if (penaltyType === "H") bucket.hazard_count = (bucket.hazard_count ?? 0) + 1;
            const feel = grade(shot.feel_grade);
            if (feel === "A" || feel === "B") {
              bucket.good_feel_penalty_count = (bucket.good_feel_penalty_count ?? 0) + 1;
            }
          }
          if (group === "shot_quality") {
            bucket.primary_club_group = bucket.primary_club_group ?? clubGroup(shot.club_normalized ?? shot.club);
          }
          if (group === "short_game") {
            bucket.up_and_down_chance_count = (bucket.up_and_down_chance_count ?? 0) + 1;
            if (upAndDownSuccess(hole)) {
              bucket.up_and_down_success_count = (bucket.up_and_down_success_count ?? 0) + 1;
            }
          }
          buckets.set(key, bucket);
        }
      }
    }
  }
  return [...buckets.values()].map((row) => ({
    ...row,
    total_shot_value: Math.round(row.total_shot_value * 1000) / 1000,
    avg_shot_value: row.count ? Math.round((row.total_shot_value / row.count) * 1000) / 1000 : 0,
    result_c_rate: row.count ? row.result_c_count / row.count : null,
    feel_c_rate: row.count ? row.feel_c_count / row.count : null,
    penalty_rate: row.count ? row.penalty_count / row.count : null,
    made_rate: row.count ? (row.made_count ?? 0) / row.count : null,
    ok_rate: row.count ? (row.ok_count ?? 0) / row.count : null,
    recovered_rate: row.count ? (row.recovered_count ?? 0) / row.count : null,
    failed_recovery_rate: row.count ? (row.failed_recovery_count ?? 0) / row.count : null,
    ob_rate: row.count ? (row.ob_count ?? 0) / row.count : null,
    hazard_rate: row.count ? (row.hazard_count ?? 0) / row.count : null,
    good_feel_penalty_rate: row.count ? (row.good_feel_penalty_count ?? 0) / row.count : null,
    item_rate: row.group === "shot_quality" ? row.count / Math.max(1, qualityShotCount(rounds)) : null,
    up_and_down_success_rate: row.up_and_down_chance_count
      ? (row.up_and_down_success_count ?? 0) / row.up_and_down_chance_count
      : null,
  })).sort((a, b) => a.group.localeCompare(b.group) || a.total_shot_value - b.total_shot_value);
}

function analysisItemsForShot(
  shot: RoundDetail["holes"][number]["shots"][number],
  par: number,
): Array<[string, string]> {
  const club = (shot.club_normalized || shot.club || "").toUpperCase();
  const items: Array<[string, string]> = [];
  if (club === "P" || club === "PT") {
    items.push(["putting", puttingItem(shot.distance)]);
  } else if (shot.shot_number === 1 && par >= 4) {
    items.push(["off_the_tee", teeItem(club)]);
    if (shot.penalty_strokes > 0) items.push(["penalty_impact", penaltyItem(shot, true)]);
  } else if (shot.penalty_strokes > 0) {
    items.push(["penalty_impact", penaltyItem(shot, false)]);
  } else if (typeof shot.distance === "number" && shot.distance < 40) {
    items.push(["short_game", shortGameItem(shot)]);
  } else if (shot.start_lie === "R" || shot.start_lie === "B" || shot.start_lie === "H" || shot.start_lie === "O") {
    items.push(["recovery", recoveryItem(shot)]);
  } else if (typeof shot.distance === "number" && shot.distance < 90) {
    items.push(["control_shot", controlShotItem(shot.distance)]);
  } else if (typeof shot.distance === "number" && shot.distance >= 90) {
    items.push(["iron_shot", ironItem(club)]);
  }
  const quality = qualityItem(shot);
  if (quality) items.push(["shot_quality", quality]);
  return items;
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

function puttingItem(distance: number | null) {
  if (distance === null) return "putt_unknown";
  if (distance <= 2) return "putt_0_2";
  if (distance <= 7) return "putt_2_7";
  if (distance <= 10) return "putt_7_10";
  if (distance <= 20) return "putt_10_20";
  return "putt_20_plus";
}

function puttOk(shot: RoundDetail["holes"][number]["shots"][number]) {
  return (shot.raw_text ?? "").toUpperCase().split(/\s+/).includes("OK") || shot.score_cost > 1;
}

function puttMade(
  shot: RoundDetail["holes"][number]["shots"][number],
  shots: RoundDetail["holes"][number]["shots"],
) {
  const putts = shots.filter((item) => ["P", "PT"].includes((item.club_normalized ?? item.club ?? "").toUpperCase()));
  if (putts.length === 0) return false;
  return shot.id === putts.reduce((latest, item) => item.shot_number > latest.shot_number ? item : latest).id && !puttOk(shot);
}

function shortGameItem(shot: RoundDetail["holes"][number]["shots"][number]) {
  if ((shot.start_lie ?? "").toUpperCase() === "B") return "greenside_bunker";
  const distance = shot.distance;
  if (distance === null) return "short_unknown";
  if (distance < 10) return "short_chip";
  if (distance < 25) return "mid_approach";
  return "long_approach";
}

function upAndDownSuccess(hole: RoundDetail["holes"][number]) {
  return typeof hole.score === "number" && hole.score <= hole.par;
}

function controlShotItem(distance: number | null) {
  if (distance === null) return "control_unknown";
  if (distance < 60) return "control_40_60";
  if (distance < 75) return "control_60_75";
  return "control_75_90";
}

function ironItem(club: string) {
  if (club === "I3" || club === "I4") return "long_iron";
  if (["I5", "I6", "I7", "I8", "I9"].includes(club)) return club;
  if (["IP", "IW", "IA", "PW"].includes(club)) return "pitching_wedge";
  return "other_iron";
}

function teeItem(club: string) {
  if (club === "D") return "driver";
  if (club.startsWith("W") || club.startsWith("U")) return "wood_utility";
  if (club.startsWith("I")) return "iron_tee";
  return "other_tee";
}

function recoveryItem(shot: RoundDetail["holes"][number]["shots"][number]) {
  const startLie = (shot.start_lie ?? "").toUpperCase();
  if (startLie === "B") return typeof shot.distance === "number" && shot.distance < 40 ? "greenside_bunker" : "fairway_bunker";
  if (startLie === "R") return "rough";
  return "other_recovery";
}

function recoverySuccess(shot: RoundDetail["holes"][number]["shots"][number]) {
  return !["R", "B", "H", "O"].includes((shot.end_lie ?? "").toUpperCase());
}

function penaltyItem(shot: RoundDetail["holes"][number]["shots"][number], isTee: boolean) {
  const normalized = (shot.penalty_type ?? "").toUpperCase();
  const prefix = isTee ? "tee" : "non_tee";
  if (normalized === "OB") return `${prefix}_ob`;
  if (normalized === "H") return `${prefix}_hazard`;
  return `${prefix}_other_penalty`;
}

function qualityItem(shot: RoundDetail["holes"][number]["shots"][number]) {
  const feel = grade(shot.feel_grade);
  const result = grade(shot.result_grade);
  if (result === "C" || shot.penalty_strokes > 0) {
    if (feel === "A" || feel === "B") return "strategy_issue";
    if (feel === "C") return "technical_miss";
    return "high_risk_shot";
  }
  if (feel === "C" && (result === "A" || result === "B")) return "lucky_result";
  if ((feel === "A" || feel === "B") && (result === "A" || result === "B")) return "reproducible_shot";
  return null;
}

function qualityShotCount(rounds: RoundDetail[]) {
  return rounds.reduce(
    (sum, round) =>
      sum + round.holes.reduce(
        (holeSum, hole) =>
          holeSum + hole.shots.filter((shot) => !["P", "PT"].includes((shot.club_normalized ?? shot.club ?? "").toUpperCase())).length,
        0,
      ),
    0,
  );
}

function clubGroup(club: string | null | undefined) {
  const normalized = (club ?? "").toUpperCase();
  if (normalized === "D") return "D";
  if (normalized.startsWith("W")) return "W";
  if (normalized.startsWith("U")) return "U";
  if (["I3", "I4"].includes(normalized)) return "LI";
  if (["I5", "I6", "I7"].includes(normalized)) return "MI";
  if (normalized.startsWith("I") || ["48", "50", "52", "56", "58", "60"].includes(normalized)) return "SI";
  return "OTHER";
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
