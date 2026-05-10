# GolfRaiders v2 라운드 중 입력 현재 동작

이 문서는 현재 구현된 라운드 중 입력 기능의 실제 동작을 설명한다.
설계 계획은 [round_logger_plan.md](round_logger_plan.md)에 남기고, 이 문서는 현재 코드가 무엇을 하고 있는지에 집중한다.

## 1. 사용 흐름

현재 흐름은 다음과 같다.

1. 사용자가 `/rounds/log`에 진입한다.
2. 로그인 상태가 아니면 홈으로 돌려보낸다.
3. 진행 중인 draft 라운드가 있으면 바로 입력 화면을 연다.
4. draft가 없으면 시작 화면에서 날짜, 코스, 동반자를 입력한 뒤 새 draft를 만든다.
5. 샷과 메타를 입력하면 서버로 디바운스 저장된다.
6. 사용자가 최종 업로드를 누르면 draft가 `pending`으로 전환되고 분석 작업이 enqueue된다.
7. 분석 작업이 끝나면 라운드 상세 화면에서 결과를 확인한다.

## 2. 현재 API

라운드 중 입력은 기존 `Round`, `Hole`, `Shot` 테이블을 그대로 사용한다.

### Draft 생성과 조회

- `POST /api/v1/rounds/draft`
  - 현재 사용자 기준 draft 라운드를 하나 만든다.
  - draft가 이미 있으면 409를 반환한다.
- `GET /api/v1/rounds/draft`
  - 현재 활성 draft를 반환한다.
  - 없으면 404를 반환한다.
- `DELETE /api/v1/rounds/draft`
  - 현재 draft를 폐기한다.

### Draft 수정

- `PATCH /api/v1/rounds/{id}/meta`
  - 날짜, 코스명, 동반자를 수정한다.
- `PATCH /api/v1/rounds/{id}/holes/{n}`
  - 홀 par와 해당 홀의 샷 전체를 upsert한다.

### Finalize

- `POST /api/v1/rounds/{id}/finalize`
  - draft를 종료하고 분석 작업을 enqueue한다.
  - 응답에는 분석 작업 id와 상태가 함께 들어간다.

## 3. 동기화 모델

현재 입력 화면은 낙관적 업데이트와 디바운스 PATCH를 쓴다.

- 샷 편집은 로컬 상태를 먼저 바꾼다.
- 서버 저장은 일정 시간 뒤에 합쳐서 보낸다.
- 오프라인 또는 일시 실패한 변경은 큐에 쌓는다.
- 우측 상단 동기화 표시기로 현재 상태와 마지막 저장 시각을 보여준다.

이 방식은 입력 도중 네트워크가 끊겨도 계속 기록할 수 있게 하려는 목적이다.

## 4. 클럽 가방

클럽 가방은 사용자의 입력 보조 설정이다.

- `/settings/clubs`에서 편집한다.
- 입력 화면에서는 클럽 선택 시 기본 거리를 미리 채울 수 있다.
- 현재 구현에서는 `UserProfile.club_bag`에 JSON 형태로 저장된다.
- PostgreSQL에서는 JSONB로, SQLite 테스트 환경에서는 호환 JSON으로 동작한다.

## 5. 분석 연결

최종 업로드 후에는 라운드 상세가 아니라 분석 작업이 먼저 진행된다.

- 분석은 별도 `analysis_jobs` row로 추적한다.
- 라운드 상세는 pending 상태일 수 있다.
- 분석 작업이 끝나면 라운드 상세와 분석 화면에서 저장된 결과를 읽는다.

## 6. 현재 문서와의 관계

`round_logger_plan.md`는 여전히 유효한 설계 문서지만, 몇 가지는 현재 구현과 뉘앙스가 다르다.

- 계획 문서는 canonical text fallback 가능성을 열어 두고 있지만, 현재 프로덕션 흐름은 ORM 직접 분석을 사용한다.
- 계획 문서는 `User.club_bag`를 JSONB로 적고 있지만, 현재 코드는 SQLite 테스트 호환을 위해 JSON variant를 쓴다.

이 둘은 기능적 모순이라기보다 구현 세부 차이로 보는 편이 맞다.
