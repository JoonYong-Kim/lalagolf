# Golf Analytics Roadmap

## Goal

이 프로젝트를 단순 골프 기록 저장소에서, 라운드 회고와 연습 우선순위까지 제시하는 분석 도구로 확장한다.  
계획은 두 축으로 나눈다.

- 단기: 현재 `rounds`, `holes`, `shots` 데이터만으로 계산 가능한 지표를 안정적으로 제공
- 장기: 샷 상태 모델, 기대 타수, 샷 가치, 전략 추천까지 포함하는 분석 엔진으로 확장

## Planning Principles

- 기존 입력 포맷과 저장 흐름은 가능한 한 유지한다.
- 계산 로직은 라우트와 템플릿에서 분리한다.
- 모든 지표는 정의를 문서화하고 테스트로 고정한다.
- 즉시 가능한 지표와 장기 확장 지표를 혼합하지 않고 단계적으로 도입한다.
- 장기 지표는 최종적으로 `연습 추천`과 `전략 추천`으로 연결한다.

## Status Legend

- `[x]` completed
- `[~]` partially implemented / foundation exists
- `[ ]` planned / not started

## Metric Catalog

### A. Immediate Metrics

이 영역은 현재 입력 데이터만으로 계산 가능하다.

#### 1. Scoring

- `[x]` `birdie_count`
- `[x]` `par_count`
- `[x]` `bogey_count`
- `[x]` `double_bogey_plus_count`
- `[x]` `birdie_rate`
- `[x]` `par_rate`
- `[x]` `bogey_rate`
- `[x]` `double_bogey_plus_rate`
- `[x]` `score_to_par`

#### 2. Par Type Performance

- `[x]` `par3_avg_score`
- `[x]` `par4_avg_score`
- `[x]` `par5_avg_score`
- `[x]` `par3_score_to_par`
- `[x]` `par4_score_to_par`
- `[x]` `par5_score_to_par`

#### 3. Putting

- `[x]` `avg_putts_per_hole`
- `[x]` `one_putt_rate`
- `[x]` `three_putt_rate`
- `[x]` `first_putt_distance_avg`
- `[x]` `putts_per_gir_hole`
- `[x]` `putts_per_non_gir_hole`

#### 4. Short Game

- `[x]` `scrambling_rate`
- `[x]` `sand_save_rate`
- `[x]` `up_and_down_rate`

#### 5. Penalties

- `[x]` `penalty_strokes_per_round`
- `[x]` `ob_count`
- `[x]` `hazard_count`
- `[x]` `unplayable_count`
- `[x]` `penalty_hole_rate`
- `[x]` `tee_shot_penalty_rate`
- `[x]` `penalty_by_club_group`

#### 6. Tee Shots

- `[x]` 첫 샷 클럽 사용 분포
- `[x]` 첫 샷 결과 분포 `A/B/C`
- `[x]` 첫 샷 클럽별 홀 평균 `score_to_par`
- `[x]` 파 유형별 티샷 전략 비교
- `[x]` `driver_penalty_rate`
- `[x]` `driver_result_c_rate`

#### 7. Approach Proxy

- `[x]` `distance < 160m` 비퍼터 샷 결과 분포
- `[x]` 거리 구간별 샷 수
- `[x]` 거리 구간별 평균 `error`
- `[x]` 거리 구간별 결과 분포
- `[x]` `gir_from_under_160_rate`
- `[ ]` 구간별 회복 성공률

### B. Medium-Term Metrics

이 영역은 기존 입력을 최대한 유지하되, 분석 구조를 더 정교하게 만들기 위한 단계다.

#### 1. Round Quality / Context

- `[x]` 코스별 난이도 보정 점수
- `[x]` 전반 / 후반 분리 분석
- `[x]` 최근 3홀 / 마무리 홀 성적
- `[x]` 버디 후 다음 홀 성적
- `[x]` 페널티 직후 회복력

#### 2. Club Reliability

- `[ ]` 클럽별 평균 거리
- `[ ]` 클럽별 거리 편차
- `[ ]` 클럽별 큰 미스율
- `[ ]` 클럽별 페널티 유발율
- `[ ]` 클럽별 기대 손실 타수

#### 3. Strategy Comparison

- `[ ]` 파4/파5 티샷에서 `D` vs `W3/U4` 비교
- `[ ]` 거리 구간별 layup vs 공격 성향 비교
- `[ ]` 특정 클럽 선택 후 평균 홀 성적 비교

### C. Long-Term Metrics

이 영역은 샷 상태 모델과 기대값 기반 분석이 필요하다.

#### 1. Expected Score by State

- `[ ]` `tee / par type` 기대 타수
- `[ ]` `fairway / distance bucket` 기대 타수
- `[ ]` `rough / distance bucket` 기대 타수
- `[ ]` `bunker / distance bucket` 기대 타수
- `[ ]` `green / putt distance bucket` 기대 타수

#### 2. Shot Value

- `[ ]` 각 샷의 `expected_before`
- `[ ]` 각 샷의 `expected_after`
- `[ ]` `shot_cost`
- `[ ]` `shot_value = expected_before - (shot_cost + expected_after)`

#### 3. Strokes Gained by Category

- `[ ]` `off_the_tee`
- `[ ]` `approach`
- `[ ]` `short_game`
- `[ ]` `putting`
- `[ ]` `recovery`
- `[ ]` `penalty_impact`

#### 4. Pressure / Context Metrics

- `[ ]` 전반 vs 후반 압박 상황 성적
- `[ ]` 마지막 3홀 성적
- `[x]` 목표 타수 근처 홀 성적
- `[x]` 좋은 흐름 / 나쁜 흐름 직후 성적

#### 5. Recommendation Metrics

- `[ ]` 최근 10라운드 기준 손실이 큰 영역 3개
- `[ ]` 다음 연습 추천 3개
- `[ ]` 코스 공략 추천
- `[ ]` 티샷 클럽 선택 추천

## Architecture Direction

### Current Modules

- `[x]` `src/metrics.py`
- `[x]` `tests/test_metrics.py`
- `[x]` `src/shot_model.py`
- `[x]` `tests/test_shot_model.py`

### Recommended Long-Term Modules

- `[ ]` `src/shot_model.py`
- `[x]` `src/analytics_config.py`
- `[~]` `src/expected_value.py`
- `[~]` `src/strokes_gained.py`
- `[~]` `src/recommendations.py`
- `[ ]` `tests/test_shot_model.py`
- `[~]` `tests/test_expected_value.py`
- `[~]` `tests/test_strokes_gained.py`
- `[~]` `tests/test_recommendations.py`

### Recommended Responsibilities

```python
def build_round_metrics(round_info: dict, holes: list[dict], shots: list[dict]) -> dict:
    ...

def build_recent_summary(raw_trend_data: list[dict], window: int = 10) -> dict:
    ...

def normalize_shot_states(round_info: dict, holes: list[dict], shots: list[dict]) -> list[dict]:
    ...

def build_expected_score_table(shot_facts: list[dict]) -> dict:
    ...

def build_shot_values(shot_facts: list[dict], expected_table: dict) -> list[dict]:
    ...

def build_recommendations(profile: dict) -> list[str]:
    ...
```

## Data Model Direction

### Current Model

- `[x]` `rounds`
- `[x]` `holes`
- `[x]` `shots`

### Derived Analysis Layer

장기적으로는 원본 테이블 위에 분석용 파생 레이어를 두는 것이 좋다.

#### Proposed `shot_facts`

- `[ ]` `round_id`
- `[ ]` `hole_num`
- `[ ]` `shot_num`
- `[ ]` `par_type`
- `[ ]` `club`
- `[ ]` `club_group`
- `[ ]` `start_state`
- `[ ]` `end_state`
- `[ ]` `distance`
- `[ ]` `distance_bucket`
- `[ ]` `is_tee_shot`
- `[ ]` `is_putt`
- `[ ]` `is_recovery`
- `[ ]` `penalty_strokes`
- `[x]` `expected_before`
- `[x]` `expected_after`
- `[x]` `shot_value`

### Optional Future Tables

- `[ ]` `courses`
- `[ ]` `tees`
- `[ ]` `round_conditions`
- `[ ]` `round_notes`

## Definitions And Constraints

### Current Constraints

- 입력 포맷에 방향성과 의도 정보가 없다.
- `Approach`는 완전한 정의가 아니라 `proxy metric`이다.
- `Sand Save`는 greenside bunker save의 근사치다.
- `First Putt Distance`는 기록 품질에 따라 편차가 클 수 있다.
- 18홀 / 27홀 모두 지원해야 하므로 고정 18홀 가정은 금지한다.

### Future Constraints

- 기대 타수 모델은 샘플 수가 부족한 구간에서 불안정할 수 있다.
- `strokes gained`는 상태 정의가 부정확하면 오히려 오판을 만들 수 있다.
- 전략 비교는 반드시 샘플 수와 분산을 함께 보여줘야 한다.

## Expected Score Stabilization Rules

현재 기대 타수 엔진과 후속 shot value 계층은 아래 운영 규칙을 기준으로 동작한다.

### Fallback Order

lookup은 가장 구체적인 상태에서 시작하고, 표본이 부족하면 다음 단계로 내려간다.

1. `full = (start_state, distance_bucket, par_type, shot_category)`
2. `no_par = (start_state, distance_bucket, shot_category)`
3. `no_distance = (start_state, par_type, shot_category)`
4. `start_category = (start_state, shot_category)`
5. `start_only = (start_state,)`

원칙:

- 가장 구체적인 상태를 우선 사용한다.
- 현재 레벨의 `sample_count`가 기준 미만이면 다음 fallback을 사용한다.
- 테이블 생성 시점에서도 현재 레벨 기준 미만 상태는 기본적으로 제외한다.
- fallback이 깊을수록 설명력은 낮아지므로 UI에는 `expected_lookup_level`, `expected_sample_count`를 같이 노출한다.

### Remaining Stroke Definition

기대 타수는 단순 남은 샷 수가 아니라 `score_cost + penalty_strokes`의 누적으로 계산한다.

- 일반 샷: 보통 `1`
- `OB`: `1 + 2`
- `H`, `UN`: `1 + 1`

이 정의를 써야 penalty가 실제 기대 손실에 반영된다.

### Current Thresholds

현재 구현 기준:

- `expected_before / expected_after / shot_value` 기본 기준: `min_samples = 2`
- 기대 타수 fallback 레벨별 기준:
  - `full = 3`
  - `no_par = 3`
  - `no_distance = 2`
  - `start_category = 2`
  - `start_only = 1`
- `tee strategy comparison`: 그룹당 `min_samples = 3`
- `layup vs attack proxy`: 그룹당 `min_samples = 3`
- `club reliability report`: 그룹당 `min_samples = 5`
- 추천 신뢰도:
  - `count >= 30` -> `표본 충분`
  - `15 <= count < 30` -> `표본 보통`
  - `count < 15` -> `표본 적음`

### Interpretation Rules

- `expected_before`가 없으면 해당 샷의 `shot_value`는 계산하지 않는다.
- 마지막 샷에서 `expected_after`를 찾지 못하면 `0`으로 둔다.
- `shot_value = expected_before - (shot_cost + expected_after)`를 사용한다.
- 전략 비교는 항상 `sample_count`, `risk`, `proxy 여부`를 함께 보여준다.

### UI Exposure Rules

- 라운드 상세: 샷별 `expected_lookup_level`, `expected_sample_count` 노출
- 전략 비교 표: 비교군 양쪽이 모두 최소 표본을 넘겼을 때만 본문 표 노출
- 표본 부족 시: 표 대신 경고 문구만 노출
- `layup vs attack`: 의도 데이터가 없으므로 반드시 `proxy`라고 명시

### Recommended Hardening

다음 안정화 우선순위:

1. `min_samples`를 모듈 상수로 통합해서 라우트 하드코딩 제거
2. fallback 레벨별 최소 표본 기준 차등 적용
3. 매우 작은 `sample_count` 구간은 테이블 생성 단계에서 제외
4. 최근 라운드 가중치 도입
5. 코스별 보정 도입 여부 검토
6. 전략 비교에 표준편차 / 분위수 기반 리스크 지표 추가

## Phased Roadmap

## Phase 1: Metrics Foundation

Status: `[x] completed`

### Scope

- `src/metrics.py` 추가
- 라운드 단위 지표 계산 로직 구현
- `tests/test_metrics.py` 추가
- 기존 라우트 계산 로직 일부를 metrics 모듈로 이동

### Checkpoints

- [x] `build_round_metrics()`가 일관된 dict를 반환한다.
- [x] `3-putt`, `1-putt`, `scrambling`, `sand save`, `penalty strokes`, `par type` 테스트가 추가된다.
- [x] 18홀과 27홀 모두 정상 계산된다.
- [x] 기존 상세 페이지 동작을 깨지 않는다.

## Phase 2: Round Detail Upgrade

Status: `[x] completed`

### Scope

- `round_detail` 라우트에서 지표 계산 사용
- 상세 페이지에 분석 섹션 추가

### Checkpoints

- [x] scoring / putting / penalty 지표가 노출된다.
- [x] `scrambling_rate`, `sand_save_rate`, `tee_shot_penalty_rate`가 표시된다.
- [x] 거리 구간별 approach proxy가 표시된다.
- [x] 티샷 프로파일이 표시된다.

## Phase 3: Trends Upgrade

Status: `[x] completed`

### Scope

- `trends` 집계 확장
- 점수대 비교 외에 최근 `5/10/20` 라운드 추세 추가

### Checkpoints

- [x] 최근 `5/10/20` 라운드 기준 지표가 계산된다.
- [x] 점수 구간별 `three_putt`, `scrambling`, `penalty` 비교가 가능하다.
- [x] 기존 `GIR`, `putts` 상관관계에 새 지표가 추가된다.
- [x] `par3/4/5 to par` 비교가 가능하다.

## Phase 4: Dashboard Summary

Status: `[x] completed`

### Scope

- 홈 / 목록 화면에 최근 10라운드 요약 카드 추가
- 최근 약점 문구 생성

### Checkpoints

- [x] 최근 10라운드 요약 카드가 추가된다.
- [x] 최근 약점 문구가 표시된다.
- [x] 동일 로직을 상세 / 트렌드와 중복 없이 재사용한다.

## Phase 5: Immediate Metrics Completion

Status: `[x] completed`

### Goal

현재 입력 구조로 계산 가능한 지표를 최대한 빠짐없이 완성한다.

### Scope

- `up_and_down_rate` 정의 및 구현
- `gir_from_under_160_rate` 추가
- `driver_penalty_rate`, `driver_result_c_rate` 추가
- 파 유형별 티샷 전략 비교
- 최근 10라운드 기준 핵심 약점 자동 강조 정교화

### Checkpoints

- [x] 모든 immediate metrics가 문서 기준으로 구현된다.
- [x] 상세 / 트렌드 / 대시보드에서 즉시 지표가 일관되게 보인다.
- [x] 정의가 애매한 지표는 UI와 문서에 제약이 명시된다.

## Phase 6: Analysis State Layer

Status: `[x] completed`

### Goal

장기 분석을 위한 샷 상태 모델을 도입한다.

### Scope

- 샷 순서 복원 헬퍼 정리
- `club_group`, `distance_bucket`, `start_state`, `end_state` 도입
- `normalize_shot_states()` 구현
- `shot_facts` 구조 설계

### Checkpoints

- [x] 모든 샷이 분석용 상태로 정규화된다.
- [x] 거리 구간 / lie / 샷 카테고리 상수가 분리된다.
- [x] 상태 모델이 테스트로 고정된다.
- [x] `shot_facts`를 집계/화면/후속 엔진에서 재사용하도록 연결한다.

## Phase 7: Expected Score Engine

Status: `[x] completed`

### Goal

상태별 기대 타수 테이블을 만든다.

### Scope

- 상태 정의 확정
- 상태별 샘플 수 계산
- 기대 잔여 타수 테이블 생성
- 불안정 구간에 대한 fallback 규칙 설계

### Checkpoints

- [x] `Expected Score by State` 테이블이 생성된다.
- [x] 샘플 수 부족 구간에 대한 보정 규칙이 있다.
- [x] 테스트 데이터로 기대값 계산이 검증된다.
- [x] 기대 타수 엔진을 화면 또는 후속 shot value 단계에서 재사용하도록 연결한다.

## Phase 8: Shot Value & Strokes Gained

Status: `[~] in progress`

### Goal

샷 가치와 카테고리별 손익을 계산한다.

### Scope

- `expected_before`, `expected_after` 계산
- `shot_value` 계산
- `off_the_tee`, `approach`, `short_game`, `putting`, `recovery`, `penalty_impact` 집계

### Checkpoints

- [x] 각 샷에 `shot_value`가 계산된다.
- [x] 최근 10라운드 기준 category별 손실이 계산된다.
- [x] 라운드 상세 / 트렌드에 strokes gained 유사 분석이 표시된다.

## Phase 9: Strategy & Reliability

Status: `[~] in progress`

### Goal

클럽 신뢰도와 전략 비교 지표를 제공한다.

### Scope

- 클럽별 평균 거리와 편차
- 클럽별 큰 미스율
- 클럽별 기대 손실 타수
- 티샷 클럽 선택 비교
- layup vs 공격 비교

### Checkpoints

- [x] 클럽 신뢰도 리포트가 생성된다.
- [x] 샘플 수가 충분한 전략 비교만 노출된다.
- [x] 전략 비교는 평균뿐 아니라 리스크를 함께 표시한다.

## Phase 10: Recommendation Layer

Status: `[x] completed`

### Goal

분석 결과를 연습 및 전략 추천으로 연결한다.

### Scope

- 최근 10라운드 손실 영역 상위 3개
- 다음 연습 추천 3개
- 코스 공략 추천
- 티샷 클럽 선택 추천

### Checkpoints

- [x] 추천 로직이 수치 기반으로 생성된다.
- [x] 추천 문구가 지나치게 일반적이지 않다.
- [x] 상세 / 대시보드 / 트렌드에 추천이 일관되게 연결된다.
- [x] `strokes gained` 해석 문구와 샘플 수 경고가 추천 UI에 포함된다.

## Implemented Summary

현재까지 완료된 핵심 묶음:

- `[x]` 라운드 지표, 최근 요약, 샷 상태 정규화, 기대 타수, shot value 기반 분석 엔진 구축
- `[x]` 클럽 신뢰도, 티샷 전략 비교, layup vs attack proxy, 리스크 지표를 `Trends` 화면에 연결
- `[x]` 홈 / 목록 / 트렌드 / 상세 화면에 최근 10라운드 추천 섹션과 인사이트 연결
- `[x]` 추천 우선순위를 `손실 총량 + 최근 흐름 + 표본 수` 공통 점수로 정렬
- `[x]` 추천 카드에 샘플 경고, 손실 이유, 우선순위 근거, `이번 주 실행 문장` 추가
- `[x]` `Top Recurring Priorities`에 반복 손실 subtype, subtype별 drill, 최근 흐름 표시 추가
- `[x]` `Round Detail`의 `Next Action` / `Round + Trend Action`에 subtype, 라운드 컨텍스트, 실행 문장 연결
- `[x]` 추천/상세 로직에 대한 테스트를 `tests/test_recommendations.py` 중심으로 확장

## Remaining Roadmap

남은 정리 작업:

- `[ ]` 최근 반복 손실 subtype을 더 세밀하게 확장할지 검토
- `[ ]` subtype별 drill 추천을 더 많은 카테고리와 패턴으로 확장
- `[ ]` 추천 카드 문구 길이와 정보 밀도를 실제 사용 흐름 기준으로 추가 다듬기
- `[ ]` `tests/test_strokes_gained.py`와 연계된 경계 조건 테스트를 더 보강

## Verification Status

- `[x]` `pytest -q`
- `[x]` `python -m py_compile src/metrics.py src/shot_model.py src/expected_value.py src/strokes_gained.py src/webapp/routes.py src/webapp/__init__.py run_webapp.py`

## Immediate Next Options

- `[x]` 추천 문구를 코스 상황별 전략 카드로 세분화
- `[x]` `strokes gained` 해석 문구와 샘플 수 경고를 UI에 더 구체적으로 보강
- `[x]` `Phase 9`용 클럽 신뢰도 / 전략 비교 설계 구체화
- `[x]` 기대 타수 엔진용 샘플 수 기준과 안정화 규칙 문서화
- `[x]` fallback 레벨별 최소 표본 기준 차등 적용
- `[x]` 저표본 상태를 기대 타수 테이블 생성 단계에서 제외
- `[x]` 같은 코스 평균 대비 `Course Adj To Par` 1차 버전 추가
- `[x]` 전반 / 후반 분리 분석
- `[x]` 최근 3홀 / 마무리 홀 성적
- `[x]` 버디 후 다음 홀 성적
- `[x]` 페널티 직후 회복력
