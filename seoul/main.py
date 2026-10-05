"""
서울시 공공서비스예약 (난지캠핑장 글램핑존 등) 실시간 빈자리 모니터링 메인 실행 스크립트
- 날짜를 수동으로 지정하지 않아도 당월 및 익월(다음 달) 일정을 100% 자동 감지
- 매달 15일 신규 오픈, 취소표 발생(예약마감 ➔ 접수중)을 실시간으로 포착하여 즉각 알림
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Dict, Any, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from seoul import crawler as seoul_crawler
from seoul import notifier as seoul_notifier
from seoul import reporter as seoul_reporter

SEOUL_STATE_FILE = os.path.join(BASE_DIR, "last_state.json")
SEOUL_CONFIG_YAML_FILE = os.path.join(BASE_DIR, "config.yaml")


def load_seoul_config() -> Dict[str, Any]:
    """
    seoul/config.yaml 설정 파일을 로드합니다.
    """
    if os.path.exists(SEOUL_CONFIG_YAML_FILE):
        try:
            with open(SEOUL_CONFIG_YAML_FILE, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                if cfg:
                    return cfg
        except Exception as e:
            print(f"[경고] seoul/config.yaml 로드 실패 ({e}), 기본값 사용")

    return {
        "targets": [
            {
                "id": "nanji_glamping",
                "name": "난지캠핑장 글램핑존",
                "keyword": "글램핑",
                "match_title": "글램핑",
                "enabled": True
            }
        ],
        "users": [
            {
                "id": "user1",
                "name": "User 1",
                "enabled": True,
                "notification": {
                    "only_new_slots": True,
                    "notify_closed_slots": False,
                    "notify_new_schedule_open": True,
                    "discord": {"enabled": True, "webhook_url": ""}
                }
            }
        ]
    }


def load_seoul_state() -> Dict[str, Any]:
    """
    seoul/last_state.json 상태 파일을 로드합니다.
    """
    if os.path.exists(SEOUL_STATE_FILE):
        try:
            with open(SEOUL_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception as e:
            print(f"[경고] seoul/last_state.json 파일 읽기 실패 ({e}), 새 상태로 시작합니다.")
    return {"services": {}, "history": []}


def save_seoul_state(state: Dict[str, Any]):
    """
    seoul/last_state.json 상태 파일에 현재 상태를 저장합니다.
    """
    try:
        with open(SEOUL_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[오류] seoul/last_state.json 저장 실패: {e}")


def run_seoul_monitoring(
    config: Dict[str, Any],
    send_alert: bool = True,
    is_daily: bool = False,
    dry_run: bool = False
):
    """
    서울시 공공예약 글램핑존 실시간 빈자리 모니터링을 실행합니다.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mode_str = "정기 종합 브리핑(06시/18시)" if is_daily else "실시간 변동 감지"
    print(f"[{now_str}] 🏕️ 서울시 공공예약 글램핑존 모니터링 시작 ({mode_str})")

    targets = [t for t in config.get("targets", []) if t.get("enabled", True)]
    if not targets:
        print("[정보] 활성화된 감시 대상이 없습니다.")
        return

    users = [u for u in config.get("users", []) if u.get("enabled", True)]
    state = load_seoul_state()
    prev_services = state.get("services", {})
    is_initial_run = (len(prev_services) == 0)

    all_current_services = {}

    for target in targets:
        t_name = target.get("name", "글램핑존")
        keyword = target.get("keyword", "글램핑")
        match_title = target.get("match_title", "글램핑")

        print(f"🔍 [{t_name}] 스캔 중 (키워드: '{keyword}')...", end=" ", flush=True)
        services = seoul_crawler.scan_seoul_services(keyword=keyword, match_title=match_title)
        print(f"완료 (총 {len(services)}개 월간 일정 감지)")

        for s in services:
            all_current_services[s["svc_id"]] = s

        # 1. 정기 종합 브리핑 모드 (06시 / 18시)
        if is_daily:
            if send_alert and not dry_run:
                for u in users:
                    u_name = u.get("name", u.get("id"))
                    u_notif = u.get("notification", {})
                    print(f"📢 [{u_name}][{t_name}] 정기 종합 브리핑(06시/18시) 발송")
                    seoul_notifier.send_seoul_daily_report(
                        u_notif, t_name, services, user_id=u.get("id", "user1"), user_name=u_name
                    )

            daily_summary = f"📋 정기 종합(06시/18시): 총 {len(services)}개 월간 일정 추적 중"
            daily_details = [
                f"[{s.get('status')}] {s.get('title')} ({s.get('use_date')})"
                for s in services
            ]
            seoul_reporter.add_seoul_history_entry(state, t_name, daily_summary, daily_details)

        # 2. 실시간 변동 비교 모드 (2분 주기)
        else:
            for s in services:
                s_id = s["svc_id"]
                curr_status = s["status"]
                title = s["title"]

                event_type = None
                prev_status = "신규등록"

                if s_id not in prev_services:
                    # 새로 발견된 월간 일정
                    if not is_initial_run:
                        if curr_status == "접수중":
                            event_type = "new_open"  # 바로 열려 있는 경우
                        elif curr_status == "안내중":
                            event_type = "new_schedule"  # 신규 월 공지 등록
                else:
                    prev_s = prev_services[s_id]
                    prev_status = prev_s.get("status", "")

                    if prev_status != curr_status:
                        if prev_status == "예약마감" and curr_status == "접수중":
                            event_type = "cancel_slot"  # 취소표 발생!
                        elif prev_status == "안내중" and curr_status == "접수중":
                            event_type = "new_open"  # 신규 월 예약 공식 오픈!
                        elif prev_status == "접수중" and curr_status == "예약마감":
                            event_type = "closed"  # 예약 마감

                if event_type:
                    summary_msg = f"[{event_type}] {title}: {prev_status} ➔ {curr_status}"
                    print(f"🚨 변동 감지! {summary_msg}")

                    if send_alert and not dry_run:
                        for u in users:
                            u_name = u.get("name", u.get("id"))
                            u_notif = u.get("notification", {})

                            # 필터 조건 확인
                            if event_type == "closed" and not u_notif.get("notify_closed_slots", False):
                                continue
                            if event_type == "new_schedule" and not u_notif.get("notify_new_schedule_open", True):
                                continue

                            seoul_notifier.send_seoul_diff_notification(
                                u_notif,
                                t_name,
                                event_type,
                                s,
                                prev_status,
                                curr_status,
                                user_id=u.get("id", "user1"),
                                user_name=u_name
                            )

                    detail_item = f"[{s.get('status')}] {title} (이용: {s.get('use_date')})"
                    seoul_reporter.add_seoul_history_entry(
                        state, t_name, f"{prev_status} ➔ {curr_status}", [detail_item]
                    )

        time.sleep(0.3)

    # 상태 업데이트
    state["services"] = all_current_services
    state["updated_at"] = datetime.now().isoformat()

    if not dry_run:
        seoul_reporter.update_seoul_status_file(state, config)
        save_seoul_state(state)
        print(f"✅ 현황판(seoul/STATUS.md) 및 상태 파일(seoul/last_state.json) 업데이트 완료!")


def main():
    parser = argparse.ArgumentParser(description="서울시 공공서비스예약 글램핑존 실시간 빈자리 모니터링")
    parser.add_argument("--check", action="store_true", help="알림 발송 없이 현재 현황만 콘솔로 즉시 확인")
    parser.add_argument("--daily", action="store_true", help="정기 종합 브리핑(06시/18시) 모드 실행")
    parser.add_argument("--test", action="store_true", help="알림 채널(디스코드 등) 연동 테스트")
    parser.add_argument("--dry-run", action="store_true", help="알림 발송 및 상태 저장 없이 조회만 수행")

    args = parser.parse_args()
    config = load_seoul_config()

    if args.test:
        print("🧪 [테스트 모드] 서울시 예약 알림 전송 테스트를 진행합니다...")
        mock_service = {
            "svc_id": "TEST_SVC_001",
            "title": "[테스트] 10월 글램핑존 (4인용) 한강공원 난지캠핑장",
            "status": "접수중",
            "rcpt_date": "2026.09.15 ~ 2026.10.31",
            "use_date": "2026.10.01 ~ 2026.10.31",
            "direct_url": "https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260901165106276774",
            "login_url": seoul_notifier.SEOUL_LOGIN_URL
        }
        for u in config.get("users", []):
            if u.get("enabled", True):
                print(f"   -> [{u.get('name')}] 테스트 알림 발송...")
                seoul_notifier.send_seoul_diff_notification(
                    u.get("notification", {}),
                    "난지캠핑장 글램핑존",
                    "cancel_slot",
                    mock_service,
                    "예약마감",
                    "접수중",
                    user_id=u.get("id", "user1"),
                    user_name=u.get("name")
                )
        print("✅ 알림 테스트 완료!")
        return

    send_alert = not args.check
    run_seoul_monitoring(config, send_alert=send_alert, is_daily=args.daily, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
