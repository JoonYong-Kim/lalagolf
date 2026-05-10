"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import { getRound, getRounds, type RoundDetail, type RoundListResponse } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function RoundsPage() {
  const [rounds, setRounds] = useState<RoundListResponse | null>(null);
  const [details, setDetails] = useState<RoundDetail[]>([]);
  const [selectedRoundIds, setSelectedRoundIds] = useState<string[]>([]);
  const [year, setYear] = useState("2026");
  const [course, setCourse] = useState("");
  const [companion, setCompanion] = useState("");
  const [error, setError] = useState("");
  const { t } = useI18n();

  async function loadRounds() {
    setError("");
    try {
      const loaded = await getRounds({ limit: 50, year, course, companion });
      setRounds(loaded);
      setSelectedRoundIds([]);
      const loadedDetails = await Promise.all(loaded.items.map((round) => getRound(round.id)));
      setDetails(loadedDetails);
    } catch (roundError) {
      setError(roundError instanceof Error ? roundError.message : t("loadingRounds"));
    }
  }

  useEffect(() => {
    loadRounds();
  }, []);

  const summary = useMemo(() => roundSummary(details), [details]);
  const detailById = useMemo(() => new Map(details.map((detail) => [detail.id, detail])), [details]);

  function toggleRound(roundId: string) {
    setSelectedRoundIds((current) =>
      current.includes(roundId)
        ? current.filter((id) => id !== roundId)
        : [...current, roundId],
    );
  }

  return (
    <AppShell eyebrow={t("roundArchive")} title={t("rounds")}>
      <div className="mt-5 space-y-5">
        <section className="rounded-md border border-line bg-white p-4">
          <div className="grid gap-3 md:grid-cols-[120px_1fr_1fr_auto_auto]">
            <label className="text-sm font-medium">
              {t("year")}
              <input className={inputClass} value={year} onChange={(event) => setYear(event.target.value)} />
            </label>
            <label className="text-sm font-medium">
              {t("course")}
              <input className={inputClass} value={course} onChange={(event) => setCourse(event.target.value)} />
            </label>
            <label className="text-sm font-medium">
              {t("companion")}
              <input className={inputClass} value={companion} onChange={(event) => setCompanion(event.target.value)} />
            </label>
            <button className="self-end rounded-md bg-green-700 px-4 py-2 text-sm font-semibold text-white" onClick={loadRounds}>
              {t("filter")}
            </button>
            <Link className="self-end rounded-md border border-line px-4 py-2 text-sm font-semibold" href="/rounds/public">
              {t("publicRounds")}
            </Link>
          </div>
        </section>

        {error && <div className="rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">{error}</div>}

        <section className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-base font-semibold">{t("filteredSummary")}</h2>
            {selectedRoundIds.length > 0 && (
              <div className="flex flex-wrap gap-2">
                <Link
                  className="rounded-md border border-line px-3 py-2 text-sm font-semibold"
                  href={`/analysis?roundIds=${selectedRoundIds.join(",")}`}
                >
                  {t("analyzeSelected")} ({selectedRoundIds.length})
                </Link>
                {selectedRoundIds.length >= 2 && (
                  <Link
                    className="rounded-md bg-green-700 px-3 py-2 text-sm font-semibold text-white"
                    href={`/rounds/compare?roundIds=${selectedRoundIds.join(",")}`}
                  >
                    {t("compareSelected")} ({selectedRoundIds.length})
                  </Link>
                )}
              </div>
            )}
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <SummaryMetric label={t("score")} value={formatSummary(summary.score)} />
            <SummaryMetric label={t("putts")} value={formatSummary(summary.putts)} />
            <SummaryMetric label={t("gir")} value={formatSummary(summary.gir)} />
            <SummaryMetric label={t("rounds")} value={rounds?.items.length ?? "-"} />
          </div>
        </section>

        <section className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3 text-sm text-muted">
            {rounds ? `${rounds.total} ${t("rounds")}` : t("loadingRounds")}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-left text-sm">
              <thead className="bg-surface text-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">{t("date")}</th>
                  <th className="px-4 py-2 font-medium">{t("selectedRounds")}</th>
                  <th className="px-4 py-2 font-medium">{t("course")}</th>
                  <th className="px-4 py-2 font-medium">{t("score")}</th>
                  <th className="px-4 py-2 font-medium">{t("holes")}</th>
                  <th className="px-4 py-2 font-medium">{t("companions")}</th>
                  <th className="px-4 py-2 font-medium">{t("status")}</th>
                  <th className="px-4 py-2 font-medium">{t("edit")}</th>
                </tr>
              </thead>
              <tbody>
                {(rounds?.items ?? []).map((round) => {
                  const detail = detailById.get(round.id);
                  return (
                    <tr className="border-t border-line hover:bg-surface" key={round.id}>
                      <td className="px-4 py-3">{round.play_date}</td>
                      <td className="px-4 py-3">
                        <input
                          checked={selectedRoundIds.includes(round.id)}
                          type="checkbox"
                          onChange={() => toggleRound(round.id)}
                        />
                      </td>
                      <td className="px-4 py-3 font-medium">
                        <Link href={`/rounds/${round.id}`}>{round.course_name}</Link>
                      </td>
                      <td className="px-4 py-3">{round.total_score ?? "-"}</td>
                      <td className="px-4 py-3">{round.hole_count}</td>
                      <td className="px-4 py-3">{round.companions.join(", ") || "-"}</td>
                      <td className="px-4 py-3">{round.computed_status}</td>
                      <td className="px-4 py-3">
                        {detail?.upload_review_id ? (
                          <Link
                            className="rounded-md border border-line px-2 py-1.5 text-xs font-semibold"
                            href={`/upload/${detail.upload_review_id}/review`}
                          >
                            {t("edit")}
                          </Link>
                        ) : (
                          "-"
                        )}
                      </td>
                    </tr>
                  );
                })}
                {rounds && rounds.items.length === 0 && (
                  <tr>
                    <td className="px-4 py-6 text-muted" colSpan={8}>{t("noRoundsMatch")}</td>
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

function SummaryMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md bg-surface p-3">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}

function roundSummary(rounds: RoundDetail[]) {
  return {
    score: stats(rounds.map((round) => round.total_score)),
    putts: stats(rounds.map((round) => round.metrics.putts_total ?? null)),
    gir: stats(rounds.map((round) => round.metrics.gir_count ?? null)),
  };
}

function stats(values: Array<number | null | undefined>) {
  const numbers = values.filter((value): value is number => typeof value === "number");
  if (numbers.length === 0) return null;
  return {
    min: Math.min(...numbers),
    max: Math.max(...numbers),
    avg: Math.round((numbers.reduce((sum, value) => sum + value, 0) / numbers.length) * 10) / 10,
  };
}

function formatSummary(value: { min: number; max: number; avg: number } | null) {
  if (!value) return "-";
  return `${value.min} / ${value.max} / ${value.avg}`;
}
