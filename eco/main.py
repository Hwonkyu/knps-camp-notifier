"""
국립공원 생태탐방원 빈자리 모니터링 메인 실행 프로그램
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

import data as eco_data
import crawler as eco_crawler
import notifier as eco_notifier
import reporter as eco_reporter

ECO_STATE_FILE = os.path.join(BASE_DIR, "last_state.json")
ECO_CONFIG_YAML_FILE = os.path.join(BASE_DIR, "config.yaml")
ECO_CONFIG_JSON_FILE = os.path.join(BASE_DIR, "config.json")


def load_eco_config() -> Dict[str, Any]:
    """
    생태탐방원 설정 파일(eco_config.yaml 또는 eco_config.json)을 로드하고 환경 변수를 병합합니다.
    """
    config = {}
    loaded = False

    # 1. YAML 시도
    if os.path.exists(ECO_CONFIG_YAML_FILE):
        try:
            import yaml
            with open(ECO_CONFIG_YAML_FILE, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                if config:
                    loaded = True
        except ImportError:
            pass

    # 2. JSON 시도
    if not loaded and os.path.exists(ECO_CONFIG_JSON_FILE):
        try:
            with open(ECO_CONFIG_JSON_FILE, "r", encoding="utf-8") as f:
                config = json.load(f) or {}
                if config:
                    loaded = True
        except Exception:
            pass

    if not config:
        print("[경고] 설정 파일을 찾을 수 없어 기본 설정을 사용합니다.")
        config = {
            "eco_centers": [
                {"name": "북한산", "dept_id": "B971002"},
                {"name": "설악산", "dept_id": "B301002"},
                {"name": "소백산", "dept_id": "B123002"},
                {"name": "변산반도", "dept_id": "B183001"},
            ],
            "filters": {"target_weekdays": ["금", "토"], "pet_only": False},
            "notification": {"only_new_slots": True, "notify_closed_slots": True}
        }

    # 환경 변수 오버라이드 (GitHub Actions Secrets)
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


def get_eco_users(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    생태탐방원 설정에서 사용자 목록을 반환합니다.
    레거시 단일 사용자 설정인 경우에도 호환되도록 단일 유저 리스트를 생성합니다.
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
        "eco_centers": config.get("eco_centers", []),
        "filters": config.get("filters", {})
    }]


def load_eco_state() -> Dict[str, Any]:
    """
    이전 상태 파일(eco_last_state.json)을 로드합니다.
    """
    if os.path.exists(ECO_STATE_FILE):
        try:
            with open(ECO_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("centers", {})
                    data.setdefault("history", [])
                    return data
        except Exception:
            pass
    return {"centers": {}, "history": [], "baseline_at": "", "updated_at": ""}


def save_eco_state(state: Dict[str, Any]):
    """
    현재 상태를 eco_last_state.json에 저장합니다.
    """
    state["updated_at"] = datetime.now().isoformat()
    with open(ECO_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def cmd_list():
    """
    전국 10개 국립공원 생태탐방원 목록을 출력합니다.
    """
    print("=" * 65)
    print(f"{'권역':<8} | {'생태탐방원':<15} | {'코드(dept_id)':<15} | {'위치'}")
    print("-" * 65)
    for c in eco_data.ECO_CENTERS:
        print(f"{c['region']:<8} | {c['name']:<15} | {c['dept_id']:<15} | {c['location']}")
    print("=" * 65)
    print(f"총 {len(eco_data.ECO_CENTERS)}개 국립공원 생태탐방원")
    print("eco_config.yaml 에 원하는 생태탐방원의 이름과 dept_id를 입력하세요.")


def cmd_test_alert(config: Dict[str, Any]):
    """
    설정된 알림 채널로 테스트 알림을 발송합니다.
    """
    users = get_eco_users(config)
    active_users = [u for u in users if u.get("enabled", True)]
    if not active_users:
        print("[경고] 활성화된 사용자(enabled: true)가 없습니다.")
        return

    print("생태탐방원 알림 채널 연동 테스트를 시작합니다...")
    today_str = datetime.now().strftime("%Y-%m-%d")

    dummy_blue = [
        {
            "slot_id": "dummy_1",
            "prd_name": "[204호] 4인실 침대(숲전망)",
            "capacity": 4,
            "price": 80000,
            "date": today_str,
            "dow": "금",
            "pet_allowed": False
        },
        {
            "slot_id": "dummy_2",
            "prd_name": "[자연의집] 6인실 독채",
            "capacity": 6,
            "price": 120000,
            "date": today_str,
            "dow": "금",
            "pet_allowed": True
        }
    ]
    dummy_red = [
        {
            "slot_id": "dummy_3",
            "prd_name": "[102호] 2인실 온돌",
            "capacity": 2,
            "price": 60000,
            "date": today_str,
            "dow": "토",
            "pet_allowed": False
        }
    ]
    dummy_consecutive = [
        {
            "pair_id": "dummy_pair_1",
            "room_name": "[204호] 4인실 침대(숲전망)",
            "capacity": 4,
            "fri_date": today_str,
            "sat_date": today_str,
            "price_total": 160000,
            "pet_allowed": False,
        }
    ]

    for u in active_users:
        u_id = u.get("id", "user1")
        u_name = u.get("name", u_id)
        u_notif = u.get("notification", {})
        dummy_center = {
            "name": "북한산",
            "center_name": "북한산 생태탐방원",
            "dept_id": "B971002",
            "user_id": u_id,
            "user_name": u_name
        }
        print(f"\n👤 [{u_name}] 테스트 알림 발송 중...")
        eco_notifier.send_eco_change_notification(
            u_notif,
            dummy_center,
            dummy_blue,
            dummy_red,
            total_remaining=2,
            consecutive_pairs=dummy_consecutive
        )
    print("\n테스트 알림 발송 완료!")


def run_eco_monitoring(
    config: Dict[str, Any],
    dry_run: bool = False,
    is_daily: bool = False,
    send_alert: bool = True
):
    """
    생태탐방원 빈자리 모니터링 실행 (멀티 유저 지원)
    :param dry_run: True이면 알림 발송 및 파일 저장 건너뜀
    :param is_daily: True이면 06시/18시 정기 종합 브리핑 모드로 실행
    :param send_alert: False이면 알림 전송 안 함 (--check 등)
    """
    users = get_eco_users(config)
    active_users = [u for u in users if u.get("enabled", True)]
    if not active_users:
        print("[경고] 활성화된 감시 사용자(users)가 없습니다.")
        return

    state = load_eco_state()
    state_users = state.setdefault("users", {})
    # 레거시 state 호환성: 만약 state에 legacy 'centers'가 있고 users에 user1이 없으면 이관
    if "centers" in state and "user1" not in state_users and state["centers"]:
        state_users["user1"] = {"centers": dict(state["centers"])}

    report_title = "생태탐방원 정기 종합 빈자리 리포트 (06시/18시)" if is_daily else "생태탐방원 모니터링"
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {report_title} 시작 (총 {len(active_users)}명 유저)")

    for u in active_users:
        u_id = u.get("id", "user1")
        u_name = u.get("name", u_id)
        centers_cfg = u.get("eco_centers", [])
        if not centers_cfg:
            print(f"[{u_name}] 감시 대상 생태탐방원이 지정되지 않았습니다.")
            continue

        filters = u.get("filters", {})
        notif_cfg = u.get("notification", {})
        only_new = notif_cfg.get("only_new_slots", True)
        notify_closed = notif_cfg.get("notify_closed_slots", True)
        notify_consec = notif_cfg.get("notify_consecutive_weekend", True)

        target_dates = eco_crawler.generate_target_dates(filters)
        if not target_dates:
            print(f"[{u_name}] 조건에 부합하는 조회 대상 날짜가 없습니다.")
            continue

        u_state = state_users.setdefault(u_id, {"centers": {}})
        u_state_centers = u_state.setdefault("centers", {})
        is_initial_run = (not u_state_centers)

        if is_initial_run or is_daily:
            if is_initial_run:
                print(f"💡 [{u_name}] 첫 모니터링입니다. 현재 잔여 객실을 기준 상태로 저장합니다.")
            u_state["baseline_at"] = datetime.now().isoformat()

        print(f"\n👤 [{u_name}] 생태탐방원 모니터링 시작 (대상 날짜: {len(target_dates)}개 일자)")

        for c_cfg in centers_cfg:
            c_name = c_cfg.get("name") or c_cfg.get("center_name", "")
            dept_id = c_cfg.get("dept_id")

            if not dept_id:
                found = eco_data.find_eco_center(c_name)
                if found:
                    dept_id = found["dept_id"]
                    c_cfg["dept_id"] = dept_id
                else:
                    print(f"[오류] 생태탐방원 '{c_name}' 정보를 찾을 수 없습니다.")
                    continue

            center_meta = eco_data.find_eco_center(dept_id) or {"name": c_name, "dept_id": dept_id}
            center_meta = dict(center_meta)
            center_meta["user_id"] = u_id
            center_meta["user_name"] = u_name

            capacities = c_cfg.get("capacities")
            pet_only = filters.get("pet_only", False)

            try:
                print(f"🔍 [{c_name} 생태탐방원] 스캔 중 (날짜 {len(target_dates)}개)...", end=" ", flush=True)
                scan_res = eco_crawler.scan_eco_center(
                    center_meta,
                    target_dates,
                    capacities=capacities,
                    pet_only=pet_only
                )

                curr_all_rooms = scan_res["all_rooms"]
                curr_avail_rooms = scan_res["available_rooms"]
                curr_consec_pairs = scan_res["consecutive_pairs"] if notify_consec else []

                print(f"완료 (총 {len(curr_all_rooms)}개 객실 중 {len(curr_avail_rooms)}실 예약 가능)")

                prev_center_data = u_state_centers.get(dept_id, {})
                prev_rooms = prev_center_data.get("rooms", {})
                prev_consec = {p["pair_id"] for p in prev_center_data.get("consecutive_pairs", [])}

                if is_daily:
                    # 1. 정기 종합 브리핑(06시/18시) 모드
                    if send_alert and not dry_run:
                        print(f"📢 [{u_name}][{c_name}] 정기 종합 브리핑(06시/18시) 발송 (잔여: {len(curr_avail_rooms)}실, 연박: {len(curr_consec_pairs)}건)")
                        eco_notifier.send_eco_daily_report(
                            notif_cfg,
                            center_meta,
                            list(curr_avail_rooms.values()),
                            curr_consec_pairs
                        )

                    daily_summary = f"📋 정기 종합(06시/18시): 잔여 {len(curr_avail_rooms)}실 (2박 연박 {len(curr_consec_pairs)}건)"
                    daily_details = [
                        f"{r['date']}({r['dow']}) {r['prd_name']} ({r['capacity']}인실)"
                        for r in list(curr_avail_rooms.values())[:10]
                    ]
                    eco_reporter.add_eco_history_entry(
                        state,
                        f"[{u_name}] {c_name} 생태탐방원",
                        daily_summary,
                        daily_details
                    )
                else:
                    # 2. 5분 주기 실시간 변동 비교 모드
                    blue_slots = []
                    red_slots = []

                    # 새로 열린 객실 감지
                    for s_id, room in curr_avail_rooms.items():
                        if s_id not in prev_rooms:
                            blue_slots.append(room)

                    # 마감된 객실 감지
                    for s_id, prev_room in prev_rooms.items():
                        if s_id not in curr_avail_rooms:
                            red_slots.append(prev_room)

                    # 주말 2박 연박 감지
                    new_consec_pairs = [p for p in curr_consec_pairs if p["pair_id"] not in prev_consec]

                    should_notify = False
                    if not is_initial_run:
                        if blue_slots or new_consec_pairs:
                            should_notify = True
                        elif red_slots and notify_closed:
                            should_notify = True
                        elif not only_new and curr_avail_rooms:
                            should_notify = True

                    if should_notify and send_alert and not dry_run:
                        print(f"📢 [{u_name}][{c_name}] 알림 발송: +{len(blue_slots)}실 예약가능, -{len(red_slots)}실 마감, 🔥 {len(new_consec_pairs)}개 2박연박")
                        
                        # 변동이 발생한 해당 날짜에 한해서만 잔여 객실 계산
                        active_changed_items = blue_slots + red_slots
                        changed_dates = sorted(list(set(
                            r.get("date") for r in active_changed_items if r.get("date")
                        )))

                        date_rem_list = []
                        for d in changed_dates:
                            avail_on_d = [r for r in curr_avail_rooms.values() if r.get("date") == d]
                            dow = ""
                            if avail_on_d:
                                dow = avail_on_d[0].get("dow", "")
                            else:
                                for it in active_changed_items:
                                    if it.get("date") == d and it.get("dow"):
                                        dow = it.get("dow")
                                        break
                            d_label = f"{d}({dow})" if dow else d
                            cnt = len(avail_on_d)
                            date_rem_list.append(f"{d_label} {cnt}실")

                        date_remaining_str = ", ".join(date_rem_list) if date_rem_list else f"{len(curr_avail_rooms)}실"

                        eco_notifier.send_eco_change_notification(
                            notif_cfg,
                            center_meta,
                            blue_slots,
                            red_slots,
                            total_remaining=date_remaining_str,
                            consecutive_pairs=curr_consec_pairs if new_consec_pairs else None
                        )

                        summary_parts = []
                        if new_consec_pairs: summary_parts.append(f"🔥 {len(new_consec_pairs)}개 2박연박")
                        if blue_slots: summary_parts.append(f"🔵 +{len(blue_slots)}실 예약가능")
                        if red_slots: summary_parts.append(f"🔴 -{len(red_slots)}실 마감")
                        summary_str = " / ".join(summary_parts) if summary_parts else "변동"

                        details = []
                        for p in new_consec_pairs:
                            details.append(f"🔥 [2박연박] {p['room_name']}({p['capacity']}인): {p['fri_date']}~{p['sat_date']}")
                        for b in blue_slots:
                            details.append(f"🔵 [예약가능] {b['date']}({b['dow']}) {b['prd_name']}({b['capacity']}인)")
                        for r in red_slots:
                            details.append(f"🔴 [예약마감] {r['date']}({r['dow']}) {r['prd_name']}({r['capacity']}인)")

                        eco_reporter.add_eco_history_entry(
                            state,
                            f"[{u_name}] {c_name} 생태탐방원",
                            summary_str,
                            details
                        )

                # 상태 갱신 (유저별 저장)
                u_state_centers[dept_id] = {
                    "dept_id": dept_id,
                    "center_name": c_name,
                    "rooms": curr_avail_rooms,
                    "consecutive_pairs": curr_consec_pairs,
                    "updated_at": datetime.now().isoformat()
                }
            except Exception as e:
                print(f"\n   [오류] [{u_name}] {c_name} 생태탐방원 조회 중 문제 발생: {e}")

            time.sleep(0.3)

    # 레거시 호환: 최상위 centers도 동기화 (통합)
    merged_centers = {}
    for u_id, u_st in state_users.items():
        for c_id, c_data in u_st.get("centers", {}).items():
            if c_id not in merged_centers:
                merged_centers[c_id] = c_data
    state["centers"] = merged_centers

    # ECO_STATUS.md 생성 및 저장
    if not dry_run:
        eco_reporter.update_eco_status_file(state, config)
        save_eco_state(state)
        print(f"\n✅ 현황판(eco/STATUS.md) 및 상태 파일(eco/last_state.json) 업데이트 완료!")


def main():
    parser = argparse.ArgumentParser(description="국립공원 생태탐방원 빈자리 모니터링 프로그램")
    parser.add_argument("--list", action="store_true", help="전국 10개 생태탐방원 목록 출력")
    parser.add_argument("--check", action="store_true", help="알림 발송 없이 현재 잔여 객실 현황만 콘솔로 즉시 확인")
    parser.add_argument("--test", action="store_true", help="알림 채널(디스코드, 텔레그램 등) 연동 테스트")
    parser.add_argument("--dry-run", action="store_true", help="알림 발송 및 상태 저장 없이 조회만 수행")
    parser.add_argument("--daily", action="store_true", help="정기(06시/18시) 전체 빈자리 종합 리포트 모드로 실행")

    args = parser.parse_args()

    if args.list:
        cmd_list()
        return

    config = load_eco_config()

    if args.test:
        cmd_test_alert(config)
        return

    if args.check:
        run_eco_monitoring(config, dry_run=False, is_daily=args.daily, send_alert=False)
        return

    run_eco_monitoring(config, dry_run=args.dry_run, is_daily=args.daily, send_alert=True)


if __name__ == "__main__":
    main()
