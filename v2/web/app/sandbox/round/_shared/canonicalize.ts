import type { RoundDraft, Shot } from "./types";

function shotLine(shot: Shot): string {
  const parts: string[] = [shot.club, shot.feel, shot.result];
  if (shot.distance !== undefined) parts.push(String(shot.distance));
  if (shot.code) parts.push(shot.code);
  return parts.join(" ");
}

export function canonicalize(draft: RoundDraft): string {
  const lines: string[] = [];
  lines.push(`${draft.date} ${draft.time}`.trim());
  lines.push(draft.course);
  lines.push(draft.companions);

  for (const hole of draft.holes) {
    if (hole.shots.length === 0) continue;
    lines.push("");
    lines.push(`${hole.number} P${hole.par}`);
    for (const shot of hole.shots) {
      lines.push(shotLine(shot));
    }
  }

  return lines.join("\n");
}

export function totalShots(draft: RoundDraft): number {
  return draft.holes.reduce((sum, h) => sum + h.shots.length, 0);
}

export function holesPlayed(draft: RoundDraft): number {
  return draft.holes.filter((h) => h.shots.length > 0).length;
}
