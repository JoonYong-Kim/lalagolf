"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import { getRound, type RoundDetail } from "@/lib/api";
import { useI18n, type MessageKey } from "@/lib/i18n";

type RoundComparisonMetric = {
  key: string;
  label: string;
  baseline: number | null;
  target: number | null;
  lowerIsBetter: boolean;
  format?: "number" | "percent";
  baselineDisplay?: string;
  targetDisplay?: string;
};

type RoundComparison = {
  mode: "two_rounds" | "average_vs_round";
  baselineLabel: string;
  targetLabel: string;
  metrics: RoundComparisonMetric[];
};

export default function RoundComparePage() {
  const [comparison, setComparison] = useState<RoundComparison | null>(null);
  const [roundCount, setRoundCount] = useState(0);
  const [error, setError] = useState("");
  const { locale, t } = useI18n();

  useEffect(() => {
    async function loadComparison() {
      setError("");
      try {
        const params = new URLSearchParams(window.location.search);
        const roundIds = (params.get("roundIds") ?? "").split(",").filter(Boolean);
        setRoundCount(roundIds.length);
        if (roundIds.length < 2) {
          setComparison(null);
          return;
        }
        const rounds = await Promise.all(roundIds.map((roundId) => getRound(roundId)));
        setComparison(buildRoundComparison(rounds, t));
      } catch (comparisonError) {
        setError(comparisonError instanceof Error ? comparisonError.message : t("loadingRounds"));
      }
    }

    loadComparison();
  }, [locale]);

  return (
    <AppShell eyebrow={t("roundArchive")} title={t("roundComparison")}>
      <div className="mt-5 space-y-5">
        {error && (
          <div className="rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">
            {error}
          </div>
        )}

        <section className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold">
                {t("selectedRounds")} ({roundCount})
              </p>
              <p className="mt-1 text-sm text-muted">
                {comparison?.mode === "average_vs_round"
                  ? `${t("baselineAverage")} vs ${t("targetRound")}`
                  : "2 rounds"}
              </p>
            </div>
            <Link className="rounded-md border border-line px-3 py-2 text-sm font-semibold" href="/rounds">
              {t("rounds")}
            </Link>
          </div>
        </section>

        {comparison ? (
          <RoundComparisonTable comparison={comparison} t={t} />
        ) : (
          <section className="rounded-md border border-line bg-white p-4 text-sm text-muted">
            {t("selectAtLeastTwoRounds")}
          </section>
        )}
      </div>
    </AppShell>
  );
}

function RoundComparisonTable({
  comparison,
  t,
}: {
  comparison: RoundComparison;
  t: (key: MessageKey) => string;
}) {
  return (
    <section className="rounded-md border border-line bg-white">
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-base font-semibold">{t("roundComparison")}</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="bg-surface text-muted">
            <tr>
              <th className="px-4 py-2 font-medium">{t("category")}</th>
              <th className="px-4 py-2 font-medium">{comparison.baselineLabel}</th>
              <th className="px-4 py-2 font-medium">{comparison.targetLabel}</th>
              <th className="px-4 py-2 font-medium">{t("difference")}</th>
            </tr>
          </thead>
          <tbody>
            {comparison.metrics.map((metric) => {
              const delta = metric.baseline === null || metric.target === null ? null : metric.target - metric.baseline;
              const improved = delta === null || delta === 0 ? null : metric.lowerIsBetter ? delta < 0 : delta > 0;
              return (
                <tr className="border-t border-line" key={metric.key}>
                  <td className="px-4 py-3 font-medium">{metric.label}</td>
                  <td className="px-4 py-3">{metric.baselineDisplay ?? formatComparable(metric.baseline, metric.format)}</td>
                  <td className="px-4 py-3">{metric.targetDisplay ?? formatComparable(metric.target, metric.format)}</td>
                  <td className={improved === null ? "px-4 py-3 text-muted" : improved ? "px-4 py-3 text-green-700" : "px-4 py-3 text-[#b42318]"}>
                    {delta === null ? "-" : `${formatSignedDelta(delta, metric.format)} ${improved === null ? "" : improved ? t("better") : t("worse")}`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function buildRoundComparison(rounds: RoundDetail[], t: (key: MessageKey) => string): RoundComparison | null {
  const completed = rounds
    .filter((round) => round.total_score !== null)
    .sort((a, b) => a.play_date.localeCompare(b.play_date));
  if (completed.length < 2) return null;

  const target = completed[completed.length - 1];
  const baselineRounds = completed.length === 2 ? [completed[0]] : completed.slice(0, -1);
  const baselineLabel = completed.length === 2
    ? roundLabel(baselineRounds[0])
    : `${baselineRounds.length} ${t("baselineAverage")}`;

  return {
    mode: completed.length === 2 ? "two_rounds" : "average_vs_round",
    baselineLabel,
    targetLabel: roundLabel(target),
    metrics: [
      comparisonMetric("score", t("score"), averageMetric(baselineRounds, (round) => round.total_score), target.total_score, true),
      comparisonMetric("putts", t("putts"), averageMetric(baselineRounds, (round) => round.metrics.putts_total ?? null), target.metrics.putts_total ?? null, true),
      comparisonMetric("puttsPerHole", t("puttsPerHole"), averageMetric(baselineRounds, puttsPerHole), puttsPerHole(target), true),
      comparisonMetric("threePutts", t("threePutts"), averageMetric(baselineRounds, threePuttHoles), threePuttHoles(target), true),
      girMetric(baselineRounds, target, t),
      comparisonMetric("fairwayHitRate", t("fairwayHitRate"), averageMetric(baselineRounds, fairwayHitRate), fairwayHitRate(target), false, "percent"),
      comparisonMetric("resultC", t("resultC"), averageMetric(baselineRounds, resultCShots), resultCShots(target), true),
      comparisonMetric("feelC", t("feelC"), averageMetric(baselineRounds, feelCShots), feelCShots(target), true),
      comparisonMetric("driverResultC", t("driverResultC"), averageMetric(baselineRounds, driverResultCRate), driverResultCRate(target), true, "percent"),
      comparisonMetric("technicalMiss", t("technicalMiss"), averageMetric(baselineRounds, technicalMissShots), technicalMissShots(target), true),
      comparisonMetric("strategyIssue", t("strategyIssue"), averageMetric(baselineRounds, strategyIssueShots), strategyIssueShots(target), true),
      comparisonMetric("luckyResult", t("luckyResult"), averageMetric(baselineRounds, luckyResultShots), luckyResultShots(target), true),
      comparisonMetric("penalties", t("penalty"), averageMetric(baselineRounds, (round) => round.metrics.penalties_total ?? null), target.metrics.penalties_total ?? null, true),
      comparisonMetric("penaltyHoles", t("penaltyHoles"), averageMetric(baselineRounds, penaltyHoles), penaltyHoles(target), true),
      comparisonMetric("birdies", t("birdie"), averageMetric(baselineRounds, birdieOrBetterHoles), birdieOrBetterHoles(target), false),
      comparisonMetric("pars", t("par"), averageMetric(baselineRounds, parHoles), parHoles(target), false),
      comparisonMetric("bogeys", t("bogey"), averageMetric(baselineRounds, bogeyHoles), bogeyHoles(target), true),
      comparisonMetric("doubleBogeyOrWorse", t("doubleBogeyOrWorse"), averageMetric(baselineRounds, doubleBogeyOrWorseHoles), doubleBogeyOrWorseHoles(target), true),
    ],
  };
}

function comparisonMetric(
  key: RoundComparisonMetric["key"],
  label: string,
  baseline: number | null,
  target: number | null,
  lowerIsBetter: boolean,
  format: "number" | "percent" = "number",
): RoundComparisonMetric {
  return { key, label, baseline, target, lowerIsBetter, format };
}

function girMetric(baselineRounds: RoundDetail[], target: RoundDetail, t: (key: MessageKey) => string): RoundComparisonMetric {
  const baseline = averageMetric(baselineRounds, (round) => round.metrics.gir_count ?? null);
  const targetValue = target.metrics.gir_count ?? null;
  return {
    ...comparisonMetric("gir", t("gir"), baseline, targetValue, false),
    baselineDisplay: formatGirValue(baseline, averageMetric(baselineRounds, girRate)),
    targetDisplay: formatGirValue(targetValue, girRate(target)),
  };
}

function averageMetric(rounds: RoundDetail[], select: (round: RoundDetail) => number | null | undefined) {
  const values = rounds.map(select).filter((value): value is number => typeof value === "number");
  if (values.length === 0) return null;
  return Math.round((values.reduce((sum, value) => sum + value, 0) / values.length) * 10) / 10;
}

function roundLabel(round: RoundDetail) {
  return `${round.play_date} ${round.course_name}`;
}

function puttsPerHole(round: RoundDetail) {
  const putts = round.holes
    .map((hole) => hole.putts)
    .filter((value): value is number => typeof value === "number");
  if (putts.length === 0) return null;
  return putts.reduce((sum, value) => sum + value, 0) / putts.length;
}

function threePuttHoles(round: RoundDetail) {
  return round.holes.filter((hole) => typeof hole.putts === "number" && hole.putts >= 3).length;
}

function girRate(round: RoundDetail) {
  if (round.holes.length === 0) return null;
  return round.holes.filter((hole) => hole.gir === true).length / round.holes.length;
}

function fairwayHitRate(round: RoundDetail) {
  if (typeof round.metrics.fairway_hit_rate === "number") return round.metrics.fairway_hit_rate;
  const fairways = round.holes
    .filter((hole) => hole.par >= 4)
    .map((hole) => hole.shots.find((shot) => shot.shot_number === 1))
    .filter((shot) => shot?.start_lie === "T" && shot.end_lie !== null);
  if (fairways.length === 0) return null;
  return fairways.filter((shot) => shot?.end_lie === "F").length / fairways.length;
}

function resultCShots(round: RoundDetail) {
  return qualityShots(round).filter((shot) => grade(shot.result_grade) === "C").length;
}

function feelCShots(round: RoundDetail) {
  return qualityShots(round).filter((shot) => grade(shot.feel_grade) === "C").length;
}

function driverResultCRate(round: RoundDetail) {
  const driverTeeShots = round.holes
    .flatMap((hole) => hole.shots.filter((shot) => shot.shot_number === 1 && hole.par >= 4 && (shot.club_normalized ?? shot.club) === "D"));
  if (driverTeeShots.length === 0) return null;
  return driverTeeShots.filter((shot) => grade(shot.result_grade) === "C").length / driverTeeShots.length;
}

function technicalMissShots(round: RoundDetail) {
  return qualityShots(round).filter((shot) => grade(shot.feel_grade) === "C" && grade(shot.result_grade) === "C").length;
}

function strategyIssueShots(round: RoundDetail) {
  return qualityShots(round).filter((shot) => {
    const feel = grade(shot.feel_grade);
    return (feel === "A" || feel === "B") && grade(shot.result_grade) === "C";
  }).length;
}

function luckyResultShots(round: RoundDetail) {
  return qualityShots(round).filter((shot) => {
    const result = grade(shot.result_grade);
    return grade(shot.feel_grade) === "C" && (result === "A" || result === "B");
  }).length;
}

function qualityShots(round: RoundDetail) {
  return round.holes
    .flatMap((hole) => hole.shots)
    .filter((shot) => (shot.club_normalized ?? shot.club) !== "P");
}

function grade(value: string | null | undefined): "A" | "B" | "C" | null {
  const normalized = (value ?? "").toUpperCase();
  return normalized === "A" || normalized === "B" || normalized === "C" ? normalized : null;
}

function penaltyHoles(round: RoundDetail) {
  return round.holes.filter((hole) => hole.penalties > 0).length;
}

function birdieOrBetterHoles(round: RoundDetail) {
  return scoreDiffCount(round, (diff) => diff <= -1);
}

function parHoles(round: RoundDetail) {
  return scoreDiffCount(round, (diff) => diff === 0);
}

function bogeyHoles(round: RoundDetail) {
  return scoreDiffCount(round, (diff) => diff === 1);
}

function doubleBogeyOrWorseHoles(round: RoundDetail) {
  return scoreDiffCount(round, (diff) => diff >= 2);
}

function scoreDiffCount(round: RoundDetail, predicate: (diff: number) => boolean) {
  return round.holes.filter((hole) => typeof hole.score === "number" && predicate(hole.score - hole.par)).length;
}

function formatComparable(value: number | null, format: "number" | "percent" = "number") {
  if (value === null) return "-";
  if (format === "percent") return `${Math.round(value * 1000) / 10}%`;
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function formatGirValue(count: number | null, rate: number | null) {
  if (count === null) return "-";
  const countText = Number.isInteger(count) ? String(count) : count.toFixed(1);
  return rate === null ? countText : `${countText} (${Math.round(rate * 1000) / 10}%)`;
}

function formatSignedDelta(value: number, format: "number" | "percent" = "number") {
  const rounded = Math.round(value * 10) / 10;
  if (format === "percent") {
    const percent = Math.round(value * 1000) / 10;
    return percent > 0 ? `+${percent}%` : `${percent}%`;
  }
  const formatted = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
  return rounded > 0 ? `+${formatted}` : formatted;
}
