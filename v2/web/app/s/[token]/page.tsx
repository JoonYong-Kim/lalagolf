"use client";

import { use, useEffect, useState } from "react";

import { getSharedRound, type SharedRound } from "@/lib/api";
import { useI18n, type MessageKey } from "@/lib/i18n";

export default function SharedRoundPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const [shared, setShared] = useState<SharedRound | null>(null);
  const [error, setError] = useState("");
  const { locale, t } = useI18n();

  useEffect(() => {
    getSharedRound(token, locale)
      .then(setShared)
      .catch((sharedError) => {
        setError(sharedError instanceof Error ? sharedError.message : t("sharedRound"));
      });
  }, [token, locale]);

  return (
    <main className="min-h-screen bg-surface p-5 text-ink">
      <section className="mx-auto max-w-5xl">
        <header className="border-b border-line pb-4">
          <p className="text-sm font-medium text-green-700">{t("sharedRoundEyebrow")}</p>
          <h1 className="mt-2 text-2xl font-semibold md:text-3xl">
            {shared?.title ?? t("sharedRound")}
          </h1>
          {shared && (
            <p className="mt-2 text-sm text-muted">
              {shared.round.course_name} · {shared.round.play_date ?? shared.round.play_month}
            </p>
          )}
        </header>

        {error && (
          <div className="mt-5 rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">
            {error}
          </div>
        )}

        {!shared && !error && (
          <div className="mt-5 rounded-md border border-line bg-white p-3 text-sm text-muted">
            {t("loadingSharedRound")}
          </div>
        )}

        {shared && (
          <div className="mt-5 space-y-5">
            <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Metric label={t("score")} value={shared.round.total_score ?? "-"} />
              <Metric label={t("toPar")} value={formatToPar(shared.round.score_to_par)} />
              <Metric label={t("putts")} value={shared.metrics.putts_total ?? "-"} />
              <Metric label={t("penalties")} value={shared.metrics.penalties_total ?? "-"} />
            </section>

            {shared.insights[0] && (
              <section className="rounded-md border border-line bg-white">
                <div className="border-b border-line px-4 py-3">
                  <h2 className="text-base font-semibold">{t("topIssue")}</h2>
                </div>
                <article className="space-y-3 p-4 text-sm leading-6">
                  <div>
                    <p className="text-xs font-semibold uppercase text-green-700">
                      {categoryLabel(shared.insights[0].category, t)} · {shared.insights[0].confidence}
                    </p>
                    <h3 className="mt-1 text-base font-semibold">{shared.insights[0].problem}</h3>
                  </div>
                  <dl className="grid gap-2 sm:grid-cols-3">
                    <IssueLine label={t("evidence")} value={shared.insights[0].evidence} />
                    <IssueLine label={t("impact")} value={shared.insights[0].impact} />
                    <IssueLine label={t("next")} value={shared.insights[0].next_action} />
                  </dl>
                </article>
              </section>
            )}

            <section className="rounded-md border border-line bg-white">
              <div className="border-b border-line px-4 py-3">
                <h2 className="text-base font-semibold">{t("scorecard")}</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[980px] table-fixed text-center text-sm">
                  <tbody>
                    <ScoreRow label={t("hole")} values={shared.holes.map((hole) => hole.hole_number)} />
                    <ScoreRow label={t("par")} values={shared.holes.map((hole) => hole.par)} />
                    <ScoreRow
                      label={t("score")}
                      values={shared.holes.map((hole) => <ScoreBadge hole={hole} t={t} />)}
                    />
                    <ScoreRow label={t("putts")} values={shared.holes.map((hole) => hole.putts ?? "-")} />
                    <ScoreRow label={t("penalty")} values={shared.holes.map((hole) => hole.penalties)} />
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )}
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-md border border-line bg-white p-4">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function ScoreRow({ label, values }: { label: string; values: React.ReactNode[] }) {
  return (
    <tr className="border-t border-line first:border-t-0">
      <th className="w-24 bg-surface px-3 py-3 text-left font-medium text-muted">{label}</th>
      {values.map((value, index) => (
        <td className="w-12 px-1.5 py-2" key={`${label}-${index}`}>
          {value}
        </td>
      ))}
    </tr>
  );
}

function ScoreBadge({
  hole,
  t,
}: {
  hole: SharedRound["holes"][number];
  t: (key: MessageKey) => string;
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

function IssueLine({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-semibold">{label}</dt>
      <dd className="text-muted">{value}</dd>
    </div>
  );
}

function categoryLabel(category: string, t: (key: MessageKey) => string) {
  const labels: Record<string, string> = {
    score: t("score"),
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

function formatToPar(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  if (value > 0) return `+${value}`;
  return String(value);
}
