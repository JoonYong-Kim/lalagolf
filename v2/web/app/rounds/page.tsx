"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import { getRounds, type RoundListResponse } from "@/lib/api";

export default function RoundsPage() {
  const [rounds, setRounds] = useState<RoundListResponse | null>(null);
  const [year, setYear] = useState("2026");
  const [course, setCourse] = useState("");
  const [companion, setCompanion] = useState("");
  const [error, setError] = useState("");

  async function loadRounds() {
    setError("");
    try {
      setRounds(await getRounds({ limit: 50, year, course, companion }));
    } catch (roundError) {
      setError(roundError instanceof Error ? roundError.message : "Round list load failed");
    }
  }

  useEffect(() => {
    loadRounds();
  }, []);

  return (
    <AppShell eyebrow="Round Archive" title="Rounds">
      <div className="mt-5 space-y-5">
        <section className="rounded-md border border-line bg-white p-4">
          <div className="grid gap-3 md:grid-cols-[120px_1fr_1fr_auto]">
            <label className="text-sm font-medium">
              Year
              <input className={inputClass} value={year} onChange={(event) => setYear(event.target.value)} />
            </label>
            <label className="text-sm font-medium">
              Course
              <input className={inputClass} value={course} onChange={(event) => setCourse(event.target.value)} />
            </label>
            <label className="text-sm font-medium">
              Companion
              <input className={inputClass} value={companion} onChange={(event) => setCompanion(event.target.value)} />
            </label>
            <button className="self-end rounded-md bg-green-700 px-4 py-2 text-sm font-semibold text-white" onClick={loadRounds}>
              Filter
            </button>
          </div>
        </section>

        {error && <div className="rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">{error}</div>}

        <section className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3 text-sm text-muted">
            {rounds ? `${rounds.total} rounds` : "Loading rounds..."}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-surface text-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">Date</th>
                  <th className="px-4 py-2 font-medium">Course</th>
                  <th className="px-4 py-2 font-medium">Score</th>
                  <th className="px-4 py-2 font-medium">Holes</th>
                  <th className="px-4 py-2 font-medium">Companions</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {(rounds?.items ?? []).map((round) => (
                  <tr className="border-t border-line hover:bg-surface" key={round.id}>
                    <td className="px-4 py-3">{round.play_date}</td>
                    <td className="px-4 py-3 font-medium">
                      <Link href={`/rounds/${round.id}`}>{round.course_name}</Link>
                    </td>
                    <td className="px-4 py-3">{round.total_score ?? "-"}</td>
                    <td className="px-4 py-3">{round.hole_count}</td>
                    <td className="px-4 py-3">{round.companions.join(", ") || "-"}</td>
                    <td className="px-4 py-3">{round.computed_status}</td>
                  </tr>
                ))}
                {rounds && rounds.items.length === 0 && (
                  <tr>
                    <td className="px-4 py-6 text-muted" colSpan={6}>No rounds match the current filters.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </AppShell>
  );
}

const inputClass = "mt-1 w-full rounded-md border border-line px-3 py-2 text-sm";
