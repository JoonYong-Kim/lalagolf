# GolfRaiders v2 PRD

## 1. Product Summary

GolfRaiders v2는 개인 골프 라운드 기록을 업로드, 분석, 공유하고, 자신의 기록을 기반으로 질의할 수 있는 멀티 유저 골프 분석 서비스다. v1의 라운드 파싱, 지표 계산, strokes gained 유사 분석, 추천 로직을 제품 코어로 유지하되, UI/UX, 계정 모델, 데이터 권한, 공유 경험, 자연어 질의 기능을 새 프로젝트 구조에서 재설계한다.

MVP는 private-first 개인 분석 앱으로 제한한다. Public feed/profile, embedding 기반 RAG, social graph는 핵심 분석 경험과 link-only 공유가 검증된 뒤 단계적으로 확장한다.

## 2. Goals

- 라운드 기록을 개인별로 안전하게 관리하고, 사용자가 공개 범위를 선택해 공유할 수 있다.
- 중복된 코멘트와 유사 분석 카드를 줄이고, 한 화면에서 우선순위가 명확한 인사이트를 제공한다.
- 모바일과 데스크톱 모두에서 라운드 업로드, 리뷰, 분석, 공유가 자연스럽게 동작한다.
- 구조화된 metric retrieval과 선택적 Ollama 보조 응답으로 사용자의 라운드 기록, 샷 데이터, 추천 결과를 질의할 수 있다.
- v1의 검증된 분석 로직을 재사용하되, API와 UI는 분리된 현대적 웹 아키텍처로 전환한다.

## 3. Non-Goals

- v2 초기 버전에서 모든 SNS 기능을 구현하지 않는다. 댓글, 좋아요, 팔로우는 단계적으로 도입한다.
- 공식 핸디캡 산정 또는 경기 운영 플랫폼을 목표로 하지 않는다.
- LLM이 자동으로 스윙 교정을 확정 진단하거나 의학적/부상 관련 조언을 제공하지 않는다.
- 외부 상용 LLM 의존을 기본값으로 두지 않는다. Ollama 로컬 구동을 기본으로 한다.

## 4. Target Users

- Primary: 자신의 라운드 기록을 꾸준히 남기고 개선 포인트를 찾고 싶은 골퍼.
- Secondary: 친구, 동반자, 코치와 일부 기록을 공유하고 피드백을 받고 싶은 골퍼.
- Admin: 사용자, 공개 콘텐츠, 데이터 파싱 오류, 시스템 상태를 관리하는 운영자.

## 5. Key User Stories

- 사용자는 이메일/소셜 로그인으로 가입하고 자신의 라운드 기록만 기본적으로 볼 수 있다.
- 사용자는 기존 텍스트 라운드 파일을 업로드하고, 파싱 결과를 저장 전에 검토/수정할 수 있다.
- 사용자는 대시보드에서 최근 성과, 주요 약점, 개선 추세, 다음 연습 과제를 확인한다.
- 사용자는 확인된 인사이트에서 연습 계획을 만들고, 연습 중 발견한 내용을 다이어리로 기록한다.
- 사용자는 다음 라운드의 측정 가능한 목표를 만들고, 라운드 저장 후 달성 여부를 확인한다.
- 사용자는 라운드를 private 또는 link-only로 공유한다. followers/public은 MVP 이후 도입한다.
- 사용자는 “최근 10라운드에서 드라이버가 스코어에 얼마나 영향을 줬어?”처럼 자연어로 질문한다.
- 사용자는 특정 라운드, 기간, 골프장, 동반자, 클럽, 샷 유형을 필터링해 분석한다.
- 운영자는 비정상 업로드, 신고된 공개 기록, LLM 오류 로그를 점검한다.

## 6. Product Scope

### 6.1 Account & Identity

- 회원가입, 로그인, 로그아웃, 비밀번호 재설정.
- 사용자 프로필: 표시 이름, 프로필 이미지, 자기소개, 평균 스코어, 기본 공개 범위. 공개 프로필은 MVP 이후 도입한다.
- 역할: user, admin.
- 데이터 소유권: 모든 라운드, 홀, 샷, 메모, LLM 대화는 user_id에 귀속된다.
- 계정 삭제: 개인 데이터 삭제 또는 익명화 정책 제공.

### 6.2 Round Data Management

- v1 텍스트 포맷 업로드 지원.
- 업로드 후 3단계 플로우: 파일 업로드 -> 파싱 리뷰 -> 저장/분석 생성.
- 파싱 오류 라인, 모호한 클럽명, 누락 홀, 27홀 라운드, 패널티 표기 오류를 UI에서 수정.
- 라운드 메타데이터: 날짜, 골프장, 코스, 티, 날씨, 동반자, 목표 스코어, 공개 범위.
- 라운드 상세: 홀별 스코어, 퍼트, GIR, 샷 타임라인, 클럽/거리/라이/결과/패널티.

### 6.3 Analytics

- v1 유지 지표: score, score_to_par, GIR, putts, one-putt, three-putt, scrambling, up-and-down, penalty strokes, par type score.
- 샷 모델: tee, short game(0-40m), control shot(40-90m), iron shot(90m+), putting, recovery,
  penalty impact 분류.
- expected score table 및 strokes gained 유사 shot_value 계산.
- 기간 비교: 최근 N라운드, 연도, 골프장, 동반자, 선택 라운드.
- 중복 정리 원칙:
  - “원인”, “영향”, “다음 행동”을 하나의 insight unit으로 통합한다.
  - 같은 근거에서 나온 코멘트는 한 번만 표시하고, Analysis에서는 하나의 전환형 위젯에서
    인사이트를 넘겨 보게 한다.
  - 추천 우선순위는 최대 3개만 기본 노출한다.
- 신뢰도 표시: 샘플 수, expected lookup level, 데이터 부족 경고.
- cold-start 정책: 사용자 샘플이 부족하면 global 또는 운영자가 승인한 baseline expected table로 fallback하고, confidence와 lookup level에 이를 표시한다.

### 6.4 Dashboard & UI

- 로그인 후 첫 화면은 마케팅 페이지가 아니라 사용자 대시보드다.
- 핵심 화면:
  - Home Dashboard: 최근 라운드, 핵심 추세, 오늘의 연습 과제.
  - Rounds: 라운드 목록, 필터, 비교 선택.
  - Round Detail: 홀/샷 단위 상세 분석.
  - Analysis: 기간/조건별 분석.
  - Practice/Goals: 인사이트를 연습 계획, 다이어리, 다음 라운드 목표로 연결.
  - Ask GolfRaiders: 자연어 질의.
  - Upload Review: 파싱 결과 검토.
  - Feed/Profile: post-MVP 공개 또는 공유된 라운드.
- 디자인 방향:
  - 스포츠 기록장이 아니라 개인 퍼포먼스 분석 앱처럼 느껴지는 조용하고 밀도 있는 UI.
  - Linear/Stripe Dashboard 계열의 정돈된 SaaS 톤을 기준으로 하되, 골프 데이터의 맥락을 색상과 차트에 반영한다.
  - 배경은 밝은 회색/오프화이트, 본문은 차콜, 주요 강조색은 딥 그린을 기본으로 한다.
  - 성과 상태 색상은 기능적으로만 사용한다. 개선은 green/blue, 악화는 amber/red, 중립은 gray 계열을 사용한다.
  - 잔디색, 골드, 우드톤 등 골프장 연상 색상을 과도하게 사용하지 않는다.
  - 카드 남용을 줄이고 표, 차트, 탭, 필터, 사이드 패널 중심 구성으로 반복 사용에 적합하게 만든다.
  - 카드는 최근 라운드, 핵심 인사이트, 공개 라운드처럼 반복 아이템이나 요약 단위에 제한적으로 사용한다.
  - 대시보드 내부 제목은 과도하게 크지 않게 하고, 수치/추세/근거를 빠르게 스캔할 수 있도록 정보 밀도를 유지한다.
  - 모바일에서는 라운드 요약과 인사이트를 우선 노출하고, 상세 표는 접힘/드릴다운 처리.
- 내비게이션:
  - 데스크톱은 좌측 사이드바를 기본으로 한다.
  - 모바일은 하단 탭 또는 상단 메뉴를 사용한다.
  - MVP 기본 메뉴는 Dashboard, Rounds, Analysis, Practice, Goals, Ask, Upload이다.
  - Feed/Profile/Settings는 post-MVP 또는 별도 계정 설정 화면으로 분리한다.
- Dashboard 구성:
  - 상단: 핵심 KPI와 최근 라운드 기반 스코어 추이 차트. 차트는 축 라벨, 평균선, 점수
    라벨, 최근 라운드별 스코어/파 대비 요약을 제공한다.
  - 중단: 우선순위 인사이트 최대 3개.
  - 우측 또는 하단: 이번 주 연습 과제와 최근 업로드 상태.
  - 하단: 최근 라운드 목록.
- Round Detail 구성:
  - 상단: 총 스코어, 전/후반, 페널티, 퍼트, GIR 요약.
  - 중단: 라운드 분석 요약과 홀별 스코어카드. 스코어카드는 동일 폭 홀 컬럼과
    eagle/birdie/par/bogey/double+ 배지로 결과를 시각화한다.
  - 하단: 홀 선택 기반 샷 타임라인. 타임라인에는 expected before, shot cost,
    expected after, stroke gained를 함께 표시한다.
  - 보조 영역: 스코어카드 헤더에 공유, 수정, 재계산 액션을 제공한다. 수정은 기존 업로드 검토
    화면으로 이동해 원문 데이터를 수정/재파싱하고 기존 라운드를 갱신한다.
- Analysis 구성:
  - 상단 고정 필터: 기간, 골프장, 동반자, 클럽, 라운드 선택.
  - 탭: All, Tee, Short Game, Control Shot, Iron Shot, Putting, Recovery, Penalty.
  - 인사이트는 긴 카드 목록이 아니라 하나의 전환형 위젯에서 1개씩 확인한다.
  - 인사이트 기반 제안은 `플랜 선택`과 `목표 선택`을 같은 레벨의 액션으로 제공한다.
- Round Compare 구성:
  - `/rounds`에서 라운드를 2개 이상 선택하면 별도 비교 페이지(`/rounds/compare`)로 이동한다.
  - 2개 라운드는 head-to-head로 비교하고, 3개 이상은 날짜상 마지막/최근 라운드를 대상 라운드로
    두고 나머지 선택 라운드 평균과 비교한다.
  - 비교 항목은 스코어, 퍼트, 홀당 퍼트, 3퍼트 홀, GIR `홀 수 (비율)`, 페어웨이 안착률, 페널티,
    페널티 홀, 버디 이상, 파, 보기, 더블보기 이상이다. `파 대비`와 `총 파`는 비교 테이블에서
    제외한다. GIR 차이는 홀 수 차이만 표시한다.
  - 페어웨이 안착률은 저장된 `fairway_hit` 값이 있으면 사용하고, 없으면 par 4/5의 티샷
    결과 위치가 `F`인지로 파생 계산한다.
- Ask GolfRaiders 구성:
  - 좌측 또는 중앙에 채팅 UI를 둔다.
  - 우측 또는 하단에 근거 데이터 패널을 제공한다.
  - 자연어 답변과 원본 수치 근거를 시각적으로 분리한다.
  - 근거 패널에는 기간, 라운드 수, 샷 수, 필터 조건, 참조 라운드 링크를 표시한다.

### 6.4.1 UI Review Gate

- Dashboard, Round Detail, Analysis는 구현 전에 저충실도 와이어프레임 또는 클릭 가능한 mock을 만든다.
- 각 화면은 desktop/mobile variant를 함께 확인한다.
- 사용자 확인 후 결정사항을 `docs/ui_review_v2.md`에 기록하고, 구현은 그 문서를 기준으로 진행한다.
- UI 확인 범위:
  - Dashboard: 첫 화면 정보 우선순위, top-3 insight, 최근 라운드/연습 과제 배치.
  - Round Detail: 스코어카드, 홀 선택, 샷 타임라인, 라운드 내 손실/개선 샷 배치.
  - Analysis: 필터, 탭, 차트/테이블 밀도, insight unit 노출 방식.
- 주요 UI 방향이 바뀌면 구현 전에 `docs/ui_review_v2.md`를 갱신한다.

### 6.4.2 Practice & Goal Loop

- GolfRaiders는 분석 화면에서 끝나지 않고, 개선 행동과 다음 라운드 검증까지 이어지는 루프를 제공한다.
- Practice Plan:
  - 인사이트의 `next_action`, `category`, `root_cause`, `primary_evidence_metric`에서 연습 계획을 만들 수 있다.
  - 사용자는 계획을 직접 입력하기보다 Analysis 인사이트에서 제안된 루틴을 선택해 연습 계획을 생성한다.
  - 계획은 제목, 목적, 카테고리, 추천 드릴, 목표량, 예정일, 상태를 가진다.
  - 상태는 `planned`, `in_progress`, `done`, `skipped`를 기본으로 한다.
  - 하나의 인사이트에서 여러 연습 계획을 만들 수 있고, 하나의 계획은 특정 인사이트 없이도 직접 만들 수 있다.
- Practice Diary:
  - 사용자는 연습 후 발견한 점, 감각, 실패 패턴, 다음 조정 사항을 다이어리 형식으로 남긴다.
  - 다이어리는 연습 계획에 연결될 수 있고, 독립적인 자유 기록도 가능하다.
  - `/practice`에서는 달력과 다이어리 기록이 하나의 위젯에서 토글되며, 달력의 날짜를
    선택한 뒤 해당 날짜의 기록을 확인하거나 새 기록을 저장한다.
  - 권장 구조는 날짜, 제목, 본문, 카테고리, 태그, 자신감/컨디션, 관련 인사이트/라운드 링크다.
  - 다이어리 내용은 기본 private이며, Ask GolfRaiders와 향후 인사이트 생성의 개인 컨텍스트로 활용 가능하다.
- Next Round Goal:
  - 사용자는 다음 라운드에서 검증할 측정 가능한 목표를 만든다.
  - 목표는 특정 카테고리와 평가 규칙을 가져야 한다. 예: `tee_penalties <= 0`, `three_putt_holes <= 1`, `score_to_par <= 12`.
  - 목표는 연습 계획 또는 인사이트에서 생성할 수 있고, 사용자가 직접 만들 수도 있다.
  - 상태는 `active`, `achieved`, `missed`, `partial`, `not_evaluable`, `cancelled`를 사용한다.
- Goal Evaluation:
  - 라운드 저장 또는 재계산 후 활성 목표를 해당 라운드 지표와 비교해 평가한다.
  - 자동 평가가 가능한 목표는 시스템이 결과를 제안하고, 모호한 목표는 사용자가 수동 평가할 수 있다.
  - 평가 결과는 목표의 history로 남기고, 이후 대시보드와 Ask에서 “연습이 다음 라운드에 영향을 줬는가?”를 확인하는 근거가 된다.
- UI:
  - Analysis 인사이트 위젯에는 제안 루틴별 `플랜 선택`, `목표 선택` 액션을 제공한다.
  - Round Detail에는 라운드 분석 요약과 공유 액션을 제공한다.
  - `/practice`는 연습 계획 목록과 달력/다이어리 토글 위젯 중심의 작업 화면이다.
  - `/goals`는 활성 목표, 평가 결과, 다음 라운드 검증 상태를 보여준다.

### 6.5 Public Home / Logged-out Experience

- MVP에서 로그인하지 않은 사용자가 `/`에 접근하면 최소 진입 화면을 보여준다.
- 공개 홈의 목적은 서비스 설명보다 “가입하면 어떤 분석을 볼 수 있는지”를 실제 제품 화면처럼 보여주는 것이지만, full public home은 v2.1 이후로 미룬다.
- 첫 화면 구성:
  - Hero: GolfRaiders 이름과 한 문장 설명.
  - Primary CTA: 시작하기. 시작하기는 회원가입 모드로 열린다.
  - Secondary CTA: 샘플 분석 보기, 로그인. 우측 상단 로그인은 로그인 모드로 열린다.
  - 샘플 대시보드 프리뷰: 평균 스코어 추세, 최근 라운드, 핵심 인사이트 2~3개를 샘플 데이터로 표시.
- 공개 콘텐츠:
  - MVP 이후 사용자가 public으로 공개한 라운드 또는 프로필 일부를 노출할 수 있다.
  - 공개 콘텐츠는 샘플 분석보다 낮은 우선순위로 배치한다.
  - 권장 비중은 샘플 분석 60%, 공개 피드 30%, CTA/신뢰 정보 10%다.
- 공개 라운드 노출 허용 정보:
  - 표시 이름 또는 닉네임.
  - 라운드 날짜 또는 상대 날짜.
  - 골프장명은 사용자가 허용한 경우에만 표시.
  - 스코어, GIR, 퍼트, 페널티, 짧은 인사이트 요약.
- 공개 라운드에서 숨겨야 하는 정보:
  - 동반자명.
  - 비공개 메모.
  - 원본 업로드 파일.
  - 정확한 티타임.
  - 사용자가 숨김 처리한 골프장/날짜.
- 기능 요약은 3개로 제한한다:
  - Upload: 라운드 텍스트를 분석 가능한 데이터로 변환.
  - Analyze: 스코어를 만든 원인을 샷/클럽/상황별로 분해.
  - Ask: 내 라운드 기록에 자연어로 질문.
- 프라이버시 신뢰 신호:
  - 기본 공개 범위는 private이다.
  - 사용자는 라운드별로 private, link-only, public을 선택할 수 있다.
  - public feed 도입 전 신고/숨김/차단 정책을 준비한다.
- 로그인 후 `/` 접근은 개인 Dashboard로 이동한다.

### 6.6 Mobile Experience

- v2는 별도 네이티브 앱이 아니라 모바일 우선 반응형 웹을 기본으로 한다.
- PWA 설치, 홈 화면 바로가기, 기본 오프라인 캐싱은 MVP 이후 단계에서 검토한다.
- 모바일 핵심 사용 시나리오:
  - 라운드 후 휴대폰에서 기록 업로드.
  - 업로드 파싱 결과를 빠르게 검토하고 저장.
  - 최근 라운드 요약과 핵심 인사이트 확인.
  - 공유 링크 생성 후 메신저/SNS로 전달.
  - Ask GolfRaiders에 짧은 질문 입력.
- 모바일 내비게이션:
  - 하단 탭을 기본으로 한다.
  - MVP 탭은 Dashboard, Rounds, Analysis, Practice, Goals, Ask, Upload를 가로 스크롤로 제공한다.
  - Feed, Profile, Settings는 post-MVP 또는 더보기 메뉴에서 접근한다.
- 모바일 Dashboard:
  - 첫 화면에는 최근 스코어 추세, 마지막 라운드 요약, 우선순위 인사이트 1~3개만 노출한다.
  - 긴 비교 테이블은 기본 숨김 처리하고, 차트/요약/상세 보기 순서로 드릴다운한다.
  - 수치는 큰 숫자만 강조하고, 설명 문장은 짧게 유지한다.
- 모바일 Round Detail:
  - 상단에 sticky 라운드 요약을 둔다.
  - 스코어카드는 가로 스크롤 또는 전반/후반 분할을 지원한다.
  - 홀을 탭하면 해당 홀의 샷 타임라인이 펼쳐진다.
  - 샷 타임라인은 클럽, 거리, 시작/종료 위치, 결과, 패널티를 한 줄 단위로 스캔 가능하게 표시한다.
  - 저장된 라운드는 `원문 데이터 수정` 버튼으로 기존 업로드 검토 화면에 진입해 raw 파일을
    수정/재파싱할 수 있다. 다시 저장하면 새 파싱 결과가 기존 라운드를 갱신하고 재계산 대상이 된다.
- 모바일 Upload Review:
  - 파싱 오류와 확인 필요 항목을 먼저 보여준다.
  - 전체 라운드 표를 먼저 보여주지 않고, 문제가 있는 홀/샷부터 수정하게 한다.
  - 클럽, 라이, 패널티, 결과 등 반복 입력은 select, segmented control, stepper를 사용한다.
  - 저장 전 “총 홀 수, 총 스코어, 파싱 경고 수”를 확인한다.
- 모바일 Analysis:
  - 필터는 상단 sheet/drawer로 제공한다.
  - All, Tee, Short Game, Control Shot, Iron Shot, Putting, Recovery, Penalty 탭을 유지하되,
    각 탭은 핵심 요약 테이블과 전환형 인사이트 위젯으로 시작한다.
  - 상세 테이블은 모바일에서 열 단위 숨김 또는 expandable row를 사용한다.
- 모바일 Ask:
  - 채팅 입력창은 하단 고정으로 둔다.
  - 근거 데이터 패널은 답변 하단의 “근거 보기” sheet로 제공한다.
  - 긴 답변은 요약을 먼저 보여주고, 근거 라운드/샷 링크를 뒤에 둔다.
- 모바일 Public Home:
  - MVP의 logged-out entry는 한 화면을 모두 차지하지 않게 하고, 로그인/가입 CTA를 명확히 둔다.
  - v2.1 public home에서는 첫 viewport 하단에 샘플 대시보드 일부가 보이게 한다.
  - 공개 라운드 피드는 1열 리스트로 표시한다.
  - CTA는 상단 또는 하단 sticky 영역에 하나만 유지한다.
- 터치/접근성 기준:
  - 주요 터치 타겟은 최소 44px 이상.
  - 테이블과 차트는 손가락 스크롤과 탭 선택을 지원한다.
  - 날짜, 골프장, 클럽 필터는 키보드 입력보다 선택 중심 UI를 우선한다.
  - 모바일에서 텍스트가 버튼/칩 밖으로 넘치지 않도록 줄바꿈과 최소/최대 너비를 정의한다.

### 6.7 Sharing & Social

- 공개 범위:
  - private: 본인만.
  - link-only: 링크를 아는 사용자.
  - public: 공개 프로필/피드 노출.
  - followers: 팔로워만. MVP 이후 도입 가능.
- 공유 가능한 단위: 라운드 요약, 특정 라운드 상세, 기간 분석 스냅샷, 연습 과제.
- 공개 화면에서는 민감 정보 제거 옵션 제공: 동반자명, 정확한 날짜, 메모 숨김.
- 신고/숨김/차단 기능은 public feed 도입 전 필수.

### 6.8 LLM / Ollama

- MVP Ask는 deterministic structured retrieval과 템플릿 답변을 기본으로 한다.
- Ollama 로컬 서버는 답변 문장화 보조로 선택적으로 사용한다.
- embeddings API와 RAG는 MVP 이후 도입한다.
- 질문 범위:
  - 내 라운드 데이터 요약.
  - 특정 기간/골프장/클럽/샷 유형 분석.
  - 추천 근거 설명.
  - 다음 라운드 전략 제안.
- MVP retrieval 구조:
  - 정형 SQL 조회: 점수, 라운드, 샷, 지표, 추천.
  - query planner: 기간, 골프장, 클럽, 샷 유형, 최근 N라운드 같은 제한된 필터를 해석한다.
  - 응답 생성: 조회 결과와 근거 데이터를 템플릿으로 답변하고, Ollama가 사용 가능하면 wording만 보조한다.
- Post-MVP RAG 구조:
  - 벡터 검색: 라운드 메모, 자동 요약, 인사이트 설명, 업로드 원문.
  - citation framework: 근거 문서와 정형 지표를 함께 제공한다.
- Guardrails:
  - 사용자의 권한 밖 데이터는 검색/응답에 포함하지 않는다.
  - 샘플 수 부족 시 단정 표현 금지.
  - 응답에는 가능한 경우 근거 라운드/기간/샷 수를 표시한다.
  - LLM 응답은 분석 결과를 보조 설명하며, 원본 수치 계산을 대체하지 않는다.

## 7. Recommended Architecture

- Frontend: Next.js App Router, React 19, TypeScript.
- UI: Tailwind CSS + shadcn/ui 계열 컴포넌트 또는 동등한 headless component system.
- Backend API: FastAPI 또는 Django REST. v1 분석 파이썬 코어 재사용을 고려하면 Python backend가 적합하다.
- Database: PostgreSQL. 벡터 검색은 pgvector 또는 별도 vector DB.
- Auth: 자체 이메일 로그인 + OAuth 확장 가능 구조.
- Jobs: RQ/Celery/Arq 중 하나로 업로드 파싱, 분석 재계산을 비동기화한다. embedding 생성 job은 post-MVP.
- LLM Service: Ollama adapter를 별도 모듈로 두고 모델명, timeout, context window, streaming 여부를 환경변수화.
- Deployment: web, api, worker, db, ollama를 분리 가능한 Docker Compose 우선.

## 8. Data Model

- users: id, email, password_hash, display_name, avatar_url, role, created_at.
- user_profiles: user_id, bio, home_course, handicap_target, privacy_default.
- rounds: id, user_id, play_date, course_id, course_name, tee, total_score, total_par, visibility, source_file_id.
- holes: id, round_id, hole_number, par, score, putts, gir, fairway_hit.
- shots: id, round_id, hole_id, seq, club, distance, start_lie, end_lie, result_grade, feel_grade, penalty_type, score_cost.
- round_metrics: round_id, metric_key, metric_value, sample_count, computed_at.
- shot_values: shot_id, category, expected_before, expected_after, shot_value, lookup_level, sample_count.
- insights: id, user_id, scope_type, scope_id, insight_type, title, summary, evidence_json, priority_score.
- practice_plans: id, user_id, insight_id, title, purpose, category, status, scheduled_for, completed_at.
- practice_diary_entries: id, user_id, practice_plan_id, entry_date, title, body, category, tags_json.
- round_goals: id, user_id, source_insight_id, practice_plan_id, title, metric_key, target_operator, target_value, status.
- goal_evaluations: id, user_id, goal_id, round_id, evaluation_status, actual_value, evaluated_at.
- shares: id, owner_id, resource_type, resource_id, visibility, token, created_at.
- follows: follower_id, following_id, status.
- llm_threads: id, user_id, title, created_at.
- llm_messages: id, thread_id, role, content, citations_json, created_at.
- embeddings: post-MVP. id, owner_id, source_type, source_id, content_hash, vector, metadata_json.

## 9. API Scope

- Auth: POST /auth/register, POST /auth/login, POST /auth/logout, POST /auth/reset-password.
- Rounds: GET/POST /rounds, GET/PATCH/DELETE /rounds/{id}.
- Uploads: POST /uploads/round-file, GET /uploads/{id}/review, POST /uploads/{id}/commit.
- Analytics: GET /analytics/summary, GET /analytics/trends, GET /analytics/rounds/{id}.
- Insights: GET /insights, PATCH /insights/{id}/dismiss.
- Practice: GET/POST /practice/plans, PATCH /practice/plans/{id}, GET/POST /practice/diary.
- Goals: GET/POST /goals, PATCH /goals/{id}, POST /goals/{id}/evaluate.
- Sharing: POST /shares, PATCH /shares/{id}, GET /s/{token}.
- Public: GET /.
- Social: post-MVP.
- LLM: POST /chat/threads, POST /chat/threads/{id}/messages, GET /chat/threads/{id}.
- Admin: GET /admin/uploads/errors.

## 10. MVP Definition

MVP에 반드시 포함:

- 계정 기반 로그인과 user_id 기반 데이터 격리.
- v1 라운드 텍스트 업로드, 리뷰, 저장.
- 개인 대시보드, 라운드 목록, 라운드 상세, 기간 분석.
- 모바일 반응형 Dashboard, Round Detail, Upload Review, Ask 화면.
- 로그인 전 최소 진입 화면.
- 중복 제거된 추천/인사이트 UI.
- private/link-only 공유.
- Ask GolfRaiders 1차 버전: 사용자 본인 데이터만 대상으로 한 structured SQL/metric 답변과 근거 표시.
- 기본 관리자 화면: 업로드 오류 로그. 관리자 메뉴는 `role=admin` 사용자에게만 노출된다.
- Dashboard, Round Detail, Analysis UI 와이어프레임 확인.

MVP 이후:

- full public home과 sample analysis preview.
- public feed, followers, comments, likes.
- embedding/RAG/citation framework.
- 코치/그룹 기능.
- 자동 라운드 요약 이미지 생성.
- 모바일 앱 또는 PWA 오프라인 입력.

## 11. Success Metrics

- 업로드 성공률: 95% 이상.
- 업로드 후 저장 완료율: 80% 이상.
- 핵심 대시보드 로딩: p95 2초 이하.
- 모바일 핵심 화면의 Lighthouse 접근성/성능 점수 90 이상.
- Ask 질의 응답: supported structured question p95 3초 이하. Ollama wording 사용 시 p95 10초 이하, timeout/error 5% 이하.
- 사용자가 한 달에 2회 이상 라운드/분석을 다시 보는 비율.
- 중복 인사이트 신고/숨김 비율 감소.
- 공유 링크 생성 후 외부 조회율.

## 12. Migration Plan

- Phase 1: v1 스키마와 분석 로직 inventory 작성.
- Phase 2: v2 PostgreSQL 스키마 설계 및 v1 MySQL 데이터 변환 스크립트 작성.
- Phase 3: 파서/분석 로직을 독립 Python package로 분리.
- Phase 4: API 서버에서 분석 package 호출.
- Phase 5: early migration import로 실제 v1 데이터를 v2 개발 DB 또는 fixture에 적재.
- Phase 6: Dashboard/Round Detail/Analysis 와이어프레임 작성 및 사용자 확인.
- Phase 7: Next.js UI 구현.
- Phase 8: Ask structured retrieval, optional Ollama adapter, chat UI 구현.
- Phase 9: 기존 repo-root data/<year> 라운드 파일 import 검증.
- Phase 10: v1/v2 결과 비교 테스트. score, GIR, penalty, shot_value, recommendation priority 차이를 리포트한다.

## 13. Risks & Open Questions

- 기존 추천 문구의 중복 원인이 데이터 레벨인지 UI 조합 레벨인지 추가 분석이 필요하다.
- 공개 공유 시 동반자명과 라운드 메모가 개인정보가 될 수 있으므로 기본 비공개가 안전하다.
- Ollama 모델 성능은 로컬 하드웨어에 크게 의존한다. MVP 기능은 Ollama 없이도 structured 답변으로 동작해야 한다.
- expected score와 shot_value는 개인 데이터가 적을수록 불안정하므로, 신뢰도 UI가 필수다.
- 핵심 화면 UI가 카드 중심으로 흐르면 v2의 분석 개선 목표가 약해진다. 구현 전 UI review gate가 필요하다.
- v1 MySQL 유지 여부와 v2 PostgreSQL 전환 시점 결정이 필요하다.

## 14. Technical References

- React docs report latest major documentation as React 19.2 as of the checked React versions page.
- Next.js App Router supports React Server Components, Suspense, and Server Functions.
- Ollama provides local `/api/chat` for optional wording support in MVP and `/api/embed` for post-MVP RAG.
