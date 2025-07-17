# Croft Golf Record

This project is a golf record management service designed to help personal efficiently record and manage golf round data.  
It allows users to systematically log each hole and shot information in a structured and intuitive manner.

## 🚀 Key Features
 1. Load data from data file
 1. Save data into Database
 1. Various helpful information serviced by web dashboard

## 📥 Installation
 TBD

## Getting started
 TBD

## 📝 Data Writing Rule

All data files are stored data folder.
Each data file include one round data.

Each line of a data file is managed as either hole information or shot information.
Hole information lines represent hole numbers from 1 to 18, with a maximum of 36 holes possible.
After the hole number, par information is entered as P3, P4, P5, etc.
For example, if the 1st hole is a par 4 hole, it can be entered as 1 P4 or 1P4.
Shot information lines must include an abbreviation for the club used, shot feel, and shot result, and can optionally include additional information such as distance, penalty, or concede.

The structure is approximately as follows:
Club Feel Result \[Landing Spot\] \[Distance\] \[Penalty or Concede\]

Club abbreviations are as follows:

 * D : Driver
 * W3 : Wood 3
 * W5 : Wood 5
 * UW : Utility Wood
 * U3 : Hybrid 3
 * U4 : Hybrid 4
 * U5 : Hybrid 5
 * I3 : Iron 3
 * I4 : Iron 4
 * I5 : Iron 5
 * I6 : Iron 6
 * I7 : Iron 7
 * I8 : Iron 8
 * I9 : Iron 9
 * IP : Iron P
 * 48 : Wedge 48
 * 52 : Wedge 52
 * 56 : Wedge 56
 * P : Putter

Shot feel and shot result are divided into A, B, C grades, with A representing the best result.
Landing Spot would be B which means it landed on bunker.
Distance is recorded in meters, and concede is marked as OK.
Penalty information includes general penalty and out of bounds, marked as H and OB respectively.

### 🎯 Example Input
```
1P4
D B C
I5 A C 150 H
P C A 10 OK
```
#### 📌 Data Format Explanation
- `1P4` → **Hole 1, Par 4**
- `D B C` → **Driver shot, B-grade feel, C-grade result**
- `I5 A C 150 H` → **Iron 5, A-grade feel, C-grade result, 150 meters, Hazard**
- `P C A 10 OK` → **Putter, C-grade feel, A-grade result, 10 meters, Conceded**

## Design Guideline

### 1. ✅ 상단 내비게이션 바

| 항목     | 현재 상태             | 개선 제안                                                             |
| ------ | ----------------- | ----------------------------------------------------------------- |
| 배경색    | 진한 카키 (`#77804E`) | 더 선명한 contrast를 위해 **조금 더 어두운 그린 (`#5F6841`)** 또는 **gradient 처리** |
| 텍스트 색상 | 흰색                | 괜찮지만 **폰트를 더 굵게(Bold)** 또는 약간 **골드톤 강조** 시 `#C7963A` 계열 사용 고려     |
| 메뉴 간격  | 약간 빽빽함            | `padding: 0 16px;` 또는 `gap: 24px` 등 간격 확보 시 고급스러움 증가              |
| 로고 영역  | 로고+텍스트 정렬 우수      | 로고 클릭 → 메인으로 이동되게 `cursor: pointer` 및 링크 추가 권장                    |

---

### 2. ✅ 배경 / 카드 영역

| 항목                     | 현재 상태                       | 개선 제안                                                     |
| ---------------------- | --------------------------- | --------------------------------------------------------- |
| 전체 배경                  | `#F3E9D2` 톤 적용 잘됨           | 👍 유지 추천                                                  |
| 카드 UI (Golf Rounds 박스) | 흰색 배경 + drop shadow         | 그림자 세기 약간 줄이기 or **카드 라운딩 증가 (`border-radius: 12px`)** 추천 |
| 카드 여백                  | `padding` / `margin` 부족해 보임 | 내부 `padding: 24px`, 외부 `margin-top: 32px` 등 공간 확보로 시각적 안정 |

---

### 3. ✅ 테이블 및 버튼

| 항목        | 현재 상태             | 개선 제안                                                                                 |
| --------- | ----------------- | ------------------------------------------------------------------------------------- |
| 헤더 컬럼     | 기본 Bootstrap 스타일  | 각 컬럼 헤더에 **더 어두운 베이지 (#E1D9C0)** 또는 **하단 보더 강조** (`border-bottom: 2px solid #C7963A`) |
| 텍스트 컬러    | 기본 블랙             | `Score`, `GIR(%)` 등 수치 데이터는 **진한 녹색 (#3A3323)** 적용 고려                                 |
| Delete 버튼 | `#C7963A` 계열 잘 반영 | 👍 다만 **hover 시 #A67625 정도로 살짝 어둡게** 하면 UX 강화됨                                        |

---

## 🎯 추가 개선 아이디어 (선택 사항)

* **폰트 변경**:
  기본 sans-serif 대신, *Montserrat*, *Noto Sans KR*, *Raleway* 등의 세련된 웹폰트로 대체 시 세련미 강화

* **데이터가 없을 때 Empty UI 제공**:
  "No golf rounds found yet" 와 함께 아이콘(⛳) 또는 CTA 버튼 추가 (예: \[첫 라운드 기록하기])

* **GIR 등 중요 수치 강조 카드 추가** (대시보드 스타일):

  * 예: `GIR 평균`, `최고 점수`, `총 라운드 수` 등의 숫자 카드

---

## 🎨 색상 팔레트 요약 (적용 확인용)

| 요소      | 색상             | 용도        |
| ------- | -------------- | --------- |
| #C7963A | 버튼, 강조 텍스트, 로고 | 메인 강조색    |
| #3A3323 | 제목, 본문 텍스트     | 강한 텍스트 색상 |
| #77804E | 상단 바 배경        | 카키 계열 배경  |
| #F3E9D2 | 전체 배경          | 크림톤 배경    |
| #7A5D35 | 버튼 hover 등     | 어두운 골드톤   |


## 🛠️ Development & Future Enhancements


