# GolfRaiders v2 인사이트 기준

이 문서는 현재 시스템이 어떤 기준으로 인사이트를 만들고, 저장하고, 화면에 노출하는지 정리한다.
목표는 "어떤 데이터가 왜 인사이트가 되는가"를 운영 관점에서 일관되게 설명하는 것이다.

## 1. 현재 인사이트의 위치

인사이트는 분석 결과의 일부로 저장된다. 라운드 재계산 작업이 끝나면 다음 순서로 갱신된다.

1. 라운드 메트릭 계산
2. 예상 스코어 테이블 계산
3. 샷별 shot value 계산
4. 인사이트 후보 생성
5. 중복 제거 및 우선순위 정리
6. `insights` 테이블 저장
7. `analysis_snapshots`에 요약 결과 저장

화면은 원시 계산을 다시 하지 않고, 저장된 `insights`와 snapshot을 읽는다.

## 2. 현재 인사이트 생성 범위

현재 인사이트 후보는 최근 10라운드 중심의 윈도우를 기준으로 만든다.

- 계산 대상 라운드 집합은 최근 10라운드다.
- 후보 인사이트의 기본 스코프는 `scope_type = window`, `scope_key = all`이다.
- 개별 라운드 상세에서는 해당 라운드의 shot value와 round-specific insight를 함께 보여준다.

즉, 현재 인사이트는 "전체 누적만 보는 장기 요약"이 아니라, 최근 흐름을 기준으로 한 라운드 운영 신호에 가깝다.

## 3. 인사이트 단위의 형태

현재 인사이트는 다음 필드를 중심으로 표현된다.

- `category`: 인사이트 분류
- `scope_type`, `scope_key`: 생성 범위
- `root_cause`: 문제의 원인 라벨
- `primary_evidence_metric`: 중복 판단과 표시에 쓰는 핵심 지표
- `dedupe_key`: 저장 중복 제거용 안정 키
- `problem`: 문제 정의
- `evidence`: 근거 문장
- `impact`: 왜 중요한지
- `next_action`: 다음 행동
- `confidence`: 신뢰도
- `priority_score`: 노출 우선순위

문장형 필드는 한국어 기본이며, 응답 경계에서 지원되는 템플릿만 영어로 렌더링한다.

## 4. 현재 후보 규칙

현재 코드에서 생성되는 대표 후보는 다음과 같다.

- 페널티 손실
  - 총 페널티 타수를 근거로 생성
  - `category = penalty_impact`
  - `root_cause = penalty_strokes`
  - `primary_evidence_metric = penalty_strokes`
- 3퍼트 위험
  - 전체 퍼트 중 3퍼트 비중을 근거로 생성
  - `category = putting`
  - `root_cause = three_putt`
  - `primary_evidence_metric = three_putt_rate`
- 드라이버 큰 미스
  - 드라이버 티샷 Result C 비율을 근거로 생성
  - `category = off_the_tee`
  - `root_cause = driver_result_c`
  - `primary_evidence_metric = driver_result_c_rate`
- 전략/판단 미스
  - Feel이 괜찮은데 Result가 나쁜 샷 수를 근거로 생성
  - `category = score`
  - `root_cause = feel_result_mismatch`
  - `primary_evidence_metric = strategy_issue_count`
- 카테고리별 shot value 손실
  - 최근 10라운드 shot value 합이 음수인 카테고리를 우선 생성
  - `category = off_the_tee`, `putting`, `short_game`, `iron_shot`, `control_shot`, `recovery`, `penalty_impact` 등
  - `root_cause = shot_value_loss`
- 평균 스코어 기준선
  - 전체 평균 스코어를 기준선 인사이트로 저장
  - 현재는 설명용 기준선 성격이 강하다

## 5. 우선순위와 신뢰도

인사이트는 `priority_score`로 정렬한다. 현재 구조는 deterministic rule 기반이다.

신뢰도(`confidence`)는 sample count에 따라 정해진다.

- `high`: 20개 이상
- `medium`: 10개 이상
- `low`: 10개 미만

우선순위는 후보별로 다른 방식으로 계산되지만, 공통 원칙은 "영향이 크고 샘플이 충분한 것"이 먼저 노출되도록 하는 것이다.

## 6. 중복 제거 기준

중복 제거는 의미 기반이 아니라 안정 키 기반으로 수행한다.

기본 키는 다음 요소를 조합한 형태다.

- `scope_type`
- `scope_key`
- `category`
- `root_cause`
- `primary_evidence_metric`

추가로 화면에서는 다음 정책을 따른다.

- 대시보드는 기본적으로 활성 인사이트 최대 3개만 노출한다.
- 같은 primary evidence metric이 반복되면 하나만 남긴다.
- 같은 category가 상위 3개에 중복되면 더 높은 priority_score 항목을 우선한다.

## 7. 저장과 조회의 역할 분리

현재 구조의 핵심은 계산과 조회를 분리한 것이다.

- 계산은 비동기 분석 작업이 담당한다.
- 조회 화면은 저장된 `insights`와 `analysis_snapshots`를 읽는다.
- `/analytics/trends`는 최신 snapshot이 있으면 그것을 우선 사용한다.

이 구조 덕분에 인사이트가 늘어나더라도 화면 렌더링 비용을 크게 올리지 않는다.

## 8. 현재 기준의 해석 원칙

운영과 제품 측면에서 인사이트는 다음 순서로 해석하는 것이 좋다.

- "최근 10라운드에서 반복되는 문제인가"
- "실제 타수 손실과 연결되는가"
- "사용자가 바로 바꿀 수 있는 행동인가"
- "같은 주장을 더 간단한 인사이트로 합칠 수 있는가"
- "샘플이 충분해서 신뢰할 수 있는가"

이 기준을 만족하지 못하면, 점수 계산이 가능하더라도 기본 인사이트로는 올리지 않는 편이 낫다.
