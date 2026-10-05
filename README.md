# 🏕️ 국립공원 야영장 & 🏡 생태탐방원 & 🏕️ 서울시 글램핑존 빈자리 자동 알림 봇

[![야영장 실시간 현황](https://img.shields.io/badge/야영장_현황-campsite%2FSTATUS.md_보기-success?style=for-the-badge&logo=markdown)](campsite/STATUS.md)
[![생태탐방원 실시간 현황](https://img.shields.io/badge/생태탐방원_현황-eco%2FSTATUS.md_보기-blue?style=for-the-badge&logo=markdown)](eco/STATUS.md)
[![서울시 글램핑존 실시간 현황](https://img.shields.io/badge/서울시_글램핑존_현황-seoul%2FSTATUS.md_보기-orange?style=for-the-badge&logo=markdown)](seoul/STATUS.md)

> 📊 **[👉 야영장 실시간 잔여석 표 및 히스토리 (campsite/STATUS.md) 바로가기](campsite/STATUS.md)**  
> 🏡 **[👉 생태탐방원 실시간 잔여 객실 표 및 히스토리 (eco/STATUS.md) 바로가기](eco/STATUS.md)**  
> 🏕️ **[👉 서울시 글램핑존 실시간 현황 및 히스토리 (seoul/STATUS.md) 바로가기](seoul/STATUS.md)**  
> 깃허브 저장소에서 언제든지 2박(금,토) 연박 가능 자리, 실시간 잔여석, 최근 알림 발송 이력을 표 형태로 확인하실 수 있습니다.

국립공원공단 예약시스템([res.knps.or.kr](https://res.knps.or.kr))의 실시간 잔여석을 감시하여, **원하는 야영장 / 생태탐방원 / 날짜 / 인실**에 빈자리가 생기면 즉시 **스마트폰 푸시 알림(디스코드, 텔레그램, 이메일)**을 발송해 주는 프로그램입니다.

매일 **아침 06시와 저녁 18시 전체 잔여석 정기 종합 브리핑(1일 2회)**을 제공하며, 이후 **5분마다 취소표 발생 및 상태 변동(🔵 즉시예약 / 🟡 대기접수 / 🔴 완전마감)**을 실시간으로 감지하여 직관적인 신호등 형태로 알려줍니다.

---

## ✨ 주요 기능

1. **전국 48개 국립공원 야영장 지원**
   - 가야산, 지리산, 설악산, 덕유산, 치악산, 북한산, 변산반도, 태안해안 등 전국 48개 국립공원 야영장 전체 지원
2. **야영장별 맞춤 시설 타입(types) 개별 매칭 & 세밀한 필터링**
   - **야영장-타입 동시 선택**: 고사포2는 `특화야영장`, 설악동은 `자동차야영장`, 소금강산은 `카라반` 등 각 야영장마다 원하는 시설 타입을 개별 지정하여 알림 수신
   - **날짜 필터**: 특정 날짜 리스트(예: `2026-10-03`), 기간 범위(시작일~종료일), 요일 필터(예: 금, 토, 일)
   - **사이트 번호 필터**: 특정 명당 자리(예: `A13`, `15`)만 지정 가능
   - **대기 예약 포함 여부**: 즉시 예약 가능(`R`)만 볼지, 대기 예약(`W`)도 포함할지 선택 가능
3. **🔥 주말 2박(금,토) 연박 예약 가능 전용 긴급 알림 (완전 즉시예약 2박 엄격 판정)**
   - 동일 영지(사이트 번호 일치)에서 금요일과 토요일 연속 2박이 가능해지면 놓치지 않도록 **단독 긴급 알림**을 즉시 발송합니다.
   - **완전 즉시예약(R+R) 우선 원칙**: 대기예약(W)이 섞인 자리는 2박 연박 긴급 알림에서 제외하고, **양일 모두 즉시 예약 가능(🔵 예약+예약)**인 확실한 2박 자리만 선별하여 긴급 알림을 발송합니다.
   - 변동 알림 및 정기 브리핑 메시지 상단에도 `🔥 2박연박` 배너를 함께 표시하여 우선순위를 한눈에 파악할 수 있습니다.
4. **06:00 & 18:00 정기 기준선(Baseline) 종합 브리핑 (1일 2회)**
   - 매일 아침 06시와 저녁 18시, 설정된 야영장의 전체 잔여석 현황을 디스코드/텔레그램으로 브리핑하고 기준선(Baseline)을 갱신합니다.
5. **5분 실시간 변동(🔵 즉시예약 / 🟡 대기접수 / 🔴 완전마감) 감지 & 해당 날짜별 잔여석 표기**
   - 직전 5분 상태 및 일일 기준선과 비교하여 **6가지 상태 전이(Transition)**를 3색 신호등 체계로 정확하게 분류하여 전달합니다:
     - 🔵 **즉시 예약 가능 (Blue Light)**: 취소표 발생(`마감 ➔ 예약가능`) 또는 대기표 승격(`대기예약 ➔ 예약가능`)으로 즉시 결제 가능한 자리
     - 🟡 **대기 접수 가능 (Yellow Light)**: 예약 마감 후 대기 오픈(`마감 ➔ 대기예약`) 또는 즉시 예약 소진으로 대기 전환(`예약가능 ➔ 대기예약`)된 자리
     - 🔴 **예약 완전 마감 (Red Light)**: 대기 순번까지 모두 소진되어 예약 목록에서 완전히 마감된 자리(`예약가능/대기예약 ➔ 마감`)
   - 취소표나 마감 등 변동이 발생했을 때, 변동이 일어난 **해당 날짜에 한정한 잔여석(예: 2026-10-31(토) 2자리)**을 정확하게 계산하여 혼동 없이 즉시 파악할 수 있습니다.
   - 변동이 없으면 불필요한 알림 없이 조용히 넘어갑니다.
6. **빠른 간편예약 링크 제공**
   - 알림 수신 즉시 클릭 한 번으로 국립공원 간편예약 페이지로 이동할 수 있습니다.

---

## 🗂️ 데이터 저장 위치 및 분리 현황

본 프로젝트는 **야영장(Campsite)**과 **생태탐방원(Eco Center)**이 완벽하게 독립된 전용 폴더 및 파일로 분리되어 관리됩니다. 서로 다른 기능을 감시하더라도 설정 및 상태 파일 간 간섭이나 동시 푸시 충돌이 전혀 발생하지 않습니다.

| 구분 | 🏕️ 국립공원 야영장 | 🏡 국립공원 생태탐방원 |
| :--- | :--- | :--- |
| **모니터링 대상** | 전국 48개 국립공원 야영장 영지/카라반 | 전국 10개 국립공원 생태탐방원 생활관(객실) |
| **설정 파일 (YAML)** | [`campsite/config.yaml`](campsite/config.yaml) | [`eco/config.yaml`](eco/config.yaml) |
| **설정 파일 (JSON 백업)** | [`campsite/config.json`](campsite/config.json) | [`eco/config.json`](eco/config.json) |
| **실시간 현황판 (Markdown)** | [`campsite/STATUS.md`](campsite/STATUS.md) | [`eco/STATUS.md`](eco/STATUS.md) |
| **이전 상태 캐시 (JSON)** | [`campsite/last_state.json`](campsite/last_state.json) | [`eco/last_state.json`](eco/last_state.json) |
| **메인 실행 파일** | [`campsite/main.py`](campsite/main.py) | [`eco/main.py`](eco/main.py) |
| **5분 실시간 워크플로우** | [`.github/workflows/knps_monitor.yml`](.github/workflows/knps_monitor.yml) | [`.github/workflows/eco_monitor.yml`](.github/workflows/eco_monitor.yml) |
| **06:00, 18:00 정기 종합 리포트** | [`.github/workflows/daily_report.yml`](.github/workflows/daily_report.yml) (야영장 & 생태탐방원 동시 브리핑) | [`.github/workflows/daily_report.yml`](.github/workflows/daily_report.yml) (야영장 & 생태탐방원 동시 브리핑) |

---

### 1. 🔥 주말 2박(금,토) 연박 전용 긴급 알림 (완전 즉시예약 2박)
> 🔥 **[변산반도 고사포2 (특화야영장)] 주말 2박(금,토) 연박 가능 자리 발견! (🔵 즉시2박 1개)**  
> 
> 🎉 **금요일과 토요일 연속 2박 숙박이 가능한 자리가 나왔습니다!**  
> 2박 연박은 가장 먼저 마감되므로 지금 바로 예약하세요.  
> 
> 🏕️ **특화야영장 15번 🔵 [즉시 2박 예약]**  
> 📅 **2026-10-02 (금) ~ 2026-10-03 (토)**  
> • 금: **예약가능** | 토: **예약가능**  
> • 요금 합계: **60,000원**  
> 
> [👉 국립공원 예약시스템 바로가기]

### 2. 06시 / 18시 정기 종합 브리핑 (Regular Baseline)
> 📊 **[변산반도 고사포2 (특화야영장)] 정기 빈자리 종합 리포트 (2자리)**
> 
> 🔥 **[주말 2박(금,토) 연박 가능 영지]**  
> • 특화야영장 15번: 2026-10-02(금) ~ 2026-10-03(토)  
> 
> 📅 **2026-10-02 (금)**  
> • 특화야영장: 15  
> 📅 **2026-10-03 (토)**  
> • 특화야영장: 15, 18  
> [👉 국립공원 예약시스템으로 바로가기]

### 3. 5분 실시간 변동 알림 (즉시예약 🔵 / 대기접수 🟡 / 완전마감 🔴)
> 🚀 **[변산반도 고사포2 (특화야영장)] 즉시 예약 가능한 빈자리 발견! (🔵 +2 / 🟡 1대기 / 🔴 -1)**  
> *현재 잔여석: **2026-10-03(금) 2자리***
> 
> 🔵 **즉시 예약 가능 (+2자리)**  
> 📅 **2026-10-03 (금)**  
> • 특화야영장 15: **마감 ➔ 예약가능**  
> • 특화야영장 18: **대기예약 ➔ 예약가능**  
> 
> 🟡 **대기 접수 가능 (1자리)**  
> 📅 **2026-10-03 (금)**  
> • 특화야영장 12: **예약가능 ➔ 대기예약**  
> 
> 🔴 **예약 완전 마감 (-1자리)**  
> 📅 **2026-10-04 (토)**  
> • 특화야영장 07: **예약가능 ➔ 마감**  
> 
> [👉 국립공원 예약시스템으로 바로가기]

---

## 🚀 설정 및 사용 가이드

### 1단계: 원하는 야영장 및 시설 타입 확인

터미널에서 아래 명령어를 실행하여 원하는 야영장의 이름과 시설 유형을 확인합니다.

```bash
# 1. 전국 48개 국립공원 야영장 목록 및 코드 확인
python campsite/main.py --list

# 2. 특정 야영장의 세부 시설 타입 확인 (예: 고사포2, 소금강산, 백운동 등)
python campsite/main.py --types 고사포2
# 출력 예시:
# • 자동차야영장
# • 특화야영장
```

---

### 2단계: `config.yaml` (또는 `config.json`) 설정

원하는 조건에 맞게 `config.yaml` 파일을 수정합니다:

```yaml
# 1. 감시할 야영장 및 시설 타입 (야영장별로 원하는 타입을 함께 지정 가능!)
campsites:
  - park_name: "변산반도"
    camp_name: "고사포2"
    dept_id: "B181004"
    types: ["특화야영장"] # 예: 고사포2는 특화야영장만 감시

  - park_name: "설악산"
    camp_name: "설악동"
    dept_id: "B031005"
    types: ["자동차야영장"] # 예: 설악동은 자동차야영장만 감시

  - park_name: "오대산"
    camp_name: "소금강산"
    dept_id: "B061001"
    types: ["카라반"]     # 예: 소금강산은 카라반만 감시
    # (types 를 생략하거나 비워두면 해당 야영장의 모든 시설 타입을 감시합니다)

# 2. 필터링 조건
filters:
  # 원하는 특정 날짜 (비워두면 기간 또는 전체)
  target_dates: []
  start_date: ""
  end_date: ""

  # 요일 필터 (금, 토, 일에만 가고 싶을 때)
  target_weekdays: ["금", "토"]

  # [선택] 전역 기본 시설 타입 (위 campsites에 types가 없을 때 기본 적용)
  target_types: []

  # 대기 예약 포함 여부 (false: 즉시 예약가능만, true: 대기예약도 포함)
  include_waiting: true

# 3. 알림 설정
notification:
  only_new_slots: true        # 새로 열린 자리만 알림 (도배 방지)
  notify_closed_slots: true   # 예약 마감된 자리도 변동 내역에 포함할지 여부
  notify_status_changes: true # 예약가능 ➔ 대기예약 상태변경 알림 포함
  notify_consecutive_weekend: true   # 주말 2박(금,토) 연박 발생 시 단독 긴급 알림
  consecutive_include_waiting: true  # 4가지 케이스(1.대기+예약, 2.예약+대기, 3.예약+예약, 4.대기+대기) 모두 알림

  # [디스코드 웹훅]
  discord:
    enabled: true
    webhook_url: "YOUR_DISCORD_WEBHOOK_URL"
```

---

### 3단계: 알림 수신 채널 연동 (디스코드 / 텔레그램)

#### 옵션 A: 디스코드 (Discord) - 30초 소요 (가장 추천 💬)
1. 디스코드 서버 내 알림을 받을 채널의 **[채널 설정(톱니바퀴)] > [연동] > [웹후크]** 클릭
2. **[새 웹후크 만들기]** 클릭 후 **[웹후크 URL 복사]** 클릭
3. 복사한 URL을 `config.yaml` 에 입력하거나 GitHub Secrets에 `DISCORD_WEBHOOK_URL`로 등록합니다.

#### 옵션 B: 텔레그램 (Telegram) 📱
1. 텔레그램 앱에서 `@BotFather` 를 검색하여 대화를 시작하고 `/newbot` 으로 봇을 생성합니다.
2. 발급받은 **HTTP API 토큰**을 복사합니다.
3. `@userinfobot` 을 검색하여 본인의 **채팅 ID(숫자)** 를 확인합니다.
4. 방금 만든 봇 채팅방에 들어가서 `/start` 메시지를 한 번 보낸 후, 토큰과 ID를 등록합니다.

#### 🔔 로컬에서 알림 테스트해보기
```bash
python main.py --test-alert
```

---

### 4단계: GitHub Actions & 외부 무료 크론(cron-job.org) 연동

GitHub Actions 자체 스케줄러(`schedule: cron`)는 무료 티어에서 수십 분~수 시간 지연되는 고질적인 문제가 있습니다. 따라서 무료 웹 크론 서비스([cron-job.org](https://cron-job.org))를 연동하여 **정각/정시에 1초 오차 없이 안정적으로 실행**하도록 구성합니다.

#### 1. GitHub 워크플로우 구성
- `.github/workflows/daily_report.yml`: 매일 새벽 01:00 KST 전체 종합 리포트 및 당일 기준선(Baseline) 확립
- `.github/workflows/knps_monitor.yml`: 5분 주기 실시간 변동(🔵 즉시예약 / 🟡 대기접수 / 🔴 완전마감) 감지

#### 2. cron-job.org 작업 등록 (총 2개 등록)

##### [작업 1] 야영장 5분 실시간 변동 모니터링 (`knps_monitor.yml`)
- **Title**: `KNPS Campsite 5min Monitor`
- **URL**: `https://api.github.com/repos/<GitHub_아이디>/knps-camp-notifier/actions/workflows/knps_monitor.yml/dispatches`
- **Execution Schedule**: Every 5 minutes (`*/5 * * * *`)
- **Request Method**: `POST`
- **Headers**:
  - `Authorization`: `Bearer <GitHub_Personal_Access_Token>`
  - `Accept`: `application/vnd.github.v3+json`
  - `Content-Type`: `application/json`
  - `User-Agent`: `cron-job-org`
- **Request Body**: `{"ref": "main"}`

##### [작업 2] 야영장 & 생태탐방원 매일 새벽 01:00 일일 종합 브리핑 (`daily_report.yml`)
- **Title**: `KNPS Daily 1AM Report (Campsite & Eco Center)`
- **URL**: `https://api.github.com/repos/<GitHub_아이디>/knps-camp-notifier/actions/workflows/daily_report.yml/dispatches`
- **Execution Schedule**:
  - Timezone: `Asia/Seoul` 선택 시 ➔ 매일 `01:00` (User-defined cron: `0 1 * * *`)
  - (또는 UTC 기준 시 ➔ 매일 `16:00` / `0 16 * * *`)
- **Request Method**: `POST`
- **Headers**:
  - `Authorization`: `Bearer <GitHub_Personal_Access_Token>`
  - `Accept`: `application/vnd.github.v3+json`
  - `Content-Type`: `application/json`
  - `User-Agent`: `cron-job-org`
- **Request Body**: `{"ref": "main"}`

##### [작업 3] 생태탐방원 실시간 독립 모니터링 (`eco_monitor.yml`)
- **Title**: `KNPS Eco Center 5min Monitor`
- **URL**: `https://api.github.com/repos/<GitHub_아이디>/knps-camp-notifier/actions/workflows/eco_monitor.yml/dispatches`
- **Execution Schedule**: Every 5 minutes (`*/5 * * * *`) (또는 원하는 주기)
- **Request Method**: `POST`
- **Headers**:
  - `Authorization`: `Bearer <GitHub_Personal_Access_Token>`
  - `Accept`: `application/vnd.github.v3+json`
  - `Content-Type`: `application/json`
  - `User-Agent`: `cron-job-org`
- **Request Body**: `{"ref": "main"}`

---

## 🛠️ CLI 유용한 명령어 모음

### 🏕️ 야영장 모니터링
| 명령어 | 설명 |
|---|---|
| `python campsite/main.py --list` | 전국 48개 국립공원 야영장 목록 및 코드 출력 |
| `python campsite/main.py --types <야영장명>` | 해당 야영장에 설치된 시설 타입(특화야영장, 카라반 등) 확인 |
| `python campsite/main.py --check` | 알림을 보내지 않고 현재 빈자리 현황만 콘솔로 즉시 확인 |
| `python campsite/main.py --check --daily` | 정기(06시/18시) 종합 브리핑 모드로 콘솔 조회 |
| `python campsite/main.py --daily` | 정기(06시/18시) 종합 리포트 발송 및 당일 기준선(Baseline) 확립 |
| `python campsite/main.py --test-alert` | 설정된 알림 채널(디스코드/텔레그램/이메일)로 테스트 메시지 발송 |
| `python campsite/main.py --reset-state` | 이전에 기록된 상태 이력(`campsite/last_state.json`) 초기화 |
| `python campsite/main.py` | 일반 5분 변동 모니터링 실행 (변동 감지 시 알림 발송) |

### 🏡 생태탐방원 모니터링 (독립 모듈)
| 명령어 | 설명 |
|---|---|
| `python eco/main.py --list` | 전국 10개 생태탐방원 목록 및 코드 출력 |
| `python eco/main.py --check` | 알림을 보내지 않고 현재 잔여 객실 현황만 콘솔로 즉시 확인 |
| `python eco/main.py --check --daily` | 정기(06시/18시) 종합 브리핑 모드로 콘솔 조회 |
| `python eco/main.py --daily` | 생태탐방원 정기(06시/18시) 종합 리포트 발송 및 당일 기준선 확립 |
| `python eco/main.py --test` | 생태탐방원 알림 채널 연동 테스트 메시지 발송 |
| `python eco/main.py --dry-run` | 알림 발송 및 상태 저장 없이 조회만 수행 |
| `python eco/main.py` | 생태탐방원 실시간 변동 모니터링 실행 (변동 감지 시 알림 및 `eco/STATUS.md` 갱신) |

---

## 📋 파일 구조

```
knps-camp-notifier/
├── .github/
│   └── workflows/
│       ├── build_app.yml      # [모바일 앱] 안드로이드용 APK 자동 빌드 및 Releases 배포 워크플로우
│       ├── daily_report.yml   # [야영장 & 생태탐방원] 매일 06:00, 18:00 정기 실행 (기준선 확립 및 전체 브리핑)
│       ├── knps_monitor.yml   # [야영장] 5분 주기 변동(오픈/마감) 감지 독립 워크플로우
│       └── eco_monitor.yml    # [생태탐방원] 5분 주기 독립 모니터링 워크플로우
│
├── app/                       # 📱 Flutter 안드로이드 모바일 설정 앱 (Material 3)
│   ├── lib/
│   │   ├── data/             # 전국 48개 야영장 & 10개 생태탐방원 메타데이터
│   │   ├── models/           # YAML 파서 및 설정 데이터 모델
│   │   ├── screens/          # 야영장 설정 / 생태탐방원 설정 / GitHub PAT 설정 화면
│   │   ├── services/         # GitHub REST API 자동 커밋 & 푸시 서비스
│   │   └── main.dart         # Flutter 모바일 앱 메인 엔트리포인트
│   └── pubspec.yaml
│
├── campsite/                  # 🏕️ 국립공원 야영장 모니터링 모듈
│   ├── __init__.py
│   ├── main.py               # 야영장 메인 실행 파일
│   ├── crawler.py            # 야영장 실시간 예약 크롤러
│   ├── data.py               # 전국 48개 야영장 메타데이터
│   ├── notifier.py           # 야영장 디스코드 Embed & 메시지 포맷터
│   ├── reporter.py           # campsite/STATUS.md 생성기
│   ├── config.yaml           # 야영장 모니터링 설정 (YAML)
│   ├── config.json           # 야영장 설정 백업 (JSON)
│   ├── last_state.json       # 야영장 직전 상태 캐시
│   └── STATUS.md             # 야영장 실시간 잔여석 대시보드
│
├── eco/                       # 🏡 국립공원 생태탐방원 모니터링 모듈
│   ├── __init__.py
│   ├── main.py               # 생태탐방원 메인 실행 파일
│   ├── crawler.py            # 생태탐방원 공식 API 크롤러 & 2박연박 엔진
│   ├── data.py               # 전국 10개 생태탐방원 메타데이터
│   ├── notifier.py           # 생태탐방원 디스코드 Embed & 메시지 포맷터
│   ├── reporter.py           # eco/STATUS.md 생성기
│   ├── config.yaml           # 생태탐방원 모니터링 설정 (YAML)
│   ├── config.json           # 생태탐방원 설정 백업 (JSON)
│   ├── last_state.json       # 생태탐방원 직전 상태 캐시
│   └── STATUS.md             # 생태탐방원 실시간 잔여 객실 대시보드
│
├── common/                    # 🔗 공통 네트워크 & 전송 모듈
│   ├── __init__.py
│   └── notifier.py           # 텔레그램, 디스코드, 이메일 공통 전송 함수
│
├── .gitignore
├── README.md                  # 프로젝트 설명서 및 통합 바로가기
└── requirements.txt
```
