"use client";

import { use, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import { getRound, requestRoundRecalculation, type RoundDetail, type RoundHole } from "@/lib/api";

export default function RoundDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [round, setRound] = useState<RoundDetail | null>(null);
  const [selectedHoleNumber, setSelectedHoleNumber] = useState(1);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    getRound(id)
      .then((loaded) => {
        setRound(loaded);
        setSelectedHoleNumber(loaded.holes[0]?.hole_number ?? 1);
      })
      .catch((roundError) => {
        setError(roundError instanceof Error ? roundError.message : "Round detail load failed");
      });
  }, [id]);

  const selectedHole = useMemo(
    () => round?.holes.find((hole) => hole.hole_number === selectedHoleNumber) ?? null,
    [round, selectedHoleNumber],
  );

  async function recalculate() {
    setStatus("Requesting recalculation...");
    setError("");
    try {
      const result = await requestRoundRecalculation(id);
      setRound((current) => current ? { ...current, computed_status: result.computed_status } : current);
      setStatus("Recalculation queued.");
    } catch (recalculateError) {
      setError(recalculateError instanceof Error ? recalculateError.message : "Recalculation failed");
      setStatus("");
    }
  }

  return (
    <AppShell eyebrow="Round Detail" title={round?.course_name ?? "Round"}>
      <div className="mt-5 space-y-5">
        {!round && !error && (
          <div className="rounded-md border border-line bg-white p-3 text-sm text-muted">
            Loading round...
          </div>
        )}
        {error && <div className="rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">{error}</div>}

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Metric label="Date" value={round?.play_date ?? "-"} />
          <Metric label="Score" value={round?.total_score ?? "-"} />
          <Metric label="To par" value={formatToPar(round?.score_to_par)} />
          <Metric label="Putts" value={round?.metrics.putts_total ?? "-"} />
          <Metric label="Status" value={round?.computed_status ?? "-"} />
        </section>

        <section className="rounded-md border border-line bg-white">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold">Scorecard</h2>
            <button className="rounded-md border border-line px-3 py-2 text-sm font-semibold" onClick={recalculate}>
              Recalculate
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[920px] text-center text-sm">
              <tbody>
                <ScorecardRow
                  holes={round?.holes ?? []}
                  label="Hole"
                  render={(hole) => hole.hole_number}
                  selectedHoleNumber={selectedHoleNumber}
                  setSelectedHoleNumber={setSelectedHoleNumber}
                />
                <ScorecardRow holes={round?.holes ?? []} label="Par" render={(hole) => hole.par} />
                <ScorecardRow holes={round?.holes ?? []} label="Score" render={(hole) => hole.score ?? "-"} />
                <ScorecardRow holes={round?.holes ?? []} label="Putts" render={(hole) => hole.putts ?? "-"} />
                <ScorecardRow holes={round?.holes ?? []} label="Penalty" render={(hole) => hole.penalties} />
              </tbody>
            </table>
          </div>
          {round && round.holes.length === 0 && (
            <p className="border-t border-line px-4 py-6 text-sm text-muted">
              No scorecard holes are available for this round.
            </p>
          )}
          {status && <p className="border-t border-line px-4 py-3 text-sm text-muted">{status}</p>}
        </section>

        <section className="grid gap-5 lg:grid-cols-[0.7fr_1.3fr]">
          <div className="rounded-md border border-line bg-white p-4">
            <h2 className="text-base font-semibold">Selected Hole</h2>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <Metric label="Hole" value={selectedHole?.hole_number ?? "-"} compact />
              <Metric label="Par" value={selectedHole?.par ?? "-"} compact />
              <Metric label="Score" value={selectedHole?.score ?? "-"} compact />
              <Metric label="Putts" value={selectedHole?.putts ?? "-"} compact />
              <Metric label="GIR" value={selectedHole?.gir === null ? "-" : selectedHole?.gir ? "Yes" : "No"} compact />
              <Metric label="Penalty" value={selectedHole?.penalties ?? "-"} compact />
            </div>
          </div>

          <div className="min-w-0 rounded-md border border-line bg-white">
            <div className="border-b border-line px-4 py-3">
              <h2 className="text-base font-semibold">Shot Timeline</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="bg-surface text-muted">
                  <tr>
                    <th className="px-4 py-2 font-medium">#</th>
                    <th className="px-4 py-2 font-medium">Club</th>
                    <th className="px-4 py-2 font-medium">Distance</th>
                    <th className="px-4 py-2 font-medium">Lie</th>
                    <th className="px-4 py-2 font-medium">Grade</th>
                    <th className="px-4 py-2 font-medium">Penalty</th>
                  </tr>
                </thead>
                <tbody>
                  {(selectedHole?.shots ?? []).map((shot) => (
                    <tr className="border-t border-line" key={shot.id}>
                      <td className="px-4 py-3">{shot.shot_number}</td>
                      <td className="px-4 py-3 font-medium">{shot.club ?? "-"}</td>
                      <td className="px-4 py-3">{shot.distance ?? "-"}</td>
                      <td className="px-4 py-3">{shot.start_lie ?? "-"} → {shot.end_lie ?? "-"}</td>
                      <td className="px-4 py-3">{shot.result_grade ?? "-"} / {shot.feel_grade ?? "-"}</td>
                      <td className="px-4 py-3">{shot.penalty_type ?? "-"}</td>
                    </tr>
                  ))}
                  {selectedHole && selectedHole.shots.length === 0 && (
                    <tr>
                      <td className="px-4 py-6 text-muted" colSpan={6}>
                        No shots are available for this hole.
                      </td>
                    </tr>
                  )}
                  {round && !selectedHole && (
                    <tr>
                      <td className="px-4 py-6 text-muted" colSpan={6}>
                        Select a hole to view shots.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
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
      <th className="w-20 bg-surface px-3 py-3 text-left font-medium text-muted">{label}</th>
      {holes.map((hole) => (
        <td className="px-2 py-2" key={`${label}-${hole.id}`}>
          {setSelectedHoleNumber ? (
            <button
              className={
                hole.hole_number === selectedHoleNumber
                  ? "h-9 w-9 rounded-md bg-green-700 font-semibold text-white"
                  : "h-9 w-9 rounded-md border border-line font-semibold"
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

function formatToPar(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  if (value > 0) return `+${value}`;
  return String(value);
}
