# Round Text Input Format

This document defines the preferred round text file format for GolfRaiders/LalaGolf uploads.
It is based on older raw files under `data/2020` and `data/2021`, which are the cleanest examples
of the original hand-written format. The parser still accepts several legacy variations, listed at
the end of this document.

## 1. Canonical Format

Use UTF-8 plain text. One line should contain one piece of information.

```text
2020.07.21 06:38
킹스데일
바시공
1 P4
D A B
I9 B C
56 B B
P C C 4 OK
2 P5
D B B
I5 A B
56 A A
P C C 1.5 OK
```

The first three non-empty lines are round metadata:

```text
{date time}
{course name}
{companions}
```

After that, repeat hole lines and shot lines:

```text
{hole number} P{par}
{club} {feel grade} {result grade} [distance] [code]
```

## 2. Metadata Lines

### Date And Time

Preferred:

```text
YYYY.MM.DD HH:MM
```

Example:

```text
2020.07.21 06:38
```

### Course Name

Free text. Keep it on one line.

```text
킹스데일
남여주 가람
```

### Companions

Free text. Older files often use a short group label or names separated by spaces.

```text
바시공
가족
홍성걸 양명욱 임길수
```

The upload normalizer splits space-separated companion names for the review screen.

## 3. Hole Lines

Preferred:

```text
1 P4
2 P5
3 P3
```

Meaning:

- `1 P4`: hole 1, par 4
- `2 P5`: hole 2, par 5
- `3 P3`: hole 3, par 3

Par values are parsed from the number after `P`. Non-standard par values such as `P6` are accepted
if present in old data.

## 4. Shot Lines

Preferred:

```text
D A B
I9 B C
56 B B
P C C 4 OK
```

General shape:

```text
{club} {feel} {result} [distance] [code]
```

### Club

Supported clubs:

```text
D
W3 W5 UW
U3 U4
I3 I4 I5 I6 I7 I8 I9
IP IW IA
48 52 56 58
P
```

Common meanings:

- `D`: driver
- `W3`, `W5`: fairway woods
- `UW`, `U3`, `U4`: utility/hybrid
- `I3`-`I9`: irons
- `IP`, `IW`, `IA`: pitching/wedge labels from older files
- `48`, `52`, `56`, `58`: wedges by loft
- `P`: putter

### Feel Grade

The first grade is the player's feel/contact evaluation.

```text
A B C
```

### Result Grade

The second grade is the actual result evaluation.

```text
A B C
```

Examples:

```text
D A B
I9 B C
P B B 4 OK
```

### Distance

Distance is optional. If omitted, the parser uses a club default.

Examples:

```text
56 B C 24
P C C 1.5 OK
IP B B 15
```

Distances are most useful for approach, wedge, and putting lines. Decimal putt distances such as
`1.5` appear in old data and should be preserved in source text. The current parser extracts the
numeric part it supports during normalization.

## 5. Result Codes

Optional result code appears after the grades and optional distance.

```text
P C C 4 OK
D C C OB
U3 C C H
I8 B C B
```

Supported codes:

| Code | Meaning | Parser effect |
| --- | --- | --- |
| `OK` | conceded/OK putt | Adds one score cost and marks concede |
| `H` | hazard | Adds one penalty stroke |
| `UN` | unplayable | Adds one penalty stroke |
| `OB` | out of bounds | Adds two penalty strokes |
| `B` | bunker / next lie bunker | Marks return place as bunker |

## 6. Recommended Authoring Rules

Use this style for new files:

```text
2026.04.11 13:23
베르힐 영종
홍성걸 양명욱 임길수

1 P4
D C C
I7 C C
IP B B
P B B 12 OK

2 P5
D C C OB
UW B B
56 B B 50
P C C 8
P C C 2 OK
```

Rules:

- Keep metadata as the first three non-empty lines.
- Use one hole line before the shots for that hole.
- Use one shot per line.
- Use uppercase club, grade, and code values.
- Put distance before code when both are present.
- Use `P` for putter lines.
- Use `OK`, `H`, `UN`, `OB`, or `B` only as the final code.
- Leave a blank line between holes if it improves readability; blank lines are ignored.

## 7. Accepted Legacy Variations

The parser accepts these variations to support old hand-written data.

### Date Variations

Accepted:

```text
2026.04.11 13:23
20260411 13:23
2026-04-11 13:23
2026.04.11
20260411
2026-04-11
```

If only a date is present, time defaults to `00:00`.

### Hole Spacing And Case

All of these are accepted:

```text
1 P4
1P4
1 p4
2 p3
```

### Shot Case

Lowercase shot lines are accepted:

```text
d b c
i5 a c 150 h
p c a 10 ok
```

The parser uppercases shot lines internally.

### Code Position Quirk

Older files sometimes put `OK` before the putt distance:

```text
P A B OK 13
P B B OK 4
```

This is legacy data. New files should use:

```text
P A B 13 OK
P B B 4 OK
```

### Bunker Code Without Distance

Old files often use `B` as a trailing code:

```text
I6 B C B
52 B C B
D B C B
```

This is accepted as a bunker/return-place marker.

## 8. Warning Conditions

The upload review can still be created with warnings. Common warning cases:

- date cannot be parsed
- course name is missing
- no holes are parsed
- parsed hole count is not 9, 18, or 27
- a hole has no shots
- a line cannot be parsed as metadata, a hole line, or a shot line

Warnings are shown on the upload review screen so the source text can be corrected and reparsed
before committing the private round.

## 9. Notes For Parser Changes

Treat section 1 through section 6 as the stable target format. Section 7 documents compatibility
behavior for existing historical files. New parser changes should preserve old-file compatibility
where practical, but new UI/help text should teach the canonical format.
