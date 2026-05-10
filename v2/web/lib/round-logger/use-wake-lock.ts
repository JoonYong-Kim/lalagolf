"use client";

import { useEffect } from "react";

type WakeLockSentinelLike = { release: () => Promise<void> };

type NavigatorWithWakeLock = Navigator & {
  wakeLock?: { request: (type: "screen") => Promise<WakeLockSentinelLike> };
};

export function useWakeLock(active: boolean = true): void {
  useEffect(() => {
    if (!active) return;
    if (typeof navigator === "undefined") return;
    const nav = navigator as NavigatorWithWakeLock;
    if (!nav.wakeLock) return;

    let cancelled = false;
    let lock: WakeLockSentinelLike | null = null;

    const request = async () => {
      try {
        if (cancelled || !nav.wakeLock) return;
        lock = await nav.wakeLock.request("screen");
      } catch {
        // user gesture not granted, page hidden, or unsupported — ignore
      }
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === "visible" && !lock) {
        void request();
      }
    };

    void request();
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      cancelled = true;
      document.removeEventListener("visibilitychange", onVisibilityChange);
      const current = lock;
      lock = null;
      if (current) void current.release().catch(() => undefined);
    };
  }, [active]);
}
