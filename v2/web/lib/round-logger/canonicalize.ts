import type { LoggerRound, LoggerShot } from "./types";

function shotLine(shot: LoggerShot): string {
  const parts: string[] = [shot.club, shot.feel, shot.result];
  if (shot.distance !== undefined) parts.push(String(shot.distance));
  if (shot.code) parts.push(shot.code);
  return parts.join(" ");
}

export function canonicalize(round: LoggerRound, time: string = ""): string {
  const lines: string[] = [];
  lines.push(time ? `${round.date} ${time}` : round.date);
  lines.push(round.course);
  lines.push(round.companions);

  for (const hole of round.holes) {
    if (hole.shots.length === 0) continue;
    lines.push("");
    lines.push(`${hole.number} P${hole.par}`);
    for (const shot of hole.shots) {
      lines.push(shotLine(shot));
    }
  }

  return lines.join("\n");
}

export function totalShots(round: LoggerRound): number {
  return round.holes.reduce((sum, h) => sum + h.shots.length, 0);
}

export function holesPlayed(round: LoggerRound): number {
  return round.holes.filter((h) => h.shots.length > 0).length;
}

export function emptyHoleNumbers(round: LoggerRound): number[] {
  return round.holes.filter((h) => h.shots.length === 0).map((h) => h.number);
}
