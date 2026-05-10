"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, getClubBag, putClubBag } from "@/lib/api";
import type { ClubBagPayload } from "@/lib/api";

import { DEFAULT_BAG_DISTANCES, DEFAULT_BAG_ENABLED } from "./clubs";
import {
  bumpAttempt,
  enqueue,
  remove,
  size,
  snapshotByKinds
} from "./sync-queue";
import type { ClubBagEntry } from "./sync-queue";
import type { Club, ClubBag } from "./types";

export type SyncStatus = "idle" | "syncing" | "error";

export type ClubBagStore = {
  bag: ClubBag;
  hydrated: boolean;
  syncStatus: SyncStatus;
  error: string | null;
  queueSize: number;
  lastSyncAt: number | null;
  authExpired: boolean;
  toggle: (club: Club) => void;
  setDistance: (club: Club, distance: number | undefined) => void;
  resetToDefault: () => void;
  flushNow: () => Promise<void>;
  clearAuthExpired: () => void;
};

const QUEUE_KINDS = ["club_bag"] as const;
const RETRY_INTERVAL_MS = 30_000;
const SYNC_DEBOUNCE_MS = 800;

function emptyBag(): ClubBag {
  return { enabled: [], distances: {} };
}

function defaultBag(): ClubBag {
  return {
    enabled: [...DEFAULT_BAG_ENABLED],
    distances: { ...DEFAULT_BAG_DISTANCES }
  };
}

function fromPayload(payload: ClubBagPayload): ClubBag {
  return {
    enabled: payload.enabled as Club[],
    distances: payload.distances as Partial<Record<Club, number>>
  };
}

function toPayload(bag: ClubBag): ClubBagPayload {
  const distances: Record<string, number> = {};
  for (const [club, dist] of Object.entries(bag.distances)) {
    if (dist !== undefined) distances[club] = dist;
  }
  return { enabled: [...bag.enabled], distances };
}

function isTransient(e: unknown): boolean {
  if (e instanceof TypeError) return true;
  if (e instanceof ApiError && e.status >= 500) return true;
  return false;
}

export function useRemoteClubBag(): ClubBagStore {
  const [bag, setBag] = useState<ClubBag>(emptyBag);
  const [hydrated, setHydrated] = useState(false);
  const [syncStatus, setSyncStatus] = useState<SyncStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [queueSize, setQueueSize] = useState(0);
  const [lastSyncAt, setLastSyncAt] = useState<number | null>(null);
  const [authExpired, setAuthExpired] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestRef = useRef<ClubBag>(emptyBag());

  const refreshQueueSize = useCallback(() => {
    setQueueSize(snapshotByKinds([...QUEUE_KINDS]).length);
  }, []);

  const flushQueue = useCallback(async () => {
    const entries = snapshotByKinds([...QUEUE_KINDS]) as ClubBagEntry[];
    for (const entry of entries) {
      try {
        await putClubBag(entry.payload);
        remove(entry.id);
        setLastSyncAt(Date.now());
      } catch (e) {
        bumpAttempt(entry.id);
        if (e instanceof ApiError && e.status === 401) {
          setAuthExpired(true);
          break;
        }
        if (!isTransient(e)) {
          remove(entry.id);
          setError(e instanceof Error ? e.message : "Sync failed");
        }
        break;
      }
    }
    refreshQueueSize();
  }, [refreshQueueSize]);

  useEffect(() => {
    let alive = true;
    getClubBag()
      .then((data) => {
        if (!alive) return;
        const next = fromPayload(data);
        setBag(next);
        latestRef.current = next;
        setLastSyncAt(Date.now());
      })
      .catch((e) => {
        if (!alive) return;
        if (e instanceof ApiError && e.status === 401) {
          setAuthExpired(true);
        }
        setError(e instanceof Error ? e.message : "Failed to load club bag");
      })
      .finally(() => {
        if (alive) {
          setHydrated(true);
          refreshQueueSize();
        }
      });
    return () => {
      alive = false;
    };
  }, [refreshQueueSize]);

  // Drain queue on online + on mount
  useEffect(() => {
    const handler = () => {
      void flushQueue();
    };
    window.addEventListener("online", handler);
    void flushQueue();
    return () => window.removeEventListener("online", handler);
  }, [flushQueue]);

  // Periodic retry while queue non-empty
  useEffect(() => {
    if (queueSize === 0 || authExpired) return;
    const id = setInterval(() => {
      if (typeof navigator === "undefined" || navigator.onLine) {
        void flushQueue();
      }
    }, RETRY_INTERVAL_MS);
    return () => clearInterval(id);
  }, [queueSize, authExpired, flushQueue]);

  const scheduleSync = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setSyncStatus("syncing");
    debounceRef.current = setTimeout(async () => {
      try {
        const updated = await putClubBag(toPayload(latestRef.current));
        latestRef.current = fromPayload(updated);
        // Drop any queued bag entry since this succeeded
        for (const entry of snapshotByKinds([...QUEUE_KINDS])) {
          remove(entry.id);
        }
        refreshQueueSize();
        setLastSyncAt(Date.now());
        setSyncStatus("idle");
        setError(null);
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          setAuthExpired(true);
        }
        if (isTransient(e) || (e instanceof ApiError && e.status === 401)) {
          enqueue({ kind: "club_bag", payload: toPayload(latestRef.current) });
          refreshQueueSize();
        }
        setSyncStatus("error");
        setError(e instanceof Error ? e.message : "Failed to save");
      }
    }, SYNC_DEBOUNCE_MS);
  }, [refreshQueueSize]);

  const updateBag = useCallback(
    (mutator: (prev: ClubBag) => ClubBag) => {
      setBag((prev) => {
        const next = mutator(prev);
        latestRef.current = next;
        return next;
      });
      scheduleSync();
    },
    [scheduleSync]
  );

  const toggle = useCallback<ClubBagStore["toggle"]>(
    (club) => {
      updateBag((prev) => {
        const isOn = prev.enabled.includes(club);
        return {
          ...prev,
          enabled: isOn ? prev.enabled.filter((c) => c !== club) : [...prev.enabled, club]
        };
      });
    },
    [updateBag]
  );

  const setDistance = useCallback<ClubBagStore["setDistance"]>(
    (club, distance) => {
      updateBag((prev) => {
        const distances = { ...prev.distances };
        if (distance === undefined || !Number.isFinite(distance)) {
          delete distances[club];
        } else {
          distances[club] = distance;
        }
        return { ...prev, distances };
      });
    },
    [updateBag]
  );

  const resetToDefault = useCallback(() => {
    updateBag(() => defaultBag());
  }, [updateBag]);

  const flushNow = useCallback(async () => {
    await flushQueue();
  }, [flushQueue]);

  const clearAuthExpired = useCallback(() => {
    setAuthExpired(false);
    void flushQueue();
  }, [flushQueue]);

  return {
    bag,
    hydrated,
    syncStatus,
    error,
    queueSize,
    lastSyncAt,
    authExpired,
    toggle,
    setDistance,
    resetToDefault,
    flushNow,
    clearAuthExpired
  };
}
