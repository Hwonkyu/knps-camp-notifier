"""
국립공원 야영장 빈자리 모니터링 메인 실행 프로그램
"""

import sys
import os
import time
import json
import argparse
from datetime import datetime
from typing import Dict, Any, List

# Windows 콘솔 인코딩 대응
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import data as campsites_data
import crawler as knps_crawler
import notifier
import reporter as status_reporter
from common import analytics

STATE_FILE = os.path.join(BASE_DIR, "last_state.json")
CONFIG_JSON_FILE = os.path.join(BASE_DIR, "config.json")
CONFIG_YAML_FILE = os.path.join(BASE_DIR, "config.yaml")


def load_config() -> Dict[str, Any]:
    """
    설정 파일(config.yaml 또는 config.json)을 로드하고 환경 변수를 병합합니다.
    """
    config = {}

    # 1. YAML 지원 여부 확인 후 로드
    loaded = False
    if os.path.exists(CONFIG_YAML_FILE):
        try:
            import yaml
            with open(CONFIG_YAML_FILE, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                loaded = True
        except ImportError:
            pass

    # 2. JSON 로드 (YAML 미설치 또는 없을 때)
    if not loaded and os.path.exists(CONFIG_JSON_FILE):
        with open(CONFIG_JSON_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            loaded = True

    if not config:
        print("[경고] 설정 파일을 찾을 수 없어 기본 설정을 사용합니다.")
        config = {
            "campsites": [{"park_name": "가야산", "camp_name": "백운동", "dept_id": "B131002"}],
            "filters": {"target_weekdays": ["금", "토", "일"], "include_waiting": False},
            "notification": {"only_new_slots": True}
        }

    # 3. 환경 변수 오버라이드 (GitHub Actions Secrets 지원)
    # 단일/글로벌 설정 오버라이드
    notif = config.setdefault("notification", {})

    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat = os.getenv("TELEGRAM_CHAT_ID")
    if tg_token and tg_chat:
        tg = notif.setdefault("telegram", {})
        tg["enabled"] = True
        tg["bot_token"] = tg_token
        tg["chat_id"] = tg_chat

    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_webhook:
        dc = notif.setdefault("discord", {})
        dc["enabled"] = True
        dc["webhook_url"] = discord_webhook

    email_user = os.getenv("EMAIL_SMTP_USER")
    email_pass = os.getenv("EMAIL_SMTP_PASS")
    email_to = os.getenv("EMAIL_TO")
    if email_user and email_pass and email_to:
        em = notif.setdefault("email", {})
        em["enabled"] = True
        em["smtp_user"] = email_user
        em["smtp_pass"] = email_pass
        em["to_email"] = email_to

    # 멀티 유저별 환경 변수 오버라이드
    if "users" in config and isinstance(config["users"], list):
        for u in config["users"]:
            if not isinstance(u, dict):
                continue
            u_id = str(u.get("id", "user1")).strip()
            u_notif = u.setdefault("notification", {})
            u_dc = u_notif.setdefault("discord", {})
            u_tg = u_notif.setdefault("telegram", {})

            # Discord per-user secret
            u_wh = os.getenv(f"DISCORD_WEBHOOK_URL_{u_id.upper()}")
            if u_wh:
                u_dc["enabled"] = True
                u_dc["webhook_url"] = u_wh
            elif u_id.lower() == "user1" and discord_webhook and not u_dc.get("webhook_url"):
                u_dc["enabled"] = True
                u_dc["webhook_url"] = discord_webhook

            # Telegram per-user secret
            u_token = os.getenv(f"TELEGRAM_BOT_TOKEN_{u_id.upper()}")
            u_cid = os.getenv(f"TELEGRAM_CHAT_ID_{u_id.upper()}")
            if u_token and u_cid:
                u_tg["enabled"] = True
                u_tg["bot_token"] = u_token
                u_tg["chat_id"] = u_cid
            elif u_id.lower() == "user1" and tg_token and tg_chat and not u_tg.get("bot_token"):
                u_tg["enabled"] = True
                u_tg["bot_token"] = tg_token
                u_tg["chat_id"] = tg_chat

    return config


def get_users(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    config에서 활성화된 사용자 목록을 반환합니다.
    단일 사용자 레거시 설정인 경우 단일 유저 리스트로 변환하여 호환성을 유지합니다.
    """
    raw_users = config.get("users")
    if isinstance(raw_users, list) and raw_users:
        users = []
        for u in raw_users:
            if isinstance(u, dict):
                users.append(u)
        return users

    # 레거시 단일 사용자 fallback
    return [{
        "id": "user1",
        "name": "User 1",
        "enabled": True,
        "notification": config.get("notification", {}),
        "campsites": config.get("campsites", []),
        "filters": config.get("filters", {})
    }]


def load_state() -> Dict[str, Any]:
    """
    이전 상태 파일(last_state.json)을 로드합니다.
    """
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("campsites", {})
                    data.setdefault("history", [])
                    if "campsites" not in data and "last_notified_slot_ids" in data:
                        return {
                            "campsites": {},
                            "history": [],
                            "legacy_ids": set(data.get("last_notified_slot_ids", [])),
                            "updated_at": data.get("updated_at", "")
                        }
                    return data
        except Exception:
            pass
    return {"campsites": {}, "history": [], "baseline_at": "", "updated_at": ""}


def save_state(state: Dict[str, Any]):
    """
    현재 상태를 last_state.json에 저장합니다.
    """
    state["updated_at"] = datetime.now().isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def cmd_list():
    """
    전국 48개 국립공원 야영장 목록을 테이블 형태로 출력합니다.
    """
    print("=" * 60)
    print(f"{'공원명':<10} | {'야영장명':<15} | {'야영장 코드(dept_id)':<15}")
    print("-" * 60)
    for c in campsites_data.CAMPSITES:
        print(f"{c['park_name']:<10} | {c['camp_name']:<15} | {c['dept_id']:<15}")
    print("=" * 60)
    print(f"총 {len(campsites_data.CAMPSITES)}개 국립공원 야영장")
    print("config.yaml 또는 config.json 에 원하는 야영장의 공원명, 야영장명, dept_id를 입력하세요.")


def cmd_types(query: str):
    """
    특정 야영장의 시설 유형 목록을 조회합니다.
    """
    camp = campsites_data.find_campsite(query)
    if not camp:
        print(f"[오류] '{query}' 에 해당하는 야영장을 찾을 수 없습니다. (--list 로 확인하세요)")
        return

    print(f"[{camp['park_name']} - {camp['camp_name']}] 시설 유형 조회 중...")
    try:
        html = knps_crawler.fetch_campsite_html(camp["park_name"], camp["camp_name"], camp["dept_id"])
        types = knps_crawler.parse_campsite_types(html)
        if not types:
            print("등록된 시설 유형 정보를 찾지 못했습니다.")
            return

        print("-" * 40)
        for t in types:
            print(f"• 코드: {t['code']:<8} | 시설명: {t['name']}")
        print("-" * 40)
        print("config.yaml 의 filters.target_types 에 위 시설명을 입력할 수 있습니다.")
    except Exception as e:
        print(f"[오류] 시설 조회 실패: {e}")


def cmd_test_alert(config: Dict[str, Any]):
    """
    설정된 알림 채널로 테스트 알림을 발송합니다.
    """
    print("알림 채널 연동 테스트를 시작합니다...")
    dummy_camp = {"park_name": "변산반도", "camp_name": "고사포2", "types": ["특화야영장"]}
    dummy_blue = [
        {
            "slot": {
                "site_type": "특화야영장",
                "site_num": "15",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "dow": "금",
            },
            "prev_status": "NONE",
            "curr_status": "R",
            "prev_status_text": "마감",
            "curr_status_text": "예약가능"
        },
        {
            "slot": {
                "site_type": "특화야영장",
                "site_num": "18",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "dow": "금",
            },
            "prev_status": "W",
            "curr_status": "R",
            "prev_status_text": "대기예약",
            "curr_status_text": "예약가능"
        }
    ]
    dummy_yellow = [
        {
            "slot": {
                "site_type": "특화야영장",
                "site_num": "12",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "dow": "금",
            },
            "prev_status": "R",
            "curr_status": "W",
            "prev_status_text": "예약가능",
            "curr_status_text": "대기예약"
        }
    ]
    dummy_red = [
        {
            "slot": {
                "site_type": "특화야영장",
                "site_num": "07",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "dow": "토",
            },
            "prev_status": "R",
            "curr_status": "NONE",
            "prev_status_text": "예약가능",
            "curr_status_text": "마감"
        }
    ]

    dummy_consecutive = [
        {
            "pair_id": "dummy_20261002_20261003_15_R_R",
            "spot_id": "특화야영장_15",
            "case_num": 3,
            "case_name": "예약가능 + 예약가능",
            "case_badge": "🔵 [예약 + 예약]",
            "park_name": "변산반도",
            "camp_name": "고사포2",
            "site_type": "특화야영장",
            "site_num": "15",
            "fri_date": "2026-10-02",
            "sat_date": "2026-10-03",
            "fri_slot": {"status": "R", "status_text": "예약가능", "price": 30000},
            "sat_slot": {"status": "R", "status_text": "예약가능", "price": 30000},
            "both_direct": True,
            "status_summary": "금:예약 / 토:예약 (즉시2박)",
            "price_total": 60000
        },
        {
            "pair_id": "dummy_20261002_20261003_18_R_W",
            "spot_id": "특화야영장_18",
            "case_num": 2,
            "case_name": "예약가능 + 대기예약",
            "case_badge": "🟡 [예약 + 대기]",
            "park_name": "변산반도",
            "camp_name": "고사포2",
            "site_type": "특화야영장",
            "site_num": "18",
            "fri_date": "2026-10-02",
            "sat_date": "2026-10-03",
            "fri_slot": {"status": "R", "status_text": "예약가능", "price": 30000},
            "sat_slot": {"status": "W", "status_text": "대기예약", "price": 30000},
            "both_direct": False,
            "status_summary": "금:예약 / 토:대기",
            "price_total": 60000
        },
        {
            "pair_id": "dummy_20261002_20261003_21_W_R",
            "spot_id": "특화야영장_21",
            "case_num": 1,
            "case_name": "대기예약 + 예약가능",
            "case_badge": "🟡 [대기 + 예약]",
            "park_name": "변산반도",
            "camp_name": "고사포2",
            "site_type": "특화야영장",
            "site_num": "21",
            "fri_date": "2026-10-02",
            "sat_date": "2026-10-03",
            "fri_slot": {"status": "W", "status_text": "대기예약", "price": 30000},
            "sat_slot": {"status": "R", "status_text": "예약가능", "price": 30000},
            "both_direct": False,
            "status_summary": "금:대기 / 토:예약",
            "price_total": 60000
        },
        {
            "pair_id": "dummy_20261002_20261003_25_W_W",
            "spot_id": "특화야영장_25",
            "case_num": 4,
            "case_name": "대기예약 + 대기예약",
            "case_badge": "🟠 [대기 + 대기]",
            "park_name": "변산반도",
            "camp_name": "고사포2",
            "site_type": "특화야영장",
            "site_num": "25",
            "fri_date": "2026-10-02",
            "sat_date": "2026-10-03",
            "fri_slot": {"status": "W", "status_text": "대기예약", "price": 30000},
            "sat_slot": {"status": "W", "status_text": "대기예약", "price": 30000},
            "both_direct": False,
            "status_summary": "금:대기 / 토:대기",
            "price_total": 60000
        }
    ]

    users = get_users(config)
    active_users = [u for u in users if u.get("enabled", True)]
    if not active_users:
        print("[경고] 활성화된 사용자(enabled: true)가 없습니다.")
        return

    for u in active_users:
        u_id = u.get("id", "user1")
        u_name = u.get("name", u_id)
        u_notif = u.get("notification", {})
        dummy_camp["user_id"] = u_id
        dummy_camp["user_name"] = u_name

        print(f"\n==========================================")
        print(f"👤 [{u_name}] 테스트 알림 발송 중...")
        print(f"==========================================")

        print("[테스트 1/2] 일반 빈자리 변동 알림 발송 중...")
        results = notifier.dispatch_diff_notifications(
            config=u_notif,
            campsite_info=dummy_camp,
            blue_slots=dummy_blue,
            yellow_slots=dummy_yellow,
            red_slots=dummy_red,
            total_remaining_count=3,
            consecutive_pairs=dummy_consecutive
        )
        if not results:
            print(f"[경고] [{u_name}] 활성화된 알림 채널이 없습니다!")
        else:
            for ch, success in results.items():
                status = "성공 ✅" if success else "실패 ❌"
                print(f"• {ch.capitalize()}: {status}")

        print("\n[테스트 2/2] 🔥 주말 2박(금,토) 연박 전용 긴급 알림 발송 중...")
        con_results = notifier.dispatch_consecutive_notifications(
            config=u_notif,
            campsite_info=dummy_camp,
            consecutive_pairs=dummy_consecutive
        )
        for ch, success in con_results.items():
            status = "성공 ✅" if success else "실패 ❌"
            print(f"• {ch.capitalize()}: {status}")


def run_monitor(config: Dict[str, Any], send_alert: bool = True, is_daily: bool = False):
    """
    설정된 사용자별 야영장들의 빈자리를 조회하고 조건에 맞으면 알림을 발송합니다.
    - is_daily=True: 매일 06시/18시 전체 잔여석 종합 리포트 발송 및 정기 기준선(baseline) 저장.
    - is_daily=False: 이전 상태 대비 6대 변동(🔵 파란 불: 즉시예약 / 🟡 노란 불: 대기접수 / 🔴 빨간 불: 완전마감) 감지 및 알림 발송.
    """
    users = get_users(config)
    active_users = [u for u in users if u.get("enabled", True)]
    if not active_users:
        print("[오류] 활성화된 감시 사용자(users)가 없습니다.")
        return

    state = load_state()
    analytics.seed_from_history_if_needed(state)
    state_users = state.setdefault("users", {})
    # 레거시 state 호환성: 만약 state에 legacy 'campsites'가 있고 users에 user1이 없으면 이관
    if "campsites" in state and "user1" not in state_users and state["campsites"]:
        state_users["user1"] = {"campsites": dict(state["campsites"])}

    report_title = "정기 빈자리 종합 리포트 (06시/18시 기준선 확립)" if is_daily else "실시간 빈자리 변동 모니터링"
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 국립공원 야영장 {report_title} 시작 (총 {len(active_users)}명 유저)")

    # 5분 실행 내 중복 HTTP 크롤링 방지를 위한 인메모리 캐시 (야영장 단위)
    slots_cache: Dict[str, List[Dict[str, Any]]] = {}

    total_changes_notified = 0

    for u in active_users:
        u_id = u.get("id", "user1")
        u_name = u.get("name", u_id)
        u_campsites = u.get("campsites", [])
        u_filters = u.get("filters", {})
        u_notif = u.get("notification", {})

        only_new_slots = u_notif.get("only_new_slots", True)
        notify_closed_slots = u_notif.get("notify_closed_slots", True)
        notify_status_changes = u_notif.get("notify_status_changes", True)
        notify_consecutive = u_notif.get("notify_consecutive_weekend", u_filters.get("notify_consecutive_weekend", True))
        consecutive_waiting = u_notif.get("consecutive_include_waiting", u_filters.get("consecutive_include_waiting", True))

        u_state = state_users.setdefault(u_id, {"campsites": {}})
        camp_states = u_state.setdefault("campsites", {})

        print(f"\n👤 [{u_name}] 야영장 모니터링 시작 ({len(u_campsites)}개소)")
        if not u_campsites:
            print(f"   ℹ️ 감시 대상 야영장이 없습니다.")
            continue

        for c_item in u_campsites:
            camp = campsites_data.resolve_campsite(
                c_item.get("park_name", ""),
                c_item.get("camp_name", ""),
                c_item.get("dept_id", "")
            )
            if not camp:
                print(f"   [경고] 야영장 정보를 찾을 수 없습니다: {c_item}")
                continue

            camp = dict(camp)
            camp["user_id"] = u_id
            camp["user_name"] = u_name
            p_name = camp["park_name"]
            c_name = camp["camp_name"]
            d_id = camp["dept_id"]

            camp_types_raw = c_item.get("types") or c_item.get("target_types") or c_item.get("type")
            if camp_types_raw is not None:
                if isinstance(camp_types_raw, str):
                    camp_types = [camp_types_raw.strip()] if camp_types_raw.strip() else []
                elif isinstance(camp_types_raw, (list, tuple, set)):
                    camp_types = [str(t).strip() for t in camp_types_raw if str(t).strip()]
                else:
                    camp_types = []
            else:
                camp_types = u_filters.get("target_types")

            camp_sites_raw = c_item.get("sites") or c_item.get("target_sites") or c_item.get("site")
            if camp_sites_raw is not None:
                if isinstance(camp_sites_raw, str):
                    camp_sites = [camp_sites_raw.strip()] if camp_sites_raw.strip() else []
                elif isinstance(camp_sites_raw, (list, tuple, set)):
                    camp_sites = [str(s).strip() for s in camp_sites_raw if str(s).strip()]
                else:
                    camp_sites = []
            else:
                camp_sites = u_filters.get("target_sites")

            camp["types"] = camp_types
            camp["sites"] = camp_sites

            types_label = f" [{', '.join(camp_types)}]" if camp_types else ""
            print(f"   🔎 [{p_name} - {c_name}{types_label}] 현황 조회 중...")

            try:
                # 인메모리 캐시 확인 (동일 야영장 중복 호출 방지)
                if d_id not in slots_cache:
                    html = knps_crawler.fetch_campsite_html(p_name, c_name, d_id)
                    all_slots = knps_crawler.parse_available_slots(html, dept_id=d_id)
                    slots_cache[d_id] = all_slots
                    time.sleep(0.5)
                else:
                    all_slots = slots_cache[d_id]

                # 사용자별 필터 적용
                matched_slots = knps_crawler.filter_slots(
                    slots=all_slots,
                    target_dates=u_filters.get("target_dates"),
                    start_date=u_filters.get("start_date"),
                    end_date=u_filters.get("end_date"),
                    target_dows=u_filters.get("target_weekdays"),
                    target_types=camp_types,
                    target_sites=camp_sites,
                    include_waiting=u_filters.get("include_waiting", False)
                )

                curr_slots_map = {s.get("site_key", s["slot_id"]): s for s in matched_slots}
                print(f"      -> 전체 {len(all_slots)}개 중 [{u_name}] 조건 부합: {len(matched_slots)}개")

                if consecutive_waiting:
                    consecutive_cand_slots = knps_crawler.filter_slots(
                        slots=all_slots,
                        target_dates=u_filters.get("target_dates"),
                        start_date=u_filters.get("start_date"),
                        end_date=u_filters.get("end_date"),
                        target_dows=u_filters.get("target_weekdays"),
                        target_types=camp_types,
                        target_sites=camp_sites,
                        include_waiting=True
                    )
                else:
                    consecutive_cand_slots = matched_slots

                consecutive_pairs = knps_crawler.find_consecutive_weekend_slots(
                    slots=consecutive_cand_slots,
                    include_waiting=consecutive_waiting
                )
                if consecutive_pairs:
                    c3_cnt = sum(1 for p in consecutive_pairs if p.get("case_num") == 3)
                    c12_cnt = sum(1 for p in consecutive_pairs if p.get("case_num") in (1, 2))
                    c4_cnt = sum(1 for p in consecutive_pairs if p.get("case_num") == 4)
                    print(f"      🔥 [주말 2박 연박] {len(consecutive_pairs)}개 영지 탐색됨 (즉시2박: {c3_cnt}개, 예약+대기: {c12_cnt}개, 대기2박: {c4_cnt}개)")

                state_key = f"{d_id}_{'_'.join(sorted(camp_types))}" if camp_types else d_id

                if is_daily:
                    golden_tip = analytics.generate_golden_time_summary_text(state, f"{p_name} {c_name}")
                    if send_alert:
                        res = notifier.dispatch_notifications(
                            config=u_notif,
                            campsite_info=camp,
                            available_slots=matched_slots,
                            is_daily=True,
                            consecutive_pairs=consecutive_pairs,
                            golden_time_text=golden_tip
                        )
                        for ch, ok in res.items():
                            print(f"         [정기 리포트(06시/18시) 전송] {ch}: {'성공' if ok else '실패'}")

                    camp_states[state_key] = {
                        "park_name": p_name,
                        "camp_name": c_name,
                        "types": camp_types,
                        "slots": curr_slots_map,
                        "consecutive_pairs": [p["pair_id"] for p in consecutive_pairs],
                        "consecutive_pairs_data": consecutive_pairs,
                        "last_checked": datetime.now().isoformat()
                    }
                    total_changes_notified += len(matched_slots)

                    daily_summary = f"📋 [{u_name}] 정기 종합(06시/18시): 잔여석 {len(matched_slots)}개 (2박 연박 {len(consecutive_pairs)}건)"
                    daily_details = [
                        f"{s['date']}({s['dow']}) {s['site_type']} {s['site_num']}번 ({'🔵 예약가능' if s['status'] == 'R' else '🟡 대기예약'})"
                        for s in matched_slots[:10]
                    ]
                    status_reporter.add_history_entry(
                        state=state,
                        camp_name_str=f"{p_name} {c_name} ({u_name})",
                        summary=daily_summary,
                        details=daily_details
                    )
                else:
                    prev_camp_data = camp_states.get(state_key) or camp_states.get(d_id)
                    prev_consecutive_set = set()
                    if prev_camp_data:
                        prev_consecutive_set = set(prev_camp_data.get("consecutive_pairs", []))

                    new_consecutive_pairs = [p for p in consecutive_pairs if p["pair_id"] not in prev_consecutive_set]

                    blue_slots = []
                    yellow_slots = []
                    red_slots = []

                    if prev_camp_data is None:
                        for curr_s in matched_slots:
                            if curr_s.get("status") == "R":
                                blue_slots.append({
                                    "slot": curr_s,
                                    "prev_status": "NONE",
                                    "curr_status": "R",
                                    "prev_status_text": "마감",
                                    "curr_status_text": "예약가능"
                                })
                            else:
                                yellow_slots.append({
                                    "slot": curr_s,
                                    "prev_status": "NONE",
                                    "curr_status": "W",
                                    "prev_status_text": "마감",
                                    "curr_status_text": "대기예약"
                                })
                    else:
                        raw_prev_slots = prev_camp_data.get("slots", {})
                        prev_slots_map = {}
                        for k, s in raw_prev_slots.items():
                            s_key = s.get("site_key") or ("_".join(k.rsplit("_", 1)[:-1]) if ("_R" in k or "_W" in k) else k)
                            prev_slots_map[s_key] = s

                        for k, curr_s in curr_slots_map.items():
                            curr_stat = curr_s.get("status")
                            if k not in prev_slots_map:
                                if curr_stat == "R":
                                    blue_slots.append({
                                        "slot": curr_s,
                                        "prev_status": "NONE",
                                        "curr_status": "R",
                                        "prev_status_text": "마감",
                                        "curr_status_text": "예약가능"
                                    })
                                else:
                                    yellow_slots.append({
                                        "slot": curr_s,
                                        "prev_status": "NONE",
                                        "curr_status": "W",
                                        "prev_status_text": "마감",
                                        "curr_status_text": "대기예약"
                                    })
                            else:
                                prev_s = prev_slots_map[k]
                                prev_stat = prev_s.get("status")
                                if prev_stat != curr_stat:
                                    if curr_stat == "R":
                                        blue_slots.append({
                                            "slot": curr_s,
                                            "prev_status": prev_stat,
                                            "curr_status": "R",
                                            "prev_status_text": "대기예약",
                                            "curr_status_text": "예약가능"
                                        })
                                    else:
                                        yellow_slots.append({
                                            "slot": curr_s,
                                            "prev_status": prev_stat,
                                            "curr_status": "W",
                                            "prev_status_text": "예약가능",
                                            "curr_status_text": "대기예약"
                                        })

                        for k, prev_s in prev_slots_map.items():
                            if k not in curr_slots_map:
                                prev_stat = prev_s.get("status")
                                p_txt = "예약가능" if prev_stat == "R" else "대기예약"
                                red_slots.append({
                                    "slot": prev_s,
                                    "prev_status": prev_stat,
                                    "curr_status": "NONE",
                                    "prev_status_text": p_txt,
                                    "curr_status_text": "마감"
                                })

                    has_new_consecutive = bool(new_consecutive_pairs) and notify_consecutive
                    if has_new_consecutive:
                        print(f"      🔥 [{u_name}] 주말 2박 연박 긴급 감지! {len(new_consecutive_pairs)}개 2박 영지 신규 오픈")
                        consec_details = []
                        for p in new_consecutive_pairs:
                            f_s = p.get("fri_slot", {})
                            s_s = p.get("sat_slot", {})
                            f_txt = f_s.get("status_text", "예약가능" if f_s.get("status") == "R" else "대기예약")
                            s_txt = s_s.get("status_text", "예약가능" if s_s.get("status") == "R" else "대기예약")
                            badge = p.get("case_badge", "")
                            print(f"         • [🔥 2박연박] {p['fri_date']}~{p['sat_date']} | {p['site_type']} {p['site_num']}번 {badge} ({f_txt} + {s_txt})")
                            consec_details.append(f"{badge} {p['fri_date']}~{p['sat_date']} | {p['site_type']} {p['site_num']}번 ({p.get('status_summary', '')})")

                        status_reporter.add_history_entry(
                            state=state,
                            camp_name_str=f"{p_name} {c_name} ({u_name})",
                            summary=f"🔥 [{u_name}] 주말 2박(금,토) 연박 신규 {len(new_consecutive_pairs)}건 오픈",
                            details=consec_details
                        )

                        if send_alert:
                            c_res = notifier.dispatch_consecutive_notifications(
                                config=u_notif,
                                campsite_info=camp,
                                consecutive_pairs=new_consecutive_pairs
                            )
                            for ch, ok in c_res.items():
                                print(f"         [2박 연박 긴급 알림 전송] {ch}: {'성공' if ok else '실패'}")

                    has_blue = bool(blue_slots)
                    has_yellow = bool(yellow_slots) and notify_status_changes
                    has_red = bool(red_slots) and notify_closed_slots

                    if has_blue or has_yellow or has_red:
                        total_changes_notified += (len(blue_slots) + len(yellow_slots) + len(red_slots))
                        print(f"      🚨 [{u_name}] 변동 감지! (🔵 즉시예약: {len(blue_slots)}개, 🟡 대기접수: {len(yellow_slots)}개, 🔴 완전마감: {len(red_slots)}개)")
                        diff_details = []
                        if blue_slots:
                            if prev_camp_data is not None:
                                cancel_evts = []
                                for item in blue_slots:
                                    s = item["slot"]
                                    t_date = s.get("date", "")
                                    lead_days = None
                                    if t_date:
                                        try:
                                            td = datetime.strptime(t_date, "%Y-%m-%d").date()
                                            lead_days = (td - datetime.now().date()).days
                                        except Exception:
                                            pass
                                    cancel_evts.append({
                                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "camp": f"{p_name} {c_name}",
                                        "park_name": p_name,
                                        "camp_name": c_name,
                                        "target_date": t_date,
                                        "target_dow": s.get("dow", ""),
                                        "cancel_dow": analytics.WEEKDAYS_KO[datetime.now().weekday()],
                                        "cancel_hour": datetime.now().hour,
                                        "lead_days": lead_days
                                    })
                                if cancel_evts:
                                    analytics.record_cancellation_events(state, cancel_evts)

                            for item in blue_slots:
                                s = item["slot"]
                                diff_details.append(f"🔵 즉시예약: {s['date']}({s['dow']}) {s['site_type']} {s['site_num']}번 ({item['prev_status_text']} ➔ {item['curr_status_text']})")
                        if yellow_slots:
                            for item in yellow_slots:
                                s = item["slot"]
                                diff_details.append(f"🟡 대기접수: {s['date']}({s['dow']}) {s['site_type']} {s['site_num']}번 ({item['prev_status_text']} ➔ {item['curr_status_text']})")
                        if red_slots:
                            for item in red_slots:
                                s = item["slot"]
                                diff_details.append(f"🔴 완전마감: {s['date']}({s['dow']}) {s['site_type']} {s['site_num']}번 ({item['prev_status_text']} ➔ {item['curr_status_text']})")

                        summary_parts = []
                        if blue_slots: summary_parts.append(f"🔵 즉시예약 {len(blue_slots)}건")
                        if yellow_slots: summary_parts.append(f"🟡 대기접수 {len(yellow_slots)}건")
                        if red_slots: summary_parts.append(f"🔴 완전마감 {len(red_slots)}건")

                        status_reporter.add_history_entry(
                            state=state,
                            camp_name_str=f"{p_name} {c_name} ({u_name})",
                            summary=f"[{u_name}] " + (", ".join(summary_parts) if summary_parts else "변동 발생"),
                            details=diff_details
                        )

                        if send_alert:
                            active_changed_items = blue_slots + (yellow_slots if notify_status_changes else []) + (red_slots if notify_closed_slots else [])
                            changed_dates = sorted(list(set(
                                (item.get("slot") or item).get("date")
                                for item in active_changed_items
                                if (item.get("slot") or item).get("date")
                            )))

                            date_rem_list = []
                            for d in changed_dates:
                                r_slots_on_d = [s for s in matched_slots if s.get("date") == d and s.get("status") == "R"]
                                w_slots_on_d = [s for s in matched_slots if s.get("date") == d and s.get("status") == "W"]
                                dow = ""
                                if r_slots_on_d:
                                    dow = r_slots_on_d[0].get("dow", "")
                                else:
                                    for it in active_changed_items:
                                        s_temp = it.get("slot") or it
                                        if s_temp.get("date") == d and s_temp.get("dow"):
                                            dow = s_temp.get("dow")
                                            break
                                d_label = f"{d}({dow})" if dow else d
                                r_cnt = len(r_slots_on_d)
                                w_cnt = len(w_slots_on_d)
                                if r_cnt > 0:
                                    if w_cnt > 0:
                                        date_rem_list.append(f"{d_label} {r_cnt}자리(대기 {w_cnt})")
                                    else:
                                        date_rem_list.append(f"{d_label} {r_cnt}자리")
                                else:
                                    if w_cnt > 0:
                                        date_rem_list.append(f"{d_label} 0자리(대기 {w_cnt})")
                                    else:
                                        date_rem_list.append(f"{d_label} 0자리")

                            date_remaining_str = ", ".join(date_rem_list) if date_rem_list else f"{len(matched_slots)}자리"

                            res = notifier.dispatch_diff_notifications(
                                config=u_notif,
                                campsite_info=camp,
                                blue_slots=blue_slots,
                                yellow_slots=yellow_slots if notify_status_changes else [],
                                red_slots=red_slots if notify_closed_slots else [],
                                total_remaining_count=date_remaining_str,
                                consecutive_pairs=consecutive_pairs
                            )
                            for ch, ok in res.items():
                                print(f"         [변동 알림 전송] {ch}: {'성공' if ok else '실패'}")
                    else:
                        if (red_slots and not notify_closed_slots) or (yellow_slots and not notify_status_changes):
                            print(f"      ℹ️ 변동 감지되었으나 설정에 의해 알림 생략 (마감 {len(red_slots)}개, 대기접수 {len(yellow_slots)}개)")
                        elif matched_slots:
                            print(f"      ℹ️ 기존 {len(matched_slots)}개 잔여석 변동 없음")
                        else:
                            print(f"      ℹ️ 조건에 맞는 빈자리 없음 (변동 없음)")

                    camp_states[state_key] = {
                        "park_name": p_name,
                        "camp_name": c_name,
                        "types": camp_types,
                        "slots": curr_slots_map,
                        "consecutive_pairs": [p["pair_id"] for p in consecutive_pairs],
                        "consecutive_pairs_data": consecutive_pairs,
                        "last_checked": datetime.now().isoformat()
                    }

            except Exception as e:
                print(f"   [오류] 조회 중 문제 발생: {e}")

    # 호환성을 위해 최상위 campsites에도 모든 유저의 camp_states 병합 반영
    merged_camps = {}
    for u_id, u_st in state_users.items():
        merged_camps.update(u_st.get("campsites", {}))
    state["campsites"] = merged_camps

    if is_daily:
        state["baseline_at"] = datetime.now().isoformat()
    state.pop("legacy_ids", None)
    state.pop("last_notified_slot_ids", None)

    try:
        status_reporter.update_status_file(state, config)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📄 실시간 잔여석 표(STATUS.md) 업데이트 완료")
    except Exception as e:
        print(f"   [경고] STATUS.md 파일 생성 중 오류: {e}")

    save_state(state)

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {report_title} 완료\n")


def main():
    parser = argparse.ArgumentParser(description="국립공원공단 야영장 빈자리 모니터링 프로그램")
    parser.add_argument("--list", action="store_true", help="전국 48개 국립공원 야영장 목록 및 코드 출력")
    parser.add_argument("--types", type=str, help="특정 야영장(이름 또는 코드)의 시설 유형 조회 (예: --types 백운동)")
    parser.add_argument("--check", action="store_true", help="1회 즉시 빈자리 조회 (알림 발송 없이 콘솔 출력만)")
    parser.add_argument("--status", action="store_true", help="현재 STATUS.md 실시간 현황 마크다운을 콘솔에 출력합니다.")
    parser.add_argument("--test-alert", action="store_true", help="설정된 알림 채널(텔레그램, 디스코드, 이메일)로 테스트 메시지 발송")
    parser.add_argument("--reset-state", action="store_true", help="알림 상태(last_state.json)를 초기화합니다.")
    parser.add_argument("--daily", action="store_true", help="정기(06시/18시) 전체 빈자리 종합 리포트 모드로 실행")

    args = parser.parse_args()

    if args.list:
        cmd_list()
        return

    if args.types:
        cmd_types(args.types)
        return

    if args.status:
        if os.path.exists("STATUS.md"):
            with open("STATUS.md", "r", encoding="utf-8") as f:
                print(f.read())
        else:
            print("STATUS.md 파일이 아직 생성되지 않았습니다. python main.py --check 를 먼저 실행하세요.")
        return

    if args.reset_state:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            print("알림 상태 기록이 초기화되었습니다.")
        else:
            print("초기화할 상태 파일이 없습니다.")
        return

    config = load_config()

    if args.test_alert:
        cmd_test_alert(config)
        return

    if args.check:
        run_monitor(config, send_alert=False, is_daily=args.daily)
        return

    # 일일 종합 리포트 실행
    if args.daily:
        run_monitor(config, send_alert=True, is_daily=True)
        return

    # 기본 실시간 모니터링 실행
    run_monitor(config, send_alert=True, is_daily=False)


if __name__ == "__main__":
    main()
    sys.exit(0)
