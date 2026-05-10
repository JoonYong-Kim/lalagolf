"use client";

import Link from "next/link";
import { useState } from "react";

import { CLUB_GROUPS } from "../_shared/clubs";
import { CODES, CODE_LABEL, GRADES } from "../_shared/types";
import type { Club, Grade, Hole, Shot, ShotCode } from "../_shared/types";
import { useRoundDraft } from "../_shared/store";
import { useClubBag } from "../_shared/settings";
import type { ClubBag } from "../_shared/settings";

type Stage = "club" | "feel" | "result" | "distance" | "code" | "ready";

type Pending = {
  club?: Club;
  feel?: Grade;
  result?: Grade;
  distance?: string;
  distanceSkipped?: boolean;
  code?: ShotCode;
  codeSkipped?: boolean;
};

const EMPTY: Pending = {};

function nextStage(p: Pending): Stage {
  if (!p.club) return "club";
  if (!p.feel) return "feel";
  if (!p.result) return "result";
  if (p.distance === undefined && !p.distanceSkipped) return "distance";
  if (p.code === undefined && !p.codeSkipped) return "code";
  return "ready";
}

export default function V2Page() {
  const store = useRoundDraft();
  const bagStore = useClubBag();
  const [pending, setPending] = useState<Pending>(EMPTY);
  const [stage, setStage] = useState<Stage>("club");
  const [editingId, setEditingId] = useState<string | null>(null);

  if (!store.hydrated || !bagStore.hydrated) {
    return <div className="p-8 text-sm text-muted">로드 중…</div>;
  }

  const hole = store.draft.holes.find((h) => h.number === store.draft.cursorHole)!;
  const editingIndex = editingId ? hole.shots.findIndex((s) => s.id === editingId) : -1;
  const shotIndex = editingIndex >= 0 ? editingIndex + 1 : hole.shots.length + 1;

  function reset() {
    setPending(EMPTY);
    setStage("club");
    setEditingId(null);
  }

  function setField(patch: Partial<Pending>) {
    const next = { ...pending, ...patch };
    setPending(next);
    setStage(nextStage(next));
  }

  function handleClubPick(club: Club) {
    const defaultDist = bagStore.bag.distances[club];
    const shouldPrefill =
      !editingId
      && pending.distance === undefined
      && !pending.distanceSkipped
      && defaultDist !== undefined;
    setField({
      club,
      ...(shouldPrefill ? { distance: String(defaultDist) } : {})
    });
  }

  function startEdit(shot: Shot) {
    const next: Pending = {
      club: shot.club,
      feel: shot.feel,
      result: shot.result,
      distance: shot.distance !== undefined ? String(shot.distance) : undefined,
      distanceSkipped: shot.distance === undefined,
      code: shot.code,
      codeSkipped: shot.code === undefined
    };
    setPending(next);
    setEditingId(shot.id);
    setStage("ready");
  }

  function commitShot() {
    if (!pending.club || !pending.feel || !pending.result) return;
    const distNum = pending.distance ? Number(pending.distance) : undefined;
    const wasEditing = Boolean(editingId);
    const holeOut = pending.code === "OK";
    const payload = {
      club: pending.club,
      feel: pending.feel,
      result: pending.result,
      distance: distNum !== undefined && Number.isFinite(distNum) ? distNum : undefined,
      code: pending.code
    };
    if (editingId) {
      store.updateShot(hole.number, editingId, payload);
    } else {
      store.addShot(hole.number, payload);
    }
    reset();
    if (!wasEditing && holeOut && hole.number < 18) {
      store.goToHole(hole.number + 1);
    }
  }

  function deleteEditingShot() {
    if (!editingId) return;
    if (!window.confirm("이 샷을 삭제할까요?")) return;
    store.removeShot(hole.number, editingId);
    reset();
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header
        editing={Boolean(editingId)}
        holeNumber={hole.number}
        onParChange={(par) => store.setPar(hole.number, par)}
        par={hole.par}
        shotIndex={shotIndex}
      />
      <PriorShots
        editingId={editingId}
        hole={hole}
        onTapShot={startEdit}
      />

      <main className="flex-1 px-4 pb-4">
        {editingId && (
          <div className="mt-3 rounded-md border border-[#e0c080] bg-[#fff7e6] p-2 text-xs text-[#8a5a00]">
            샷 #{shotIndex} 수정 중 — 저장하면 덮어쓰고, 위치는 그대로 유지됩니다.
          </div>
        )}

        {pending.club && (
          <DoneRow label="클럽" onEdit={() => setStage("club")} value={pending.club} />
        )}
        {pending.feel && (
          <DoneRow label="Feel" onEdit={() => setStage("feel")} value={pending.feel} />
        )}
        {pending.result && (
          <DoneRow label="Result" onEdit={() => setStage("result")} value={pending.result} />
        )}
        {(pending.distance || pending.distanceSkipped) && (
          <DoneRow
            label="거리"
            onEdit={() => setStage("distance")}
            value={pending.distance ? `${pending.distance} m` : "—"}
          />
        )}
        {(pending.code || pending.codeSkipped) && (
          <DoneRow
            label="특이사항"
            onEdit={() => setStage("code")}
            value={pending.code ? CODE_LABEL[pending.code] : "—"}
          />
        )}

        {stage === "club" && (
          <Active label="클럽 선택">
            <ClubPicker bag={bagStore.bag} onChange={handleClubPick} value={pending.club} />
          </Active>
        )}

        {stage === "feel" && (
          <Active label="Feel">
            <GradeRow onChange={(feel) => setField({ feel })} value={pending.feel} />
          </Active>
        )}

        {stage === "result" && (
          <Active label="Result">
            <GradeRow onChange={(result) => setField({ result })} value={pending.result} />
          </Active>
        )}

        {stage === "distance" && (
          <Active label="거리 (선택)">
            <div className="flex items-center gap-2">
              <input
                autoFocus
                className="h-12 flex-1 rounded-md border border-line bg-white px-3 text-base"
                inputMode="decimal"
                onChange={(e) =>
                  setPending((p) => ({
                    ...p,
                    distance: e.target.value.replace(/[^0-9.]/g, ""),
                    distanceSkipped: false
                  }))
                }
                placeholder="예: 150"
                value={pending.distance ?? ""}
              />
              <button
                className="h-12 rounded-md border border-line px-4 text-sm"
                onClick={() => setField({ distance: undefined, distanceSkipped: true })}
              >
                건너뛰기
              </button>
              <button
                className="h-12 rounded-md bg-green-700 px-4 text-sm font-semibold text-white disabled:bg-line disabled:text-muted"
                disabled={!pending.distance}
                onClick={() => setField({ distanceSkipped: false })}
              >
                다음
              </button>
            </div>
          </Active>
        )}

        {stage === "code" && (
          <Active label="특이사항 (선택)">
            <div className="flex flex-wrap gap-2">
              <button
                className={chipClass(pending.code === undefined && Boolean(pending.codeSkipped))}
                onClick={() => setField({ code: undefined, codeSkipped: true })}
              >
                없음
              </button>
              {CODES.map((c) => (
                <button
                  className={chipClass(pending.code === c)}
                  key={c}
                  onClick={() => setField({ code: c, codeSkipped: false })}
                >
                  {CODE_LABEL[c]}
                </button>
              ))}
            </div>
          </Active>
        )}

        {stage === "ready" && (
          <div className="mt-4 space-y-2">
            <button
              className="h-14 w-full rounded-md bg-green-700 text-base font-semibold text-white"
              onClick={commitShot}
            >
              ✓ {editingId ? "수정 저장" : "샷 저장 후 다음"}
            </button>
            {editingId && (
              <div className="grid grid-cols-2 gap-2">
                <button className="h-12 rounded-md border border-line text-sm" onClick={reset}>
                  편집 취소
                </button>
                <button
                  className="h-12 rounded-md border border-[#a34242] text-sm text-[#a34242]"
                  onClick={deleteEditingShot}
                >
                  이 샷 삭제
                </button>
              </div>
            )}
          </div>
        )}
      </main>

      <Footer
        canGoNext={hole.number < 18}
        canGoPrev={hole.number > 1}
        canRemoveLast={hole.shots.length > 0 && !editingId}
        onNext={() => {
          store.goToHole(hole.number + 1);
          reset();
        }}
        onPrev={() => {
          store.goToHole(hole.number - 1);
          reset();
        }}
        onRemoveLast={() => store.removeLastShot(hole.number)}
      />
    </div>
  );
}

function Header({
  editing,
  holeNumber,
  par,
  shotIndex,
  onParChange
}: {
  editing: boolean;
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
        <ParChip onChange={onParChange} value={par} />
        <span className="text-muted">·</span>
        <span>{editing ? `샷 #${shotIndex} 수정` : `샷 #${shotIndex}`}</span>
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

function PriorShots({
  hole,
  editingId,
  onTapShot
}: {
  hole: Hole;
  editingId: string | null;
  onTapShot: (shot: Shot) => void;
}) {
  if (hole.shots.length === 0) {
    return (
      <div className="border-b border-line bg-surface px-4 py-2 text-xs text-muted">
        이번 홀 첫 샷 — 입력 후 칩을 탭하면 그 샷을 수정할 수 있습니다.
      </div>
    );
  }
  return (
    <div className="flex gap-2 overflow-x-auto border-b border-line bg-surface px-4 py-2 text-xs">
      {hole.shots.map((s, i) => {
        const parts: string[] = [s.club, s.feel, s.result];
        if (s.distance !== undefined) parts.push(String(s.distance));
        if (s.code) parts.push(s.code);
        return (
          <button
            className={`whitespace-nowrap rounded-full border px-3 py-1 ${
              editingId === s.id
                ? "border-green-700 bg-green-700 text-white"
                : "border-line bg-white"
            }`}
            key={s.id}
            onClick={() => onTapShot(s)}
          >
            {i + 1}. {parts.join(" ")}
          </button>
        );
      })}
    </div>
  );
}

function DoneRow({
  label,
  value,
  onEdit
}: {
  label: string;
  value: string;
  onEdit: () => void;
}) {
  return (
    <div className="mt-2 flex items-center justify-between rounded-md border border-line bg-white px-3 py-2 text-sm">
      <span>
        <span className="text-muted">{label}: </span>
        <span className="font-semibold">{value}</span>
      </span>
      <button className="text-xs text-green-700" onClick={onEdit}>
        수정
      </button>
    </div>
  );
}

function Active({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="mt-3 rounded-md border-2 border-green-700 bg-white p-3">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-green-700">{label}</p>
      {children}
    </section>
  );
}

function ClubPicker({
  bag,
  value,
  onChange
}: {
  bag: ClubBag;
  value?: Club;
  onChange: (c: Club) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const inBag = (club: Club) => bag.enabled.includes(club);

  return (
    <div className="space-y-2">
      {CLUB_GROUPS.map((group) => {
        const clubs = showAll ? group.clubs : group.clubs.filter(inBag);
        if (clubs.length === 0) return null;
        return (
          <div className="flex flex-wrap items-center gap-1" key={group.label}>
            <span className="mr-1 w-16 shrink-0 text-xs text-muted">{group.label}</span>
            {clubs.map((club) => {
              const isSelected = value === club;
              const isOutOfBag = !inBag(club);
              return (
                <button
                  className={`min-w-[3rem] rounded-md border px-3 py-2 text-sm font-semibold ${
                    isSelected
                      ? "border-green-700 bg-green-700 text-white"
                      : isOutOfBag
                        ? "border-dashed border-line bg-white text-muted"
                        : "border-line bg-white"
                  }`}
                  key={club}
                  onClick={() => onChange(club)}
                >
                  {club}
                </button>
              );
            })}
          </div>
        );
      })}
      <button
        className="mt-2 text-xs text-green-700 underline"
        onClick={() => setShowAll((s) => !s)}
      >
        {showAll ? "내 클럽만 보기" : "전체 클럽 보기"}
      </button>
    </div>
  );
}

function GradeRow({ value, onChange }: { value?: Grade; onChange: (g: Grade) => void }) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {GRADES.map((g) => (
        <button
          className={`h-14 rounded-md border text-xl font-bold ${
            value === g ? "border-green-700 bg-green-700 text-white" : "border-line bg-white"
          }`}
          key={g}
          onClick={() => onChange(g)}
        >
          {g}
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

function chipClass(active: boolean): string {
  return `rounded-md border px-3 py-2 text-sm ${
    active ? "border-green-700 bg-green-700 text-white" : "border-line bg-white"
  }`;
}
