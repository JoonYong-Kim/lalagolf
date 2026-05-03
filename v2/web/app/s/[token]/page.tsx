"use client";

import { use, useEffect, useState } from "react";

import { getSharedRound, type SharedRound } from "@/lib/api";

export default function SharedRoundPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const [shared, setShared] = useState<SharedRound | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getSharedRound(token)
      .then(setShared)
      .catch((sharedError) => {
        setError(sharedError instanceof Error ? sharedError.message : "Shared round not found");
      });
  }, [token]);

  return (
    <main className="min-h-screen bg-surface p-5 text-ink">
      <section className="mx-auto max-w-5xl">
        <header className="border-b border-line pb-4">
          <p className="text-sm font-medium text-green-700">LalaGolf Shared Round</p>
          <h1 className="mt-2 text-2xl font-semibold md:text-3xl">
            {shared?.title ?? "Shared round"}
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
            Loading shared round...
          </div>
        )}

        {shared && (
          <div className="mt-5 space-y-5">
            <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Metric label="Score" value={shared.round.total_score ?? "-"} />
              <Metric label="To par" value={formatToPar(shared.round.score_to_par)} />
              <Metric label="Putts" value={shared.metrics.putts_total ?? "-"} />
              <Metric label="Penalties" value={shared.metrics.penalties_total ?? "-"} />
            </section>

            {shared.insights[0] && (
              <section className="rounded-md border border-line bg-white">
                <div className="border-b border-line px-4 py-3">
                  <h2 className="text-base font-semibold">Top Issue</h2>
                </div>
                <article className="space-y-3 p-4 text-sm leading-6">
                  <div>
                    <p className="text-xs font-semibold uppercase text-green-700">
                      {categoryLabel(shared.insights[0].category)} · {shared.insights[0].confidence}
                    </p>
                    <h3 className="mt-1 text-base font-semibold">{shared.insights[0].problem}</h3>
                  </div>
                  <dl className="grid gap-2 sm:grid-cols-3">
                    <IssueLine label="Evidence" value={shared.insights[0].evidence} />
                    <IssueLine label="Impact" value={shared.insights[0].impact} />
                    <IssueLine label="Next" value={shared.insights[0].next_action} />
                  </dl>
                </article>
              </section>
            )}

            <section className="rounded-md border border-line bg-white">
              <div className="border-b border-line px-4 py-3">
                <h2 className="text-base font-semibold">Scorecard</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-center text-sm">
                  <tbody>
                    <ScoreRow label="Hole" values={shared.holes.map((hole) => hole.hole_number)} />
                    <ScoreRow label="Par" values={shared.holes.map((hole) => hole.par)} />
                    <ScoreRow label="Score" values={shared.holes.map((hole) => hole.score ?? "-")} />
                    <ScoreRow label="Putts" values={shared.holes.map((hole) => hole.putts ?? "-")} />
                    <ScoreRow label="Penalty" values={shared.holes.map((hole) => hole.penalties)} />
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

function ScoreRow({ label, values }: { label: string; values: Array<number | string> }) {
  return (
    <tr className="border-t border-line first:border-t-0">
      <th className="w-20 bg-surface px-3 py-3 text-left font-medium text-muted">{label}</th>
      {values.map((value, index) => (
        <td className="px-2 py-3" key={`${label}-${index}`}>
          {value}
        </td>
      ))}
    </tr>
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

function formatToPar(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  if (value > 0) return `+${value}`;
  return String(value);
}
