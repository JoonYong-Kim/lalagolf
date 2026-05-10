# Round Logger V2 → 프로덕션 작업 계획

샌드박스의 V2 입력 UX (점진 노출 + 클럽 가방 + OK 자동 진행)를 실제 라운드 기록용
모바일 페이지로 승격하기 위한 작업 계획.

## 목표

로그인 → 라운드 중 입력 → 최종 업로드 → 분석으로 이어지는 end-to-end 흐름 완성.

## 이미 정해진 기반

- UX: V2 (점진 노출 + 클럽 가방 + OK 자동 진행). 샌드박스(`v2/web/app/sandbox/round/`)에서 확정.
- 인증: 기존 30일 쿠키 세션 그대로 사용.
- 데이터 모델: 기존 `Round/Hole/Shot` 재사용. `RoundDraft` 같은 별도 테이블은 만들지 않는다.
- 동기화 모델: 낙관적 업데이트 + 디바운스 PATCH.
- 별도 서비스 느낌: URL 분리(`/rounds/log` 등) + 로그인 후 직진 흐름.
- 분석 입력: ORM 직접 분석을 사용한다. 캐노니컬 텍스트는 현재는 설명용/비상용 참고 경로다.

## 결정된 항목

| 항목 | 결정 | 이유 |
| --- | --- | --- |
| `draft` 상태 위치 | `Round.computed_status` enum에 값 추가 | 변경 최소, 모델 일관성 |
| 클럽 가방 저장 | `User.club_bag` JSONB | 14개 미만 작은 데이터, 단순 |
| 동시 draft 개수 | 사용자당 1개 제한 | 사용자 멘탈 모델 단순 |
| 분석 입력 방식 | ORM 직접 분석 (가능하다면) | 텍스트 변환 단계 제거 |
| 샌드박스 영역 | 유지 | UX 변형 비교 자산 |
| 별도 도메인 | P1 이후 검토 | URL 분리만으로 충분 |

## P0 — MVP (백엔드 연결, 한 사람이 끝까지 사용 가능)

진행 순서: **P0.1 → P0.2 → P0.4 → P0.5 → P0.3 → P0.6 → P0.7**

### P0.1 스키마 마이그레이션

`v2/api/alembic/versions/` 신규 마이그레이션:

- `Round.computed_status` enum에 `draft` 값 추가
- `User.club_bag` JSONB 컬럼 추가 (nullable)

기존 데이터 영향 없음.

### P0.2 API

`v2/api/app/api/v1/`:

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| GET | `/me/club-bag` | 사용자 클럽 가방 |
| PUT | `/me/club-bag` | 가방 저장 |
| POST | `/rounds/draft` | 빈 draft Round + 18홀 생성, id 반환 |
| GET | `/rounds/draft` | 현재 사용자의 draft (없으면 404) |
| PATCH | `/rounds/{id}/meta` | date/time/course/companions |
| PATCH | `/rounds/{id}/holes/{n}` | par + shots[] 전체 upsert |
| POST | `/rounds/{id}/finalize` | status: draft→pending, 분석 잡 enqueue |
| DELETE | `/rounds/{id}/draft` | draft 폐기 |

오너십: 전 엔드포인트에서 `user_id` 일치 검증. 한 사용자당 동시 draft 1개로 제한.

### P0.3 분석 워커 호환

- `v2/api/app/services/analytics.py`에서 ORM 직접 분석 가능 여부 확인
- 캐노니컬 텍스트 경로는 현재 프로덕션 흐름에서는 사용하지 않는다

### P0.4 공용 코드 승격

`v2/web/app/sandbox/round/_shared/` → `v2/web/lib/round-logger/`:

- `types.ts`, `clubs.ts`, `canonicalize.ts` 그대로
- `store.ts` → `useLocalDraft` (오프라인 보조)
- 신규 `useRemoteDraft` (GET → 로컬 → 디바운스 PATCH)
- 신규 `useRemoteClubBag`

### P0.5 프론트 라우트

- `v2/web/app/rounds/log/page.tsx` — V2 UX 본 페이지
  - 진입 시 `GET /rounds/draft`
    - 200: 곧장 입력 화면
    - 404: 라운드 시작 화면 (메타 입력 → `POST /rounds/draft` → 진입)
- `v2/web/app/rounds/log/finalize/page.tsx` — 18홀 요약 + 빈 홀 경고 + 캐노니컬 텍스트 토글, "최종 업로드"
- `v2/web/app/settings/clubs/page.tsx` — 가방/거리 편집 (샌드박스 인덱스의 가방 섹션 이식)

### P0.6 진입점 / 인증

- `/dashboard`에 "라운드 기록 시작" 큰 버튼 추가
- 미인증 `/rounds/log` → entry(`/`) 리다이렉트 후 재진입

### P0.7 샌드박스 처리

- 그대로 유지. 추후 정리.

**P0 완료 조건**: 로그인 → `/settings/clubs`에서 가방 설정 → `/rounds/log`에서 18홀 입력 →
최종 업로드 → 라운드 상세 페이지에서 분석 결과 확인.

## P1 — 신뢰성 (라운드 중 끊김 대응)

- **P1.1** 오프라인 큐: IndexedDB 기반 PATCH 큐, 동일 리소스 합치기
- **P1.2** 동기화 인디케이터: 헤더 우측 ✓/⟳/⚠ + 마지막 동기화 시각
- **P1.3** 401 처리: 로컬 상태 유지 + 재로그인 모달, 큐 자동 flush
- **P1.4** WakeLock API (라운드 중 화면 잠금 방지, 옵션)

## P2 — 입력 편의 보강

- 코스/동반자 자동완성 (`GET /me/recent-courses`, `/me/recent-companions`)
- 가방 초기 설정 위저드 (신규 사용자)
- 칩 길게 누르기 → 빠른 삭제
- 페널티 빠른 단축 (`+ OB`, `+ H`) 재검토

## P3 — 분석 진행 가시성

- finalize 후 `/rounds/{id}`에서 분석 잡 상태 polling 또는 SSE
- "분석 진행 중…" → 완료 시 자동 새로고침
- 핵심 인사이트 1-2개 즉시 노출

## P4 — 멀티 디바이스 / 엣지

- 두 기기 동시 편집 시 last-write-wins + "다른 기기에서 변경됨" 알림
- 다크 모드 기본화 (야외 가독성/배터리)
