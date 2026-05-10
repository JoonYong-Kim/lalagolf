"use client";

import Link from "next/link";
import { useState } from "react";

import { canonicalize, holesPlayed, totalShots } from "./_shared/canonicalize";
import { CLUB_GROUPS } from "./_shared/clubs";
import { useClubBag } from "./_shared/settings";
import { useRoundDraft } from "./_shared/store";
import type { Club } from "./_shared/types";

const VARIANTS = [
  {
    id: "v1",
    title: "V1 — 모든 필드 펼침",
    summary: "한 화면에 클럽/등급/거리/코드 모두 동시 노출. 자동 진행 없음. 탭 수 최소, 화면 빽빽.",
    href: "/sandbox/round/v1"
  },
  {
    id: "v2",
    title: "V2 — 점진 노출",
    summary: "클럽 → Feel → Result → 거리 → 코드 순으로 필드가 차례로 등장. 시선 집중, 탭 수 약간 많음.",
    href: "/sandbox/round/v2"
  },
  {
    id: "v3",
    title: "V3 — 바텀시트 피커",
    summary: "한 줄짜리 요약 행을 탭하면 풀스크린 시트가 올라와 그 필드만 입력. 위에서 아래로 흐름.",
    href: "/sandbox/round/v3"
  }
] as const;

export default function SandboxIndex() {
  const store = useRoundDraft();
  const bagStore = useClubBag();
  const [showText, setShowText] = useState(false);
  const [editMeta, setEditMeta] = useState(false);
  const [showBag, setShowBag] = useState(false);

  if (!store.hydrated || !bagStore.hydrated) {
    return <div className="p-8 text-sm text-muted">로드 중…</div>;
  }

  const { draft } = store;
  const text = canonicalize(draft);

  return (
    <main className="mx-auto max-w-xl px-4 py-6">
      <header className="mb-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-green-700">Sandbox</p>
        <h1 className="mt-1 text-2xl font-semibold">라운드 입력 UX 비교</h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          API 연결 없이 모바일 입력 UX만 비교하는 임시 영역입니다. 모든 변형이 같은 드래프트
          (localStorage)를 공유하므로, 한 변형에서 입력한 값이 다른 변형에서도 보입니다.
        </p>
        <p className="mt-2 rounded-md border border-line bg-white p-3 text-xs leading-5 text-muted">
          정식 라운드 기록은{" "}
          <Link className="text-green-700 underline" href="/rounds/log">
            /rounds/log
          </Link>{" "}
          에서 사용하세요. 이 샌드박스는 UX 변형 비교용으로 유지됩니다.
        </p>
      </header>

      <section className="mb-5 rounded-md border border-line bg-white p-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted">현재 드래프트</p>
            <p className="mt-1 text-sm">
              <span className="font-semibold">{draft.date} {draft.time}</span>
            </p>
            <p className="text-sm">{draft.course || <span className="text-muted">코스 미입력</span>}</p>
            <p className="text-sm">
              {draft.companions || <span className="text-muted">동반자 미입력</span>}
            </p>
            <p className="mt-2 text-xs text-muted">
              {holesPlayed(draft)}홀 진행 · 총 {totalShots(draft)}샷
            </p>
          </div>
          <button
            className="shrink-0 rounded-md border border-line px-3 py-2 text-sm"
            onClick={() => setEditMeta((v) => !v)}
          >
            {editMeta ? "닫기" : "메타 수정"}
          </button>
        </div>

        {editMeta && (
          <div className="mt-3 grid gap-2 border-t border-line pt-3">
            <Field label="날짜">
              <input
                className={inputClass}
                onChange={(e) => store.setMeta({ date: e.target.value })}
                placeholder="2026.05.09"
                value={draft.date}
              />
            </Field>
            <Field label="시간">
              <input
                className={inputClass}
                onChange={(e) => store.setMeta({ time: e.target.value })}
                placeholder="14:30"
                value={draft.time}
              />
            </Field>
            <Field label="코스">
              <input
                className={inputClass}
                onChange={(e) => store.setMeta({ course: e.target.value })}
                placeholder="베르힐 영종"
                value={draft.course}
              />
            </Field>
            <Field label="동반자">
              <input
                className={inputClass}
                onChange={(e) => store.setMeta({ companions: e.target.value })}
                placeholder="홍성걸 양명욱"
                value={draft.companions}
              />
            </Field>
          </div>
        )}
      </section>

      <section className="mb-5 rounded-md border border-line bg-white">
        <button
          className="flex w-full items-center justify-between p-4 text-left"
          onClick={() => setShowBag((v) => !v)}
        >
          <span className="text-sm font-semibold">내 클럽 세팅</span>
          <span className="text-sm text-muted">
            {bagStore.bag.enabled.length}개 사용 · {showBag ? "접기" : "펼치기"}
          </span>
        </button>
        {showBag && (
          <div className="border-t border-line p-4">
            <p className="mb-3 text-xs leading-5 text-muted">
              사용하는 클럽을 탭으로 가방에 넣고/뺍니다. 거리는 평균값을 미터로 입력하면, V2에서
              클럽 선택 시 자동으로 채워지고 거리 입력 단계가 건너뛰어집니다.
            </p>
            {CLUB_GROUPS.map((group) => (
              <div className="mb-3" key={group.label}>
                <p className="mb-1 text-xs font-semibold text-muted">{group.label}</p>
                <div className="grid grid-cols-2 gap-2">
                  {group.clubs.map((club) => (
                    <ClubBagRow
                      club={club}
                      distance={bagStore.bag.distances[club]}
                      enabled={bagStore.bag.enabled.includes(club)}
                      key={club}
                      onSetDistance={(d) => bagStore.setDistance(club, d)}
                      onToggle={() => bagStore.toggle(club)}
                    />
                  ))}
                </div>
              </div>
            ))}
            <button
              className="mt-2 text-xs text-muted underline"
              onClick={() => {
                if (window.confirm("기본 클럽 세트로 되돌립니다.")) bagStore.resetToDefault();
              }}
            >
              기본값 복원
            </button>
          </div>
        )}
      </section>

      <section className="mb-5 space-y-3">
        {VARIANTS.map((v) => (
          <Link
            className="block rounded-md border border-line bg-white p-4 hover:border-green-700"
            href={v.href}
            key={v.id}
          >
            <div className="flex items-center justify-between">
              <p className="font-semibold">{v.title}</p>
              <span className="text-sm text-green-700">열기 →</span>
            </div>
            <p className="mt-1 text-sm leading-6 text-muted">{v.summary}</p>
          </Link>
        ))}
      </section>

      <section className="mb-5 rounded-md border border-line bg-white">
        <button
          className="flex w-full items-center justify-between p-4 text-left"
          onClick={() => setShowText((v) => !v)}
        >
          <span className="text-sm font-semibold">텍스트 미리보기</span>
          <span className="text-sm text-muted">{showText ? "접기" : "펼치기"}</span>
        </button>
        {showText && (
          <pre className="overflow-x-auto whitespace-pre-wrap break-words border-t border-line p-4 text-xs leading-5">
            {text || <span className="text-muted">아직 샷이 없습니다.</span>}
          </pre>
        )}
      </section>

      <section className="flex justify-end">
        <button
          className="rounded-md border border-line px-3 py-2 text-sm text-[#a34242]"
          onClick={() => {
            if (window.confirm("드래프트를 모두 지웁니다. 진행할까요?")) {
              store.reset();
            }
          }}
        >
          드래프트 초기화
        </button>
      </section>
    </main>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid grid-cols-[5rem_1fr] items-center gap-2 text-sm">
      <span className="text-muted">{label}</span>
      {children}
    </label>
  );
}

function ClubBagRow({
  club,
  enabled,
  distance,
  onToggle,
  onSetDistance
}: {
  club: Club;
  enabled: boolean;
  distance: number | undefined;
  onToggle: () => void;
  onSetDistance: (d: number | undefined) => void;
}) {
  return (
    <div
      className={`flex items-center gap-2 rounded-md border px-2 py-1 ${
        enabled ? "border-green-700 bg-white" : "border-line bg-surface"
      }`}
    >
      <button
        className={`h-9 min-w-[3rem] rounded text-sm font-bold ${
          enabled ? "bg-green-700 text-white" : "bg-line text-muted"
        }`}
        onClick={onToggle}
      >
        {club}
      </button>
      <input
        className="h-9 w-full rounded border border-line bg-white px-2 text-sm disabled:bg-surface disabled:text-muted"
        disabled={!enabled}
        inputMode="numeric"
        onChange={(e) => {
          const v = e.target.value.replace(/[^0-9]/g, "");
          onSetDistance(v ? Number(v) : undefined);
        }}
        placeholder="m"
        value={distance ?? ""}
      />
    </div>
  );
}

const inputClass = "h-10 w-full rounded-md border border-line bg-white px-3 text-sm";
