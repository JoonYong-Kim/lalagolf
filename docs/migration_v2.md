# GolfRaiders v2 Migration Plan

## 1. Migration Goals

- v1 MySQL 데이터와 repo-root `data/<year>` 원본 라운드 파일을 v2 PostgreSQL 구조로 이전한다.
- v1에서 검증된 파싱/분석 결과를 v2에서도 동일하거나 설명 가능한 수준으로 재현한다.
- 단일 사용자 중심 데이터 구조를 v2의 multi-user ownership 모델로 안전하게 변환한다.
- 기존 운영 데이터 손실 없이 v1과 v2를 비교 검증한 뒤 전환한다.

## 2. Migration Principles

- 원본 데이터는 보존한다.
- 계산 결과는 가능한 한 복사하지 않고 v2 분석 코어로 재계산한다.
- 모든 imported row는 owner user를 명시한다.
- migration script는 반복 실행 가능하거나, 실행 이력이 명확해야 한다.
- v1 데이터와 v2 데이터의 row id 매핑표를 남긴다.
- 개인정보성 데이터는 기본 private으로 import한다.

## 3. Source Systems

### 3.1 v1 MySQL

Expected source tables or concepts:

- rounds
- holes
- shots
- coplayers or round companion text
- existing score and trend fields if present

v1의 정확한 스키마는 migration 전 `SHOW CREATE TABLE` 결과로 freeze한다.

### 3.2 Raw Files

- repo-root `data/<year>/` 아래 라운드 텍스트 파일.
- tests fixture로 존재하는 라운드 파일.
- raw file은 v2 `source_files`와 `upload_reviews` 검증에 사용한다.

### 3.3 v1 Python Logic

- `src/data_parser.py`
- `src/metrics.py`
- `src/shot_model.py`
- `src/expected_value.py`
- `src/strokes_gained.py`
- `src/recommendations.py`

이 로직은 v2 analytics core로 이관한 뒤 migration 검증에 사용한다.

## 4. Target System

- PostgreSQL.
- UUID primary keys.
- 모든 user-owned table은 `user_id` 또는 `owner_id`를 가진다.
- 기본 visibility는 `private`.
- v1 computed data는 `round_metrics`, `expected_score_tables`, `shot_values`, `insights`로 재생성한다.

## 5. Migration Phases

### Phase 0. Inventory

Tasks:

- v1 MySQL schema dump 생성.
- v1 row count 수집.
- v1 data quality 점검.
- raw file 목록과 MySQL round 매칭 가능성 확인.
- v1 분석 로직 테스트 현황 확인.

Outputs:

- `migration_inventory.json`
- `schema_v1.sql`
- source row count report
- known data issue list

Checklist:

- rounds count
- holes count
- shots count
- rounds without holes
- holes without shots
- invalid dates
- duplicate rounds
- unparsed/raw-only rounds
- companion string patterns

### Phase 1. v2 Schema Preparation

Tasks:

- Alembic migration으로 v2 schema 생성.
- seed admin/user account 생성.
- import owner user 결정.
- citext extension 활성화.
- pgvector extension은 post-MVP RAG 작업에서 추가한다.
- import mapping tables 준비.

Suggested mapping tables:

- `migration_runs`
- `migration_id_map`
- `migration_issues`

Example:

```sql
create table migration_id_map (
  id uuid primary key,
  migration_run_id uuid not null,
  source_system text not null,
  source_table text not null,
  source_id text not null,
  target_table text not null,
  target_id uuid not null,
  created_at timestamptz not null
);
```

### Phase 2. Core Data Import

Import order:

1. users
2. courses, optional
3. source_files, if raw file exists
4. rounds
5. round_companions
6. holes
7. shots

Rules:

- All imported rounds get `visibility = private`.
- If course normalization is uncertain, store `course_name` on rounds and leave `course_id = null`.
- Companion strings are split into `round_companions`.
- v1 round id is preserved only in `migration_id_map`, not as primary key.
- Missing optional fields remain null.
- Invalid rows are skipped only with a `migration_issues` entry.

### Phase 3. Raw File Re-Import Validation

Tasks:

- Parse raw files with v2 parser.
- Compare parsed output against imported MySQL rows.
- Flag mismatches.

Comparison dimensions:

- play date
- course name
- hole count
- total score
- hole par
- hole score
- putts
- shot count
- club
- distance
- start/end lie
- penalty
- result/feel grade

Decision rules:

- If MySQL data and raw file differ, prefer MySQL for production import unless raw file is proven more complete.
- Store raw file as source evidence even if not used as direct import.

### Phase 4. Analytics Recalculation

Tasks:

- Recalculate round metrics for every imported round.
- Build user expected score table.
- Calculate shot values.
- Generate insights.

Rules:

- Do not copy v1 recommendation text directly.
- Store v2 generated insights as `active`.
- Mark low-confidence insights when sample count is small.
- Embedding generation is post-MVP; analytics and migration validation must not depend on it.

### Phase 5. v1/v2 Result Diff

For representative rounds and aggregate windows, compare:

- total score
- score_to_par
- GIR
- putts
- one-putt rate
- three-putt rate
- scrambling
- up-and-down
- penalty strokes
- par3/par4/par5 score to par
- shot category counts
- expected_before
- expected_after
- shot_value
- recommendation priority category

Tolerance:

- Integer score metrics: exact match expected.
- Rates: tolerate minor rounding differences.
- expected values/shot values: tolerate defined numeric epsilon if algorithm changed.
- recommendation text: semantic category match is more important than exact wording.

Output:

- `migration_diff_report.json`
- `migration_diff_summary.md`

### Phase 6. User Acceptance Check

Tasks:

- Owner user reviews imported rounds.
- Spot-check top 10 recent rounds.
- Spot-check worst/best rounds.
- Spot-check analysis dashboard.
- Spot-check Ask GolfRaiders structured answers with imported data.

Acceptance:

- No missing recent rounds.
- Total score and major metrics match v1.
- Sensitive data remains private.
- Link-only/public sharing is off by default.

### Phase 7. Cutover

Options:

- Soft launch: v2 runs read-only from imported snapshot.
- Parallel run: v1 remains live, v2 import is repeated on demand.
- Full cutover: v1 becomes read-only, v2 becomes source of truth.

Recommended:

- Start with soft launch.
- Run one final import.
- Mark v1 read-only.
- Switch production link to v2.

## 6. Migration Script Design

Suggested scripts:

- `scripts/migration/export_v1_mysql.py`
- `scripts/migration/import_v2_postgres.py`
- `scripts/migration/import_raw_files.py`
- `scripts/migration/recalculate_analytics.py`
- `scripts/migration/compare_v1_v2.py`
- `scripts/migration/report_migration.py`

Script requirements:

- Accept config via environment variables.
- Never print secrets.
- Log row counts and issue counts.
- Support dry-run mode.
- Support migration run id.
- Write structured issue records.
- Fail fast on schema mismatch.

## 7. Data Quality Issue Categories

- `missing_required_field`
- `invalid_date`
- `duplicate_round`
- `round_without_holes`
- `hole_without_round`
- `shot_without_hole`
- `invalid_hole_number`
- `invalid_par`
- `score_mismatch`
- `unsupported_penalty_type`
- `unknown_club`
- `raw_file_not_found`
- `raw_file_parse_failed`
- `privacy_sensitive_text`

## 8. Privacy Defaults

Imported data defaults:

- rounds.visibility: `private`
- analysis_snapshots.visibility: `private`
- source_files: private
- notes_private: preserve private notes
- notes_public: empty
- share_course: false unless explicitly set
- share_exact_date: false unless explicitly set

Public sharing must be opt-in after import.

## 9. Rollback Strategy

- v1 database is not modified by migration.
- v2 import uses a `migration_run_id`.
- Imported rows can be deleted by migration run before production cutover.
- After cutover, rollback means switching traffic back to v1 and freezing v2 writes.
- Full rollback after user writes in v2 requires export or manual reconciliation.

## 10. Verification Queries

Examples:

```sql
select count(*) from rounds where user_id = :owner_id;
select count(*) from holes where user_id = :owner_id;
select count(*) from shots where user_id = :owner_id;
select visibility, count(*) from rounds group by visibility;
select computed_status, count(*) from rounds group by computed_status;
select count(*) from migration_issues where severity = 'error';
```

## 11. Acceptance Criteria

- 100% of valid v1 rounds imported or explicitly documented as skipped.
- 100% of imported rounds have an owner user.
- 100% of imported rounds default to private.
- Recent 20 rounds match v1 total score exactly.
- Aggregate score/GIR/putt/penalty metrics match within agreed tolerance.
- v2 analytics jobs complete without unhandled failures.
- LLM cannot retrieve data for another user.
- Link-only/public access does not expose companion names or private notes.

## 12. Open Questions

- Is the current v1 MySQL schema the only source of truth, or are raw files sometimes more complete?
- Should all historical data be assigned to one initial owner, or should past companion names become users later?
- Should course normalization happen during migration or after MVP?
- How much v1 recommendation text should be preserved for comparison only?
- Will v1 remain available read-only after v2 launch?
