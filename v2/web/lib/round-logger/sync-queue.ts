"use client";

import type { ClubBagPayload, DraftHolePayload, DraftMetaPayload } from "@/lib/api";

const STORAGE_KEY = "lalagolf.round-logger.sync-queue.v1";

export type DraftMetaEntry = {
  id: string;
  kind: "draft_meta";
  roundId: string;
  payload: DraftMetaPayload;
  createdAt: number;
  attempts: number;
};

export type DraftHoleEntry = {
  id: string;
  kind: "draft_hole";
  roundId: string;
  holeNumber: number;
  payload: DraftHolePayload;
  createdAt: number;
  attempts: number;
};

export type ClubBagEntry = {
  id: string;
  kind: "club_bag";
  payload: ClubBagPayload;
  createdAt: number;
  attempts: number;
};

export type QueueEntry = DraftMetaEntry | DraftHoleEntry | ClubBagEntry;

export type EnqueueInput =
  | { kind: "draft_meta"; roundId: string; payload: DraftMetaPayload }
  | { kind: "draft_hole"; roundId: string; holeNumber: number; payload: DraftHolePayload }
  | { kind: "club_bag"; payload: ClubBagPayload };

function dedupeKey(entry: QueueEntry | EnqueueInput): string {
  if (entry.kind === "draft_meta") return `meta:${entry.roundId}`;
  if (entry.kind === "draft_hole") return `hole:${entry.roundId}:${entry.holeNumber}`;
  return "club_bag";
}

function newId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `q-${crypto.randomUUID()}`;
  }
  return `q-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function readQueue(): QueueEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as QueueEntry[]) : [];
  } catch {
    return [];
  }
}

function writeQueue(entries: QueueEntry[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // ignore quota errors
  }
}

export function enqueue(input: EnqueueInput): QueueEntry {
  const key = dedupeKey(input);
  const queue = readQueue();
  const filtered = queue.filter((e) => dedupeKey(e) !== key);
  const base = { id: newId(), createdAt: Date.now(), attempts: 0 };
  const entry: QueueEntry =
    input.kind === "draft_meta"
      ? { ...base, kind: "draft_meta", roundId: input.roundId, payload: input.payload }
      : input.kind === "draft_hole"
        ? {
            ...base,
            kind: "draft_hole",
            roundId: input.roundId,
            holeNumber: input.holeNumber,
            payload: input.payload
          }
        : { ...base, kind: "club_bag", payload: input.payload };
  filtered.push(entry);
  writeQueue(filtered);
  return entry;
}

export function snapshot(): QueueEntry[] {
  return readQueue();
}

export function snapshotByKinds(kinds: QueueEntry["kind"][]): QueueEntry[] {
  return readQueue().filter((e) => kinds.includes(e.kind));
}

export function remove(id: string): void {
  writeQueue(readQueue().filter((e) => e.id !== id));
}

export function bumpAttempt(id: string): void {
  const queue = readQueue();
  const next = queue.map((e) => (e.id === id ? { ...e, attempts: e.attempts + 1 } : e));
  writeQueue(next);
}

export function clear(): void {
  writeQueue([]);
}

export function clearKinds(kinds: QueueEntry["kind"][]): void {
  writeQueue(readQueue().filter((e) => !kinds.includes(e.kind)));
}

export function size(): number {
  return readQueue().length;
}

export function sizeByKinds(kinds: QueueEntry["kind"][]): number {
  return readQueue().filter((e) => kinds.includes(e.kind)).length;
}
