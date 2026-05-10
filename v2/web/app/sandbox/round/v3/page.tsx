"use client";

import Link from "next/link";
import { useState } from "react";

import { CLUB_GROUPS } from "../_shared/clubs";
import { CODES, CODE_LABEL, GRADES } from "../_shared/types";
import type { Club, Grade, Hole, Shot, ShotCode } from "../_shared/types";
import { useRoundDraft } from "../_shared/store";

type Field = "club" | "feel" | "result" | "distance" | "code";

type Pending = {
  club?: Club;
  feel?: Grade;
  result?: Grade;
  distance?: string;
  code?: ShotCode;
  codeNone?: boolean;
};

const EMPTY: Pending = {};

export default function V3Page() {
  const store = useRoundDraft();
  const [pending, setPending] = useState<Pending>(EMPTY);
  const [sheet, setSheet] = useState<Field | null>(null);

  if (!store.hydrated) {
    return <div className="p-8 text-sm text-muted">로드 중…</div>;
  }

  const hole = store.draft.holes.find((h) => h.number === store.draft.cursorHole)!;
  const shotIndex = hole.shots.length + 1;
  const canSave = Boolean(pending.club && pending.feel && pending.result);

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

  return (
    <div className="flex min-h-screen flex-col">
      <Header
        holeNumber={hole.number}
        par={hole.par}
        shotIndex={shotIndex}
        onParChange={(par) => store.setPar(hole.number, par)}
      />
      <PriorShots hole={hole} />

      <main className="flex-1 px-4 py-3">
        <div className="overflow-hidden rounded-md border border-line bg-white">
          <Row
            label="클럽"
            placeholder="선택"
            value={pending.club}
            onTap={() => setSheet("club")}
          />
          <Row
            label="Feel"
            placeholder="선택"
            value={pending.feel}
            onTap={() => setSheet("feel")}
          />
          <Row
            label="Result"
            placeholder="선택"
            value={pending.result}
            onTap={() => setSheet("result")}
          />
          <Row
            label="거리"
            placeholder="(선택)"
            value={pending.distance ? `${pending.distance} m` : undefined}
            onTap={() => setSheet("distance")}
            optional
          />
          <Row
            label="특이사항"
            placeholder="(선택)"
            value={pending.code ?? (pending.codeNone ? "—" : undefined)}
            onTap={() => setSheet("code")}
            optional
            last
          />
        </div>

        <button
          className={`mt-4 h-14 w-full rounded-md text-base font-semibold ${
            canSave ? "bg-green-700 text-white" : "bg-line text-muted"
          }`}
          disabled={!canSave}
          onClick={commitShot}
        >
          ✓ 샷 저장 후 다음
        </button>

        <p className="mt-3 text-center text-xs text-muted">
          행을 탭하면 해당 필드만 입력하는 시트가 올라옵니다.
        </p>
      </main>

      <Footer
        canGoPrev={hole.number > 1}
        canGoNext={hole.number < 18}
        onPrev={() => {
          store.goToHole(hole.number - 1);
          setPending(EMPTY);
        }}
        onNext={() => {
          store.goToHole(hole.number + 1);
          setPending(EMPTY);
        }}
        canRemoveLast={hole.shots.length > 0}
        onRemoveLast={() => store.removeLastShot(hole.number)}
      />

      {sheet && (
        <Sheet title={SHEET_TITLE[sheet]} onClose={() => setSheet(null)}>
          {sheet === "club" && (
            <ClubPicker
              value={pending.club}
              onChange={(club) => {
                setPending((p) => ({ ...p, club }));
                setSheet(null);
              }}
            />
          )}
          {sheet === "feel" && (
            <BigGrade
              value={pending.feel}
              onChange={(feel) => {
                setPending((p) => ({ ...p, feel }));
                setSheet(null);
              }}
            />
          )}
          {sheet === "result" && (
            <BigGrade
              value={pending.result}
              onChange={(result) => {
                setPending((p) => ({ ...p, result }));
                setSheet(null);
              }}
            />
          )}
          {sheet === "distance" && (
            <DistanceSheet
              value={pending.distance ?? ""}
              onCancel={() => setSheet(null)}
              onClear={() => {
                setPending((p) => ({ ...p, distance: undefined }));
                setSheet(null);
              }}
              onSubmit={(v) => {
                setPending((p) => ({ ...p, distance: v }));
                setSheet(null);
              }}
            />
          )}
          {sheet === "code" && (
            <CodeSheet
              value={pending.code}
              none={pending.codeNone}
              onPick={(code, none) => {
                setPending((p) => ({ ...p, code, codeNone: Boolean(none) }));
                setSheet(null);
              }}
            />
          )}
        </Sheet>
      )}
    </div>
  );
}

const SHEET_TITLE: Record<Field, string> = {
  club: "클럽",
  feel: "Feel",
  result: "Result",
  distance: "거리",
  code: "특이사항"
};

function Row({
  label,
  placeholder,
  value,
  onTap,
  optional,
  last
}: {
  label: string;
  placeholder: string;
  value?: string;
  onTap: () => void;
  optional?: boolean;
  last?: boolean;
}) {
  return (
    <button
      className={`flex w-full items-center justify-between px-4 py-4 text-left ${
        last ? "" : "border-b border-line"
      }`}
      onClick={onTap}
    >
      <span className="text-sm text-muted">
        {label}
        {optional && <span className="ml-1 text-xs">(선택)</span>}
      </span>
      <span className="flex items-center gap-2">
        <span className={value ? "text-base font-semibold" : "text-sm text-muted"}>
          {value ?? placeholder}
        </span>
        <span className="text-muted">›</span>
      </span>
    </button>
  );
}

function Sheet({
  title,
  children,
  onClose
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-30 flex flex-col bg-surface">
      <header className="flex items-center justify-between border-b border-line bg-white px-3 py-2">
        <button className="rounded-md border border-line px-3 py-2 text-sm" onClick={onClose}>
          ↶ 닫기
        </button>
        <span className="text-sm font-semibold">{title}</span>
        <div className="w-[60px]" />
      </header>
      <div className="flex-1 overflow-y-auto p-4">{children}</div>
    </div>
  );
}

function ClubPicker({ value, onChange }: { value?: Club; onChange: (c: Club) => void }) {
  return (
    <div className="space-y-3">
      {CLUB_GROUPS.map((group) => (
        <div key={group.label}>
          <p className="mb-1 text-xs text-muted">{group.label}</p>
          <div className="flex flex-wrap gap-2">
            {group.clubs.map((club) => (
              <button
                key={club}
                className={`min-w-[3.5rem] rounded-md border px-4 py-3 text-base font-semibold ${
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
        </div>
      ))}
    </div>
  );
}

function BigGrade({ value, onChange }: { value?: Grade; onChange: (g: Grade) => void }) {
  return (
    <div className="grid grid-cols-1 gap-3">
      {GRADES.map((g) => (
        <button
          key={g}
          className={`h-20 rounded-md border text-3xl font-bold ${
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

function DistanceSheet({
  value,
  onSubmit,
  onClear,
  onCancel
}: {
  value: string;
  onSubmit: (v: string) => void;
  onClear: () => void;
  onCancel: () => void;
}) {
  const [local, setLocal] = useState(value);
  return (
    <div className="space-y-3">
      <input
        autoFocus
        className="h-14 w-full rounded-md border border-line bg-white px-4 text-2xl"
        inputMode="decimal"
        onChange={(e) => setLocal(e.target.value.replace(/[^0-9.]/g, ""))}
        placeholder="예: 150"
        value={local}
      />
      <div className="grid grid-cols-3 gap-2">
        <button
          className="h-12 rounded-md border border-line text-sm"
          onClick={onCancel}
        >
          취소
        </button>
        <button className="h-12 rounded-md border border-line text-sm" onClick={onClear}>
          비우기
        </button>
        <button
          className="h-12 rounded-md bg-green-700 text-sm font-semibold text-white disabled:bg-line disabled:text-muted"
          disabled={!local}
          onClick={() => onSubmit(local)}
        >
          확인
        </button>
      </div>
    </div>
  );
}

function CodeSheet({
  value,
  none,
  onPick
}: {
  value?: ShotCode;
  none?: boolean;
  onPick: (code: ShotCode | undefined, none: boolean) => void;
}) {
  return (
    <div className="grid grid-cols-1 gap-2">
      <button
        className={`h-14 rounded-md border text-base font-semibold ${
          none ? "border-green-700 bg-green-700 text-white" : "border-line bg-white"
        }`}
        onClick={() => onPick(undefined, true)}
      >
        없음
      </button>
      {CODES.map((c) => (
        <button
          key={c}
          className={`h-14 rounded-md border text-base font-semibold ${
            value === c ? "border-green-700 bg-green-700 text-white" : "border-line bg-white"
          }`}
          onClick={() => onPick(c, false)}
        >
          {CODE_LABEL[c]}
        </button>
      ))}
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
