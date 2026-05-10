"use client";

import Link from "next/link";
import { useState } from "react";

import { CLUB_GROUPS } from "../_shared/clubs";
import { CODES, CODE_LABEL, GRADES } from "../_shared/types";
import type { Club, Grade, Hole, Shot, ShotCode } from "../_shared/types";
import { useRoundDraft } from "../_shared/store";

type Pending = {
  club?: Club;
  feel?: Grade;
  result?: Grade;
  distance?: string;
  code?: ShotCode;
};

const EMPTY: Pending = {};

export default function V1Page() {
  const store = useRoundDraft();
  const [pending, setPending] = useState<Pending>(EMPTY);

  if (!store.hydrated) {
    return <div className="p-8 text-sm text-muted">로드 중…</div>;
  }

  const hole = store.draft.holes.find((h) => h.number === store.draft.cursorHole)!;
  const shotIndex = hole.shots.length + 1;

  const canSave = pending.club && pending.feel && pending.result;

  function commitShot() {
    if (!pending.club || !pending.feel || !pending.result) return;
    const distance = pending.distance ? Number(pending.distance) : undefined;
    store.addShot(hole.number, {
      club: pending.club,
      feel: pending.feel,
      result: pending.result,
      distance: Number.isFinite(distance) ? distance : undefined,
      code: pending.code
    });
    setPending(EMPTY);
  }

  function goPrev() {
    if (hole.number > 1) store.goToHole(hole.number - 1);
  }
  function goNext() {
    if (hole.number < 18) store.goToHole(hole.number + 1);
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header
        holeNumber={hole.number}
        par={hole.par}
        shotIndex={shotIndex}
        onParChange={(par) => store.setPar(hole.number, par)}
      />
      <PriorShots hole={hole} />

      <main className="flex-1 px-4 pb-4">
        <Section label="클럽">
          <ClubPicker value={pending.club} onChange={(club) => setPending((p) => ({ ...p, club }))} />
        </Section>

        <Section label="Feel">
          <GradeRow
            value={pending.feel}
            onChange={(feel) => setPending((p) => ({ ...p, feel }))}
          />
        </Section>

        <Section label="Result">
          <GradeRow
            value={pending.result}
            onChange={(result) => setPending((p) => ({ ...p, result }))}
          />
        </Section>

        <Section label="거리 (선택)">
          <DistanceInput
            value={pending.distance ?? ""}
            onChange={(distance) => setPending((p) => ({ ...p, distance }))}
          />
        </Section>

        <Section label="특이사항 (선택)">
          <CodePicker value={pending.code} onChange={(code) => setPending((p) => ({ ...p, code }))} />
        </Section>

        <button
          className={`mt-4 h-14 w-full rounded-md text-base font-semibold ${
            canSave ? "bg-green-700 text-white" : "bg-line text-muted"
          }`}
          disabled={!canSave}
          onClick={commitShot}
        >
          ✓ 샷 저장 후 다음
        </button>
      </main>

      <Footer
        canGoPrev={hole.number > 1}
        canGoNext={hole.number < 18}
        onPrev={goPrev}
        onNext={goNext}
        canRemoveLast={hole.shots.length > 0}
        onRemoveLast={() => store.removeLastShot(hole.number)}
      />
    </div>
  );
}

function Header({
  holeNumber,
  par,
  shotIndex,
  onParChange
}: {
  holeNumber: number;
  par: number;
  shotIndex: number;
  onParChange: (par: number) => void;
}) {
  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-white px-3 py-2">
      <Link href="/sandbox/round" className="rounded-md border border-line px-3 py-2 text-sm">
        ✕
      </Link>
      <div className="flex items-center gap-2 text-sm">
        <span className="font-semibold">홀 {holeNumber}</span>
        <span className="text-muted">·</span>
        <ParChip value={par} onChange={onParChange} />
        <span className="text-muted">·</span>
        <span>샷 #{shotIndex}</span>
      </div>
      <div className="w-[44px]" />
    </header>
  );
}

function ParChip({ value, onChange }: { value: number; onChange: (par: number) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        className="rounded-md border border-line px-2 py-1 text-sm"
        onClick={() => setOpen((o) => !o)}
      >
        P{value}
      </button>
      {open && (
        <div className="absolute right-0 top-full z-20 mt-1 flex gap-1 rounded-md border border-line bg-white p-1 shadow-md">
          {[3, 4, 5, 6].map((p) => (
            <button
              key={p}
              className={`rounded px-2 py-1 text-sm ${p === value ? "bg-green-700 text-white" : ""}`}
              onClick={() => {
                onChange(p);
                setOpen(false);
              }}
            >
              P{p}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function PriorShots({ hole }: { hole: Hole }) {
  if (hole.shots.length === 0) {
    return (
      <div className="border-b border-line bg-surface px-4 py-2 text-xs text-muted">
        이번 홀 첫 샷
      </div>
    );
  }
  return (
    <div className="flex gap-2 overflow-x-auto border-b border-line bg-surface px-4 py-2 text-xs">
      {hole.shots.map((s, i) => (
        <ShotPill index={i + 1} key={s.id} shot={s} />
      ))}
    </div>
  );
}

function ShotPill({ index, shot }: { index: number; shot: Shot }) {
  const parts: string[] = [shot.club, shot.feel, shot.result];
  if (shot.distance !== undefined) parts.push(String(shot.distance));
  if (shot.code) parts.push(shot.code);
  return (
    <span className="whitespace-nowrap rounded-full border border-line bg-white px-3 py-1">
      {index}. {parts.join(" ")}
    </span>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="mt-3">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
      {children}
    </section>
  );
}

function ClubPicker({ value, onChange }: { value?: Club; onChange: (c: Club) => void }) {
  return (
    <div className="space-y-2">
      {CLUB_GROUPS.map((group) => (
        <div key={group.label} className="flex flex-wrap items-center gap-1">
          <span className="mr-1 w-16 shrink-0 text-xs text-muted">{group.label}</span>
          {group.clubs.map((club) => (
            <button
              key={club}
              className={`min-w-[3rem] rounded-md border px-3 py-2 text-sm font-semibold ${
                value === club
                  ? "border-green-700 bg-green-700 text-white"
                  : "border-line bg-white"
              }`}
              onClick={() => onChange(club)}
            >
              {club}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}

function GradeRow({ value, onChange }: { value?: Grade; onChange: (g: Grade) => void }) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {GRADES.map((g) => (
        <button
          key={g}
          className={`h-12 rounded-md border text-lg font-bold ${
            value === g ? "border-green-700 bg-green-700 text-white" : "border-line bg-white"
          }`}
          onClick={() => onChange(g)}
        >
          {g}
        </button>
      ))}
    </div>
  );
}

function DistanceInput({
  value,
  onChange
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <input
      className="h-12 w-full rounded-md border border-line bg-white px-3 text-base"
      inputMode="decimal"
      onChange={(e) => onChange(e.target.value.replace(/[^0-9.]/g, ""))}
      placeholder="거리 (예: 150)"
      value={value}
    />
  );
}

function CodePicker({
  value,
  onChange
}: {
  value?: ShotCode;
  onChange: (c: ShotCode | undefined) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <button
        className={`rounded-md border px-3 py-2 text-sm ${
          value === undefined ? "border-green-700 bg-green-700 text-white" : "border-line bg-white"
        }`}
        onClick={() => onChange(undefined)}
      >
        없음
      </button>
      {CODES.map((c) => (
        <button
          key={c}
          className={`rounded-md border px-3 py-2 text-sm ${
            value === c ? "border-green-700 bg-green-700 text-white" : "border-line bg-white"
          }`}
          onClick={() => onChange(c)}
        >
          {CODE_LABEL[c]}
        </button>
      ))}
    </div>
  );
}

function Footer({
  canGoPrev,
  canGoNext,
  onPrev,
  onNext,
  canRemoveLast,
  onRemoveLast
}: {
  canGoPrev: boolean;
  canGoNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  canRemoveLast: boolean;
  onRemoveLast: () => void;
}) {
  return (
    <footer className="sticky bottom-0 grid grid-cols-3 gap-1 border-t border-line bg-white p-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
      <button
        className="h-12 rounded-md border border-line text-sm disabled:text-muted"
        disabled={!canGoPrev}
        onClick={onPrev}
      >
        ◀ 이전 홀
      </button>
      <button
        className="h-12 rounded-md border border-line text-sm disabled:text-muted"
        disabled={!canRemoveLast}
        onClick={onRemoveLast}
      >
        ↶ 직전 샷 삭제
      </button>
      <button
        className="h-12 rounded-md border border-line text-sm disabled:text-muted"
        disabled={!canGoNext}
        onClick={onNext}
      >
        다음 홀 ▶
      </button>
    </footer>
  );
}
