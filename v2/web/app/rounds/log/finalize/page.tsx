"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthExpiredModal } from "@/app/components/round-logger/AuthExpiredModal";
import { SyncIndicator } from "@/app/components/round-logger/SyncIndicator";
import { getCurrentUser } from "@/lib/api";
import {
  canonicalize,
  emptyHoleNumbers,
  holesPlayed,
  totalShots
} from "@/lib/round-logger/canonicalize";
import { useRemoteDraft } from "@/lib/round-logger/use-remote-draft";

export default function FinalizePage() {
  const router = useRouter();
  const draft = useRemoteDraft();
  const [authChecked, setAuthChecked] = useState(false);
  const [showText, setShowText] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  if (!authChecked || !draft.hydrated) {
    return <div className="p-8 text-sm text-muted">로드 중…</div>;
  }

  if (!draft.round) {
    return (
      <main className="mx-auto max-w-md px-4 py-6">
        <p className="text-sm text-muted">진행 중인 라운드가 없습니다.</p>
        <Link className="mt-4 inline-block rounded-md bg-green-700 px-4 py-2 text-sm font-semibold text-white" href="/rounds/log">
          새 라운드 시작
        </Link>
      </main>
    );
  }

  const round = draft.round;
  const empties = emptyHoleNumbers(round);
  const playedHoles = holesPlayed(round);
  const total = totalShots(round);
  const text = canonicalize(round);

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const result = await draft.finalize();
      if (result) {
        router.push(`/rounds/${result.round_id}`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "최종 업로드 실패");
      setSubmitting(false);
    }
  }

  async function discard() {
    if (!window.confirm("진행 중인 라운드를 폐기합니다. 되돌릴 수 없습니다.")) return;
    setSubmitting(true);
    try {
      await draft.discard();
      router.push("/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "폐기 실패");
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-md px-4 py-6">
      <header className="mb-5 flex items-center justify-between">
        <Link className="text-sm text-muted" href="/rounds/log">
          ← 입력으로
        </Link>
        <SyncIndicator
          authExpired={draft.authExpired}
          lastSyncAt={draft.lastSyncAt}
          onRetry={() => draft.flushNow()}
          queueSize={draft.queueSize}
          syncStatus={draft.syncStatus}
        />
      </header>

      <h1 className="text-xl font-semibold">{round.course || "코스 미입력"}</h1>
      <p className="mt-1 text-sm text-muted">
        {round.date}
        {round.companions && ` · ${round.companions}`}
      </p>

      <section className="mt-5 grid grid-cols-3 gap-2 text-center">
        <Stat label="진행 홀" value={`${playedHoles} / 18`} />
        <Stat label="총 샷" value={String(total)} />
        <Stat label="빈 홀" value={String(empties.length)} />
      </section>

      {empties.length > 0 && (
        <section className="mt-4 rounded-md border border-[#e0c080] bg-[#fff7e6] p-3 text-xs leading-5 text-[#8a5a00]">
          빈 홀 {empties.length}개: {empties.join(", ")}
          <br />
          그대로 업로드해도 되지만, 분석 정확도를 위해 채우는 것을 권장합니다.
        </section>
      )}

      {!round.course.trim() && (
        <section className="mt-4 rounded-md border border-[#e09090] bg-[#fdebeb] p-3 text-xs leading-5 text-[#a34242]">
          코스명이 비어있어 최종 업로드할 수 없습니다. 입력 화면에서 코스명을 채워주세요.
        </section>
      )}

      <section className="mt-4 rounded-md border border-line bg-white">
        <button
          className="flex w-full items-center justify-between p-3 text-sm"
          onClick={() => setShowText((v) => !v)}
        >
          <span className="font-semibold">텍스트 미리보기</span>
          <span className="text-muted">{showText ? "접기" : "펼치기"}</span>
        </button>
        {showText && (
          <pre className="overflow-x-auto whitespace-pre-wrap break-words border-t border-line p-3 text-xs leading-5">
            {text || <span className="text-muted">샷이 없습니다.</span>}
          </pre>
        )}
      </section>

      {error && <p className="mt-4 text-sm text-[#a34242]">{error}</p>}

      <button
        className="mt-6 h-14 w-full rounded-md bg-green-700 text-base font-semibold text-white disabled:bg-line disabled:text-muted"
        disabled={submitting || !round.course.trim()}
        onClick={submit}
      >
        {submitting ? "업로드 중…" : "✓ 최종 업로드"}
      </button>

      <button
        className="mt-3 h-12 w-full rounded-md border border-[#a34242] text-sm text-[#a34242] disabled:opacity-50"
        disabled={submitting}
        onClick={discard}
      >
        라운드 폐기
      </button>

      {draft.authExpired && (
        <AuthExpiredModal
          onSuccess={() => draft.clearAuthExpired()}
        />
      )}
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-white p-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}
