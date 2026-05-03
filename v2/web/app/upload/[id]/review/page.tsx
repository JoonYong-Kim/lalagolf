"use client";

import { use, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import {
  commitUploadReview,
  getUploadReview,
  updateUploadReview,
  type ParsedRound,
  type ParsedHole,
  type UploadReview,
} from "@/lib/api";

type PageParams = {
  params: Promise<{ id: string }>;
};

export default function UploadReviewPage({ params }: PageParams) {
  const { id } = use(params);
  const [review, setReview] = useState<UploadReview | null>(null);
  const [courseName, setCourseName] = useState("");
  const [playDate, setPlayDate] = useState("");
  const [companions, setCompanions] = useState("");
  const [editableHoles, setEditableHoles] = useState<ParsedHole[]>([]);
  const [selectedHole, setSelectedHole] = useState<number | null>(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [committedRoundId, setCommittedRoundId] = useState<string | null>(null);

  useEffect(() => {
    getUploadReview(id)
      .then((loadedReview) => {
        setReview(loadedReview);
        hydrateForm(loadedReview.parsed_round);
      })
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "Failed to load review");
      });
  }, [id]);

  const parsedRound = review?.parsed_round;
  const holes = editableHoles;
  const activeHole = holes.find((hole) => hole.hole_number === selectedHole) ?? holes[0];
  const summary = useMemo(() => summarize(parsedRound), [parsedRound]);

  useEffect(() => {
    if (selectedHole === null && holes.length > 0) {
      setSelectedHole(holes[0].hole_number);
    }
  }, [holes, selectedHole]);

  async function saveEdits() {
    setStatus("Saving edits...");
    setError("");
    try {
      const updated = await updateUploadReview(id, {
        course_name: courseName,
        play_date: playDate,
        companions: companions
          .split(",")
          .map((name) => name.trim())
          .filter(Boolean),
        holes: editableHoles,
      });
      setReview(updated);
      hydrateForm(updated.parsed_round);
      setStatus("Edits saved.");
    } catch (saveError) {
      setStatus("");
      setError(saveError instanceof Error ? saveError.message : "Failed to save edits");
    }
  }

  async function commitReview() {
    setStatus("Committing private round...");
    setError("");
    try {
      const committed = await commitUploadReview(id);
      setCommittedRoundId(committed.round_id);
      setStatus(`Committed. Analytics status: ${committed.computed_status}`);
      const updated = await getUploadReview(id);
      setReview(updated);
    } catch (commitError) {
      setStatus("");
      setError(commitError instanceof Error ? commitError.message : "Failed to commit upload");
    }
  }

  function hydrateForm(round: ParsedRound) {
    setCourseName(round.course_name ?? "");
    setPlayDate(round.play_date ?? "");
    setCompanions((round.companions ?? []).join(", "));
    setEditableHoles(round.holes ?? []);
  }

  function updateActiveHole(field: "par" | "score" | "putts", value: string) {
    const numericValue = Number(value);
    setEditableHoles((currentHoles) =>
      currentHoles.map((hole) =>
        hole.hole_number === activeHole?.hole_number
          ? { ...hole, [field]: Number.isNaN(numericValue) ? 0 : numericValue }
          : hole,
      ),
    );
  }

  function updateShot(
    shotNumber: number,
    field: "club" | "distance" | "penalty_type",
    value: string,
  ) {
    setEditableHoles((currentHoles) =>
      currentHoles.map((hole) => {
        if (hole.hole_number !== activeHole?.hole_number) {
          return hole;
        }
        return {
          ...hole,
          shots: hole.shots.map((shot) => {
            if (shot.shot_number !== shotNumber) {
              return shot;
            }
            if (field === "distance") {
              const numericValue = Number(value);
              return { ...shot, distance: Number.isNaN(numericValue) ? null : numericValue };
            }
            return { ...shot, [field]: value || null };
          }),
        };
      }),
    );
  }

  if (error && !review) {
    return (
      <main className="min-h-screen bg-surface p-5 text-ink">
        <section className="mx-auto max-w-3xl rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-4 text-[#a34242]">
          {error}
        </section>
      </main>
    );
  }

  if (!review || !parsedRound) {
    return (
      <main className="min-h-screen bg-surface p-5 text-ink">
        <section className="mx-auto max-w-5xl rounded-md border border-line bg-white p-5">
          Loading upload review...
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-surface p-5 text-ink">
      <section className="mx-auto max-w-6xl">
        <div className="mb-5 border-b border-line pb-4">
          <p className="text-sm font-medium text-green-700">Upload Review</p>
          <h1 className="mt-2 text-3xl font-semibold">{courseName || "Parsed round"}</h1>
          <p className="mt-2 text-sm text-muted">
            Review parsed metadata, warnings, holes, and shots before committing a private round.
          </p>
        </div>

        <div className="mb-4 grid gap-3 md:grid-cols-5">
          <SummaryCell label="Status" value={review.status} />
          <SummaryCell label="Score" value={summary.score} />
          <SummaryCell label="Holes" value={summary.holes} />
          <SummaryCell label="Shots" value={summary.shots} />
          <SummaryCell label="Warnings" value={String(review.warnings.length)} />
        </div>

        <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
          <section className="space-y-4">
            <Panel title="Round metadata">
              <div className="space-y-3">
                <label className="block text-sm font-medium">
                  Course
                  <input className={inputClass} value={courseName} onChange={(event) => setCourseName(event.target.value)} />
                </label>
                <label className="block text-sm font-medium">
                  Play date
                  <input className={inputClass} type="date" value={playDate} onChange={(event) => setPlayDate(event.target.value)} />
                </label>
                <label className="block text-sm font-medium">
                  Companions
                  <input className={inputClass} value={companions} onChange={(event) => setCompanions(event.target.value)} />
                </label>
                <button className="rounded-md border border-line px-4 py-2 text-sm font-semibold" onClick={saveEdits}>
                  Save edits
                </button>
              </div>
            </Panel>

            <Panel title="Warnings">
              {review.warnings.length === 0 ? (
                <p className="text-sm text-muted">No parser warnings.</p>
              ) : (
                <div className="space-y-2">
                  {review.warnings.map((warning) => (
                    <div className="rounded-md border border-[#e8d2a5] bg-[#fff8e8] p-3 text-sm" key={`${warning.code}-${warning.path}`}>
                      <p className="font-semibold text-[#7a4c00]">{warning.code}</p>
                      <p className="mt-1 text-[#59451c]">{warning.message}</p>
                      <p className="mt-1 text-xs text-muted">{warning.path}</p>
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          </section>

          <section className="space-y-4">
            <Panel title="Hole and shot review">
              <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
                {holes.map((hole) => (
                  <button
                    className={`h-9 min-w-9 rounded-md border text-sm font-semibold ${
                      activeHole?.hole_number === hole.hole_number
                        ? "border-green-700 bg-green-700 text-white"
                        : "border-line bg-white"
                    }`}
                    key={hole.hole_number}
                    onClick={() => setSelectedHole(hole.hole_number)}
                  >
                    {hole.hole_number}
                  </button>
                ))}
              </div>
              {activeHole && (
                <div className="grid gap-3 xl:grid-cols-[0.8fr_1.2fr]">
                  <div className="rounded-md border border-line bg-surface p-3 text-sm">
                    <p className="font-semibold">
                      Hole {activeHole.hole_number} · Par {activeHole.par} · Score {activeHole.score}
                    </p>
                    <dl className="mt-3 grid grid-cols-2 gap-2">
                      <Metric label="Putts" value={activeHole.putts} />
                      <Metric label="Penalties" value={activeHole.penalties} />
                      <Metric label="GIR" value={activeHole.gir ? "Yes" : "No"} />
                      <Metric label="Shots" value={activeHole.shots.length} />
                    </dl>
                    <div className="mt-4 grid grid-cols-3 gap-2">
                      <label className="text-xs font-medium text-muted">
                        Par
                        <input
                          className={smallInputClass}
                          type="number"
                          value={activeHole.par}
                          onChange={(event) => updateActiveHole("par", event.target.value)}
                        />
                      </label>
                      <label className="text-xs font-medium text-muted">
                        Score
                        <input
                          className={smallInputClass}
                          type="number"
                          value={activeHole.score}
                          onChange={(event) => updateActiveHole("score", event.target.value)}
                        />
                      </label>
                      <label className="text-xs font-medium text-muted">
                        Putts
                        <input
                          className={smallInputClass}
                          type="number"
                          value={activeHole.putts}
                          onChange={(event) => updateActiveHole("putts", event.target.value)}
                        />
                      </label>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[560px] text-left text-sm">
                      <thead className="bg-[#eef3f0] text-muted">
                        <tr>
                          <th className="px-3 py-2">#</th>
                          <th className="px-3 py-2">Club</th>
                          <th className="px-3 py-2">Dist</th>
                          <th className="px-3 py-2">Lie</th>
                          <th className="px-3 py-2">Result</th>
                          <th className="px-3 py-2">Penalty</th>
                        </tr>
                      </thead>
                      <tbody>
                        {activeHole.shots.map((shot) => (
                          <tr className="border-t border-line bg-white" key={shot.shot_number}>
                            <td className="px-3 py-2 font-semibold">{shot.shot_number}</td>
                            <td className="px-3 py-2">
                              <input
                                className={tableInputClass}
                                value={shot.club ?? ""}
                                onChange={(event) => updateShot(shot.shot_number, "club", event.target.value)}
                              />
                            </td>
                            <td className="px-3 py-2">
                              <input
                                className={tableInputClass}
                                type="number"
                                value={shot.distance ?? ""}
                                onChange={(event) => updateShot(shot.shot_number, "distance", event.target.value)}
                              />
                            </td>
                            <td className="px-3 py-2">{shot.start_lie} to {shot.end_lie}</td>
                            <td className="px-3 py-2">{shot.result_grade}</td>
                            <td className="px-3 py-2">
                              <select
                                className={tableInputClass}
                                value={shot.penalty_type ?? ""}
                                onChange={(event) => updateShot(shot.shot_number, "penalty_type", event.target.value)}
                              >
                                <option value="">-</option>
                                <option value="H">H</option>
                                <option value="OB">OB</option>
                                <option value="UN">UN</option>
                              </select>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </Panel>

            <div className="rounded-md border border-line bg-white p-4">
              <div className="flex flex-wrap items-center gap-3">
                <button className="rounded-md bg-green-700 px-4 py-2 text-sm font-semibold text-white" onClick={commitReview}>
                  Commit private round
                </button>
                {status && <span className="text-sm text-muted">{status}</span>}
              </div>
              {committedRoundId && (
                <p className="mt-3 text-sm text-green-700">Round committed: {committedRoundId}</p>
              )}
              {error && (
                <div className="mt-3 rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">
                  {error}
                </div>
              )}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

function summarize(round?: ParsedRound) {
  const holes = round?.holes ?? [];
  const shots = holes.reduce((total, hole) => total + hole.shots.length, 0);
  return {
    score: round?.total_score == null ? "-" : String(round.total_score),
    holes: String(round?.hole_count ?? holes.length),
    shots: String(shots),
  };
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-md border border-line bg-white">
      <div className="border-b border-line px-4 py-3">
        <h2 className="font-semibold">{title}</h2>
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function SummaryCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-white p-3">
      <p className="text-xs font-medium text-muted">{label}</p>
      <p className="mt-2 text-xl font-semibold">{value}</p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="font-semibold">{value}</dd>
    </div>
  );
}

const inputClass = "mt-1 w-full rounded-md border border-line px-3 py-2 text-sm";
const smallInputClass = "mt-1 w-full rounded-md border border-line bg-white px-2 py-1.5 text-sm text-ink";
const tableInputClass = "w-20 rounded-md border border-line bg-white px-2 py-1 text-sm text-ink";
