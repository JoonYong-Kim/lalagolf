import type { Club } from "./types";

export type ClubGroup = {
  label: string;
  clubs: Club[];
};

export const CLUB_GROUPS: ClubGroup[] = [
  { label: "드라이버", clubs: ["D"] },
  { label: "우드", clubs: ["W3", "W5", "UW"] },
  { label: "유틸리티", clubs: ["U3", "U4"] },
  { label: "아이언", clubs: ["I3", "I4", "I5", "I6", "I7", "I8", "I9"] },
  { label: "웨지(라벨)", clubs: ["IP", "IW", "IA"] },
  { label: "웨지(로프트)", clubs: ["48", "52", "56", "58"] },
  { label: "퍼터", clubs: ["P"] }
];

export const ALL_CLUBS: Club[] = CLUB_GROUPS.flatMap((g) => g.clubs);

export const DEFAULT_BAG_ENABLED: Club[] = [
  "D", "W3", "U4", "I5", "I6", "I7", "I8", "I9", "52", "56", "58", "P"
];

export const DEFAULT_BAG_DISTANCES: Partial<Record<Club, number>> = {
  D: 230, W3: 200, U4: 170,
  I5: 150, I6: 140, I7: 130, I8: 115, I9: 100,
  "52": 90, "56": 75, "58": 60
};
