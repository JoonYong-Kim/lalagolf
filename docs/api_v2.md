# GolfRaiders v2 API Proposal

## 1. API Goals

- Next.js frontend이 사용할 안정적인 JSON API를 제공한다.
- 모든 private resource는 현재 사용자 scope를 강제한다.
- 라운드 업로드, 분석 조회, 공유, Ask 질의를 분리된 endpoint로 제공한다.
- 비용이 큰 분석 작업은 background job으로 처리한다. embedding 작업은 post-MVP RAG에서 추가한다.
- public/link-only 응답은 private 응답과 serializer를 분리한다.

## 2. Conventions

- Base path: `/api/v1`
- Content type: `application/json`
- Auth: secure httpOnly cookie session 또는 bearer token. 최종 선택 전까지 문서에서는 `Authorization` 또는 cookie를 모두 허용 가능한 것으로 둔다.
- IDs: UUID string.
- Date: ISO 8601.
- Pagination: cursor-based.
- Error envelope:

```json
{
  "error": {
    "code": "round_not_found",
    "message": "Round not found",
    "details": {}
  }
}
```

- Success response envelope:

```json
{
  "data": {},
  "meta": {}
}
```

List response:

```json
{
  "data": [],
  "meta": {
    "next_cursor": "cursor-value",
    "has_more": true
  }
}
```

## 3. Auth

### POST /auth/register

Creates a user account.

Request:

```json
{
  "email": "user@example.com",
  "password": "secret",
  "display_name": "Lala Golfer"
}
```

Response:

```json
{
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "display_name": "Lala Golfer",
      "role": "user"
    }
  }
}
```

### POST /auth/login

Request:

```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

Response:

```json
{
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "display_name": "Lala Golfer",
      "role": "user"
    }
  }
}
```

### POST /auth/logout

Invalidates current session.

### GET /auth/google/start

Starts Google OAuth login. Requires `GOOGLE_OAUTH_CLIENT_ID` and
`GOOGLE_OAUTH_CLIENT_SECRET` to be configured. The API sets a short-lived OAuth state cookie and
redirects to Google.

### GET /auth/google/callback

Handles Google OAuth callback, verifies the state cookie and Google token audience, creates or
reuses an active user with a verified Google email, creates a session cookie, and redirects to
`WEB_BASE_URL` `/upload`.

### GET /me

Returns current user and profile.

### PATCH /me/profile

Updates profile defaults.

Request:

```json
{
  "display_name": "Lala",
  "handle": "lala",
  "bio": "Weekend golfer",
  "privacy_default": "private",
  "share_course_by_default": false,
  "share_exact_date_by_default": false
}
```

## 4. Logged-out Entry

MVP logged-out entry can be rendered by Next.js without a dedicated API. Full public home, sample analysis, and public round lists are post-MVP.

### GET /public/home

Post-MVP. Returns data for logged-out public home.

Returns data for logged-out home.

Response:

```json
{
  "data": {
    "sample_dashboard": {
      "score_trend": [],
      "insights": [],
      "recent_rounds": []
    },
    "public_rounds": []
  }
}
```

### GET /sample-analysis

Post-MVP.

Returns static or seeded sample analysis.

### GET /public/rounds

Post-MVP.

Returns public-safe round cards.

Query:

- `cursor`
- `limit`

## 5. Uploads

### POST /uploads/round-file

Uploads a text round file. This endpoint uses multipart form data.

Request fields:

- `file`

Response:

```json
{
  "data": {
    "source_file_id": "uuid",
    "upload_review_id": "uuid",
    "status": "pending",
    "job_id": "uuid"
  }
}
```

### GET /uploads/{upload_review_id}/review

Returns parsed preview and warnings.

Response:

```json
{
  "data": {
    "id": "uuid",
    "status": "needs_review",
    "parsed_round": {
      "play_date": "2026-04-10",
      "course_name": "Sky72",
      "holes": [],
      "shots": []
    },
    "warnings": [
      {
        "code": "unknown_club",
        "message": "Unknown club value",
        "path": "holes[3].shots[1].club"
      }
    ],
    "user_edits": {}
  }
}
```

### PATCH /uploads/{upload_review_id}/review

Saves user edits before commit.

Request:

```json
{
  "user_edits": {
    "holes.3.shots.1.club": "7I"
  }
}
```

### POST /uploads/{upload_review_id}/commit

Commits parsed data into rounds/holes/shots.

Request:

```json
{
  "visibility": "private",
  "share_course": false,
  "share_exact_date": false
}
```

Response:

```json
{
  "data": {
    "round_id": "uuid",
    "analysis_job_id": "uuid"
  }
}
```

## 6. Jobs

### GET /jobs/{job_id}

Returns background job status.

Response:

```json
{
  "data": {
    "id": "uuid",
    "type": "recalculate_round_metrics",
    "status": "running",
    "progress": 0.6,
    "error": null
  }
}
```

Statuses:

- `queued`
- `running`
- `succeeded`
- `failed`
- `cancelled`

## 7. Rounds

### GET /rounds

Returns private round list for current user.

Query:

- `cursor`
- `limit`
- `year`
- `course`
- `companion`
- `visibility`
- `sort`, default `play_date_desc`

Response:

```json
{
  "data": [
    {
      "id": "uuid",
      "play_date": "2026-04-10",
      "course_name": "Sky72",
      "total_score": 82,
      "score_to_par": 10,
      "gir_rate": 0.44,
      "putts": 32,
      "penalty_strokes": 2,
      "visibility": "private"
    }
  ],
  "meta": {
    "next_cursor": null,
    "has_more": false
  }
}
```

### POST /rounds

Creates a round manually. MVP can delay this if upload-only is enough.

### GET /rounds/{round_id}

Returns round detail for owner.

Response includes:

- round summary
- holes
- shots
- metrics
- shot_values
- insights

### PATCH /rounds/{round_id}

Updates metadata and privacy fields.

Request:

```json
{
  "course_name": "Sky72",
  "play_date": "2026-04-10",
  "visibility": "link_only",
  "share_course": true,
  "share_exact_date": false,
  "notes_private": "Driver felt unstable"
}
```

### DELETE /rounds/{round_id}

Soft-deletes a round.

### POST /rounds/{round_id}/recalculate

Queues analytics recalculation.

Response:

```json
{
  "data": {
    "job_id": "uuid"
  }
}
```

## 8. Holes & Shots

### GET /rounds/{round_id}/holes

Returns hole list.

### PATCH /holes/{hole_id}

Updates hole-level fields.

### GET /rounds/{round_id}/shots

Returns all shots in a round.

### PATCH /shots/{shot_id}

Updates shot-level fields and marks analytics stale.

Request:

```json
{
  "club": "D",
  "distance": 220,
  "start_lie": "tee",
  "end_lie": "rough",
  "result_grade": "C",
  "penalty_type": "OB"
}
```

## 9. Analytics

### GET /analytics/summary

Returns dashboard summary.

Query:

- `window`, e.g. `last_5`, `last_10`, `all`
- `locale`: optional `ko` or `en`, default `ko`. Applies to insight text fields only.

Response:

```json
{
  "data": {
    "kpis": {
      "avg_score": 82.4,
      "avg_gir": 0.42,
      "avg_putts": 32.1,
      "avg_penalty_strokes": 1.8
    },
    "score_trend": [],
    "priority_insights": []
  }
}
```

### GET /analytics/trends

Returns analysis workspace data.

Query:

- `year`
- `window`
- `course`
- `companion`
- `round_ids`
- `tab`: `score`, `tee`, `approach`, `short_game`, `putting`
- `locale`: optional `ko` or `en`, default `ko`. Applies to insight text fields only.

### GET /analytics/rounds/{round_id}

Returns detailed analytics for one round.

Query:

- `locale`: optional `ko` or `en`, default `ko`. Applies to insight text fields only.

### GET /analytics/compare

Returns shot-value comparison rows grouped across the current user's analytics data.

Query:

- `group_by`: `category` or `club`, default `category`

Note: the web round-comparison page (`/rounds/compare`) is not backed by this endpoint. It loads
selected round details and compares scorecard-derived metrics client-side: score, putts, putts per
hole, 3-putt holes, GIR count/rate, fairway hit rate, penalties, penalty holes, birdie-or-better,
par, bogey, and double-bogey-or-worse.

## 10. Insights

### GET /insights

Returns deduplicated insights.

Query:

- `status`
- `locale`: optional `ko` or `en`, default `ko`

Insight text fields use the MVP unit shape: `problem`, `evidence`, `impact`, `next_action`, and
`confidence`. Korean is the default stored/generated language. For `locale=en`, the API renders
supported deterministic MVP insight templates into English at the response boundary without changing
stored rows.

### PATCH /insights/{insight_id}

Updates insight status.

Query:

- `locale`: optional `ko` or `en`, default `ko`

Request:

```json
{
  "status": "dismissed"
}
```

## 11. Practice Plans, Diary, and Goals

These endpoints close the loop from analysis to action:

- create a practice plan from an insight,
- record practice discoveries in a private diary,
- define a measurable next-round goal,
- evaluate the goal after a round is committed or recalculated.

All endpoints are owner-scoped and require authentication.

### GET /practice/plans

Lists practice plans.

Query:

- `status`: optional `planned`, `in_progress`, `done`, `skipped`
- `category`
- `from`
- `to`

### POST /practice/plans

Creates a practice plan. `source_insight_id` is optional; when supplied, the API may prefill category,
root cause, and suggested drills from the insight.

Request:

```json
{
  "source_insight_id": "uuid",
  "title": "Reduce 3-putt risk",
  "purpose": "Improve lag-putt distance control before the next round.",
  "category": "putting",
  "scheduled_for": "2026-05-10",
  "drill_json": {
    "drills": [
      {
        "name": "6-12m lag putting",
        "quantity": "30 minutes"
      },
      {
        "name": "1-2m finish putts",
        "quantity": "50 reps"
      }
    ]
  },
  "target_json": {
    "sessions": 2,
    "minutes": 60
  }
}
```

Response:

```json
{
  "data": {
    "id": "uuid",
    "status": "planned",
    "category": "putting",
    "title": "Reduce 3-putt risk"
  }
}
```

### PATCH /practice/plans/{plan_id}

Updates plan content or status.

Request:

```json
{
  "status": "done",
  "completed_at": "2026-05-10T09:30:00Z"
}
```

### GET /practice/diary

Lists private practice diary entries.

Query:

- `practice_plan_id`
- `category`
- `from`
- `to`

### POST /practice/diary

Creates a diary entry.

Request:

```json
{
  "practice_plan_id": "uuid",
  "entry_date": "2026-05-10",
  "title": "Lag putting discovery",
  "body": "8m uphill putts were consistently short. 6m downhill putts needed a smaller stroke than expected.",
  "category": "putting",
  "tags": ["lag-putt", "distance-control"],
  "confidence": "medium"
}
```

### GET /goals

Lists round goals.

Query:

- `status`: optional `active`, `achieved`, `missed`, `partial`, `not_evaluable`, `cancelled`
- `category`

### POST /goals

Creates a measurable goal for a future round.

Request:

```json
{
  "source_insight_id": "uuid",
  "practice_plan_id": "uuid",
  "title": "Keep 3-putts to one or fewer",
  "category": "putting",
  "metric_key": "three_putt_holes",
  "target_operator": "<=",
  "target_value": 1,
  "applies_to": "next_round",
  "due_date": "2026-05-20"
}
```

Supported first-pass `metric_key` candidates:

- `score_to_par`
- `total_score`
- `putts_total`
- `three_putt_holes`
- `penalties_total`
- `tee_penalties`
- `gir_count`
- `fairway_miss_count`

### PATCH /goals/{goal_id}

Updates goal content or status.

### POST /goals/{goal_id}/evaluate

Evaluates a goal against a round. If `round_id` is omitted, the API may choose the first eligible
round after the goal was created for `applies_to = next_round`.

Request:

```json
{
  "round_id": "uuid"
}
```

Response:

```json
{
  "data": {
    "goal_id": "uuid",
    "round_id": "uuid",
    "evaluation_status": "achieved",
    "actual_value": 1,
    "actual_json": {
      "metric_key": "three_putt_holes",
      "target": "<= 1"
    },
    "evaluated_by": "system"
  }
}
```

### POST /goals/{goal_id}/manual-evaluation

Creates or overrides a manual evaluation for goals that are qualitative or not automatically
evaluable.

Request:

```json
{
  "round_id": "uuid",
  "evaluation_status": "partial",
  "note": "No tee penalty, but two recovery shots still came from conservative misses."
}
```

## 12. Sharing

### POST /shares

Creates or returns a link-only share.

Request:

```json
{
  "resource_type": "round",
  "resource_id": "uuid",
  "expires_at": null
}
```

Response:

```json
{
  "data": {
    "share_id": "uuid",
    "token": "opaque-token",
    "url": "https://example.com/s/opaque-token"
  }
}
```

### PATCH /shares/{share_id}

Revokes or updates share.

### GET /shares

Lists current user's shares.

### GET /s/{token}

Public route, not under `/api/v1` if rendered by Next.js. API equivalent can be:

`GET /api/v1/shared/{token}`

Returns public-safe serialized resource. For shared scorecards, `insights` contains at most one
public-safe top issue for that round.

Query:

- `locale`: optional `ko` or `en`, default `ko`. Applies to shared insight text fields only.

Response excerpt:

```json
{
  "data": {
    "title": "Weekend round",
    "round": {
      "course_name": "Shared course",
      "play_date": null,
      "play_month": "2026-04",
      "total_score": 91
    },
    "holes": [],
    "metrics": {},
    "insights": [
      {
        "category": "penalty_impact",
        "problem": "페널티가 이 라운드의 최우선 이슈입니다.",
        "evidence": "스코어카드에 페널티가 총 2타 기록됐습니다.",
        "impact": "페널티는 즉시 1타 이상을 더하고 다음 샷 선택까지 어렵게 만듭니다.",
        "next_action": "공유된 라운드의 페널티 홀부터 티샷 목표와 세이프 클럽을 다시 정하세요.",
        "confidence": "medium",
        "priority_score": 2.0
      }
    ]
  }
}
```

## 13. Social

Post-MVP. Public profiles, public rounds, feed, follows, comments, and likes are not part of the MVP.

### GET /users/{handle}

Returns public-safe profile.

### GET /users/{handle}/rounds

Returns public rounds for a user.

### GET /feed

Returns public or following feed.

### POST /follow

MVP 이후 가능.

Request:

```json
{
  "user_id": "uuid"
}
```

## 14. Ask GolfRaiders

MVP Ask uses structured SQL/metric retrieval plus deterministic answer templates. Ollama may be used only to improve wording. Embedding/RAG retrieval is post-MVP.

### POST /chat/threads

Creates a chat thread.

Request:

```json
{
  "title": "Driver analysis"
}
```

### GET /chat/threads

Lists current user's chat threads.

### GET /chat/threads/{thread_id}

Returns messages.

### POST /chat/threads/{thread_id}/messages

Asks a question.

Request:

```json
{
  "message": "최근 10라운드에서 드라이버가 스코어에 얼마나 영향을 줬어?",
  "filters": {
    "window": "last_10"
  },
  "stream": false
}
```

Response:

```json
{
  "data": {
    "message_id": "uuid",
    "content": "최근 10라운드에서 드라이버 관련 페널티가...",
    "citations": [
      {
        "type": "round",
        "id": "uuid",
        "label": "2026-04-10 Sky72",
        "metric": "driver_penalty_rate"
      }
    ],
    "evidence": {
      "round_count": 10,
      "shot_count": 42,
      "filters": {
        "window": "last_10"
      }
    }
  }
}
```

### POST /chat/query-plan

Optional debug/admin endpoint. Returns interpreted filters and planned data sources.

## 15. Profile & Settings

### GET /settings/privacy

Returns privacy settings.

### PATCH /settings/privacy

Updates defaults.

Request:

```json
{
  "privacy_default": "private",
  "share_course_by_default": false,
  "share_exact_date_by_default": false
}
```

### POST /account/delete

Starts account deletion flow.

## 16. Admin

All admin endpoints require admin role.

### GET /admin/uploads/errors

Returns failed upload parse reviews for operational triage.

The following admin endpoints are post-MVP placeholders and are not part of the current
implementation contract:

- `GET /admin/users`
- `GET /admin/reports`
- `PATCH /admin/reports/{report_id}`
- `GET /admin/jobs`
- `GET /admin/llm/errors`

## 17. Common Error Codes

- `unauthorized`
- `forbidden`
- `validation_error`
- `not_found`
- `round_not_found`
- `upload_not_found`
- `upload_not_ready`
- `parse_failed`
- `analysis_not_ready`
- `job_not_found`
- `share_not_found`
- `share_revoked`
- `llm_unavailable`
- `llm_timeout`
- `rate_limited`

## 18. Authorization Matrix

| Resource | Owner | Link token | Public | Other logged-in user | Admin |
| --- | --- | --- | --- | --- | --- |
| private round | read/write | no | no | no | audited read |
| link-only round | read/write | public-safe read | no feed | no | audited read |
| public round | post-MVP | post-MVP | post-MVP | post-MVP | audited read |
| source file | read/write | no | no | no | audited read |
| private chat | read/write | no | no | no | audited read only if needed |
| public profile | post-MVP | post-MVP | post-MVP | post-MVP | audited read/write moderation |

## 19. Rate Limits

Suggested initial limits:

- login: strict per IP/email.
- upload: per user per hour.
- chat: per user per minute and per day.
- public feed: post-MVP, per IP.
- share token access: per IP/token.

## 20. Open Decisions

- Final auth mechanism: cookie session vs JWT.
- Supported MVP Ask question set.
- Whether manual round creation is MVP or upload-only.
- Whether API response envelope should be used for all responses including file upload.
