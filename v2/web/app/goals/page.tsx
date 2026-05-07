"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import {
  createGoal,
  evaluateGoal,
  getGoals,
  manuallyEvaluateGoal,
  type RoundGoal,
} from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const metricOptions = ["three_putt_holes", "penalties_total", "tee_penalties", "putts_total", "score_to_par"];

export default function GoalsPage() {
  const { t } = useI18n();
  const [goals, setGoals] = useState<RoundGoal[]>([]);
  const [title, setTitle] = useState("");
  const [metricKey, setMetricKey] = useState("three_putt_holes");
  const [targetValue, setTargetValue] = useState("1");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      setGoals(await getGoals());
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
        category: metricKey.includes("putt") ? "putting" : "score",
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
    try {
      const evaluation = await evaluateGoal(goal.id);
      setStatus(`${t("goalEvaluated")} ${evaluation.evaluation_status}`);
      await load();
    } catch (evaluationError) {
      setError(evaluationError instanceof Error ? evaluationError.message : "Goal evaluation failed");
    }
  }

  async function manualPartial(goal: RoundGoal) {
    setError("");
    try {
      await manuallyEvaluateGoal(goal.id, {
        evaluation_status: "partial",
        note: "Manual partial evaluation.",
      });
      setStatus(t("goalEvaluated"));
      await load();
    } catch (evaluationError) {
      setError(evaluationError instanceof Error ? evaluationError.message : "Manual evaluation failed");
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
                  {option}
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
                      {goal.category} · {goal.status}
                    </p>
                    <h3 className="mt-1 font-semibold">{goal.title}</h3>
                    <p className="mt-2 text-sm text-muted">
                      {t("metric")}: {goal.metric_key} · {t("target")}: {goal.target_operator} {goal.target_value}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button className={secondaryButton} onClick={() => runEvaluation(goal)}>
                      {t("evaluate")}
                    </button>
                    <button className={secondaryButton} onClick={() => manualPartial(goal)}>
                      {t("manualEvaluation")}
                    </button>
                  </div>
                </div>
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
