# LalaGolf

취미 골프 라운드를 텍스트 파일로 기록하고, 이를 MySQL과 Flask 대시보드로 분석하는 개인용 골프 기록 서비스입니다.  
단순 스코어 저장보다 `샷 단위 기록 -> 라운드 지표 -> 최근 추세 -> 연습/전략 추천` 흐름에 초점을 둡니다.

## Key Features

- 텍스트 파일 기반 라운드 입력 및 파싱
- MySQL 적재와 라운드/홀/샷 단위 데이터 조회
- 라운드 상세 분석: scoring, putting, short game, penalties, tee shot, approach
- 최근 추세 분석: 최근 `5/10/20` 라운드 비교, 코스 보정, 전/후반, 마무리 3홀, 버디 직후, 페널티 직후, 목표 타수 방어
- 샷 가치 분석: expected score, shot value, category summary
- 추천 레이어: `Practice Priorities`, `Top Recurring Priorities`, `Next Action`, `Round + Trend Action`
- subtype 기반 추천: 예) `거리 오차형 어프로치`, `큰 미스 누적형 티샷`, `거리감 손실형 퍼팅`

## Project Layout

- `src/data_parser.py`: 텍스트 라운드 파일 파싱
- `src/db_loader.py`: DB 저장/조회
- `src/metrics.py`: 라운드/최근 추세 지표
- `src/shot_model.py`: 샷 상태 정규화
- `src/expected_value.py`: 기대 타수 계산
- `src/strokes_gained.py`: shot value 집계
- `src/recommendations.py`: 추천/우선순위/드릴 생성
- `src/webapp/`: Flask 앱, 라우트, 템플릿
- `scripts/schema.sql`: 현재 코드 기준 관리형 DB 스키마
- `scripts/install_systemd.sh`: `/opt/lalagolf` + `systemd` 설치 스크립트
- `scripts/uninstall_systemd.sh`: systemd 서비스 및 설치 경로 제거 스크립트
- `tests/`: `pytest` 테스트
- `docs/plan.md`: 구현 계획 및 상태 정리

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`conf/lalagolf.conf`에 최소한 다음 항목을 맞춰야 합니다.

- `DB_CONFIG`
- `WEBAPP_USERS`

실서버용 비밀값은 소스가 아니라 환경변수로 관리하세요. Flask `SECRET_KEY`는 환경변수로 주입하거나, 개발 환경에서는 자동 생성 키를 사용합니다.

## Run

라운드 파일을 DB에 적재:

```bash
python load_data.py
```

웹 앱 실행:

```bash
python run_webapp.py
```

기본 포트는 `2323`입니다.

## systemd Deployment

`systemd` 운영을 위해 `/opt/lalagolf` 기준 설치/삭제 스크립트를 제공합니다.

설치:

```bash
sudo bash scripts/install_systemd.sh
```

삭제:

```bash
sudo bash scripts/uninstall_systemd.sh
```

설치 스크립트는 다음을 수행합니다.

- `/opt/lalagolf`에 애플리케이션 배치
- `/opt/lalagolf/.venv` 생성 및 의존성 설치
- `/etc/lalagolf/lalagolf.env` 생성
- `lalagolf` system user 생성
- `/etc/systemd/system/lalagolf.service` 생성 및 활성화

운영 전 확인할 파일:

- `/opt/lalagolf/conf/lalagolf.conf`
- `/etc/lalagolf/lalagolf.env`

## Testing

전체 테스트:

```bash
pytest -q
```

추천/라우트 변경 후 빠른 문법 체크:

```bash
python -m py_compile src/recommendations.py src/webapp/routes.py
```

## Data Format

한 파일은 한 라운드를 의미하며, 파일은 repo-root `data/<year>/` 아래에 둡니다.  
각 줄은 홀 정보 또는 샷 정보입니다.

- 홀 정보: `1P4`, `2 P5`
- 샷 정보: `Club Feel Result [Landing] [Distance] [Penalty|OK]`

예시:

```text
1P4
D B C
I5 A C 150 H
P C A 10 OK
```

해석:

- `1P4`: 1번 홀, 파 4
- `D B C`: 드라이버, 감각 B, 결과 C
- `I5 A C 150 H`: 5번 아이언, 150m, 해저드
- `P C A 10 OK`: 퍼터, 10m, 컨시드

대표 클럽 표기:

- `D`, `W3`, `W5`, `UW`, `U3`, `U4`
- `I3`-`I9`, `IP`
- `48`, `52`, `56`, `58`
- `P`

대표 부가 표기:

- 결과/감각 등급: `A`, `B`, `C`
- 벙커: `B`
- 페널티: `H`, `OB`, `UN`
- 컨시드: `OK`

## Current Analytics Surfaces

- 홈: 최근 요약, `Recent Focus`, `Top Recurring Priorities`, `Practice Priorities`
- 라운드 목록: 최근 추천과 반복 손실 우선순위
- 트렌드: 최근 구간 비교, 코스 보정, 전략 비교, 추천 카드
- 라운드 상세: 해설 카드, 손실 상위 3개, `Next Action`, `Round + Trend Action`

## Notes

- 입력 항목을 늘리지 않고도 계산 가능한 지표 중심으로 고도화되어 있습니다.
- 최근 추천은 손실 크기뿐 아니라 최근 흐름과 표본 수를 같이 반영합니다.
- DB 초기 생성 기준은 `scripts/schema.sql`을 사용합니다.
- 세부 구현 로드맵과 남은 작업은 `docs/plan.md`를 기준으로 관리합니다.
