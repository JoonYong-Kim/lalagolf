"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  ApiError,
  createDraft,
  discardDraft,
  finalizeDraft,
  getCurrentDraft,
  patchDraftHole,
  patchDraftMeta
} from "@/lib/api";
import type { FinalizeDraftResponse, RoundDetail } from "@/lib/api";

import { fromServer, metaFromRound, shotToPayload } from "./converters";
import {
  bumpAttempt,
  clearKinds,
  enqueue,
  remove,
  snapshotByKinds
} from "./sync-queue";
import type { DraftHoleEntry, DraftMetaEntry } from "./sync-queue";
import type { Club, Grade, LoggerHole, LoggerRound, LoggerShot, ShotCode } from "./types";

const SYNC_DEBOUNCE_MS = 800;
const RETRY_INTERVAL_MS = 30_000;
const QUEUE_KINDS = ["draft_meta", "draft_hole"] as const;

export type SyncStatus = "idle" | "syncing" | "error";

export type ShotInput = {
  club: Club;
  feel: Grade;
  result: Grade;
  distance?: number;
  code?: ShotCode;
};

export type RemoteDraftStore = {
  round: LoggerRound | null;
  exists: boolean;
  hydrated: boolean;
  syncStatus: SyncStatus;
  error: string | null;
  queueSize: number;
  lastSyncAt: number | null;
  authExpired: boolean;
  start: () => Promise<void>;
  setMeta: (patch: Partial<Pick<LoggerRound, "date" | "course" | "companions">>) => void;
  setPar: (holeNumber: number, par: number) => void;
  goToHole: (holeNumber: number) => void;
  addShot: (holeNumber: number, input: ShotInput) => void;
  updateShot: (holeNumber: number, shotId: string, patch: Partial<ShotInput>) => void;
  removeShot: (holeNumber: number, shotId: string) => void;
  removeLastShot: (holeNumber: number) => void;
  discard: () => Promise<void>;
  finalize: () => Promise<FinalizeDraftResponse | null>;
  flushNow: () => Promise<void>;
  clearAuthExpired: () => void;
};

function newClientId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `tmp-${crypto.randomUUID()}`;
  }
  return `tmp-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function isTransient(e: unknown): boolean {
  if (e instanceof TypeError) return true;
  if (e instanceof ApiError && e.status >= 500) return true;
  return false;
}

export function useRemoteDraft(): RemoteDraftStore {
  const [round, setRound] = useState<LoggerRound | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [syncStatus, setSyncStatus] = useState<SyncStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [queueSize, setQueueSize] = useState(0);
  const [lastSyncAt, setLastSyncAt] = useState<number | null>(null);
  const [authExpired, setAuthExpired] = useState(false);

  const roundRef = useRef<LoggerRound | null>(null);
  const holeTimersRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());
  const metaTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inflightRef = useRef(0);

  const refreshQueueSize = useCallback(() => {
    setQueueSize(snapshotByKinds([...QUEUE_KINDS]).length);
  }, []);

  const applyServerRound = useCallback((detail: RoundDetail) => {
    const next = fromServer(detail);
    if (roundRef.current) {
      next.cursorHole = roundRef.current.cursorHole;
    }
    roundRef.current = next;
    setRound(next);
  }, []);

  const beginSync = useCallback(() => {
    inflightRef.current += 1;
    setSyncStatus("syncing");
  }, []);

  const endSync = useCallback((err?: unknown) => {
    inflightRef.current = Math.max(0, inflightRef.current - 1);
    if (err) {
      setSyncStatus("error");
      setError(err instanceof Error ? err.message : "Sync failed");
      return;
    }
    setLastSyncAt(Date.now());
    if (inflightRef.current === 0) {
      setSyncStatus("idle");
      setError(null);
    }
  }, []);

  const flushHole = useCallback(
    async (holeNumber: number) => {
      const snapshot = roundRef.current;
      if (!snapshot) return;
      const hole = snapshot.holes.find((h) => h.number === holeNumber);
      if (!hole) return;
      beginSync();
      try {
        const detail = await patchDraftHole(snapshot.id, holeNumber, {
          par: hole.par,
          shots: hole.shots.map(shotToPayload)
        });
        applyServerRound(detail);
        // Drop any queued entry for this hole since this succeeded
        for (const entry of snapshotByKinds(["draft_hole"])) {
          if (
            entry.kind === "draft_hole"
            && entry.roundId === snapshot.id
            && entry.holeNumber === holeNumber
          ) {
            remove(entry.id);
          }
        }
        refreshQueueSize();
        endSync();
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          setAuthExpired(true);
        }
        if (isTransient(e) || (e instanceof ApiError && e.status === 401)) {
          enqueue({
            kind: "draft_hole",
            roundId: snapshot.id,
            holeNumber,
            payload: { par: hole.par, shots: hole.shots.map(shotToPayload) }
          });
          refreshQueueSize();
        }
        endSync(e);
      }
    },
    [applyServerRound, beginSync, endSync, refreshQueueSize]
  );

  const flushMeta = useCallback(async () => {
    const snapshot = roundRef.current;
    if (!snapshot) return;
    beginSync();
    try {
      const detail = await patchDraftMeta(snapshot.id, metaFromRound(snapshot));
      applyServerRound(detail);
      for (const entry of snapshotByKinds(["draft_meta"])) {
        if (entry.kind === "draft_meta" && entry.roundId === snapshot.id) {
          remove(entry.id);
        }
      }
      refreshQueueSize();
      endSync();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setAuthExpired(true);
      }
      if (isTransient(e) || (e instanceof ApiError && e.status === 401)) {
        enqueue({
          kind: "draft_meta",
          roundId: snapshot.id,
          payload: metaFromRound(snapshot)
        });
        refreshQueueSize();
      }
      endSync(e);
    }
  }, [applyServerRound, beginSync, endSync, refreshQueueSize]);

  const scheduleHoleSync = useCallback(
    (holeNumber: number) => {
      const existing = holeTimersRef.current.get(holeNumber);
      if (existing) clearTimeout(existing);
      const timer = setTimeout(() => {
        holeTimersRef.current.delete(holeNumber);
        void flushHole(holeNumber);
      }, SYNC_DEBOUNCE_MS);
      holeTimersRef.current.set(holeNumber, timer);
    },
    [flushHole]
  );

  const scheduleMetaSync = useCallback(() => {
    if (metaTimerRef.current) clearTimeout(metaTimerRef.current);
    metaTimerRef.current = setTimeout(() => {
      metaTimerRef.current = null;
      void flushMeta();
    }, SYNC_DEBOUNCE_MS);
  }, [flushMeta]);

  const flushQueue = useCallback(async () => {
    const entries = snapshotByKinds([...QUEUE_KINDS]);
    for (const entry of entries) {
      try {
        if (entry.kind === "draft_meta") {
          const e = entry as DraftMetaEntry;
          const detail = await patchDraftMeta(e.roundId, e.payload);
          if (roundRef.current?.id === e.roundId) {
            applyServerRound(detail);
          }
        } else if (entry.kind === "draft_hole") {
          const e = entry as DraftHoleEntry;
          const detail = await patchDraftHole(e.roundId, e.holeNumber, e.payload);
          if (roundRef.current?.id === e.roundId) {
            applyServerRound(detail);
          }
        }
        remove(entry.id);
        setLastSyncAt(Date.now());
      } catch (e) {
        bumpAttempt(entry.id);
        if (e instanceof ApiError && e.status === 401) {
          setAuthExpired(true);
          break;
        }
        if (e instanceof ApiError && e.status === 404) {
          // Round/hole no longer exists. Drop entry.
          remove(entry.id);
          continue;
        }
        if (!isTransient(e)) {
          remove(entry.id);
          setError(e instanceof Error ? e.message : "Sync failed");
        }
        break;
      }
    }
    refreshQueueSize();
    if (snapshotByKinds([...QUEUE_KINDS]).length === 0 && inflightRef.current === 0) {
      setSyncStatus("idle");
      setError(null);
    }
  }, [applyServerRound, refreshQueueSize]);

  useEffect(() => {
    let alive = true;
    getCurrentDraft()
      .then((detail) => {
        if (!alive) return;
        if (detail) {
          applyServerRound(detail);
          setLastSyncAt(Date.now());
        }
      })
      .catch((e) => {
        if (!alive) return;
        if (e instanceof ApiError && e.status === 401) {
          setAuthExpired(true);
        }
        setError(e instanceof Error ? e.message : "Failed to load draft");
      })
      .finally(() => {
        if (alive) {
          setHydrated(true);
          refreshQueueSize();
          void flushQueue();
        }
      });
    return () => {
      alive = false;
    };
  }, [applyServerRound, flushQueue, refreshQueueSize]);

  useEffect(() => {
    const handler = () => {
      void flushQueue();
    };
    window.addEventListener("online", handler);
    return () => window.removeEventListener("online", handler);
  }, [flushQueue]);

  useEffect(() => {
    if (queueSize === 0 || authExpired) return;
    const id = setInterval(() => {
      if (typeof navigator === "undefined" || navigator.onLine) {
        void flushQueue();
      }
    }, RETRY_INTERVAL_MS);
    return () => clearInterval(id);
  }, [queueSize, authExpired, flushQueue]);

  const updateLocal = useCallback((mutator: (prev: LoggerRound) => LoggerRound) => {
    setRound((prev) => {
      if (!prev) return prev;
      const next = mutator(prev);
      roundRef.current = next;
      return next;
    });
  }, []);

  const start = useCallback(async () => {
    if (roundRef.current) return;
    beginSync();
    try {
      const detail = await createDraft();
      applyServerRound(detail);
      endSync();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setAuthExpired(true);
      }
      endSync(e);
      throw e;
    }
  }, [applyServerRound, beginSync, endSync]);

  const setMeta = useCallback<RemoteDraftStore["setMeta"]>(
    (patch) => {
      updateLocal((prev) => ({ ...prev, ...patch }));
      scheduleMetaSync();
    },
    [scheduleMetaSync, updateLocal]
  );

  const setPar = useCallback<RemoteDraftStore["setPar"]>(
    (holeNumber, par) => {
      updateLocal((prev) => ({
        ...prev,
        holes: prev.holes.map((h) => (h.number === holeNumber ? { ...h, par } : h))
      }));
      scheduleHoleSync(holeNumber);
    },
    [scheduleHoleSync, updateLocal]
  );

  const goToHole = useCallback<RemoteDraftStore["goToHole"]>((holeNumber) => {
    updateLocal((prev) => ({ ...prev, cursorHole: holeNumber }));
  }, [updateLocal]);

  const addShot = useCallback<RemoteDraftStore["addShot"]>(
    (holeNumber, input) => {
      updateLocal((prev) => ({
        ...prev,
        holes: prev.holes.map((h) =>
          h.number === holeNumber
            ? { ...h, shots: [...h.shots, { id: newClientId(), ...input } satisfies LoggerShot] }
            : h
        )
      }));
      scheduleHoleSync(holeNumber);
    },
    [scheduleHoleSync, updateLocal]
  );

  const updateShot = useCallback<RemoteDraftStore["updateShot"]>(
    (holeNumber, shotId, patch) => {
      updateLocal((prev) => ({
        ...prev,
        holes: prev.holes.map((h) =>
          h.number === holeNumber
            ? {
                ...h,
                shots: h.shots.map((s) => (s.id === shotId ? { ...s, ...patch } : s))
              }
            : h
        )
      }));
      scheduleHoleSync(holeNumber);
    },
    [scheduleHoleSync, updateLocal]
  );

  const removeShot = useCallback<RemoteDraftStore["removeShot"]>(
    (holeNumber, shotId) => {
      updateLocal((prev) => ({
        ...prev,
        holes: prev.holes.map((h) =>
          h.number === holeNumber ? { ...h, shots: h.shots.filter((s) => s.id !== shotId) } : h
        )
      }));
      scheduleHoleSync(holeNumber);
    },
    [scheduleHoleSync, updateLocal]
  );

  const removeLastShot = useCallback<RemoteDraftStore["removeLastShot"]>(
    (holeNumber) => {
      updateLocal((prev) => ({
        ...prev,
        holes: prev.holes.map((h) =>
          h.number === holeNumber ? { ...h, shots: h.shots.slice(0, -1) } : h
        )
      }));
      scheduleHoleSync(holeNumber);
    },
    [scheduleHoleSync, updateLocal]
  );

  const cancelTimers = useCallback(() => {
    holeTimersRef.current.forEach((t) => clearTimeout(t));
    holeTimersRef.current.clear();
    if (metaTimerRef.current) {
      clearTimeout(metaTimerRef.current);
      metaTimerRef.current = null;
    }
  }, []);

  const discard = useCallback(async () => {
    cancelTimers();
    clearKinds([...QUEUE_KINDS]);
    refreshQueueSize();
    beginSync();
    try {
      await discardDraft();
      roundRef.current = null;
      setRound(null);
      endSync();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setAuthExpired(true);
      }
      endSync(e);
      throw e;
    }
  }, [beginSync, cancelTimers, endSync, refreshQueueSize]);

  const finalize = useCallback(async (): Promise<FinalizeDraftResponse | null> => {
    const snapshot = roundRef.current;
    if (!snapshot) return null;

    cancelTimers();

    beginSync();
    try {
      // Push any pending queue first to ensure all shots saved
      await flushQueue();
      await patchDraftMeta(snapshot.id, metaFromRound(snapshot));
      const result = await finalizeDraft(snapshot.id);
      clearKinds([...QUEUE_KINDS]);
      refreshQueueSize();
      roundRef.current = null;
      setRound(null);
      endSync();
      return result;
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setAuthExpired(true);
      }
      endSync(e);
      throw e;
    }
  }, [beginSync, cancelTimers, endSync, flushQueue, refreshQueueSize]);

  const flushNow = useCallback(async () => {
    await flushQueue();
  }, [flushQueue]);

  const clearAuthExpired = useCallback(() => {
    setAuthExpired(false);
    void flushQueue();
  }, [flushQueue]);

  return {
    round,
    exists: round !== null,
    hydrated,
    syncStatus,
    error,
    queueSize,
    lastSyncAt,
    authExpired,
    start,
    setMeta,
    setPar,
    goToHole,
    addShot,
    updateShot,
    removeShot,
    removeLastShot,
    discard,
    finalize,
    flushNow,
    clearAuthExpired
  };
}
