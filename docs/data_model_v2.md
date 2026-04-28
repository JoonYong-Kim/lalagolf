# LalaGolf v2 Data Model Proposal

## 1. Data Model Goals

- 모든 사용자 데이터를 명확한 owner scope로 분리한다.
- 라운드, 홀, 샷 원본 데이터와 계산된 분석 결과를 구분한다.
- 분석 결과는 재계산 가능하게 유지하고, 원본 데이터는 보존한다.
- 공유/공개 화면에서 민감 정보가 노출되지 않도록 visibility와 serializer 기준을 명확히 한다.
- LLM/RAG를 위해 정형 데이터와 embedding 문서를 함께 관리한다.

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
  ├─ shares
  ├─ llm_threads
  │    └─ llm_messages
  └─ embeddings
```

## 4. Core Tables

### 4.1 users

Stores account identity.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| email | citext unique not null | case-insensitive |
| password_hash | text nullable | nullable if OAuth-only |
| display_name | text not null | |
| handle | citext unique nullable | public profile URL |
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
| share_course_by_default | boolean not null | default false |
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
| share_course | boolean not null | |
| share_exact_date | boolean not null | |
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
| fairway_hit | boolean nullable | par 4/5 tee result if known |
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
| scope_type | text not null | `user`, `global`, `cohort` |
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
| scope_type | text not null | `round`, `window`, `user` |
| scope_id | uuid nullable | round id or snapshot id |
| insight_type | text not null | `weakness`, `strength`, `practice`, `warning` |
| category | text nullable | tee/approach/short_game/putting |
| title | text not null | |
| summary | text not null | |
| impact | text nullable | |
| next_action | text nullable | |
| priority_score | numeric nullable | |
| confidence | text not null | `low`, `medium`, `high` |
| evidence | jsonb not null | metric references |
| status | text not null | `active`, `dismissed`, `stale` |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |

Indexes:

- `(user_id, scope_type, scope_id)`
- `(user_id, status, priority_score desc)`
- `(user_id, category)`

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

## 7. Sharing & Social Tables

### 7.1 shares

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

### 7.2 follows

MVP 이후 도입 가능.

| Column | Type | Notes |
| --- | --- | --- |
| follower_id | uuid fk users.id | |
| following_id | uuid fk users.id | |
| status | text not null | `pending`, `accepted`, `blocked` |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |

Constraints:

- primary key `(follower_id, following_id)`

### 7.3 public_feed_items

Optional materialized feed table.

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

## 8. LLM & Embedding Tables

### 8.1 llm_threads

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

### 8.2 llm_messages

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

### 8.3 embedding_documents

Stores text chunks to embed.

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

### 8.4 embeddings

Requires pgvector extension.

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

## 9. Admin & Audit Tables

### 9.1 audit_logs

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

### 9.2 reports

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

## 10. Visibility Rules

### 10.1 Private

- Only owner and admin can access.
- Admin access must be logged.
- LLM can use data only for the owner.

### 10.2 Link-only

- Resource can be read via valid share token.
- Search engines should not index link-only pages.
- Link-only pages use public-safe serializer.
- LLM access through shared resource is read-only and limited to the shared scope if implemented.

### 10.3 Public

- Resource can appear on public profile/feed.
- Public-safe serializer removes private fields.
- Public resource may generate `public_feed_items`.

### 10.4 Followers

- MVP 이후.
- Requires accepted follow relationship.

## 11. Public-Safe Serialization

Never expose:

- `round_companions`
- `notes_private`
- `source_files.storage_key`
- original upload file content
- exact tee time
- private upload warnings containing raw private text
- private LLM messages

Expose only if allowed:

- course name
- exact play date
- public note
- profile fields

Always safe to expose for public rounds:

- score summary
- aggregate rates
- public insight title/summary
- anonymized shot category counts

## 12. v1 to v2 Mapping

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
- Original text files in `data/<year>` should be re-imported as validation fixtures where possible.

## 13. Suggested Initial Alembic Order

1. extensions: `uuid-ossp` or app-generated UUID, `citext`, `vector`.
2. users, user_profiles.
3. source_files, upload_reviews.
4. courses, rounds, round_companions.
5. holes, shots.
6. round_metrics, expected_score_tables, shot_values, insights, analysis_snapshots.
7. shares, follows, public_feed_items.
8. llm_threads, llm_messages, embedding_documents, embeddings.
9. audit_logs, reports.

## 14. Open Decisions

- UUID generation in application vs PostgreSQL.
- Whether `course_name` remains denormalized only for MVP.
- Whether `round_metrics` should store all metrics row-wise or selected metrics in typed columns.
- Exact pgvector dimension, determined by the embedding model.
- Whether soft delete should be universal or limited to user-facing entities.
- Whether private LLM messages should be included in account export/delete workflows.
