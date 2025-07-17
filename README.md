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

### 🎨 Lara Golf 웹사이트 색상 팔레트

| 용도                | 색상명            | HEX       | RGB             | 설명                              |
| ----------------- | -------------- | --------- | --------------- | ------------------------------- |
| 🎯 메인 텍스트 / 로고 강조 | **골드 브론즈**     | `#C7963A` | `199, 150, 58`  | 라라 골프 텍스트에 사용된 고급스러운 황토빛        |
| 🌿 배경 또는 서브 포인트   | **어두운 올리브 그린** | `#3A3323` | `58, 51, 35`    | 실루엣과 외곽 테두리 등에 사용된 모험 느낌의 짙은 컬러 |
| 🌄 배경             | **연한 잔디 그린**   | `#77804E` | `119, 128, 78`  | 골프장 배경의 언덕이나 잔디 느낌의 중간톤 그린      |
| 🌳 서브 배경          | **페일 카키**      | `#A6AD84` | `166, 173, 132` | 배경 하이라이트나 카테고리 강조 등에 적합         |
| ☁️ 전체 배경색         | **오트밀 베이지**    | `#F3E9D2` | `243, 233, 210` | 전체 배경에 사용된 크림톤. 눈에 부담 없는 기본 배경  |
| ⛳ 포인트 강조 (선택)     | **디저트 브라운**    | `#7A5D35` | `122, 93, 53`   | 버튼이나 메뉴 하이라이트용으로 활용 가능          |

---

### ✳️ 추천 활용 예시

* **배경색**: `#F3E9D2` (오트밀 베이지)
* **본문 텍스트**: `#3A3323` 또는 다크 그레이
* **버튼 배경**: `#C7963A` + hover 시 `#7A5D35`
* **헤더 / 푸터 배경**: `#3A3323` 또는 `#77804E`
* **포인트 아이콘 / 링크**: `#C7963A`


## 🛠️ Development & Future Enhancements


