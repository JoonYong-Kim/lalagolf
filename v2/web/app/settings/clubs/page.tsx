"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthExpiredModal } from "@/app/components/round-logger/AuthExpiredModal";
import { SyncIndicator } from "@/app/components/round-logger/SyncIndicator";
import { getCurrentUser } from "@/lib/api";
import { CLUB_GROUPS } from "@/lib/round-logger/clubs";
import type { Club } from "@/lib/round-logger/types";
import { useRemoteClubBag } from "@/lib/round-logger/use-remote-club-bag";

export default function ClubBagSettingsPage() {
  const router = useRouter();
  const bagStore = useRemoteClubBag();
  const [authChecked, setAuthChecked] = useState(false);

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

  if (!authChecked || !bagStore.hydrated) {
    return <div className="p-8 text-sm text-muted">로드 중…</div>;
  }

  return (
    <main className="mx-auto max-w-md px-4 py-6">
      <header className="mb-5 flex items-center justify-between">
        <Link className="text-sm text-muted" href="/dashboard">
          ← 대시보드
        </Link>
        <SyncIndicator
          authExpired={bagStore.authExpired}
          lastSyncAt={bagStore.lastSyncAt}
          onRetry={() => bagStore.flushNow()}
          queueSize={bagStore.queueSize}
          syncStatus={bagStore.syncStatus}
        />
      </header>

      <h1 className="text-xl font-semibold">내 클럽 가방</h1>
      <p className="mt-1 text-sm leading-6 text-muted">
        사용하는 클럽을 탭으로 가방에 넣고 빼며, 평균 거리(미터)를 입력해두면 라운드 입력 시 자동으로
        채워집니다.
      </p>

      <section className="mt-5">
        {CLUB_GROUPS.map((group) => (
          <div className="mb-4" key={group.label}>
            <p className="mb-1 text-xs font-semibold text-muted">{group.label}</p>
            <div className="grid grid-cols-2 gap-2">
              {group.clubs.map((club) => (
                <ClubRow
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
      </section>

      <div className="mt-6 flex items-center justify-between">
        <button
          className="text-xs text-muted underline"
          onClick={() => {
            if (window.confirm("기본 12클럽 세트로 되돌립니다.")) bagStore.resetToDefault();
          }}
        >
          기본값 복원
        </button>
        <Link className="rounded-md bg-green-700 px-4 py-2 text-sm font-semibold text-white" href="/rounds/log">
          라운드 시작 →
        </Link>
      </div>

      {bagStore.error && (
        <p className="mt-4 text-sm text-[#a34242]">동기화 오류: {bagStore.error}</p>
      )}

      {bagStore.authExpired && (
        <AuthExpiredModal onSuccess={() => bagStore.clearAuthExpired()} />
      )}
    </main>
  );
}

function ClubRow({
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

