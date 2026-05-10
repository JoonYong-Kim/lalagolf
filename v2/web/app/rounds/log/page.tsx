"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthExpiredModal } from "@/app/components/round-logger/AuthExpiredModal";
import { SyncIndicator } from "@/app/components/round-logger/SyncIndicator";
import { getCurrentUser } from "@/lib/api";
import { CLUB_GROUPS } from "@/lib/round-logger/clubs";
import type { ClubBag } from "@/lib/round-logger/types";
import { CODES, CODE_LABEL, GRADES } from "@/lib/round-logger/types";
import type {
  Club,
  Grade,
  LoggerHole,
  LoggerRound,
  LoggerShot,
  ShotCode
} from "@/lib/round-logger/types";
import { useRemoteClubBag } from "@/lib/round-logger/use-remote-club-bag";
import type { ShotInput } from "@/lib/round-logger/use-remote-draft";
import { useRemoteDraft } from "@/lib/round-logger/use-remote-draft";
import { useWakeLock } from "@/lib/round-logger/use-wake-lock";

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

function todayDate(): string {
  const d = new Date();
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

export default function RoundLogPage() {
  const router = useRouter();
  const [authChecked, setAuthChecked] = useState(false);
  const draft = useRemoteDraft();
  const bagStore = useRemoteClubBag();

  useWakeLock(authChecked);

  useEffect(() => {
    let alive = true;
    getCurrentUser()
      .then((user) => {
        if (!alive) return;
        if (!user) {
          router.replace("/");
          return;
        }
        setAuthChecked(true);
      })
      .catch(() => {
        if (alive) router.replace("/");
      });
    return () => {
      alive = false;
    };
  }, [router]);

  if (!authChecked || !draft.hydrated || !bagStore.hydrated) {
    return <div className="p-8 text-sm text-muted">로드 중…</div>;
  }

  const showAuthModal = draft.authExpired || bagStore.authExpired;

  return (
    <>
      {!draft.round ? (
        <StartRound
          onStart={async (meta) => {
            await draft.start();
            draft.setMeta(meta);
          }}
        />
      ) : (
        <LoggerView draft={draft} bag={bagStore.bag} />
      )}
      {showAuthModal && (
        <AuthExpiredModal
          onSuccess={() => {
            draft.clearAuthExpired();
            bagStore.clearAuthExpired();
          }}
        />
      )}
    </>
  );
}

function StartRound({
  onStart
}: {
  onStart: (meta: { date: string; course: string; companions: string }) => Promise<void>;
}) {
  const [date, setDate] = useState(todayDate());
  const [course, setCourse] = useState("");
  const [companions, setCompanions] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!course.trim()) {
      setError("코스명을 입력해주세요");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onStart({ date, course: course.trim(), companions: companions.trim() });
    } catch (e) {
      setError(e instanceof Error ? e.message : "라운드 시작 실패");
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-md px-4 py-6">
      <header className="mb-6 flex items-center justify-between">
        <Link className="text-sm text-muted" href="/dashboard">
          ← 대시보드
        </Link>
        <p className="text-xs uppercase tracking-wide text-green-700">라운드 시작</p>
      </header>

      <h1 className="mb-1 text-xl font-semibold">라운드 시작</h1>
      <p className="mb-6 text-sm text-muted">
        시작 후에는 한 샷씩 기록하면 자동으로 저장됩니다. 라운드 도중 앱을 닫아도 이어서 기록할 수
        있습니다.
      </p>

      <div className="space-y-3">
        <Field label="날짜">
          <input
            className={inputClass}
            onChange={(e) => setDate(e.target.value)}
            placeholder="2026.05.09"
            value={date}
          />
        </Field>
        <Field label="코스">
          <input
            className={inputClass}
            onChange={(e) => setCourse(e.target.value)}
            placeholder="베르힐 영종"
            value={course}
          />
        </Field>
        <Field label="동반자">
          <input
            className={inputClass}
            onChange={(e) => setCompanions(e.target.value)}
            placeholder="이름 공백으로 구분"
            value={companions}
          />
        </Field>
      </div>

      {error && <p className="mt-3 text-sm text-[#a34242]">{error}</p>}

      <button
        className="mt-6 h-14 w-full rounded-md bg-green-700 text-base font-semibold text-white disabled:bg-line disabled:text-muted"
        disabled={submitting}
        onClick={submit}
      >
        {submitting ? "시작하는 중…" : "라운드 시작"}
      </button>

      <p className="mt-6 text-center text-xs text-muted">
        클럽 가방을 먼저 설정하면 거리가 자동 입력됩니다 ·{" "}
        <Link className="underline" href="/settings/clubs">
          클럽 가방 설정
        </Link>
      </p>
    </main>
  );
}

function LoggerView({
  draft,
  bag
}: {
  draft: ReturnType<typeof useRemoteDraft>;
  bag: ClubBag;
}) {
  const round = draft.round!;
  const [pending, setPending] = useState<Pending>(EMPTY);
  const [stage, setStage] = useState<Stage>("club");
  const [editingId, setEditingId] = useState<string | null>(null);

  const hole = round.holes.find((h) => h.number === round.cursorHole)!;
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
    const defaultDist = bag.distances[club];
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

  function startEdit(shot: LoggerShot) {
    setPending({
      club: shot.club,
      feel: shot.feel,
      result: shot.result,
      distance: shot.distance !== undefined ? String(shot.distance) : undefined,
      distanceSkipped: shot.distance === undefined,
      code: shot.code,
      codeSkipped: shot.code === undefined
    });
    setEditingId(shot.id);
    setStage("ready");
  }

  function commitShot() {
    if (!pending.club || !pending.feel || !pending.result) return;
    const distNum = pending.distance ? Number(pending.distance) : undefined;
    const wasEditing = Boolean(editingId);
    const holeOut = pending.code === "OK";
    const input: ShotInput = {
      club: pending.club,
      feel: pending.feel,
      result: pending.result,
      distance: distNum !== undefined && Number.isFinite(distNum) ? distNum : undefined,
      code: pending.code
    };
    if (editingId) {
      draft.updateShot(hole.number, editingId, input);
    } else {
      draft.addShot(hole.number, input);
    }
    reset();
    if (!wasEditing && holeOut && hole.number < 18) {
      draft.goToHole(hole.number + 1);
    }
  }

  function deleteEditingShot() {
    if (!editingId) return;
    if (!window.confirm("이 샷을 삭제할까요?")) return;
    draft.removeShot(hole.number, editingId);
    reset();
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header
        authExpired={draft.authExpired}
        editing={Boolean(editingId)}
        holeNumber={hole.number}
        lastSyncAt={draft.lastSyncAt}
        onParChange={(par) => draft.setPar(hole.number, par)}
        onRetry={() => draft.flushNow()}
        par={hole.par}
        queueSize={draft.queueSize}
        round={round}
        shotIndex={shotIndex}
        syncStatus={draft.syncStatus}
      />
      <PriorShots editingId={editingId} hole={hole} onTapShot={startEdit} />

      <main className="flex-1 px-4 pb-4">
        {editingId && (
          <div className="mt-3 rounded-md border border-[#e0c080] bg-[#fff7e6] p-2 text-xs text-[#8a5a00]">
            샷 #{shotIndex} 수정 중 — 저장하면 덮어쓰고 위치는 유지됩니다.
          </div>
        )}

        {pending.club && (
          <DoneRow label="클럽" onEdit={() => setStage("club")} value={pending.club} />
        )}
        {pending.feel && <DoneRow label="Feel" onEdit={() => setStage("feel")} value={pending.feel} />}
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
            <ClubPicker bag={bag} onChange={handleClubPick} value={pending.club} />
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

        {draft.error && (
          <p className="mt-4 text-xs text-[#a34242]">동기화 오류: {draft.error}</p>
        )}
      </main>

      <Footer
        canFinalize={round.holes.some((h) => h.shots.length > 0)}
        canGoNext={hole.number < 18}
        canGoPrev={hole.number > 1}
        canRemoveLast={hole.shots.length > 0 && !editingId}
        onNext={() => {
          draft.goToHole(hole.number + 1);
          reset();
        }}
        onPrev={() => {
          draft.goToHole(hole.number - 1);
          reset();
        }}
        onRemoveLast={() => draft.removeLastShot(hole.number)}
      />
    </div>
  );
}

function Header({
  authExpired,
  editing,
  holeNumber,
  lastSyncAt,
  par,
  queueSize,
  shotIndex,
  syncStatus,
  round,
  onParChange,
  onRetry
}: {
  authExpired: boolean;
  editing: boolean;
  holeNumber: number;
  lastSyncAt: number | null;
  par: number;
  queueSize: number;
  shotIndex: number;
  syncStatus: "idle" | "syncing" | "error";
  round: LoggerRound;
  onParChange: (par: number) => void;
  onRetry: () => void | Promise<void>;
}) {
  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-white px-3 py-2">
      <Link
        className="rounded-md border border-line px-3 py-2 text-sm"
        href="/rounds/log/finalize"
      >
        ✓ 종료
      </Link>
      <div className="flex items-center gap-2 text-sm">
        <span className="font-semibold">홀 {holeNumber}</span>
        <span className="text-muted">·</span>
        <ParChip onChange={onParChange} value={par} />
        <span className="text-muted">·</span>
        <span>{editing ? `샷 #${shotIndex} 수정` : `샷 #${shotIndex}`}</span>
      </div>
      <SyncIndicator
        authExpired={authExpired}
        lastSyncAt={lastSyncAt}
        onRetry={onRetry}
        queueSize={queueSize}
        syncStatus={syncStatus}
      />
      <span className="sr-only">{round.course || "코스 미입력"}</span>
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
              className={`rounded px-2 py-1 text-sm ${p === value ? "bg-green-700 text-white" : ""}`}
              key={p}
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
  hole: LoggerHole;
  editingId: string | null;
  onTapShot: (shot: LoggerShot) => void;
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
  const hasBag = bag.enabled.length > 0;

  return (
    <div className="space-y-2">
      {!hasBag && !showAll && (
        <p className="text-xs text-muted">
          가방이 비어있습니다.{" "}
          <Link className="text-green-700 underline" href="/settings/clubs">
            가방 설정
          </Link>{" "}
          또는 [전체 클럽 보기]를 사용해주세요.
        </p>
      )}
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
  onRemoveLast,
  canFinalize
}: {
  canGoPrev: boolean;
  canGoNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  canRemoveLast: boolean;
  onRemoveLast: () => void;
  canFinalize: boolean;
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
      <Link
        className={`col-span-3 mt-1 grid h-10 place-items-center rounded-md text-sm ${
          canFinalize ? "bg-green-700 text-white" : "bg-line text-muted pointer-events-none"
        }`}
        href="/rounds/log/finalize"
      >
        ✓ 종료 화면으로
      </Link>
    </footer>
  );
}

function chipClass(active: boolean): string {
  return `rounded-md border px-3 py-2 text-sm ${
    active ? "border-green-700 bg-green-700 text-white" : "border-line bg-white"
  }`;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid grid-cols-[5rem_1fr] items-center gap-2 text-sm">
      <span className="text-muted">{label}</span>
      {children}
    </label>
  );
}

const inputClass = "h-10 w-full rounded-md border border-line bg-white px-3 text-sm";
