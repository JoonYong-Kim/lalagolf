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
- companion 매칭은 동반자 이름, 동일한 코스, 동일한 시간을 기준으로 한다.
- 최종적으로 비교 가능한지는 해당 라운드의 공개 기준을 따른다.
- companion 이름이나 계정 매핑 정보가 있으면 같은 사람의 라운드를 더 쉽게 찾을 수 있다.

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

## 8. Ownership Rules

- 모든 소셜 테이블은 owner scope를 분명히 둔다.
- 공개 조회는 public-safe serializer를 통과해야 한다.
- comment/like는 follow 허용 관계와 visibility rule을 모두 통과해야 한다.
- link-only share는 social graph와 분리한다.
