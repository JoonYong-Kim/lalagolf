# GolfRaiders v2 Data Model Proposal

## 1. Data Model Goals

- 모든 사용자 데이터를 명확한 owner scope로 분리한다.
- 라운드, 홀, 샷 원본 데이터와 계산된 분석 결과를 구분한다.
- 분석 결과는 재계산 가능하게 유지하고, 원본 데이터는 보존한다.
- 공유/공개 화면에서 민감 정보가 노출되지 않도록 visibility와 serializer 기준을 명확히 한다.
- MVP Ask를 위해 정형 질의와 메시지를 관리하고, post-MVP RAG를 위해 embedding 문서를 확장 가능하게 둔다.

## 2. Conventions

- Primary key는 UUID를 기본으로 한다.
- 모든 주요 테이블은 `created_at`, `updated_at`을 가진다.
- 삭제는 기본적으로 soft delete를 검토한다. 초기 MVP에서는 중요한 사용자 데이터에 `deleted_at`을 둔다.
- 외래키는 가능한 한 명시적으로 둔다.
- JSONB는 스키마 변화가 잦은 보조 정보에만 사용한다.
- 금액/점수/거리처럼 계산되는 값은 numeric 또는 integer를 명시적으로 선택한다.
- visibility enum:
  - `private`
  - `link_only`
  - `public`
  - `followers`

## 3. Entity Overview

```text
users
  ├─ user_profiles
  ├─ source_files
  ├─ upload_reviews
  ├─ rounds
  │    ├─ holes
  │    │    └─ shots
  │    ├─ round_metrics
  │    ├─ shot_values
  │    └─ insights
  ├─ practice_plans
  │    └─ practice_diary_entries
  ├─ round_goals
  │    └─ goal_evaluations
  ├─ shares
  ├─ llm_threads
  │    └─ llm_messages
  └─ post-MVP embeddings
```

## 4. Core Tables

### 4.1 users

Stores account identity.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| email | citext unique not null | case-insensitive |
| password_hash | text not null | email/password hash; Google OAuth users receive an opaque generated password hash |
| display_name | text not null | |
| handle | citext unique nullable | post-MVP public profile URL |
| avatar_url | text nullable | |
| role | text not null | `user`, `admin` |
| status | text not null | `active`, `disabled`, `deleted` |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |
| deleted_at | timestamptz nullable | |

Indexes:

- unique `(email)`
- unique `(handle)` where handle is not null
- `(status)`

### 4.2 user_profiles

Stores profile and defaults.

| Column | Type | Notes |
| --- | --- | --- |
| user_id | uuid pk/fk users.id | |
| bio | text nullable | |
| home_course | text nullable | |
| handicap_target | numeric(4,1) nullable | |
| privacy_default | text not null | default `private` |
| share_course_by_default | boolean not null | deprecated; course name is shown for shared/public rounds |
| share_exact_date_by_default | boolean not null | default false |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |

### 4.3 source_files

Stores uploaded original files.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| user_id | uuid fk users.id not null | owner |
| filename | text not null | |
| content_type | text nullable | |
| storage_key | text not null | local path or object key |
| file_size | integer not null | |
| content_hash | text not null | duplicate detection |
| status | text not null | `uploaded`, `parsed`, `committed`, `failed` |
| parse_error | text nullable | |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |
| deleted_at | timestamptz nullable | |

Indexes:

- `(user_id, created_at desc)`
- `(user_id, content_hash)`

### 4.4 upload_reviews

Stores editable parse preview before commit.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| user_id | uuid fk users.id not null | |
| source_file_id | uuid fk source_files.id not null | |
| status | text not null | `pending`, `needs_review`, `ready`, `committed`, `failed` |
| parsed_round | jsonb not null | normalized round preview |
| warnings | jsonb not null | parse warnings |
| user_edits | jsonb not null | edits applied in review UI |
| committed_round_id | uuid nullable | fk rounds.id after commit |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |

Indexes:

- `(user_id, created_at desc)`
- `(source_file_id)`

## 5. Round Tables

### 5.1 courses

Optional normalized course table. MVP can store `course_name` directly on rounds and backfill later.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| name | text not null | |
| region | text nullable | |
| country | text nullable | |
| metadata | jsonb not null | |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |

Indexes:

- `(name)`

### 5.2 rounds

Stores one played round.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| user_id | uuid fk users.id not null | owner |
| source_file_id | uuid fk source_files.id nullable | |
| course_id | uuid fk courses.id nullable | |
| course_name | text not null | denormalized display |
| course_variant | text nullable | course/circuit name |
| play_date | date not null | |
| tee | text nullable | |
| total_score | integer nullable | |
| total_par | integer nullable | |
| score_to_par | integer nullable | |
| hole_count | integer not null | 9, 18, 27 |
| weather | text nullable | |
| target_score | integer nullable | |
| visibility | text not null | default `private` |
| share_course | boolean not null | deprecated; course name is shown for shared/public rounds |
| share_exact_date | boolean not null | |
| social_published_at | timestamptz nullable | set when a round enters `public` or `followers` visibility |
| notes_private | text nullable | never public |
| notes_public | text nullable | public-safe note |
| computed_status | text not null | `pending`, `ready`, `stale`, `failed` |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |
| deleted_at | timestamptz nullable | |

Indexes:

- `(user_id, play_date desc)`
- `(user_id, course_name)`
- `(user_id, visibility)`
- `(visibility, play_date desc)` where visibility = `public`
- `(visibility, social_published_at desc, id desc)` where social_published_at is not null

### 5.3 round_companions

Stores companion names privately. This table is never exposed publicly by default.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| round_id | uuid fk rounds.id not null | |
| user_id | uuid fk users.id not null | owner denormalized |
| name | text not null | |
| created_at | timestamptz not null | |

Indexes:

- `(user_id, name)`
- `(round_id)`

### 5.4 holes

Stores hole-level score data.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| round_id | uuid fk rounds.id not null | |
| user_id | uuid fk users.id not null | owner denormalized |
| hole_number | integer not null | |
| par | integer not null | |
| score | integer nullable | |
| putts | integer nullable | |
| fairway_hit | boolean nullable | par 4/5 tee result if known; upload commit derives this from the first tee shot ending in `F` when explicit data is absent |
| gir | boolean nullable | computed or parsed |
| up_and_down | boolean nullable | |
| sand_save | boolean nullable | |
| penalties | integer not null | default 0 |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |

Constraints:

- unique `(round_id, hole_number)`

Indexes:

- `(user_id, round_id)`

### 5.5 shots

Stores shot-level data.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| round_id | uuid fk rounds.id not null | |
| hole_id | uuid fk holes.id not null | |
| user_id | uuid fk users.id not null | owner denormalized |
| shot_number | integer not null | sequence in hole |
| club | text nullable | raw/display club |
| club_normalized | text nullable | normalized |
| distance | integer nullable | meters or configured unit |
| start_lie | text nullable | tee/fairway/rough/bunker/green/etc |
| end_lie | text nullable | |
| result_grade | text nullable | A/B/C or normalized |
| feel_grade | text nullable | A/B/C |
| penalty_type | text nullable | OB/H/UN/etc |
| penalty_strokes | integer not null | default 0 |
| score_cost | integer not null | default 1 |
| raw_text | text nullable | original line fragment |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |

Constraints:

- unique `(hole_id, shot_number)`

Indexes:

- `(user_id, round_id)`
- `(user_id, club_normalized)`
- `(user_id, start_lie, end_lie)`
- `(user_id, penalty_type)`

## 6. Analytics Tables

### 6.1 round_metrics

Stores precomputed round or aggregate metrics.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| user_id | uuid fk users.id not null | |
| round_id | uuid fk rounds.id nullable | null for user-level aggregate snapshots |
| scope_type | text not null | `round`, `window`, `course`, `comparison` |
| scope_key | text not null | e.g. `last_10`, `course:Sky72` |
| metric_key | text not null | e.g. `gir_rate` |
| metric_value | numeric nullable | |
| metric_text | text nullable | for labels |
| sample_count | integer nullable | |
| metadata | jsonb not null | |
| computed_at | timestamptz not null | |

Indexes:

- `(user_id, round_id)`
- `(user_id, scope_type, scope_key)`
- `(user_id, metric_key)`

### 6.2 expected_score_tables

Stores generated expected value table versions.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| user_id | uuid fk users.id not null | |
| scope_type | text not null | `user`, `global`, `baseline`, `cohort` |
| version | integer not null | |
| min_samples | integer not null | |
| table_json | jsonb not null | expected score lookup |
| source_round_count | integer not null | |
| source_shot_count | integer not null | |
| computed_at | timestamptz not null | |

Constraints:

- unique `(user_id, scope_type, version)`

Indexes:

- `(user_id, computed_at desc)`

Cold-start and fallback policy:

- Primary lookup checks `scope_type = user` first when the user table has enough samples for the requested lookup level.
- If user samples are below `min_samples`, MVP checks `scope_type = global`, then an operator-approved `baseline` table.
- Lookup order is level-first, then scope: `full` user/global/baseline, then `no_par` user/global/baseline, then coarser levels. This keeps a high-sample global exact bucket ahead of a very coarse user-only bucket for new users.
- `scope_type = cohort` is post-MVP unless a clear cohort definition is approved.
- Consumers must persist and expose `expected_lookup_level`, `expected_sample_count`, `expected_source_scope`, and `expected_confidence` so low-confidence shot values are visible in UI and Ask answers.
- Insights generated from fallback-heavy data should usually use `confidence = low` or `medium`, not `high`.

### 6.3 shot_values

Stores strokes gained style values per shot.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| user_id | uuid fk users.id not null | |
| round_id | uuid fk rounds.id not null | |
| shot_id | uuid fk shots.id not null | |
| expected_table_id | uuid fk expected_score_tables.id nullable | |
| shot_category | text not null | off_the_tee/approach/short_game/putting |
| expected_before | numeric nullable | |
| expected_after | numeric nullable | |
| shot_value | numeric nullable | |
| expected_lookup_level | text nullable | full/fallback/etc |
| expected_sample_count | integer nullable | |
| metadata | jsonb not null | |
| computed_at | timestamptz not null | |

Constraints:

- unique `(shot_id, expected_table_id)`

Indexes:

- `(user_id, round_id)`
- `(user_id, shot_category)`
- `(user_id, shot_value)`

### 6.4 insights

Stores deduplicated recommendation and explanation units.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| user_id | uuid fk users.id not null | |
| round_id | uuid nullable | source round when insight is round-specific |
| scope_type | text not null | `round`, `window`, `user` |
| scope_key | text not null | stable scope key such as `all` or `last_10` |
| category | text not null | `score`, `off_the_tee`, `approach`, `short_game`, `putting`, `penalty_impact` |
| root_cause | text not null | deterministic cause label |
| primary_evidence_metric | text not null | metric used for dedupe and dashboard suppression |
| dedupe_key | text not null | stable unique key per user |
| problem | text not null | display text; generated in Korean by default |
| evidence | text not null | display text; generated in Korean by default |
| impact | text not null | display text; generated in Korean by default |
| next_action | text not null | display text; generated in Korean by default |
| confidence | text not null | `low`, `medium`, `high` |
| status | text not null | `active`, `dismissed`, `stale` |
| priority_score | numeric not null | |
| dismissed_at | timestamptz nullable | |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |

Indexes:

- unique `(user_id, dedupe_key)`
- `(user_id, status, priority_score desc)`
- `(user_id, category)`

MVP dedupe policy:

- Dedupe is deterministic and rule-based.
- Candidate insights should include a stable dedupe key derived from category, root cause, and primary evidence metric.
- Dashboard default selection is max 3 active insights ordered by `priority_score`, with duplicate evidence suppressed.
- Advanced semantic clustering or LLM-based dedupe is post-MVP.
- MVP Korean insight text is stored as generated display text. English is supported at selected API
  response boundaries by rendering deterministic templates from structured insight fields; this does
  not require duplicate stored rows.
- Concrete examples and key rules live in `docs/insight_dedupe_v2.md`.

### 6.5 analysis_snapshots

Stores selected filter analysis results for sharing and caching.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| user_id | uuid fk users.id not null | |
| title | text nullable | |
| filter_json | jsonb not null | selected year/window/course/etc |
| summary_json | jsonb not null | computed summary |
| visibility | text not null | default `private` |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |
| deleted_at | timestamptz nullable | |

Indexes:

- `(user_id, created_at desc)`
- `(visibility, created_at desc)` where visibility = `public`

## 7. Practice & Goal Tables

Practice and goals convert analysis into an action loop:

1. Insight identifies a problem and next action.
2. Practice plan turns the next action into scheduled work.
3. Practice diary records what the user discovered while practicing.
4. Round goal defines a measurable target for the next round.
5. Goal evaluation compares the target with the next round's actual data.

All records are private by default and scoped by `user_id`.

### 7.1 practice_plans

Stores planned practice work derived from insights or created manually.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| user_id | uuid fk users.id not null | owner |
| source_insight_id | uuid fk insights.id nullable | insight that suggested the plan |
| title | text not null | short display title |
| purpose | text nullable | why this practice exists |
| category | text not null | `score`, `off_the_tee`, `approach`, `short_game`, `putting`, `penalty_impact`, `mental`, `fitness` |
| root_cause | text nullable | copied from insight when available |
| drill_json | jsonb not null | recommended drills, quantities, notes |
| target_json | jsonb not null | planned duration/reps/sessions |
| scheduled_for | date nullable | planned date or week start |
| status | text not null | `planned`, `in_progress`, `done`, `skipped` |
| completed_at | timestamptz nullable | |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |

Indexes:

- `(user_id, status, scheduled_for)`
- `(user_id, category)`
- `(source_insight_id)`

### 7.2 practice_diary_entries

Stores practice reflections and discoveries. Entries may be linked to a plan, insight, or round, but
can also be standalone.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| user_id | uuid fk users.id not null | owner |
| practice_plan_id | uuid fk practice_plans.id nullable | |
| source_insight_id | uuid fk insights.id nullable | |
| round_id | uuid fk rounds.id nullable | related round if any |
| entry_date | date not null | |
| title | text not null | |
| body | text not null | diary text; private by default, public only when visibility allows |
| category | text nullable | same category set as plans |
| tags | jsonb not null | user tags |
| confidence | text nullable | user-reported `low`, `medium`, `high` |
| mood | text nullable | optional practice context |
| visibility | text not null | default `private`; `private`, `followers`, `public` |
| social_published_at | timestamptz nullable | set when entry enters `public` or `followers` visibility |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |

Indexes:

- `(user_id, entry_date desc)`
- `(user_id, category)`
- `(practice_plan_id)`
- `(visibility, social_published_at desc, id desc)` where social_published_at is not null

### 7.3 round_goals

Stores measurable targets for future rounds. Goals should prefer structured metric rules so they can
be evaluated automatically after a round is committed or recalculated.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| user_id | uuid fk users.id not null | owner |
| source_insight_id | uuid fk insights.id nullable | |
| practice_plan_id | uuid fk practice_plans.id nullable | |
| title | text not null | |
| description | text nullable | |
| category | text not null | same category set as plans |
| metric_key | text not null | e.g. `tee_penalties`, `three_putt_holes`, `score_to_par`, `putts_total` |
| target_operator | text not null | `<=`, `<`, `>=`, `>`, `=`, `between` |
| target_value | numeric nullable | primary threshold |
| target_value_max | numeric nullable | upper bound for `between` |
| target_json | jsonb not null | extensible rule payload |
| applies_to | text not null | `next_round`, `date_range`, `course`, `any_round` |
| due_round_id | uuid fk rounds.id nullable | explicit round target when known |
| due_date | date nullable | |
| status | text not null | `active`, `achieved`, `missed`, `partial`, `not_evaluable`, `cancelled` |
| visibility | text not null | default `private`; `private`, `followers`, `public` |
| social_published_at | timestamptz nullable | set when goal enters `public` or `followers` visibility |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |
| closed_at | timestamptz nullable | |

Indexes:

- `(user_id, status, due_date)`
- `(user_id, category)`
- `(source_insight_id)`
- `(practice_plan_id)`
- `(visibility, social_published_at desc, id desc)` where social_published_at is not null

### 7.4 goal_evaluations

Stores the result of comparing a goal with a round.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| user_id | uuid fk users.id not null | owner |
| goal_id | uuid fk round_goals.id not null | |
| round_id | uuid fk rounds.id nullable | evaluated round |
| evaluation_status | text not null | `achieved`, `missed`, `partial`, `not_evaluable` |
| actual_value | numeric nullable | value read from the round |
| actual_json | jsonb not null | supporting metrics and evidence |
| evaluated_by | text not null | `system`, `user` |
| note | text nullable | |
| evaluated_at | timestamptz not null | |
| created_at | timestamptz not null | |

Indexes:

- `(user_id, evaluated_at desc)`
- `(goal_id, round_id)`
- `(round_id)`

Goal evaluation rules:

- Automatic evaluation should only run for goals with a supported `metric_key`.
- Unsupported or ambiguous goals return `not_evaluable` and can be manually evaluated by the user.
- Evaluations must use the owner-scoped round data and never inspect another user's rounds.
- A goal can have multiple evaluations if the user intentionally checks it against multiple rounds,
  but `applies_to = next_round` should close after the first eligible evaluation.

## 8. Sharing & Social Tables

### 8.1 shares

Stores link-only share tokens.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| owner_id | uuid fk users.id not null | |
| resource_type | text not null | `round`, `analysis_snapshot` |
| resource_id | uuid not null | |
| token | text unique not null | random opaque token |
| visibility | text not null | usually `link_only` |
| expires_at | timestamptz nullable | |
| access_count | integer not null | default 0 |
| created_at | timestamptz not null | |
| revoked_at | timestamptz nullable | |

Indexes:

- `(owner_id, created_at desc)`
- unique `(token)`

### 8.2 follows

Stores directional follow relationships.

| Column | Type | Notes |
| --- | --- | --- |
| follower_id | uuid fk users.id | requester |
| following_id | uuid fk users.id | target |
| status | text not null | `pending`, `accepted`, `blocked` |
| requested_at | timestamptz not null | |
| accepted_at | timestamptz nullable | |
| blocked_at | timestamptz nullable | |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |

Constraints:

- primary key `(follower_id, following_id)`

### 8.3 round_likes

Stores like reactions on round visibility posts.

| Column | Type | Notes |
| --- | --- | --- |
| round_id | uuid fk rounds.id not null | |
| user_id | uuid fk users.id not null | liker |
| created_at | timestamptz not null | |

Constraints:

- primary key `(round_id, user_id)`

### 8.4 round_comments

Stores comments on visible rounds.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| round_id | uuid fk rounds.id not null | |
| user_id | uuid fk users.id not null | author |
| parent_comment_id | uuid fk round_comments.id nullable | optional thread |
| body | text not null | |
| status | text not null | `active`, `deleted`, `hidden` |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |
| deleted_at | timestamptz nullable | |

Indexes:

- `(round_id, created_at desc)`
- `(user_id, created_at desc)`

### 8.5 public_feed_items

Post-MVP optional materialized feed table. The first social feed implementation should query
`rounds` directly with `social_published_at` keyset pagination. Add this table only when dynamic
queries become too slow or the product needs non-round feed resources.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| owner_id | uuid fk users.id not null | |
| resource_type | text not null | `round`, `analysis_snapshot` |
| resource_id | uuid not null | |
| title | text not null | |
| summary | text not null | |
| preview_json | jsonb not null | public-safe data |
| published_at | timestamptz not null | |
| hidden_at | timestamptz nullable | |

Indexes:

- `(published_at desc)` where hidden_at is null
- `(owner_id, published_at desc)`

## 9. Ask, LLM & Embedding Tables

### 9.1 llm_threads

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| user_id | uuid fk users.id not null | |
| title | text nullable | |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |
| deleted_at | timestamptz nullable | |

Indexes:

- `(user_id, updated_at desc)`

### 9.2 llm_messages

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| thread_id | uuid fk llm_threads.id not null | |
| user_id | uuid fk users.id not null | owner denormalized |
| role | text not null | `user`, `assistant`, `system` |
| content | text not null | |
| citations | jsonb not null | |
| model | text nullable | |
| latency_ms | integer nullable | |
| prompt_tokens | integer nullable | if available |
| completion_tokens | integer nullable | if available |
| error_code | text nullable | |
| created_at | timestamptz not null | |

Indexes:

- `(thread_id, created_at)`
- `(user_id, created_at desc)`

### 9.3 embedding_documents

Post-MVP. Stores text chunks to embed.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| owner_id | uuid fk users.id not null | |
| source_type | text not null | `round`, `shot`, `insight`, `note`, `upload_text` |
| source_id | uuid not null | |
| visibility | text not null | copied from source |
| content | text not null | chunk text |
| content_hash | text not null | |
| metadata | jsonb not null | filters/citation info |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |

Indexes:

- `(owner_id, source_type, source_id)`
- `(owner_id, content_hash)`
- `(visibility)`

### 9.4 embeddings

Post-MVP. Requires pgvector extension.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| document_id | uuid fk embedding_documents.id not null | |
| owner_id | uuid fk users.id not null | denormalized for filtering |
| model | text not null | embedding model |
| dimensions | integer not null | |
| vector | vector | dimension depends on model |
| created_at | timestamptz not null | |

Constraints:

- unique `(document_id, model)`

Indexes:

- `(owner_id, model)`
- vector index on `vector` using ivfflat or hnsw after dimension is fixed.

## 10. Admin & Audit Tables

### 10.1 audit_logs

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| actor_user_id | uuid fk users.id nullable | |
| action | text not null | |
| resource_type | text nullable | |
| resource_id | uuid nullable | |
| ip_address | inet nullable | |
| user_agent | text nullable | |
| metadata | jsonb not null | |
| created_at | timestamptz not null | |

Indexes:

- `(actor_user_id, created_at desc)`
- `(resource_type, resource_id)`

### 10.2 reports

For public content reports.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| reporter_id | uuid fk users.id nullable | |
| resource_type | text not null | |
| resource_id | uuid not null | |
| reason | text not null | |
| status | text not null | `open`, `reviewed`, `dismissed`, `actioned` |
| metadata | jsonb not null | |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |

Indexes:

- `(status, created_at desc)`
- `(resource_type, resource_id)`

## 11. Visibility Rules

### 11.1 Private

- Only owner and admin can access.
- Admin access must be logged.
- LLM can use data only for the owner.

### 11.2 Link-only

- Resource can be read via valid share token.
- Search engines should not index link-only pages.
- Link-only pages use public-safe serializer.
- LLM access through shared resource is read-only and limited to the shared scope if implemented.

### 11.3 Public

- Resource can appear in public search.
- Public-safe serializer removes private fields.
- Public resource may later generate `public_feed_items`.

### 11.4 Followers

- Requires accepted follow relationship.
- Follower-visible rounds can be read by accepted followers.
- Followed users' rounds can be surfaced in companion compare and social lists.

### 11.5 Social Actions

- Likes and comments require accepted follow relationship.
- First implementation limits social actions to follow-scoped visibility, even on public rounds.
- Owners and admins can moderate or remove comments.

### 11.6 Social Feed

- The initial feed is chronological, not ranked.
- Logged-out feed includes only `visibility = public`.
- Logged-in feed includes `visibility = public` plus `visibility = followers` where the viewer has
  an accepted follow relationship to the round owner.
- `private` and `link_only` rounds are never feedable.
- Public/follower-visible practice diary entries and round goals can also be feed items.
- `social_published_at` is set when a round, diary entry, or goal becomes `public` or `followers`,
  retained when moving between those two states, and cleared when moving back to `private`.
- Existing public/followers rows can backfill `social_published_at` from `updated_at` or `created_at`.
- Feed cards use a stricter public-safe serializer than round detail and never expose companions,
  private notes, source file metadata, raw upload text, shot raw text, link-only tokens, or private
  LLM/practice data.
- Public/follower-visible rounds always expose `course_name`; exact `play_date` still follows
  `share_exact_date`.
- Public/follower-visible round feed cards include at most one public-safe top insight.

## 12. Public-Safe Serialization

Never expose:

- `round_companions`
- `notes_private`
- `source_files.storage_key`
- original upload file content
- exact tee time
- private upload warnings containing raw private text
- private LLM messages
- private practice diary entries
- private practice plans and goals

Expose only if allowed:

- course name for shared/public/follower-visible rounds
- exact play date
- public note
- profile fields
- public/follower-visible practice diary title/body/tags/category
- public/follower-visible round goal title/description/normalized target/status

Always safe to expose for public rounds:

- score summary
- aggregate rates
- public insight title/summary
- anonymized shot category counts

## 13. v1 to v2 Mapping

Expected v1 source concepts:

- `rounds` -> `rounds`
- `holes` -> `holes`
- `shots` -> `shots`
- `coplayers` -> `round_companions`
- parser raw file -> `source_files`, `upload_reviews`
- route-built trend summaries -> `round_metrics`, `analysis_snapshots`
- `expected_value.py` output -> `expected_score_tables`
- `strokes_gained.py` output -> `shot_values`
- `recommendations.py` output -> `insights`

Migration notes:

- v1 has no true multi-user ownership. Initial import must assign all records to a selected owner user.
- Existing companion strings should be split into `round_companions`.
- v1 computed data should be recalculated in v2 rather than blindly copied.
- Original text files in repo-root `data/<year>` should be re-imported as validation fixtures where possible.

## 14. Suggested Initial Alembic Order

1. extensions: `uuid-ossp` or app-generated UUID, `citext`. Add `vector` only when post-MVP RAG starts.
2. users, user_profiles.
3. source_files, upload_reviews.
4. courses, rounds, round_companions.
5. holes, shots.
6. round_metrics, expected_score_tables, shot_values, insights, analysis_snapshots.
7. practice_plans, practice_diary_entries, round_goals, goal_evaluations.
8. shares.
9. llm_threads, llm_messages.
10. post-MVP: public_feed_items, embedding_documents, embeddings.
11. audit_logs, reports.

## 15. Open Decisions

- UUID generation in application vs PostgreSQL.
- Whether `course_name` remains denormalized only for MVP.
- Whether `round_metrics` should store all metrics row-wise or selected metrics in typed columns.
- Whether soft delete should be universal or limited to user-facing entities.
- Whether private LLM messages should be included in account export/delete workflows.
- Which goal metric keys are supported in the first automatic evaluator.
- Whether practice diary entries should be included in Ask context by default or behind a setting.
- Exact pgvector dimension, determined by the post-MVP embedding model.
