import type { RoundDetail, RoundHole, RoundShot } from "@/lib/api";

import type { Club, Grade, LoggerHole, LoggerRound, LoggerShot, ShotCode } from "./types";

const VALID_CODES: ShotCode[] = ["OK", "H", "UN", "OB", "B"];

function parseCodeFromRawText(rawText: string | null): ShotCode | undefined {
  if (!rawText) return undefined;
  const tokens = rawText.trim().split(/\s+/);
  const last = tokens[tokens.length - 1];
  if ((VALID_CODES as string[]).includes(last)) return last as ShotCode;
  return undefined;
}

function shotFromServer(s: RoundShot): LoggerShot {
  return {
    id: s.id,
    club: (s.club ?? "P") as Club,
    feel: (s.feel_grade ?? "C") as Grade,
    result: (s.result_grade ?? "C") as Grade,
    distance: s.distance ?? undefined,
    code: parseCodeFromRawText(s.raw_text)
  };
}

function holeFromServer(h: RoundHole): LoggerHole {
  return {
    number: h.hole_number,
    par: h.par,
    shots: [...h.shots]
      .sort((a, b) => a.shot_number - b.shot_number)
      .map(shotFromServer)
  };
}

function formatDate(playDate: string): string {
  const [y, m, d] = playDate.split("-");
  if (!y || !m || !d) return playDate;
  return `${y}.${m}.${d}`;
}

export function fromServer(round: RoundDetail): LoggerRound {
  const holesByNumber = new Map<number, LoggerHole>();
  for (const h of round.holes) holesByNumber.set(h.hole_number, holeFromServer(h));
  const holes: LoggerHole[] = [];
  for (let n = 1; n <= 18; n += 1) {
    const existing = holesByNumber.get(n);
    holes.push(existing ?? { number: n, par: 4, shots: [] });
  }

  return {
    id: round.id,
    date: formatDate(round.play_date),
    course: round.course_name,
    companions: round.companions.join(" "),
    holes,
    cursorHole: 1
  };
}

export type ShotPayload = {
  club: string;
  feel: Grade;
  result: Grade;
  distance: number | null;
  code: ShotCode | null;
};

export function shotToPayload(shot: LoggerShot): ShotPayload {
  return {
    club: shot.club,
    feel: shot.feel,
    result: shot.result,
    distance: shot.distance ?? null,
    code: shot.code ?? null
  };
}

export function metaFromRound(round: LoggerRound): {
  play_date: string;
  course_name: string;
  companions: string[];
} {
  const [y, m, d] = round.date.split(".");
  const playDate = y && m && d ? `${y}-${m}-${d}` : round.date;
  return {
    play_date: playDate,
    course_name: round.course,
    companions: round.companions.split(/\s+/).filter((s) => s.length > 0)
  };
}
