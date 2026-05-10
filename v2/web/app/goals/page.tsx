"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import {
  createGoal,
  deleteGoal,
  evaluateGoal,
  getGoals,
  getRounds,
  manuallyEvaluateGoal,
  type RoundGoal,
  type RoundListItem,
} from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { MessageKey } from "@/lib/i18n";

const metricOptions = [
  "three_putt_holes",
  "putts_total",
  "score_to_par",
  "total_score",
  "penalties_total",
  "tee_penalties",
  "gir_count",
  "fairway_miss_count",
  "driver_result_c_count",
  "strategy_issue_count",
] as const;
const manualEvaluationStatuses = ["achieved", "missed", "partial", "not_evaluable"] as const;

type ManualEvaluationStatus = (typeof manualEvaluationStatuses)[number];

export default function GoalsPage() {
  const { t } = useI18n();
  const [goals, setGoals] = useState<RoundGoal[]>([]);
  const [rounds, setRounds] = useState<RoundListItem[]>([]);
  const [title, setTitle] = useState("");
  const [metricKey, setMetricKey] = useState("three_putt_holes");
  const [targetValue, setTargetValue] = useState("1");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [goalActionState, setGoalActionState] = useState<Record<string, { status: string; loading: boolean }>>({});
  const [openManualGoalId, setOpenManualGoalId] = useState<string | null>(null);
  const [manualEvaluationStatus, setManualEvaluationStatus] = useState<ManualEvaluationStatus>("partial");
  const [manualRoundId, setManualRoundId] = useState("");
  const [manualNote, setManualNote] = useState("");

  async function load() {
    setError("");
    try {
      const [loadedGoals, loadedRounds] = await Promise.all([getGoals(), getRounds({ limit: 20 })]);
      setGoals(loadedGoals);
      setRounds(loadedRounds.items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Goals load failed");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function submitGoal() {
    if (!title.trim()) return;
    setError("");
    try {
      await createGoal({
        title: title.trim(),
        category: goalCategoryForMetric(metricKey),
        metric_key: metricKey,
        target_operator: "<=",
        target_value: Number(targetValue),
        applies_to: "next_round",
      });
      setTitle("");
      setStatus(t("saved"));
      await load();
    } catch (goalError) {
      setError(goalError instanceof Error ? goalError.message : "Goal save failed");
    }
  }

  async function runEvaluation(goal: RoundGoal) {
    setError("");
    setGoalActionState((current) => ({
      ...current,
      [goal.id]: { status: t("goalAutoEvaluating"), loading: true },
    }));
    try {
      const evaluation = await evaluateGoal(goal.id);
      const label = evaluationStatusLabel(evaluation.evaluation_status as ManualEvaluationStatus, t);
      setStatus(`${t("goalAutoEvaluationDone")} ${label}`);
      setGoalActionState((current) => ({
        ...current,
        [goal.id]: { status: `${t("goalAutoEvaluationDone")} ${label}`, loading: false },
      }));
      await load();
    } catch (evaluationError) {
      setError(evaluationError instanceof Error ? evaluationError.message : "Goal evaluation failed");
      setGoalActionState((current) => ({
        ...current,
        [goal.id]: { status: t("goalEvaluationFailed"), loading: false },
      }));
    }
  }

  async function submitManualEvaluation(goal: RoundGoal) {
    setError("");
    setGoalActionState((current) => ({
      ...current,
      [goal.id]: { status: t("manualEvaluating"), loading: true },
    }));
    try {
      await manuallyEvaluateGoal(goal.id, {
        evaluation_status: manualEvaluationStatus,
        round_id: manualRoundId || undefined,
        note: manualNote.trim() || undefined,
      });
      setStatus(`${t("manualEvaluationSaved")} ${evaluationStatusLabel(manualEvaluationStatus, t)}`);
      setGoalActionState((current) => ({
        ...current,
        [goal.id]: {
          status: `${t("manualEvaluationSaved")} ${evaluationStatusLabel(manualEvaluationStatus, t)}`,
          loading: false,
        },
      }));
      setOpenManualGoalId(null);
      setManualRoundId("");
      setManualNote("");
      setManualEvaluationStatus("partial");
      await load();
    } catch (evaluationError) {
      setError(evaluationError instanceof Error ? evaluationError.message : "Manual evaluation failed");
      setGoalActionState((current) => ({
        ...current,
        [goal.id]: { status: t("goalEvaluationFailed"), loading: false },
      }));
    }
  }

  async function removeGoal(goal: RoundGoal) {
    const confirmed = window.confirm(`${goal.title}\n\n${t("deleteGoalConfirm")}`);
    if (!confirmed) return;
    setError("");
    try {
      await deleteGoal(goal.id);
      setStatus(t("goalDeleted"));
      await load();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Goal delete failed");
    }
  }

  return (
    <AppShell eyebrow={t("goals")} title={t("nextRoundGoals")}>
      <div className="mt-5 space-y-5">
        <section className="rounded-md border border-line bg-white p-4">
          <h2 className="text-base font-semibold">{t("createGoal")}</h2>
          <div className="mt-3 grid gap-3 md:grid-cols-[1fr_220px_120px_auto]">
            <input
              className={inputClass}
              placeholder={t("title")}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
            <select className={inputClass} value={metricKey} onChange={(event) => setMetricKey(event.target.value)}>
              {metricOptions.map((option) => (
                <option key={option} value={option}>
                  {goalMetricLabel(option, t)}
                </option>
              ))}
            </select>
            <input
              className={inputClass}
              type="number"
              value={targetValue}
              onChange={(event) => setTargetValue(event.target.value)}
            />
            <button className={primaryButton} onClick={submitGoal}>
              {t("saveEdits")}
            </button>
          </div>
          <div className="mt-4 rounded-md border border-line bg-surface p-3 text-xs leading-6 text-muted">
            <p className="font-semibold text-ink">{t("evaluate")}</p>
            <p>{t("goalEvaluationHelp")}</p>
            <p className="mt-2">
              {t("status")}: {t("goalStatusActive")} / {t("goalStatusAchieved")} / {t("goalStatusMissed")} / {t("goalStatusPartial")} / {t("goalStatusNotEvaluable")} / {t("goalStatusCancelled")}
            </p>
            <p className="mt-2">
              {t("manualEvaluation")}: {t("evaluationResult")} + {t("manualEvaluationNote")} + {t("manualEvaluationRound")}
            </p>
          </div>
        </section>

        <section className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold">{t("nextRoundGoals")}</h2>
          </div>
          <div className="divide-y divide-line">
            {goals.map((goal) => (
              <article className="p-4" key={goal.id}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase text-green-700">
                      {goalCategoryLabel(goal.category, t)} · {goalStatusLabel(goal.status, t)}
                    </p>
                    <h3 className="mt-1 font-semibold">{goal.title}</h3>
                    <p className="mt-2 text-sm text-muted">
                      {t("metric")}: {goalMetricLabel(goal.metric_key, t)} · {t("target")}: {goal.target_operator} {goal.target_value}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button className={secondaryButton} type="button" onClick={() => runEvaluation(goal)}>
                      {t("autoEvaluate")}
                    </button>
                    <button
                      className={secondaryButton}
                      type="button"
                      onClick={() => {
                        setOpenManualGoalId((current) => (current === goal.id ? null : goal.id));
                        setManualRoundId("");
                        setManualNote("");
                        setManualEvaluationStatus("partial");
                      }}
                    >
                      {t("manualEvaluation")}
                    </button>
                    <button className={dangerButton} type="button" onClick={() => removeGoal(goal)}>
                      {t("delete")}
                    </button>
                  </div>
                </div>
                <p className="mt-3 text-xs text-muted">
                  {t("goalEvaluationHelp")}
                </p>
                {openManualGoalId === goal.id && (
                  <div className="mt-3 rounded-md border border-line bg-surface p-4">
                    <div className="grid gap-4 lg:grid-cols-[180px_minmax(0,1fr)_280px]">
                      <label className="block text-xs font-medium text-muted">
                        {t("evaluationResult")}
                        <select
                          className={`${inputClass} mt-2 w-full`}
                          value={manualEvaluationStatus}
                          onChange={(event) => setManualEvaluationStatus(event.target.value as ManualEvaluationStatus)}
                        >
                          {manualEvaluationStatuses.map((value) => (
                            <option key={value} value={value}>
                              {evaluationStatusLabel(value, t)}
                            </option>
                          ))}
                        </select>
                        <p className="mt-2 leading-5 text-muted">
                          {manualEvaluationStatus === "achieved" && t("goalStatusAchieved")}
                          {manualEvaluationStatus === "missed" && t("goalStatusMissed")}
                          {manualEvaluationStatus === "partial" && t("goalStatusPartial")}
                          {manualEvaluationStatus === "not_evaluable" && t("goalStatusNotEvaluable")}
                        </p>
                      </label>

                      <label className="block text-xs font-medium text-muted">
                        {t("manualEvaluationNote")}
                        <textarea
                          className={`${inputClass} mt-2 min-h-[136px] w-full resize-y`}
                          value={manualNote}
                          onChange={(event) => setManualNote(event.target.value)}
                          placeholder={t("manualEvaluationNotePlaceholder")}
                        />
                      </label>

                      <div className="flex flex-col gap-3">
                        <label className="block text-xs font-medium text-muted">
                          {t("manualEvaluationRound")}
                          <select
                            className={`${inputClass} mt-2 w-full`}
                            value={manualRoundId}
                            onChange={(event) => setManualRoundId(event.target.value)}
                          >
                            <option value="">{t("manualEvaluationRoundOptional")}</option>
                            {rounds.map((round) => (
                              <option key={round.id} value={round.id}>
                                {formatRoundLabel(round)}
                              </option>
                            ))}
                          </select>
                        </label>
                        <div className="rounded-md border border-line bg-white p-3 text-xs leading-5 text-muted">
                          {t("manualEvaluationHelp")}
                        </div>
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                      <p className="text-xs text-muted">
                        {t("manualEvaluationHelp")}
                      </p>
                      <div className="flex gap-2">
                        <button
                          className={primaryButton}
                          type="button"
                          onClick={() => submitManualEvaluation(goal)}
                        >
                          {t("manualEvaluationSave")}
                        </button>
                        <button
                          className={secondaryButton}
                          type="button"
                          onClick={() => setOpenManualGoalId(null)}
                        >
                          {t("cancel")}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
                {goalActionState[goal.id]?.status && (
                  <p className="mt-2 text-xs font-medium text-green-700">
                    {goalActionState[goal.id]?.status}
                  </p>
                )}
              </article>
            ))}
            {goals.length === 0 && <p className="p-4 text-sm text-muted">{t("noGoals")}</p>}
          </div>
        </section>
      </div>
      {status && <p className="mt-4 text-sm text-muted">{status}</p>}
      {error && <p className="mt-4 rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">{error}</p>}
    </AppShell>
  );
}

const inputClass = "min-w-0 rounded-md border border-line px-3 py-2 text-sm";
const primaryButton = "rounded-md bg-green-700 px-4 py-2 text-sm font-semibold text-white";
const secondaryButton = "rounded-md border border-line px-3 py-1.5 text-sm font-semibold";
const dangerButton = "rounded-md border border-[#e4c0bd] bg-[#fff2f0] px-3 py-1.5 text-sm font-semibold text-[#a34242]";

function formatRoundLabel(round: RoundListItem) {
  return `${round.play_date} · ${round.course_name} · ${
    round.score_to_par === null || round.score_to_par === undefined
      ? "-"
      : round.score_to_par > 0
        ? `+${round.score_to_par}`
        : String(round.score_to_par)
  }`;
}

function goalCategoryForMetric(metricKey: string) {
  return metricKey === "putts_total" || metricKey === "three_putt_holes" ? "putting" : "score";
}

function goalCategoryLabel(category: string, t: (key: MessageKey) => string) {
  switch (category) {
    case "putting":
      return t("goalCategoryPutting");
    case "score":
      return t("goalCategoryScore");
    default:
      return category;
  }
}

function goalMetricLabel(metricKey: string, t: (key: MessageKey) => string) {
  switch (metricKey) {
    case "three_putt_holes":
      return t("goalMetricThreePuttHoles");
    case "putts_total":
      return t("goalMetricPuttsTotal");
    case "score_to_par":
      return t("goalMetricScoreToPar");
    case "total_score":
      return t("goalMetricTotalScore");
    case "penalties_total":
      return t("goalMetricPenaltiesTotal");
    case "tee_penalties":
      return t("goalMetricTeePenalties");
    case "gir_count":
      return t("goalMetricGirCount");
    case "fairway_miss_count":
      return t("goalMetricFairwayMissCount");
    case "driver_result_c_count":
      return t("goalMetricDriverResultCCount");
    case "strategy_issue_count":
      return t("goalMetricStrategyIssueCount");
    default:
      return metricKey;
  }
}

function goalStatusLabel(status: string, t: (key: MessageKey) => string) {
  switch (status) {
    case "active":
      return t("goalStatusActive");
    case "achieved":
      return t("goalStatusAchieved");
    case "missed":
      return t("goalStatusMissed");
    case "partial":
      return t("goalStatusPartial");
    case "not_evaluable":
      return t("goalStatusNotEvaluable");
    case "cancelled":
      return t("goalStatusCancelled");
    default:
      return status;
  }
}

function evaluationStatusLabel(status: ManualEvaluationStatus, t: (key: MessageKey) => string) {
  switch (status) {
    case "achieved":
      return t("goalStatusAchieved");
    case "missed":
      return t("goalStatusMissed");
    case "partial":
      return t("goalStatusPartial");
    case "not_evaluable":
      return t("goalStatusNotEvaluable");
  }
}
