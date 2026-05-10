"use client";

import { useCallback, useEffect, useState } from "react";

import { newId } from "./id";
import type { Club, Grade, Hole, RoundDraft, Shot, ShotCode } from "./types";

const STORAGE_KEY = "lalagolf.sandbox.round.draft.v1";

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

function todayDateString(): string {
  const d = new Date();
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())}`;
}

function nowTimeString(): string {
  const d = new Date();
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function makeEmptyDraft(): RoundDraft {
  const holes: Hole[] = Array.from({ length: 18 }, (_, i) => ({
    number: i + 1,
    par: 4,
    shots: []
  }));
  return {
    startedAt: new Date().toISOString(),
    date: todayDateString(),
    time: nowTimeString(),
    course: "",
    companions: "",
    holes,
    cursorHole: 1
  };
}

export type ShotInput = {
  club: Club;
  feel: Grade;
  result: Grade;
  distance?: number;
  code?: ShotCode;
};

export type RoundDraftStore = {
  draft: RoundDraft;
  hydrated: boolean;
  setMeta: (patch: Partial<Pick<RoundDraft, "date" | "time" | "course" | "companions">>) => void;
  setPar: (holeNumber: number, par: number) => void;
  goToHole: (holeNumber: number) => void;
  addShot: (holeNumber: number, input: ShotInput) => void;
  updateShot: (holeNumber: number, shotId: string, patch: Partial<ShotInput>) => void;
  removeShot: (holeNumber: number, shotId: string) => void;
  removeLastShot: (holeNumber: number) => void;
  setLastShotCode: (holeNumber: number, code: ShotCode | undefined) => void;
  reset: () => void;
};

export function useRoundDraft(): RoundDraftStore {
  const [draft, setDraft] = useState<RoundDraft>(() => makeEmptyDraft());
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as RoundDraft;
        if (parsed && Array.isArray(parsed.holes) && parsed.holes.length === 18) {
          setDraft(parsed);
        }
      }
    } catch {
      // ignore corrupt storage
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
    } catch {
      // ignore quota errors during prototype
    }
  }, [draft, hydrated]);

  const setMeta = useCallback<RoundDraftStore["setMeta"]>((patch) => {
    setDraft((prev) => ({ ...prev, ...patch }));
  }, []);

  const setPar = useCallback<RoundDraftStore["setPar"]>((holeNumber, par) => {
    setDraft((prev) => ({
      ...prev,
      holes: prev.holes.map((h) => (h.number === holeNumber ? { ...h, par } : h))
    }));
  }, []);

  const goToHole = useCallback<RoundDraftStore["goToHole"]>((holeNumber) => {
    setDraft((prev) => ({ ...prev, cursorHole: holeNumber }));
  }, []);

  const addShot = useCallback<RoundDraftStore["addShot"]>((holeNumber, input) => {
    setDraft((prev) => ({
      ...prev,
      holes: prev.holes.map((h) =>
        h.number === holeNumber
          ? { ...h, shots: [...h.shots, { id: newId(), ...input } satisfies Shot] }
          : h
      )
    }));
  }, []);

  const updateShot = useCallback<RoundDraftStore["updateShot"]>((holeNumber, shotId, patch) => {
    setDraft((prev) => ({
      ...prev,
      holes: prev.holes.map((h) =>
        h.number === holeNumber
          ? { ...h, shots: h.shots.map((s) => (s.id === shotId ? { ...s, ...patch } : s)) }
          : h
      )
    }));
  }, []);

  const removeShot = useCallback<RoundDraftStore["removeShot"]>((holeNumber, shotId) => {
    setDraft((prev) => ({
      ...prev,
      holes: prev.holes.map((h) =>
        h.number === holeNumber ? { ...h, shots: h.shots.filter((s) => s.id !== shotId) } : h
      )
    }));
  }, []);

  const removeLastShot = useCallback<RoundDraftStore["removeLastShot"]>((holeNumber) => {
    setDraft((prev) => ({
      ...prev,
      holes: prev.holes.map((h) =>
        h.number === holeNumber ? { ...h, shots: h.shots.slice(0, -1) } : h
      )
    }));
  }, []);

  const setLastShotCode = useCallback<RoundDraftStore["setLastShotCode"]>((holeNumber, code) => {
    setDraft((prev) => ({
      ...prev,
      holes: prev.holes.map((h) => {
        if (h.number !== holeNumber || h.shots.length === 0) return h;
        const last = h.shots[h.shots.length - 1];
        return {
          ...h,
          shots: [...h.shots.slice(0, -1), { ...last, code }]
        };
      })
    }));
  }, []);

  const reset = useCallback(() => {
    setDraft(makeEmptyDraft());
  }, []);

  return {
    draft,
    hydrated,
    setMeta,
    setPar,
    goToHole,
    addShot,
    updateShot,
    removeShot,
    removeLastShot,
    setLastShotCode,
    reset
  };
}
