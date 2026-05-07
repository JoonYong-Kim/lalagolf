# GolfRaiders v2 UI Review

## 1. Purpose

Core private screens must be reviewed before implementation. The goal is to confirm how the UI improves over v1 from the user's point of view before engineering work locks in layout and component choices.

This document records wireframe decisions for:

- Dashboard
- Round Detail
- Analysis

Browser prototype:

- Local route: `/ui-review`
- Purpose: review color, density, screen hierarchy, tab behavior, hole selection, and insight expansion before implementing production screens.
- This route is a static review prototype and should not be treated as the final application implementation.

## 2. Review Rules

- Create low-fidelity wireframes before building each core screen.
- Include desktop and mobile variants.
- Use imported v1 data examples when available.
- Prefer dense but readable tables, charts, tabs, filters, and side panels.
- Use cards only for repeated items or compact summary units such as recent rounds and insight units.
- Record confirmed decisions here before implementation starts.
- If a major layout direction changes after confirmation, update this document first.

## 3. Dashboard

Status: confirmed.

Imported data examples used:

- 파인힐스, 2026-04-14, 92 / +20, 18 holes, 74 shots, 4 penalty shots, 29 putts
- 베르힐 영종, 2026-04-11, 90 / +18, 18 holes, 77 shots, 2 penalty shots, 28 putts

Required wireframes:

- [x] Desktop dashboard
- [x] Mobile dashboard

Questions to confirm:

- What must be visible in the first viewport?
- Which KPI and trend blocks matter most?
- Where do max-3 priority insights appear?
- How should recent rounds and upload status be scanned?
- What should be hidden behind drill-down on mobile?

Confirmed decisions:

- First viewport hierarchy is approved: KPI strip, recent rounds table, max-3 priority insights, and compact upload/import status.
- Recent rounds should stay table/list-first, with chart added only when sample size supports it.
- Dashboard insight area is capped at 3 active units and suppresses duplicate primary evidence metrics.
- Mobile dashboard keeps insights before recent rounds because insights are the action surface.

### 3.1 Desktop Dashboard Wireframe

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Top nav: GolfRaiders | Dashboard | Rounds | Analysis | Upload       [User menu] │
├──────────────────────────────────────────────────────────────────────────────┤
│ Page header                                                                  │
│ Dashboard                         [Upload round] [Last 10 rounds v]          │
│ Imported sample: 2 rounds, private                                           │
├──────────────────────────────────────────────────────────────────────────────┤
│ KPI strip                                                                    │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│ │ Avg score  │ │ Best round │ │ Penalties  │ │ Putts      │ │ Data conf. │   │
│ │ 91.0       │ │ 90         │ │ 3.0/round  │ │ 28.5/round │ │ low sample │   │
│ └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
├────────────────────────────────────────────┬─────────────────────────────────┤
│ Score trend / recent rounds table          │ Priority insights, max 3        │
│ ┌────────────────────────────────────────┐ │ ┌─────────────────────────────┐ │
│ │ Date       Course      Score  +/- Pen │ │ │ Problem                     │ │
│ │ 04-14      파인힐스    92     +20 4   │ │ │ Evidence                    │ │
│ │ 04-11      베르힐 영종 90     +18 2   │ │ │ Impact                      │ │
│ └────────────────────────────────────────┘ │ │ Next action                 │ │
│ Small line chart above table once >=3 rows │ │ Confidence: low sample      │ │
│                                            │ └─────────────────────────────┘ │
│                                            │ Same evidence metric suppressed │
├────────────────────────────────────────────┴─────────────────────────────────┤
│ Work queue / upload status                                                   │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ Last import: 2 committed, 0 failed. 파인힐스 has 1 parse warning.        │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

Dashboard rules:

- First viewport prioritizes score, penalty, putt, confidence, recent rounds, and max-3 insights.
- Cards are limited to KPI cells and insight units. Recent rounds use a dense table.
- Trend chart appears above the table only when at least 3 rounds exist. With 2 rounds, the table carries the view.
- Dashboard insight area never shows more than 3 active insight units and suppresses duplicate `primary_evidence_metric`.
- Upload/import status is a compact full-width row, not a large card.

### 3.2 Mobile Dashboard Wireframe

```text
┌──────────────────────────────┐
│ Header: Dashboard       Menu │
├──────────────────────────────┤
│ [Upload round] [Filter v]    │
├──────────────────────────────┤
│ KPI carousel, 2 columns      │
│ Avg 91.0 | Best 90           │
│ Pen 3.0  | Putts 28.5        │
│ Confidence: low sample       │
├──────────────────────────────┤
│ Priority insights, max 3     │
│ ┌──────────────────────────┐ │
│ │ Problem                  │ │
│ │ Evidence                 │ │
│ │ Next action              │ │
│ └──────────────────────────┘ │
├──────────────────────────────┤
│ Recent rounds                │
│ 04-14 파인힐스     92 +20    │
│ 04-11 베르힐 영종  90 +18    │
├──────────────────────────────┤
│ Upload/import status         │
└──────────────────────────────┘
```

Mobile rules:

- KPI cells wrap to 2 columns.
- Insight units appear before recent rounds because they are the action surface.
- Recent rounds collapse to compact list rows with score and score-to-par.
- Upload details are drill-down; only the latest status appears in the dashboard.

## 4. Round Detail

Status: confirmed.

Imported data example used: 파인힐스, 2026-04-14, 92 / +20, 18 holes.

Required wireframes:

- [x] Desktop round detail
- [x] Mobile round detail

Questions to confirm:

- How is the round summary kept visible?
- How does the user select a hole?
- How does the shot timeline show club, distance, lie, result, and penalty without becoming noisy?
- Where do biggest gain/loss shots appear?
- How are private fields and sharing controls separated?

Confirmed decisions:

- Compact round header and summary strip are approved.
- Hole table plus selected shot timeline is approved as the primary interaction.
- Penalty, high-score, and putting flags stay in the hole table rather than becoming separate cards.
- Private notes, raw import data, and sharing controls must remain separated from the main overview.
- Mobile uses horizontal hole chips and opens one selected timeline at a time.

### 4.1 Desktop Round Detail Wireframe

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Top nav                                                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│ Round header                                                                 │
│ 파인힐스 · 2026-04-14 · 92 (+20)        [Private] [Edit] [Share settings]    │
│ Summary strip: Par 72 | 18 holes | 74 shots | 29 putts | 4 penalty shots     │
├──────────────────────────────────────────────────────────────────────────────┤
│ Tabs: Overview | Holes & Shots | Metrics | Raw Import                        │
├──────────────────────────────────────────────┬───────────────────────────────┤
│ Hole table                                    │ Selected hole detail          │
│ ┌──────────────────────────────────────────┐ │ Hole 11 · Par 5 · 7 (+2)     │
│ │ # Par Score Putts Pen Flag              │ │ ┌───────────────────────────┐ │
│ │ 1 4   4     2     0                     │ │ │ Shot timeline             │ │
│ │ 5 5   8     3     0   High score        │ │ │ 1 D 220 T→F C H cost 2    │ │
│ │ 11 5  7     2     1   Penalty           │ │ │ 2 I7 110 F→F B            │ │
│ │ 12 3  5     4     0   4 putts           │ │ │ 3 48 75 F→R C             │ │
│ │ 18 4  5     2     1   Penalty           │ │ │ 4 52 16 R→R C             │ │
│ └──────────────────────────────────────────┘ │ │ 5 P 13 R→R C              │ │
│                                              │ │ 6 P 2 R→H B               │ │
│                                              │ └───────────────────────────┘ │
├──────────────────────────────────────────────┴───────────────────────────────┤
│ Bottom band: biggest loss/gain shots once shot values are computed           │
│ Empty state now: "Shot value will appear after expected table is available." │
├──────────────────────────────────────────────────────────────────────────────┤
│ Private/import controls                                                      │
│ Source file, parse warnings, private notes, sharing controls separated here. │
└──────────────────────────────────────────────────────────────────────────────┘
```

Round detail rules:

- Header remains compact and sticky on desktop while switching tabs.
- Hole table is the primary scan surface. Shot timeline is contextual to the selected hole.
- Penalty, 3+ putts, and high-score holes are flags in the table, not separate cards.
- Sharing controls are separated from private notes and raw upload content.
- Raw import content stays behind the `Raw Import` tab, not in the main overview.

### 4.2 Mobile Round Detail Wireframe

```text
┌──────────────────────────────┐
│ 파인힐스 92 (+20)       Menu │
│ 2026-04-14 · Private         │
├──────────────────────────────┤
│ Summary strip scroll         │
│ Par72 | 18h | 74 shots | Pen4│
├──────────────────────────────┤
│ Segmented tabs               │
│ Overview | Holes | Metrics   │
├──────────────────────────────┤
│ Hole selector chips          │
│ 1 2 3 4 5 6 7 8 9 ... 18     │
├──────────────────────────────┤
│ Selected hole                │
│ Hole 11 · Par 5 · 7 (+2)     │
│ Shot timeline, vertical      │
│ 1 D 220 T→F C H              │
│ 2 I7 110 F→F B               │
│ 3 48 75 F→R C                │
│ ...                          │
├──────────────────────────────┤
│ Flags: penalty, recovery     │
└──────────────────────────────┘
```

Mobile rules:

- Hole selector uses stable chip dimensions and horizontal scroll.
- Only one hole timeline is open at a time.
- Long raw text and private notes are hidden under secondary actions.

## 5. Analysis

Status: confirmed.

Imported data examples used: 2 private rounds, 151 shots, 6 penalty shots, 57 putts.

Required wireframes:

- [x] Desktop analysis
- [x] Mobile analysis

Questions to confirm:

- Which filters are always visible?
- How are All, Tee, Short Game, Control Shot, Iron Shot, Putting, Recovery, and Penalty tabs organized?
- Which chart/table appears first in each tab?
- How are insight units shown without making the page card-heavy?
- How are low-confidence metrics and sample counts displayed?

Confirmed decisions:

- Filters remain visible on desktop and horizontally scrollable on mobile.
- All, Tee, Short Game, Control Shot, Iron Shot, Putting, Recovery, Penalty tabs are approved.
- Main analysis stays table/table-first with insights as a side widget on desktop.
- Insights are shown one at a time in a switchable widget to avoid card-heavy scrolling.
- Low sample and fallback confidence labels remain visible instead of hiding metrics.

### 5.1 Desktop Analysis Wireframe

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Top nav                                                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│ Analysis header                                                              │
│ Filters: [Date range v] [Course v] [Round count: 2] [Min confidence v]       │
│ Sample notice: low sample, global/baseline expected value may be used        │
├──────────────────────────────────────────────────────────────────────────────┤
│ Tabs: All | Tee | Short Game | Control Shot | Iron Shot | Putting | Penalty │
├──────────────────────────────────────────────┬───────────────────────────────┤
│ Main chart/table area                         │ Insight widget               │
│ Score tab default:                            │ Max 3 for selected filters   │
│ ┌──────────────────────────────────────────┐ │ ┌───────────────────────────┐ │
│ │ Round comparison table                  │ │ │ Problem                   │ │
│ │ Course       Date       Score +/- Pen   │ │ │ Evidence + sample         │ │
│ │ 파인힐스     04-14      92    +20 4     │ │ │ Impact                    │ │
│ │ 베르힐 영종  04-11      90    +18 2     │ │ │ Next action               │ │
│ └──────────────────────────────────────────┘ │ │ [<] 1 / N [>]             │ │
│ Chart appears when sample size supports it    │ └───────────────────────────┘ │
├──────────────────────────────────────────────┴───────────────────────────────┤
│ Detail table for selected tab                                                │
│ Tee: club, count, result C rate, penalty rate, avg shot value when ready     │
│ Approach: distance band, count, avg error, GIR conversion                    │
│ Putting: first putt distance, 3-putt rate, putts per GIR/non-GIR             │
└──────────────────────────────────────────────────────────────────────────────┘
```

Analysis rules:

- Filters are always visible on desktop.
- Tabs own the main table/chart. Insights are a side widget, not the entire page.
- The side widget displays one deduplicated insight at a time with previous/next controls and dot
  indicators.
- If sample is low, table remains available but chart labels and insight confidence show low/medium.
- Cards are limited to the selected insight unit, suggested routine items, and compact notices.
- Dedupe is visible: one evidence metric appears once in the widget sequence.

### 5.2 Mobile Analysis Wireframe

```text
┌──────────────────────────────┐
│ Analysis                Menu │
├──────────────────────────────┤
│ Filter bar, horizontal scroll│
│ Date v | Course v | Conf v   │
├──────────────────────────────┤
│ Sample notice                │
│ 2 rounds · low sample        │
├──────────────────────────────┤
│ Tabs, horizontal scroll      │
│ Score Tee Approach Short...  │
├──────────────────────────────┤
│ Selected tab table           │
│ Course       Score +/- Pen   │
│ 파인힐스     92    +20 4     │
│ 베르힐 영종  90    +18 2     │
├──────────────────────────────┤
│ Insight widget, one at a time│
│ Problem + confidence         │
│ Evidence/action + [<] [>]    │
└──────────────────────────────┘
```

Mobile rules:

- Filters and tabs use horizontal scroll, not stacked full-width controls.
- Tables keep key columns visible first. Secondary metrics move into row expansion.
- Insight units appear one at a time in a switchable widget to avoid card-heavy scrolling.

## 6. Empty, Loading, And Error States

Dashboard:

- Empty: show upload CTA, one short sentence, and no fake chart.
- Loading: skeleton for KPI strip, recent rounds rows, and insight widget.
- Error: compact inline retry near the failed panel. Do not block the whole page unless auth fails.

Round Detail:

- Empty/not found: return to rounds list and show upload CTA.
- Loading: header skeleton plus hole table skeleton.
- Parse warning: show warning count in `Raw Import` tab and upload status row.

Analysis:

- Empty: show filters disabled and upload/import CTA.
- Low sample: keep data visible and mark confidence as low.
- Error: preserve filters and show retry inside main chart/table region.

## 7. Review Checklist

- [x] Dashboard first viewport hierarchy is acceptable.
- [x] Dashboard max-3 insight behavior is acceptable.
- [x] Round Detail hole table + selected timeline interaction is acceptable.
- [x] Round Detail private/share/raw import separation is acceptable.
- [x] Analysis tab/filter/table layout is acceptable.
- [x] Mobile navigation and dense table behavior is acceptable.
- [x] Empty/loading/error state direction is acceptable.

## 8. Approval Log

| Date | Screen | Variant | Decision | Owner |
| --- | --- | --- | --- | --- |
| 2026-05-03 | Dashboard | Desktop/Mobile | Confirmed `/ui-review` hierarchy, max-3 insights, recent rounds table/list, compact upload status | User |
| 2026-05-03 | Round Detail | Desktop/Mobile | Confirmed compact header, hole table, selected shot timeline, and separated private/share/raw controls | User |
| 2026-05-03 | Analysis | Desktop/Mobile | Confirmed filters, tabs, table/chart-first layout, and confidence labels; superseded by 2026-05-07 widget update | User |
| 2026-05-07 | Analysis | Desktop/Mobile | Updated insight presentation to one-at-a-time switchable widget and equal-level plan/goal actions | User |
