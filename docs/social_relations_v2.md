# GolfRaiders v2 Social & Visibility

이 문서는 라운드 공개, 팔로우, 지인 공개 스코어카드, 댓글/좋아요, 동반 라운드 비교에 대한 현재 설계 원칙을 정리한다.

## 1. 결정된 범위

- 업로드 시 라운드는 항상 private으로 저장한다.
- 공개 범위는 라운드 상세에서 나중에 바꾼다.
- 공개 범위는 `private`, `followers`, `public` 3단계다.
- link-only 공유는 별도 메커니즘으로 유지한다.
- public 라운드는 누구나 검색해서 볼 수 있다.
- follow가 허용된 지인 범위에서만 댓글과 좋아요를 허용한다.
- 동반자 비교는 접근 가능한 다른 라운드와 내 라운드를 기존 라운드 비교 화면처럼 선택해 비교하는 방식으로 일반화한다.

## 2. Visibility Model

### 2.1 Private

- 소유자와 관리자만 읽을 수 있다.
- 업로드 직후 기본 상태다.

### 2.2 Followers

- 팔로우 관계가 `accepted`인 사용자만 읽을 수 있다.
- 지인 공개 라운드의 댓글과 좋아요도 이 범위에서만 허용한다.

### 2.3 Public

- 누구나 검색할 수 있다.
- 비로그인 사용자가 읽을 수 있다.
- 다만 댓글과 좋아요는 follow 허용 관계 안에서만 허용한다.

### 2.4 Link-only

- 공개 범위와 무관한 토큰 기반 별도 공유다.
- link-only는 검색 노출 대상이 아니다.

## 3. Follow Model

팔로우는 방향성 있는 관계다.

- follower: 요청을 보낸 사용자
- following: 요청을 받는 사용자
- status: `pending`, `accepted`, `blocked`

초기 구현에서는 상호 팔로우가 아니라 방향성 follow만 필요하다.
허용된 follow 관계는 다음 용도로 사용한다.

- 지인 공개 라운드 접근
- 댓글 작성
- 좋아요 작성
- 접근 가능한 라운드 비교 후보 노출

## 4. Comparable Round Compare

비교 기능은 companion 전용이 아니라, 사용자가 접근 가능한 다른 라운드와 자신의 라운드를 비교하는 일반 기능으로 본다.

- 라운드 상세에는 `동반자 비교` 버튼을 둔다.
- companion 정보가 있으면 버튼이 활성화된다.
- 버튼을 누르면 companion 정보와 접근 가능 범위를 바탕으로 비교 가능한 라운드 후보를 보여준다.
- 사용자는 후보 중에서 비교 대상을 선택한다.
- 기본 상호작용은 기존 라운드 비교 UI처럼 두 라운드를 선택해서 비교하는 방식이다.
- companion 정보는 비교 후보를 좁히는 보조 정보로만 사용한다.
- 회원 확인은 사용자가 명시적으로 저장한 `companion_name -> companion_user_id` 매핑을 기준으로 한다.
- companion 매칭은 매핑된 회원의 라운드 중 동일한 코스, 동일한 날짜, 기준 라운드에 시간이 있으면 동일한 시간을 기준으로 한다.
- 최종적으로 비교 가능한지는 해당 라운드의 공개 기준을 따른다.
- 공개/공유/피드 응답에는 companion 이름이나 계정 매핑 정보를 포함하지 않는다.

## 5. Likes & Comments

댓글과 좋아요는 단순한 피드 기능이 아니라, 지인 공개 라운드에 대한 짧은 반응으로 본다.

- 작성 가능 대상: accepted follow 관계에 있는 사용자
- 표시 대상: 라운드 소유자와 허용된 팔로워
- 공개 범위가 public이라도, 첫 구현에서는 follow 관계 밖의 사용자는 반응할 수 없다

이 제한은 스팸과 공개 피드화를 늦추기 위한 것이다.

## 6. Recommended Tables

### 6.1 follows

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
- follower_id != following_id

### 6.2 round_likes

| Column | Type | Notes |
| --- | --- | --- |
| round_id | uuid fk rounds.id | |
| user_id | uuid fk users.id | liker |
| created_at | timestamptz not null | |

Constraints:

- primary key `(round_id, user_id)`

### 6.3 round_comments

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

## 7. Search Strategy

Public scorecards should be searchable without a separate feed.

- query the `rounds` table by `visibility = public`
- filter by course, date, handle, and keyword
- return public-safe serializer only

If search volume grows, a materialized public search index can be added later. The first version does
not require it.

## 8. Social Feed

새 소셜 피드는 공개 라운드와 지인 공개 라운드를 사용자가 아래로 스크롤하면서 보는 화면이다.
MVP의 "복잡한 public feed ranking 제외" 결정은 유지하고, 첫 구현은 **시간순 keyset feed**로 제한한다.

### 8.1 Product Scope

- 로그인 사용자 기본 피드: 내가 볼 수 있는 `public` 라운드 + 내가 accepted follower인 사용자의 `followers` 라운드.
- 비로그인 사용자 피드: `public` 라운드만.
- 내 라운드는 기본 피드에서 제외한다. 별도 옵션 `include_self=true`가 있을 때만 포함한다.
- link-only 라운드는 피드에 절대 노출하지 않는다.
- private 라운드는 소유자 전용 목록(`/rounds`)에만 남긴다.
- 첫 버전은 라운드 카드 중심이다. 댓글/좋아요는 카드의 카운트와 내 반응 상태만 표시하고, 전체 댓글은 라운드 상세에서 본다.
- 공개된 연습 다이어리와 라운드 목표도 별도 소셜 활동 카드로 확장할 수 있다.

### 8.2 Feed Ordering

정렬 기준은 `social_published_at desc, item_id desc`로 둔다.

- `social_published_at`은 라운드가 `public` 또는 `followers`로 전환된 시점이다.
- private에서 public/followers로 처음 전환할 때 현재 시각으로 설정한다.
- public/followers 사이를 전환할 때는 기존 값을 유지한다.
- private으로 되돌릴 때는 `social_published_at = null`로 지운다.
- 기존 데이터 마이그레이션은 공개 상태인 라운드에 대해 `created_at` 또는 `updated_at`을 backfill 값으로 사용한다.

`play_date`는 과거 라운드를 새로 공개했을 때 피드 맨 아래로 묻히는 문제가 있으므로 정렬 기준으로 쓰지 않는다.
카드 안에서는 `play_date` 또는 `play_month`만 표시한다.

### 8.3 API Shape

```text
GET /api/v1/social/feed
```

Query:

- `scope`: `all`, `public`, `following` 중 하나. 기본 `all`.
- `cursor`: 이전 응답의 `next_cursor`.
- `limit`: 기본 20, 최대 50.
- `locale`: `ko` 또는 `en`, 기본 `ko`.
- `include_self`: 기본 false.

Response:

```json
{
  "data": [
    {
      "round_id": "uuid",
      "owner": {
        "id": "uuid",
        "display_name": "Lala Golfer",
        "handle": "lala"
      },
      "visibility": "public",
      "social_published_at": "2026-05-10T12:00:00Z",
      "course_name": "베르힐영종",
      "play_date": null,
      "play_month": "2026-04",
      "total_score": 82,
      "score_to_par": 10,
      "hole_count": 18,
      "metrics": {
        "putts_total": 32,
        "gir_count": 7,
        "penalties_total": 2
      },
      "top_insight": {
        "category": "putting",
        "problem": "3퍼트가 이 라운드의 최우선 이슈입니다.",
        "confidence": "medium"
      },
      "like_count": 3,
      "comment_count": 1,
      "liked_by_me": false,
      "viewer_can_react": true
    }
  ],
  "meta": {
    "next_cursor": "opaque-cursor",
    "has_more": true
  }
}
```

### 8.4 Feed Visibility Query

라운드 feed item에 대한 로그인 사용자의 `scope=all` 조건:

```text
rounds.deleted_at is null
AND rounds.social_published_at is not null
AND (
  rounds.visibility = 'public'
  OR (
    rounds.visibility = 'followers'
    AND exists accepted follows row:
      follows.follower_id = viewer.id
      follows.following_id = rounds.user_id
      follows.status = 'accepted'
  )
)
AND rounds.visibility != 'link_only'
AND rounds.visibility != 'private'
```

비로그인 사용자는 `rounds.visibility = 'public'`만 허용한다.
`scope=following`은 로그인 사용자 전용이며 accepted follow 관계가 있는 `followers` 라운드와 followed 사용자의 `public` 라운드만 반환한다.
연습 다이어리와 라운드 목표도 동일한 visibility/follow 조건을 적용하되, 각 테이블의 `visibility`와 `social_published_at`을 기준으로 조회한다.

### 8.5 Feed Serialization Rules

피드 카드는 상세 화면보다 더 보수적인 public-safe serializer를 사용한다.

Never expose:

- companion names
- `notes_private`
- original upload text or shot `raw_text`
- source file metadata and storage key
- private LLM/chat/practice data
- link-only token or share title
- exact tee time

Expose conditionally:

- `course_name`: 공개/지인 공개 라운드에서는 항상 실제 코스명을 표시한다. 코스명은 소셜 맥락에서 핵심 식별 정보로 본다.
- `play_date`: `share_exact_date == true`이면 실제 날짜, 아니면 null.
- `play_month`: 항상 허용. 정확한 날짜 대신 월 단위 힌트로 사용한다.
- `top_insight`: 공개된 라운드에는 주요 인사이트 1개를 함께 표시한다. 활성 인사이트가 있으면 `priority_score desc, created_at desc` 1개를 쓰고, 없으면 scorecard 기반 fallback issue를 만든다.
- shot detail: 첫 버전 피드 카드에는 포함하지 않는다. 상세 진입 후 권한 검사를 다시 통과한 경우에만 보여준다.

### 8.6 Public Practice Diary and Goals

연습 다이어리와 라운드 목표는 기본 private을 유지하되, 사용자가 명시적으로 공개할 수 있다.

Visibility:

- `private`: 소유자만 볼 수 있다.
- `followers`: accepted follower만 볼 수 있다.
- `public`: 비로그인 사용자를 포함해 누구나 볼 수 있다.

Recommended fields:

- `practice_diary_entries.visibility`
- `practice_diary_entries.social_published_at`
- `round_goals.visibility`
- `round_goals.social_published_at`

Practice diary public card:

```json
{
  "item_type": "practice_diary",
  "item_id": "uuid",
  "owner": {
    "id": "uuid",
    "display_name": "Lala Golfer",
    "handle": "lala"
  },
  "visibility": "public",
  "social_published_at": "2026-05-10T12:00:00Z",
  "entry_date": "2026-05-10",
  "title": "Lag putting discovery",
  "body_preview": "8m uphill putts were consistently short.",
  "category": "putting",
  "tags": ["lag-putt", "distance-control"],
  "linked_round": {
    "round_id": "uuid",
    "course_name": "베르힐영종",
    "play_month": "2026-04"
  }
}
```

Round goal public card:

```json
{
  "item_type": "round_goal",
  "item_id": "uuid",
  "owner": {
    "id": "uuid",
    "display_name": "Lala Golfer",
    "handle": "lala"
  },
  "visibility": "followers",
  "social_published_at": "2026-05-10T12:00:00Z",
  "title": "Keep 3-putts to one or fewer",
  "description": "Distance control first, avoid leaving long second putts.",
  "category": "putting",
  "target": {
    "metric_key": "three_putt_holes",
    "operator": "<=",
    "value": 1
  },
  "status": "active",
  "due_date": "2026-05-20",
  "latest_evaluation": null
}
```

Public-safe rules:

- 다이어리 본문은 공개 시 사용자가 직접 노출을 선택한 것으로 보고 공개 가능하지만, 목록 카드에는 `body_preview`만 사용한다.
- 다이어리 상세 공개가 필요하면 별도 `GET /practice/diary/public/{entry_id}` 또는 profile 하위 공개 API에서 전체 `body`를 반환한다.
- `mood`, private plan internals, linked insight raw evidence, private round shot raw text는 공개 카드에서 제외한다.
- 목표의 `target_json`은 공개 카드에서 그대로 노출하지 말고 사람이 읽을 수 있는 `target` 형태로 정규화한다.
- goal evaluation note는 사용자가 수동으로 쓴 사적 메모일 수 있으므로 기본 공개하지 않는다. 공개용 요약만 별도 필드로 추가할 때 노출한다.

### 8.7 UI Behavior

새 화면은 `/social` 또는 `/feed` 중 하나로 둔다. 추천은 `/social`이다.

- 상단 segmented control: `All`, `Following`, `Public`.
- 모바일은 단일 컬럼 카드 리스트와 무한 스크롤.
- 데스크톱은 카드 리스트 폭을 제한하고 우측에는 follow 요청/추천 영역을 둘 수 있다.
- 라운드 카드에는 주요 인사이트 1개를 score summary 아래에 표시한다.
- 카드 클릭 시 리소스별 상세 경로로 이동한다.
  - public 라운드: `/rounds/public/{round_id}` 또는 현재 구현의 public-safe detail.
  - followers 라운드: 로그인 필요, `GET /rounds/{round_id}` 권한 검사를 통과해야 한다.
  - public/followers 다이어리: 공개/지인 공개 다이어리 상세.
  - public/followers 목표: 공개/지인 공개 목표 상세 또는 목표 카드 expanded view.
- 빈 상태:
  - Following: "아직 볼 수 있는 지인 라운드가 없습니다."
  - Public: "공개 라운드가 아직 없습니다."
- 무한 스크롤은 IntersectionObserver 기반으로 하고, 실패 시 "더 보기" 버튼으로 fallback한다.

### 8.8 Required Fixes Before Feed

피드를 만들기 전에 아래 검토 이슈를 먼저 수정해야 한다.

- follow 요청자가 자기 요청을 `accepted`로 바꿀 수 없게 한다.
- `blocked` 상태를 요청자가 `pending`으로 되돌릴 수 없게 한다.
- `RoundUpdateRequest`와 프론트 타입에 `share_exact_date`를 추가한다.
- 연습 다이어리와 라운드 목표에 visibility/public-safe serializer를 추가한다.

### 8.9 Testing Requirements

- 비로그인 피드는 public 라운드만 반환한다.
- 로그인 피드는 public + accepted-following followers 라운드를 반환한다.
- pending/blocked follow 관계는 followers 라운드를 반환하지 않는다.
- private/link-only 라운드는 어떤 피드 scope에도 나오지 않는다.
- 공개/지인 공개 라운드는 피드 카드에서 코스명을 표시한다.
- `share_exact_date=false` 라운드는 `play_date=null`, `play_month`만 반환한다.
- 공개 라운드 피드 카드에는 주요 인사이트가 최대 1개 포함된다.
- 공개 다이어리와 공개 목표는 public feed에 나오고, followers 다이어리/목표는 accepted follower feed에만 나온다.
- private 다이어리/목표는 어떤 피드 scope에도 나오지 않는다.
- cursor pagination은 중복과 누락 없이 다음 페이지를 반환한다.
- 다른 사용자의 companion/raw_text/source_file/private note가 피드 응답에 포함되지 않는다.

## 9. Ownership Rules

- 모든 소셜 테이블은 owner scope를 분명히 둔다.
- 공개 조회는 public-safe serializer를 통과해야 한다.
- comment/like는 follow 허용 관계와 visibility rule을 모두 통과해야 한다.
- link-only share는 social graph와 분리한다.
