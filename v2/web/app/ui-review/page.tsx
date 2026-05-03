"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";

type ScreenKey = "dashboard" | "round" | "analysis";
type ViewKey = "desktop" | "mobile";
type AnalysisTab = "Score" | "Tee" | "Approach" | "Short Game" | "Putting";

const rounds = [
  {
    course: "파인힐스",
    date: "2026-04-14",
    shortDate: "04-14",
    score: 92,
    toPar: 20,
    holes: 18,
    shots: 74,
    penalties: 4,
    putts: 29,
    warnings: 1,
  },
  {
    course: "베르힐 영종",
    date: "2026-04-11",
    shortDate: "04-11",
    score: 90,
    toPar: 18,
    holes: 18,
    shots: 77,
    penalties: 2,
    putts: 28,
    warnings: 0,
  },
];

const holes = [
  { number: 1, par: 4, score: 4, putts: 2, penalties: 0, flag: "steady" },
  { number: 5, par: 5, score: 8, putts: 3, penalties: 0, flag: "high score" },
  { number: 11, par: 5, score: 7, putts: 2, penalties: 1, flag: "penalty" },
  { number: 12, par: 3, score: 5, putts: 4, penalties: 0, flag: "4 putts" },
  { number: 15, par: 5, score: 8, putts: 3, penalties: 1, flag: "penalty" },
  { number: 18, par: 4, score: 5, putts: 2, penalties: 1, flag: "penalty" },
];

const timelines: Record<number, string[]> = {
  1: ["1 D 220 T to R / C", "2 I8 125 R to G / B", "3 P 6 G to H / B / cost 2"],
  5: ["1 D 220 T to F / B", "2 UW 180 F to F / B", "3 I5 155 F to F / C", "4 48 95 F to R / C", "5 56 30 R to G / C", "6 P 8 G to G / C", "7 P 10 G to H / B / cost 2"],
  11: ["1 D 220 T to F / C / H / cost 2", "2 I7 110 F to F / B", "3 48 75 F to R / C", "4 52 16 R to R / C", "5 P 13 R to R / C", "6 P 2 R to H / B"],
  12: ["1 I9 115 T to F / B", "2 P 15 F to G / C", "3 P 15 G to G / B", "4 P 2 G to H / C / cost 2"],
  15: ["1 D 220 T to F / B", "2 UW 180 F to F / C / H / cost 2", "3 I5 155 F to F / B", "4 48 70 F to G / B", "5 P 6 G to G / C", "6 P 9 G to H / B / cost 2"],
  18: ["1 D 220 T to F / C / H / cost 2", "2 I9 115 F to G / B", "3 P 6 G to H / B / cost 2"],
};

const insights = [
  {
    problem: "티샷 페널티가 최근 점수 손실을 키웁니다.",
    evidence: "2라운드에서 페널티 샷 6개, 파인힐스 11/18번 모두 티샷 페널티.",
    impact: "라운드당 약 3타가 벌타로 고정됩니다.",
    action: "좁은 홀은 드라이버 유지보다 안전 구역과 미스 허용 방향을 먼저 선언합니다.",
    confidence: "low sample",
    metric: "tee_shot_penalty_rate",
  },
  {
    problem: "후반 파5에서 큰 수가 반복됩니다.",
    evidence: "파인힐스 11번 7타, 15번 8타. 둘 다 페널티 또는 리커버리 포함.",
    impact: "좋은 홀의 이득을 한두 홀에서 되돌립니다.",
    action: "파5 두 번째 샷은 직접 만회보다 다음 샷 거리 확보 기준으로 선택합니다.",
    confidence: "low sample",
    metric: "par5_score_to_par",
  },
  {
    problem: "3퍼트 이상 위험 홀이 있습니다.",
    evidence: "파인힐스 12번은 4퍼트, 전체 2라운드 57 putts.",
    impact: "그린 위에서 보기 이상으로 밀리는 홀이 생깁니다.",
    action: "8-12m 첫 퍼트는 홀컵보다 1m 안전 원에 남기는 기준으로 연습합니다.",
    confidence: "low sample",
    metric: "three_putt_rate",
  },
];

const metricRows = [
  ["Penalty shots", "6", "2 rounds", "Low"],
  ["Putts", "57", "28.5 / round", "Low"],
  ["Imported shots", "151", "private", "OK"],
  ["Warnings", "1", "파인힐스", "Review"],
];

export default function UiReviewPage() {
  const [screen, setScreen] = useState<ScreenKey>("dashboard");
  const [view, setView] = useState<ViewKey>("desktop");
  const [selectedHole, setSelectedHole] = useState(11);
  const [analysisTab, setAnalysisTab] = useState<AnalysisTab>("Score");
  const [expandedInsight, setExpandedInsight] = useState(0);

  const activeTimeline = timelines[selectedHole] ?? [];
  const activeHole = holes.find((hole) => hole.number === selectedHole) ?? holes[0];
  const avgScore = useMemo(
    () => rounds.reduce((total, round) => total + round.score, 0) / rounds.length,
    [],
  );

  return (
    <main className="min-h-screen bg-[#f4f5f1] text-[#1f2522]">
      <div className="border-b border-[#d7ddd5] bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase text-[#4d6f8f]">UI Review Gate</p>
            <h1 className="mt-1 text-2xl font-semibold">LalaGolf v2 Core Screens</h1>
          </div>
          <div className="flex flex-wrap gap-2">
            <SegmentButton active={screen === "dashboard"} onClick={() => setScreen("dashboard")}>
              Dashboard
            </SegmentButton>
            <SegmentButton active={screen === "round"} onClick={() => setScreen("round")}>
              Round Detail
            </SegmentButton>
            <SegmentButton active={screen === "analysis"} onClick={() => setScreen("analysis")}>
              Analysis
            </SegmentButton>
            <span className="mx-1 hidden h-9 border-l border-[#d7ddd5] sm:block" />
            <SegmentButton active={view === "desktop"} onClick={() => setView("desktop")}>
              Desktop
            </SegmentButton>
            <SegmentButton active={view === "mobile"} onClick={() => setView("mobile")}>
              Mobile
            </SegmentButton>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-5 py-5">
        <div className="mb-5 grid gap-3 rounded-md border border-[#d7ddd5] bg-white p-4 lg:grid-cols-[1fr_auto] lg:items-center">
          <div>
            <p className="text-sm font-medium text-[#32413a]">
              검토용 샘플 데이터: 파인힐스 92타, 베르힐 영종 90타, 2라운드 151샷
            </p>
            <p className="mt-1 text-sm text-[#69736d]">
              실제 개발 화면이 아니라 색감, 밀도, 정보 구조, 주요 상호작용을 확인하기 위한 프로토타입입니다.
            </p>
          </div>
          <div className="flex gap-2 text-xs">
            <StatusPill tone="blue">private first</StatusPill>
            <StatusPill tone="amber">low sample</StatusPill>
            <StatusPill tone="green">max 3 insights</StatusPill>
          </div>
        </div>

        <div className={view === "mobile" ? "mx-auto max-w-[390px]" : ""}>
          {screen === "dashboard" && (
            <DashboardMock view={view} avgScore={avgScore} expandedInsight={expandedInsight} setExpandedInsight={setExpandedInsight} />
          )}
          {screen === "round" && (
            <RoundMock
              view={view}
              activeHole={activeHole}
              selectedHole={selectedHole}
              setSelectedHole={setSelectedHole}
              activeTimeline={activeTimeline}
            />
          )}
          {screen === "analysis" && (
            <AnalysisMock
              view={view}
              analysisTab={analysisTab}
              setAnalysisTab={setAnalysisTab}
              expandedInsight={expandedInsight}
              setExpandedInsight={setExpandedInsight}
            />
          )}
        </div>
      </div>
    </main>
  );
}

function DashboardMock({
  view,
  avgScore,
  expandedInsight,
  setExpandedInsight,
}: {
  view: ViewKey;
  avgScore: number;
  expandedInsight: number;
  setExpandedInsight: (index: number) => void;
}) {
  const mobile = view === "mobile";
  return (
    <section className="overflow-hidden rounded-md border border-[#d7ddd5] bg-[#fbfbf8] shadow-sm">
      <MockNav mobile={mobile} title="Dashboard" />
      <div className="border-b border-[#d7ddd5] bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">Dashboard</h2>
            <p className="mt-1 text-sm text-[#69736d]">2 private rounds imported</p>
          </div>
          <button className="rounded-md bg-[#256a46] px-4 py-2 text-sm font-semibold text-white">
            Upload round
          </button>
        </div>
      </div>
      <div className="space-y-4 p-4">
        <div className={mobile ? "grid grid-cols-2 gap-2" : "grid grid-cols-5 gap-3"}>
          <Kpi label="Avg score" value={avgScore.toFixed(1)} accent="blue" />
          <Kpi label="Best round" value="90" accent="green" />
          <Kpi label="Penalties" value="3.0" suffix="/ round" accent="red" />
          <Kpi label="Putts" value="28.5" suffix="/ round" accent="amber" />
          <Kpi label="Data conf." value="Low" accent="slate" />
        </div>

        <div className={mobile ? "space-y-4" : "grid grid-cols-[1.45fr_1fr] gap-4"}>
          <Panel title="Recent rounds" caption="Dense table first; chart appears with 3+ rounds">
            <RoundTable compact={mobile} />
          </Panel>
          <Panel title="Priority insights" caption="Max 3; duplicate evidence suppressed">
            <InsightList expandedInsight={expandedInsight} setExpandedInsight={setExpandedInsight} compact={mobile} />
          </Panel>
        </div>

        <div className="rounded-md border border-[#d7ddd5] bg-white px-4 py-3 text-sm text-[#405047]">
          Last import: 2 committed, 0 failed. 파인힐스 has 1 parse warning.
        </div>
      </div>
    </section>
  );
}

function RoundMock({
  view,
  activeHole,
  selectedHole,
  setSelectedHole,
  activeTimeline,
}: {
  view: ViewKey;
  activeHole: (typeof holes)[number];
  selectedHole: number;
  setSelectedHole: (hole: number) => void;
  activeTimeline: string[];
}) {
  const mobile = view === "mobile";
  return (
    <section className="overflow-hidden rounded-md border border-[#d7ddd5] bg-[#fbfbf8] shadow-sm">
      <MockNav mobile={mobile} title="Round Detail" />
      <div className="border-b border-[#d7ddd5] bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">파인힐스 · 92 (+20)</h2>
            <p className="mt-1 text-sm text-[#69736d]">2026-04-14 · 18 holes · 74 shots</p>
          </div>
          <div className="flex gap-2">
            <StatusPill tone="green">Private</StatusPill>
            <button className="rounded-md border border-[#b9c3bc] px-3 py-1.5 text-sm font-medium">
              Share settings
            </button>
          </div>
        </div>
      </div>
      <div className="border-b border-[#d7ddd5] bg-[#eef3f0] px-4 py-3">
        <div className="flex gap-2 overflow-x-auto text-sm">
          {["Overview", "Holes & Shots", "Metrics", "Raw Import"].map((tab, index) => (
            <span
              className={`whitespace-nowrap rounded-md px-3 py-1.5 font-medium ${
                index === 1 ? "bg-[#256a46] text-white" : "bg-white text-[#405047]"
              }`}
              key={tab}
            >
              {tab}
            </span>
          ))}
        </div>
      </div>
      <div className="p-4">
        <div className={mobile ? "space-y-4" : "grid grid-cols-[1.15fr_1fr] gap-4"}>
          <Panel title="Hole scan" caption="Flags live in the table, not separate cards">
            <div className={mobile ? "mb-3 flex gap-2 overflow-x-auto pb-1" : "hidden"}>
              {holes.map((hole) => (
                <button
                  className={`h-9 min-w-9 rounded-md border text-sm font-semibold ${
                    hole.number === selectedHole
                      ? "border-[#256a46] bg-[#256a46] text-white"
                      : "border-[#d7ddd5] bg-white"
                  }`}
                  key={hole.number}
                  onClick={() => setSelectedHole(hole.number)}
                >
                  {hole.number}
                </button>
              ))}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] border-collapse text-sm">
                <thead className="bg-[#eef3f0] text-left text-[#526059]">
                  <tr>
                    <th className="px-3 py-2">#</th>
                    <th className="px-3 py-2">Par</th>
                    <th className="px-3 py-2">Score</th>
                    <th className="px-3 py-2">Putts</th>
                    <th className="px-3 py-2">Pen</th>
                    <th className="px-3 py-2">Flag</th>
                  </tr>
                </thead>
                <tbody>
                  {holes.map((hole) => (
                    <tr
                      className={`cursor-pointer border-t border-[#e4e8e1] ${
                        hole.number === selectedHole ? "bg-[#e7f0ec]" : "bg-white"
                      }`}
                      key={hole.number}
                      onClick={() => setSelectedHole(hole.number)}
                    >
                      <td className="px-3 py-2 font-semibold">{hole.number}</td>
                      <td className="px-3 py-2">{hole.par}</td>
                      <td className="px-3 py-2">{hole.score}</td>
                      <td className="px-3 py-2">{hole.putts}</td>
                      <td className="px-3 py-2">{hole.penalties}</td>
                      <td className="px-3 py-2">
                        <FlagLabel flag={hole.flag} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel title={`Hole ${activeHole.number} · Par ${activeHole.par} · ${activeHole.score} (${activeHole.score - activeHole.par >= 0 ? "+" : ""}${activeHole.score - activeHole.par})`} caption="Selected timeline">
            <div className="space-y-2">
              {activeTimeline.map((shot) => (
                <div className="rounded-md border border-[#d7ddd5] bg-white px-3 py-2 text-sm" key={shot}>
                  {shot}
                </div>
              ))}
            </div>
          </Panel>
        </div>
        <div className="mt-4 rounded-md border border-dashed border-[#b9c3bc] bg-white px-4 py-3 text-sm text-[#69736d]">
          Biggest gain/loss shots will appear here after expected value tables are available.
        </div>
      </div>
    </section>
  );
}

function AnalysisMock({
  view,
  analysisTab,
  setAnalysisTab,
  expandedInsight,
  setExpandedInsight,
}: {
  view: ViewKey;
  analysisTab: AnalysisTab;
  setAnalysisTab: (tab: AnalysisTab) => void;
  expandedInsight: number;
  setExpandedInsight: (index: number) => void;
}) {
  const mobile = view === "mobile";
  return (
    <section className="overflow-hidden rounded-md border border-[#d7ddd5] bg-[#fbfbf8] shadow-sm">
      <MockNav mobile={mobile} title="Analysis" />
      <div className="border-b border-[#d7ddd5] bg-white p-4">
        <h2 className="text-xl font-semibold">Analysis</h2>
        <div className="mt-3 flex gap-2 overflow-x-auto text-sm">
          {["Date range", "Course", "Round count: 2", "Min confidence"].map((filter) => (
            <button className="whitespace-nowrap rounded-md border border-[#b9c3bc] bg-white px-3 py-1.5" key={filter}>
              {filter}
            </button>
          ))}
        </div>
        <p className="mt-3 rounded-md bg-[#fff7e6] px-3 py-2 text-sm text-[#7a4c00]">
          Low sample: metrics are visible, but confidence labels stay low until more rounds are imported.
        </p>
      </div>
      <div className="border-b border-[#d7ddd5] bg-[#eef3f0] px-4 py-3">
        <div className="flex gap-2 overflow-x-auto text-sm">
          {(["Score", "Tee", "Approach", "Short Game", "Putting"] as AnalysisTab[]).map((tab) => (
            <button
              className={`whitespace-nowrap rounded-md px-3 py-1.5 font-medium ${
                tab === analysisTab ? "bg-[#256a46] text-white" : "bg-white text-[#405047]"
              }`}
              key={tab}
              onClick={() => setAnalysisTab(tab)}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>
      <div className="p-4">
        <div className={mobile ? "space-y-4" : "grid grid-cols-[1.45fr_0.85fr] gap-4"}>
          <Panel title={`${analysisTab} table`} caption="Chart comes after sample size supports it">
            {analysisTab === "Score" ? <RoundTable compact={mobile} /> : <MetricTable tab={analysisTab} />}
          </Panel>
          <Panel title="Insight rail" caption="Max 3 for selected filters">
            <InsightList expandedInsight={expandedInsight} setExpandedInsight={setExpandedInsight} compact={mobile} />
          </Panel>
        </div>
        <Panel title="Detail metrics" caption="Secondary metrics stay in tables" className="mt-4">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead className="bg-[#eef3f0] text-[#526059]">
                <tr>
                  <th className="px-3 py-2">Metric</th>
                  <th className="px-3 py-2">Value</th>
                  <th className="px-3 py-2">Sample</th>
                  <th className="px-3 py-2">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {metricRows.map((row) => (
                  <tr className="border-t border-[#e4e8e1] bg-white" key={row[0]}>
                    {row.map((cell) => (
                      <td className="px-3 py-2" key={cell}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
    </section>
  );
}

function RoundTable({ compact }: { compact: boolean }) {
  if (compact) {
    return (
      <div className="space-y-2">
        {rounds.map((round) => (
          <div className="rounded-md border border-[#d7ddd5] bg-white p-3" key={round.course}>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="font-semibold">{round.course}</p>
                <p className="text-xs text-[#69736d]">{round.date}</p>
              </div>
              <div className="text-right">
                <p className="text-lg font-semibold">{round.score}</p>
                <p className="text-xs text-[#a34242]">+{round.toPar}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] text-left text-sm">
        <thead className="bg-[#eef3f0] text-[#526059]">
          <tr>
            <th className="px-3 py-2">Date</th>
            <th className="px-3 py-2">Course</th>
            <th className="px-3 py-2">Score</th>
            <th className="px-3 py-2">+/-</th>
            <th className="px-3 py-2">Pen</th>
            <th className="px-3 py-2">Putts</th>
          </tr>
        </thead>
        <tbody>
          {rounds.map((round) => (
            <tr className="border-t border-[#e4e8e1] bg-white" key={round.course}>
              <td className="px-3 py-2">{round.shortDate}</td>
              <td className="px-3 py-2 font-medium">{round.course}</td>
              <td className="px-3 py-2">{round.score}</td>
              <td className="px-3 py-2 text-[#a34242]">+{round.toPar}</td>
              <td className="px-3 py-2">{round.penalties}</td>
              <td className="px-3 py-2">{round.putts}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InsightList({
  expandedInsight,
  setExpandedInsight,
  compact,
}: {
  expandedInsight: number;
  setExpandedInsight: (index: number) => void;
  compact: boolean;
}) {
  return (
    <div className="space-y-2">
      {insights.map((insight, index) => {
        const expanded = !compact || expandedInsight === index;
        return (
          <button
            className="block w-full rounded-md border border-[#d7ddd5] bg-white p-3 text-left"
            key={insight.metric}
            onClick={() => setExpandedInsight(index)}
          >
            <div className="flex items-start justify-between gap-3">
              <p className="font-semibold leading-6">{insight.problem}</p>
              <span className="shrink-0 rounded bg-[#fff7e6] px-2 py-1 text-xs font-medium text-[#7a4c00]">
                {insight.confidence}
              </span>
            </div>
            {expanded && (
              <div className="mt-2 space-y-2 text-sm leading-6 text-[#526059]">
                <p>{insight.evidence}</p>
                <p>{insight.impact}</p>
                <p className="font-medium text-[#1f2522]">{insight.action}</p>
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}

function MetricTable({ tab }: { tab: AnalysisTab }) {
  const rows: Record<AnalysisTab, string[][]> = {
    Score: [],
    Tee: [
      ["Driver", "24 shots", "Result C high", "Low"],
      ["Penalty", "6 shots", "H/OB", "Low"],
    ],
    Approach: [
      ["120-160m", "sample pending", "avg error TBD", "Low"],
      ["0-30m", "sample pending", "recovery", "Low"],
    ],
    "Short Game": [
      ["Recovery", "flags on hole 11/15", "penalty linked", "Low"],
      ["Bunker", "not enough sample", "hidden by default", "Low"],
    ],
    Putting: [
      ["Putts", "57 total", "28.5 / round", "Low"],
      ["4-putt flag", "파인힐스 12", "review", "Low"],
    ],
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[480px] text-left text-sm">
        <tbody>
          {rows[tab].map((row) => (
            <tr className="border-t border-[#e4e8e1] bg-white first:border-t-0" key={row[0]}>
              {row.map((cell) => (
                <td className="px-3 py-2" key={cell}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Panel({
  title,
  caption,
  className = "",
  children,
}: {
  title: string;
  caption?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={`rounded-md border border-[#d7ddd5] bg-[#fdfdfb] ${className}`}>
      <div className="border-b border-[#d7ddd5] px-4 py-3">
        <h3 className="font-semibold">{title}</h3>
        {caption && <p className="mt-1 text-xs text-[#69736d]">{caption}</p>}
      </div>
      <div className="p-3">{children}</div>
    </section>
  );
}

function Kpi({
  label,
  value,
  suffix,
  accent,
}: {
  label: string;
  value: string;
  suffix?: string;
  accent: "blue" | "green" | "red" | "amber" | "slate";
}) {
  const accents = {
    blue: "border-[#b8cce0] bg-[#f0f6fb]",
    green: "border-[#b8d4c4] bg-[#edf7f1]",
    red: "border-[#e4c0bd] bg-[#fff2f0]",
    amber: "border-[#e8d2a5] bg-[#fff8e8]",
    slate: "border-[#c9cfcb] bg-[#f5f6f4]",
  };
  return (
    <div className={`rounded-md border p-3 ${accents[accent]}`}>
      <p className="text-xs font-medium text-[#526059]">{label}</p>
      <p className="mt-2 text-2xl font-semibold">
        {value}
        {suffix && <span className="ml-1 text-xs font-medium text-[#69736d]">{suffix}</span>}
      </p>
    </div>
  );
}

function MockNav({ mobile, title }: { mobile: boolean; title: string }) {
  if (mobile) {
    return (
      <div className="flex items-center justify-between border-b border-[#d7ddd5] bg-[#1f2522] px-4 py-3 text-white">
        <span className="font-semibold">{title}</span>
        <span className="rounded border border-white/30 px-2 py-1 text-xs">Menu</span>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between border-b border-[#d7ddd5] bg-[#1f2522] px-4 py-3 text-white">
      <div className="flex gap-5 text-sm">
        <span className="font-semibold">LalaGolf</span>
        <span>Dashboard</span>
        <span>Rounds</span>
        <span>Analysis</span>
        <span>Upload</span>
      </div>
      <span className="rounded border border-white/30 px-2 py-1 text-xs">User menu</span>
    </div>
  );
}

function SegmentButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      className={`rounded-md border px-3 py-2 text-sm font-medium ${
        active
          ? "border-[#256a46] bg-[#256a46] text-white"
          : "border-[#c9cfcb] bg-white text-[#32413a]"
      }`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function StatusPill({ tone, children }: { tone: "blue" | "amber" | "green"; children: ReactNode }) {
  const tones = {
    blue: "bg-[#e9f2fb] text-[#2d5878]",
    amber: "bg-[#fff4d7] text-[#7a4c00]",
    green: "bg-[#e7f4ec] text-[#256a46]",
  };
  return <span className={`rounded-full px-3 py-1 text-xs font-semibold ${tones[tone]}`}>{children}</span>;
}

function FlagLabel({ flag }: { flag: string }) {
  const important = flag !== "steady";
  return (
    <span className={`rounded px-2 py-1 text-xs font-medium ${important ? "bg-[#fff2f0] text-[#a34242]" : "bg-[#eef3f0] text-[#526059]"}`}>
      {flag}
    </span>
  );
}
