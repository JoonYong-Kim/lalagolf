"use client";

import Link from "next/link";
import { use, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import {
  createShare,
  getRound,
  getRoundAnalytics,
  requestRoundRecalculation,
  type RoundAnalytics,
  type RoundDetail,
  type RoundHole,
} from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function RoundDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [round, setRound] = useState<RoundDetail | null>(null);
  const [analytics, setAnalytics] = useState<RoundAnalytics | null>(null);
  const [shareUrl, setShareUrl] = useState("");
  const [selectedHoleNumber, setSelectedHoleNumber] = useState(1);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const { t } = useI18n();

  useEffect(() => {
    getRound(id)
      .then((loaded) => {
        setRound(loaded);
        setSelectedHoleNumber(loaded.holes[0]?.hole_number ?? 1);
      })
      .catch((roundError) => {
        setError(roundError instanceof Error ? roundError.message : t("loadingRound"));
      });
    getRoundAnalytics(id).then(setAnalytics).catch(() => setAnalytics(null));
  }, [id]);

  const selectedHole = useMemo(
    () => round?.holes.find((hole) => hole.hole_number === selectedHoleNumber) ?? null,
    [round, selectedHoleNumber],
  );
  const shotValueById = useMemo(() => {
    const values = new Map<string, RoundAnalytics["shot_values"][number]>();
    for (const value of analytics?.shot_values ?? []) {
      values.set(value.shot_id, value);
    }
    return values;
  }, [analytics]);

  async function recalculate() {
    setStatus(t("requestingRecalculation"));
    setError("");
    try {
      const result = await requestRoundRecalculation(id);
      setRound((current) => current ? { ...current, computed_status: result.computed_status } : current);
      setStatus(t("recalculationQueued"));
    } catch (recalculateError) {
      setError(recalculateError instanceof Error ? recalculateError.message : t("requestingRecalculation"));
      setStatus("");
    }
  }

  async function shareRound() {
    setError("");
    try {
      const share = await createShare(id, round?.course_name);
      const url = `${window.location.origin}${share.url_path}`;
      setShareUrl(url);
      await navigator.clipboard?.writeText(url);
      setStatus(t("shareCreated"));
    } catch (shareError) {
      setError(shareError instanceof Error ? shareError.message : t("share"));
    }
  }

  return (
    <AppShell eyebrow={t("roundDetail")} title={round?.course_name ?? t("round")}>
      <div className="mt-5 space-y-5">
        {!round && !error && (
          <div className="rounded-md border border-line bg-white p-3 text-sm text-muted">
            {t("loadingRound")}
          </div>
        )}
        {error && <div className="rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">{error}</div>}

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Metric label={t("date")} value={round?.play_date ?? "-"} />
          <Metric label={t("score")} value={round?.total_score ?? "-"} />
          <Metric label={t("toPar")} value={formatToPar(round?.score_to_par)} />
          <Metric label={t("putts")} value={round?.metrics.putts_total ?? "-"} />
          <Metric label={t("status")} value={round?.computed_status ?? "-"} />
        </section>

        <section className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold">{t("roundAnalysis")}</h2>
          </div>
          <div className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4">
            {strokeGainedRows(analytics).map((row) => (
              <AnalysisMetric
                key={row.category}
                label={`${categoryLabel(row.category, t)} ${t("strokeGained")}`}
                total={row.total}
                count={row.count}
              />
            ))}
            {analytics && strokeGainedRows(analytics).length === 0 && (
              <p className="text-sm text-muted">{t("noAnalysisRows")}</p>
            )}
          </div>
          <div className="border-t border-line px-4 py-3 text-sm text-muted">
            {t("contributionFormula")}
          </div>
        </section>

        <section className="rounded-md border border-line bg-white">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold">{t("scorecard")}</h2>
            <div className="flex flex-wrap gap-2">
              {round?.upload_review_id && (
                <Link
                  className="rounded-md border border-line px-3 py-2 text-sm font-semibold"
                  href={`/upload/${round.upload_review_id}/review`}
                >
                  {t("editRawUpload")}
                </Link>
              )}
              <button className="rounded-md border border-line px-3 py-2 text-sm font-semibold" onClick={shareRound}>
                {t("share")}
              </button>
              <button className="rounded-md border border-line px-3 py-2 text-sm font-semibold" onClick={recalculate}>
                {t("recalculate")}
              </button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] table-fixed text-center text-sm">
              <tbody>
                <ScorecardRow
                  holes={round?.holes ?? []}
                  label={t("hole")}
                  render={(hole) => hole.hole_number}
                  selectedHoleNumber={selectedHoleNumber}
                  setSelectedHoleNumber={setSelectedHoleNumber}
                />
                <ScorecardRow holes={round?.holes ?? []} label={t("par")} render={(hole) => hole.par} />
                <ScorecardRow
                  holes={round?.holes ?? []}
                  label={t("score")}
                  render={(hole) => <ScoreBadge hole={hole} t={t} />}
                />
                <ScorecardRow holes={round?.holes ?? []} label={t("putts")} render={(hole) => hole.putts ?? "-"} />
                <ScorecardRow holes={round?.holes ?? []} label={t("penalty")} render={(hole) => hole.penalties} />
              </tbody>
            </table>
          </div>
          {round && round.holes.length === 0 && (
            <p className="border-t border-line px-4 py-6 text-sm text-muted">
              {t("noScorecardHoles")}
            </p>
          )}
          {status && <p className="border-t border-line px-4 py-3 text-sm text-muted">{status}</p>}
          {shareUrl && <p className="border-t border-line px-4 py-3 text-sm text-green-700">{shareUrl}</p>}
        </section>

        <section className="grid gap-5 lg:grid-cols-[0.7fr_1.3fr]">
          <div className="rounded-md border border-line bg-white p-4">
            <h2 className="text-base font-semibold">{t("selectedHole")}</h2>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <Metric label={t("hole")} value={selectedHole?.hole_number ?? "-"} compact />
              <Metric label={t("par")} value={selectedHole?.par ?? "-"} compact />
              <Metric label={t("score")} value={selectedHole?.score ?? "-"} compact />
              <Metric label={t("putts")} value={selectedHole?.putts ?? "-"} compact />
              <Metric label="GIR" value={selectedHole?.gir === null ? "-" : selectedHole?.gir ? t("yes") : t("no")} compact />
              <Metric label={t("penalty")} value={selectedHole?.penalties ?? "-"} compact />
            </div>
          </div>

          <div className="min-w-0 rounded-md border border-line bg-white">
            <div className="border-b border-line px-4 py-3">
              <h2 className="text-base font-semibold">{t("shotTimeline")}</h2>
            </div>
            <div className="grid gap-3 p-4">
              {(selectedHole?.shots ?? []).map((shot) => (
                <article className="rounded-md border border-line bg-surface p-3 text-sm" key={shot.id}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-semibold">#{shot.shot_number} · {shot.club ?? "-"}</h3>
                    <span className="text-muted">{shot.distance ?? "-"}m</span>
                  </div>
                  <div className="mt-2 grid gap-2 sm:grid-cols-3">
                    <ShotMeta label={t("lie")} value={`${shot.start_lie ?? "-"} -> ${shot.end_lie ?? "-"}`} />
                    <ShotMeta label={t("grade")} value={`${shot.result_grade ?? "-"} / ${shot.feel_grade ?? "-"}`} />
                    <ShotMeta label={t("penalty")} value={shot.penalty_type ?? "-"} />
                  </div>
                  <div className="mt-3 grid gap-2 border-t border-line pt-3 sm:grid-cols-4">
                    <ShotMeta label={t("expectedBefore")} value={formatNullable(shotValueById.get(shot.id)?.expected_before)} />
                    <ShotMeta label={t("shotCost")} value={formatNullable(shotValueById.get(shot.id)?.shot_cost)} />
                    <ShotMeta label={t("expectedAfter")} value={formatNullable(shotValueById.get(shot.id)?.expected_after)} />
                    <ShotMeta label={t("strokeGained")} value={formatNullable(shotValueById.get(shot.id)?.shot_value)} />
                  </div>
                </article>
              ))}
              {selectedHole && selectedHole.shots.length === 0 && (
                <p className="text-sm text-muted">{t("noShotsForHole")}</p>
              )}
              {round && !selectedHole && (
                <p className="text-sm text-muted">{t("selectHoleToViewShots")}</p>
              )}
            </div>
          </div>
        </section>

      </div>
    </AppShell>
  );
}

function ScorecardRow({
  holes,
  label,
  render,
  selectedHoleNumber,
  setSelectedHoleNumber,
}: {
  holes: RoundHole[];
  label: string;
  render: (hole: RoundHole) => React.ReactNode;
  selectedHoleNumber?: number;
  setSelectedHoleNumber?: (holeNumber: number) => void;
}) {
  return (
    <tr className="border-t border-line first:border-t-0">
      <th className="w-24 bg-surface px-3 py-3 text-left font-medium text-muted">{label}</th>
      {holes.map((hole) => (
        <td className="w-12 px-1.5 py-2" key={`${label}-${hole.id}`}>
          {setSelectedHoleNumber ? (
            <button
              className={
                hole.hole_number === selectedHoleNumber
                  ? "h-9 w-10 rounded-md bg-green-700 font-semibold text-white"
                  : "h-9 w-10 rounded-md border border-line font-semibold"
              }
              onClick={() => setSelectedHoleNumber(hole.hole_number)}
            >
              {render(hole)}
            </button>
          ) : (
            render(hole)
          )}
        </td>
      ))}
    </tr>
  );
}

function ScoreBadge({
  hole,
  t,
}: {
  hole: RoundHole;
  t: (key: "par" | "eagleOrBetter" | "birdie" | "bogey" | "doubleBogeyOrWorse") => string;
}) {
  if (hole.score === null || hole.score === undefined) return "-";

  const diff = hole.score - hole.par;
  const outcome =
    diff <= -2
      ? { label: t("eagleOrBetter"), className: "border-[#9fc4e8] bg-[#eef6ff] text-[#175cd3]" }
      : diff === -1
        ? { label: t("birdie"), className: "border-[#b7dec4] bg-[#eef8f1] text-green-700" }
        : diff === 0
          ? { label: t("par"), className: "border-line bg-white text-ink" }
          : diff === 1
            ? { label: t("bogey"), className: "border-[#f1d29a] bg-[#fff7e6] text-[#a15c07]" }
            : { label: t("doubleBogeyOrWorse"), className: "border-[#e7c1bd] bg-[#fff2f0] text-[#b42318]" };

  return (
    <span
      className={`mx-auto flex h-12 w-11 flex-col items-center justify-center rounded-md border font-semibold ${outcome.className}`}
      title={`${outcome.label} (${formatToPar(diff)})`}
    >
      <span className="text-base leading-none">{hole.score}</span>
      <span className="mt-1 text-[10px] leading-none">{outcome.label}</span>
    </span>
  );
}

function Metric({
  label,
  value,
  compact = false,
}: {
  label: string;
  value: number | string;
  compact?: boolean;
}) {
  return (
    <div className={compact ? "rounded-md bg-surface p-3" : "rounded-md border border-line bg-white p-4"}>
      <p className="text-sm text-muted">{label}</p>
      <p className={compact ? "mt-1 text-lg font-semibold" : "mt-2 text-2xl font-semibold"}>{value}</p>
    </div>
  );
}

function AnalysisMetric({
  label,
  total,
  count,
}: {
  label: string;
  total: number;
  count: number;
}) {
  const tone =
    total > 0
      ? "border-[#b7dec4] bg-[#eef8f1] text-green-700"
      : total < 0
        ? "border-[#e7c1bd] bg-[#fff2f0] text-[#b42318]"
        : "border-line bg-surface text-ink";

  return (
    <div className={`rounded-md border p-3 ${tone}`}>
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold">{formatSigned(total)}</p>
      <p className="mt-1 text-xs text-muted">{count}</p>
    </div>
  );
}

function ShotMeta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}

function strokeGainedRows(analytics: RoundAnalytics | null) {
  if (!analytics) return [];
  const rows = new Map<string, { category: string; total: number; count: number }>();
  for (const value of analytics.shot_values) {
    const row = rows.get(value.category) ?? { category: value.category, total: 0, count: 0 };
    row.total += value.shot_value ?? 0;
    row.count += 1;
    rows.set(value.category, row);
  }
  return [...rows.values()].sort((a, b) => a.total - b.total);
}

function categoryLabel(category: string, t: (key: "tee" | "approach" | "shortGame" | "controlShot" | "ironShot" | "putting" | "recovery" | "penalty") => string) {
  const labels: Record<string, string> = {
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

function formatNumber(value: number) {
  return (Math.round(value * 100) / 100).toFixed(2);
}

function formatSigned(value: number) {
  const formatted = formatNumber(value);
  if (value > 0) return `+${formatted}`;
  return formatted;
}

function formatNullable(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return (Math.round(value * 100) / 100).toFixed(2);
}

function formatToPar(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  if (value > 0) return `+${value}`;
  return String(value);
}
