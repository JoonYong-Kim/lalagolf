"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import {
  createPracticeDiary,
  getPracticeDiary,
  getPracticePlans,
  updatePracticePlan,
  type PracticeDiaryEntry,
  type PracticePlan,
} from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const initialSelectedDate = "2000-01-01";

export default function PracticePage() {
  const { t } = useI18n();
  const [plans, setPlans] = useState<PracticePlan[]>([]);
  const [entries, setEntries] = useState<PracticeDiaryEntry[]>([]);
  const [selectedDate, setSelectedDate] = useState(initialSelectedDate);
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [diaryTitle, setDiaryTitle] = useState("");
  const [diaryBody, setDiaryBody] = useState("");
  const [practiceView, setPracticeView] = useState<"calendar" | "diary">("calendar");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      const [nextPlans, nextEntries] = await Promise.all([getPracticePlans(), getPracticeDiary()]);
      setPlans(nextPlans);
      setEntries(nextEntries);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Practice load failed");
    }
  }

  useEffect(() => {
    setSelectedDate(formatDate(new Date()));
    load();
  }, []);

  const selectedEntries = useMemo(
    () => entries.filter((entry) => entry.entry_date === selectedDate),
    [entries, selectedDate],
  );
  const entryDates = useMemo(() => new Set(entries.map((entry) => entry.entry_date)), [entries]);
  const activePlans = plans.filter((plan) => plan.status !== "done");
  const donePlans = plans.filter((plan) => plan.status === "done");

  async function submitDiary() {
    if (!diaryBody.trim()) return;
    setError("");
    const selectedPlan = plans.find((plan) => plan.id === selectedPlanId);
    try {
      await createPracticeDiary({
        entry_date: selectedDate,
        title: diaryTitle.trim() || selectedPlan?.title || t("diaryEntry"),
        body: diaryBody.trim(),
        category: selectedPlan?.category ?? "putting",
        practice_plan_id: selectedPlanId || undefined,
        source_insight_id: selectedPlan?.source_insight_id ?? undefined,
      });
      setDiaryTitle("");
      setDiaryBody("");
      setStatus(t("saved"));
      await load();
    } catch (diaryError) {
      setError(diaryError instanceof Error ? diaryError.message : "Diary save failed");
    }
  }

  async function markDone(plan: PracticePlan) {
    await updatePracticePlan(plan.id, { status: "done" });
    await load();
  }

  return (
    <AppShell eyebrow={t("practice")} title={t("practicePlans")}>
      <div className="mt-5 space-y-5">
        <section className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold">{t("createPracticePlan")}</h2>
              <p className="mt-1 text-sm leading-6 text-muted">{t("insightDrivenPractice")}</p>
            </div>
            <Link className={primaryButton} href="/analysis">
              {t("goToAnalysis")}
            </Link>
          </div>
        </section>

        <section className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
          <div className="rounded-md border border-line bg-white">
            <div className="flex items-center justify-between border-b border-line px-4 py-3">
              <h2 className="text-base font-semibold">{t("practicePlans")}</h2>
              <span className="text-sm text-muted">{activePlans.length} {t("active")}</span>
            </div>
            <div className="divide-y divide-line">
              {activePlans.map((plan) => (
                <PracticePlanRow doneLabel={t("markDone")} key={plan.id} onDone={markDone} plan={plan} />
              ))}
              {activePlans.length === 0 && <p className="p-4 text-sm text-muted">{t("noPracticePlans")}</p>}
            </div>
            {donePlans.length > 0 && (
              <div className="border-t border-line bg-surface px-4 py-3">
                <p className="mb-2 text-xs font-semibold uppercase text-muted">{t("done")}</p>
                <div className="grid gap-2">
                  {donePlans.slice(0, 4).map((plan) => (
                    <div className="rounded-md border border-line bg-white px-3 py-2 text-sm" key={plan.id}>
                      <span className="font-semibold">{plan.title}</span>
                      <span className="ml-2 text-muted">{plan.category}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="rounded-md border border-line bg-white">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
              <div>
                <h2 className="text-base font-semibold">
                  {practiceView === "calendar" ? t("practiceCalendar") : t("practiceDiary")}
                </h2>
                <p className="mt-1 text-sm text-muted">
                  {t("selectedDate")}: <span className="font-semibold text-ink">{selectedDate}</span>
                </p>
              </div>
              <div className="flex rounded-md border border-line bg-surface p-1">
                <button
                  className={practiceView === "calendar" ? segmentedActive : segmentedButton}
                  onClick={() => setPracticeView("calendar")}
                >
                  {t("practiceCalendar")}
                </button>
                <button
                  className={practiceView === "diary" ? segmentedActive : segmentedButton}
                  onClick={() => setPracticeView("diary")}
                >
                  {t("practiceDiary")}
                </button>
              </div>
            </div>

            {practiceView === "calendar" ? (
              <div className="p-4">
                <PracticeCalendar
                  entryDates={entryDates}
                  selectedDate={selectedDate}
                  setSelectedDate={setSelectedDate}
                />
              </div>
            ) : (
              <div className="grid gap-4 p-4">
                <div>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-semibold">{t("practiceDiary")}</h3>
                    <span className="text-sm text-muted">{selectedEntries.length}</span>
                  </div>
                  <div className="mt-3 grid max-h-56 gap-3 overflow-y-auto pr-1">
                    {selectedEntries.map((entry) => (
                      <article className="rounded-md border border-line bg-surface p-3" key={entry.id}>
                        <p className="text-xs font-semibold text-green-700">{entry.entry_date}</p>
                        <h4 className="mt-1 font-semibold">{entry.title}</h4>
                        <p className="mt-2 text-sm leading-6 text-muted">{entry.body}</p>
                      </article>
                    ))}
                    {selectedEntries.length === 0 && <p className="text-sm text-muted">{t("noDiaryEntries")}</p>}
                  </div>
                </div>

                <div className="border-t border-line pt-4">
                  <h3 className="text-sm font-semibold">{t("diaryEntry")}</h3>
                  <div className="mt-3 grid gap-3">
                    <select
                      className={inputClass}
                      value={selectedPlanId}
                      onChange={(event) => setSelectedPlanId(event.target.value)}
                    >
                      <option value="">{t("linkedPracticePlan")}</option>
                      {plans.map((plan) => (
                        <option key={plan.id} value={plan.id}>
                          {plan.title}
                        </option>
                      ))}
                    </select>
                    <input
                      className={inputClass}
                      placeholder={t("title")}
                      value={diaryTitle}
                      onChange={(event) => setDiaryTitle(event.target.value)}
                    />
                    <textarea
                      className={`${inputClass} min-h-36 resize-y`}
                      placeholder={t("body")}
                      value={diaryBody}
                      onChange={(event) => setDiaryBody(event.target.value)}
                    />
                    <div className="flex justify-end">
                      <button className={primaryButton} onClick={submitDiary}>
                        {t("saveEdits")}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
      {status && <p className="mt-4 text-sm text-muted">{status}</p>}
      {error && <p className="mt-4 rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">{error}</p>}
    </AppShell>
  );
}

const inputClass = "min-w-0 flex-1 rounded-md border border-line px-3 py-2 text-sm";
const primaryButton = "rounded-md bg-green-700 px-4 py-2 text-sm font-semibold text-white";
const secondaryButton = "rounded-md border border-line px-3 py-1.5 text-sm font-semibold";
const segmentedButton = "rounded px-3 py-1.5 text-sm font-semibold text-muted";
const segmentedActive = "rounded bg-white px-3 py-1.5 text-sm font-semibold text-green-700 shadow-sm";

function PracticePlanRow({
  doneLabel,
  onDone,
  plan,
}: {
  doneLabel: string;
  onDone: (plan: PracticePlan) => void;
  plan: PracticePlan;
}) {
  const routine = Array.isArray(plan.drill_json?.routine) ? plan.drill_json.routine : [];
  return (
    <article className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase text-green-700">
            {plan.category} · {plan.status}
          </p>
          <h3 className="mt-1 text-base font-semibold">{plan.title}</h3>
          {plan.purpose && <p className="mt-2 text-sm leading-6 text-muted">{plan.purpose}</p>}
        </div>
        <button className={secondaryButton} onClick={() => onDone(plan)}>
          {doneLabel}
        </button>
      </div>
      {routine.length > 0 && (
        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          {routine.map((item) => (
            <div className="rounded-md bg-surface px-3 py-2 text-sm text-muted" key={String(item)}>
              {String(item)}
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

function PracticeCalendar({
  entryDates,
  selectedDate,
  setSelectedDate,
}: {
  entryDates: Set<string>;
  selectedDate: string;
  setSelectedDate: (date: string) => void;
}) {
  const current = new Date(`${selectedDate}T00:00:00`);
  const year = current.getFullYear();
  const month = current.getMonth();
  const firstDay = new Date(year, month, 1);
  const startOffset = firstDay.getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [
    ...Array.from({ length: startOffset }, () => null),
    ...Array.from({ length: daysInMonth }, (_, index) => index + 1),
  ];

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <button className={secondaryButton} onClick={() => setSelectedDate(formatDate(new Date(year, month - 1, 1)))}>
          {"<"}
        </button>
        <p className="text-sm font-semibold">{year}-{String(month + 1).padStart(2, "0")}</p>
        <button className={secondaryButton} onClick={() => setSelectedDate(formatDate(new Date(year, month + 1, 1)))}>
          {">"}
        </button>
      </div>
      <div className="grid grid-cols-7 gap-1 text-center text-sm">
        {["S", "M", "T", "W", "T", "F", "S"].map((day, index) => (
          <div className="py-1 text-xs font-semibold text-muted" key={`${day}-${index}`}>{day}</div>
        ))}
        {cells.map((day, index) => {
          const value = day ? formatDate(new Date(year, month, day)) : "";
          return (
            <button
              className={
                value === selectedDate
                  ? "relative h-11 rounded-md bg-green-700 text-sm font-semibold text-white"
                  : "relative h-11 rounded-md border border-line bg-white text-sm font-semibold disabled:bg-surface"
              }
              disabled={!day}
              key={`${day ?? "empty"}-${index}`}
              onClick={() => setSelectedDate(value)}
            >
              <span>{day ?? ""}</span>
              {value && entryDates.has(value) && (
                <span
                  className={
                    value === selectedDate
                      ? "absolute bottom-1 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full bg-white"
                      : "absolute bottom-1 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full bg-green-700"
                  }
                />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function formatDate(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
