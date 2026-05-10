"use client";

import { useEffect, useState } from "react";

export type SyncStatus = "idle" | "syncing" | "error";

export type SyncIndicatorProps = {
  syncStatus: SyncStatus;
  queueSize: number;
  lastSyncAt: number | null;
  authExpired: boolean;
  onRetry: () => void | Promise<void>;
};

function relativeTime(ts: number | null, now: number): string {
  if (ts === null) return "—";
  const seconds = Math.max(0, Math.floor((now - ts) / 1000));
  if (seconds < 5) return "방금";
  if (seconds < 60) return `${seconds}초 전`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  const date = new Date(ts);
  return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

export function SyncIndicator({
  syncStatus,
  queueSize,
  lastSyncAt,
  authExpired,
  onRetry
}: SyncIndicatorProps) {
  const [open, setOpen] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!open) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [open]);

  let icon: string;
  let badgeText: string | null = null;
  let color: string;
  if (authExpired) {
    icon = "🔒";
    color = "text-[#a34242]";
  } else if (queueSize > 0) {
    icon = "⚠";
    color = "text-[#a36a00]";
    badgeText = String(queueSize);
  } else if (syncStatus === "syncing") {
    icon = "⟳";
    color = "text-muted";
  } else if (syncStatus === "error") {
    icon = "⚠";
    color = "text-[#a34242]";
  } else {
    icon = "✓";
    color = "text-green-700";
  }

  return (
    <div className="relative">
      <button
        aria-label="동기화 상태"
        className={`flex h-9 w-12 items-center justify-center rounded-md border border-line bg-white text-sm ${color}`}
        onClick={() => setOpen((o) => !o)}
      >
        <span>{icon}</span>
        {badgeText && <span className="ml-1 text-xs font-semibold">{badgeText}</span>}
      </button>
      {open && (
        <div className="absolute right-0 top-full z-30 mt-1 w-60 rounded-md border border-line bg-white p-3 text-sm shadow-lg">
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-muted">상태</span>
              <span className="font-semibold">{statusLabel(syncStatus, queueSize, authExpired)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">마지막 동기화</span>
              <span>{relativeTime(lastSyncAt, now)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">대기 항목</span>
              <span>{queueSize}건</span>
            </div>
          </div>
          {(queueSize > 0 || syncStatus === "error") && !authExpired && (
            <button
              className="mt-3 h-9 w-full rounded-md border border-green-700 text-xs font-semibold text-green-700"
              onClick={() => {
                setOpen(false);
                void onRetry();
              }}
            >
              지금 동기화
            </button>
          )}
          {authExpired && (
            <p className="mt-3 text-xs text-[#a34242]">로그인이 만료됐습니다. 재로그인 후 자동 동기화됩니다.</p>
          )}
        </div>
      )}
    </div>
  );
}

function statusLabel(syncStatus: SyncStatus, queueSize: number, authExpired: boolean): string {
  if (authExpired) return "재로그인 필요";
  if (queueSize > 0) return "오프라인 대기";
  if (syncStatus === "syncing") return "동기화 중";
  if (syncStatus === "error") return "오류";
  return "동기화됨";
}
