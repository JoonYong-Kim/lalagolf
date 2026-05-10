export type Grade = "A" | "B" | "C";

export type Club =
  | "D"
  | "W3" | "W5" | "UW"
  | "U3" | "U4"
  | "I3" | "I4" | "I5" | "I6" | "I7" | "I8" | "I9"
  | "IP" | "IW" | "IA"
  | "48" | "52" | "56" | "58"
  | "P";

export type ShotCode = "OK" | "H" | "UN" | "OB" | "B";

export type LoggerShot = {
  id: string;
  club: Club;
  feel: Grade;
  result: Grade;
  distance?: number;
  code?: ShotCode;
};

export type LoggerHole = {
  number: number;
  par: number;
  shots: LoggerShot[];
};

export type LoggerRound = {
  id: string;
  date: string;
  course: string;
  companions: string;
  holes: LoggerHole[];
  cursorHole: number;
};

export type ClubBag = {
  enabled: Club[];
  distances: Partial<Record<Club, number>>;
};

export const GRADES: Grade[] = ["A", "B", "C"];
export const CODES: ShotCode[] = ["OK", "H", "UN", "OB", "B"];

export const CODE_LABEL: Record<ShotCode, string> = {
  OK: "OK 컨시드",
  H: "H 해저드",
  UN: "UN 언플레이어블",
  OB: "OB 아웃오브바운즈",
  B: "B 벙커"
};
