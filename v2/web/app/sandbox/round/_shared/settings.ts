"use client";

import { useCallback, useEffect, useState } from "react";

import type { Club } from "./types";

const STORAGE_KEY = "lalagolf.sandbox.round.clubBag.v1";

export type ClubBag = {
  enabled: Club[];
  distances: Partial<Record<Club, number>>;
};

const DEFAULT_BAG: ClubBag = {
  enabled: ["D", "W3", "U4", "I5", "I6", "I7", "I8", "I9", "52", "56", "58", "P"],
  distances: {
    D: 230,
    W3: 200,
    U4: 170,
    I5: 150,
    I6: 140,
    I7: 130,
    I8: 115,
    I9: 100,
    "52": 90,
    "56": 75,
    "58": 60
  }
};

export function makeDefaultBag(): ClubBag {
  return {
    enabled: [...DEFAULT_BAG.enabled],
    distances: { ...DEFAULT_BAG.distances }
  };
}

export type ClubBagStore = {
  bag: ClubBag;
  hydrated: boolean;
  toggle: (club: Club) => void;
  setDistance: (club: Club, distance: number | undefined) => void;
  resetToDefault: () => void;
};

export function useClubBag(): ClubBagStore {
  const [bag, setBag] = useState<ClubBag>(() => makeDefaultBag());
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as ClubBag;
        if (parsed && Array.isArray(parsed.enabled) && parsed.distances) {
          setBag(parsed);
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
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(bag));
    } catch {
      // ignore quota errors during prototype
    }
  }, [bag, hydrated]);

  const toggle = useCallback<ClubBagStore["toggle"]>((club) => {
    setBag((prev) => {
      const isOn = prev.enabled.includes(club);
      return {
        ...prev,
        enabled: isOn ? prev.enabled.filter((c) => c !== club) : [...prev.enabled, club]
      };
    });
  }, []);

  const setDistance = useCallback<ClubBagStore["setDistance"]>((club, distance) => {
    setBag((prev) => {
      const next = { ...prev.distances };
      if (distance === undefined || !Number.isFinite(distance)) {
        delete next[club];
      } else {
        next[club] = distance;
      }
      return { ...prev, distances: next };
    });
  }, []);

  const resetToDefault = useCallback(() => {
    setBag(makeDefaultBag());
  }, []);

  return { bag, hydrated, toggle, setDistance, resetToDefault };
}
