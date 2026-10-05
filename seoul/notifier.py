"""
서울시 공공서비스예약 (난지캠핑장 글램핑존 등) 알림 전송 모듈
- 디스코드(임베드), 텔레그램, 이메일 연동 지원
- 빈자리(취소표) 발생 즉시 알림, 신규 월 오픈 알림, 정기 종합 브리핑(06시/18시) 제공
"""

import os
import sys
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from common import notifier

SEOUL_LOGIN_URL = "https://yeyak.seoul.go.kr/web/loginForm.do"


def resolve_discord_webhook(notif_cfg: Dict[str, Any], user_id: str = "user1") -> str:
    """
    유저별 디스코드 웹훅 주소를 해석합니다.
    1. config.yaml 의 user.notification.discord.webhook_url
    2. 환경변수 DISCORD_WEBHOOK_URL_{USER_ID} (예: DISCORD_WEBHOOK_URL_USER2)
    3. user1인 경우 기존 기본 DISCORD_WEBHOOK_URL 환경변수 fallback
    """
    dc = notif_cfg.get("discord", {}) if isinstance(notif_cfg, dict) else {}
    url = (dc.get("webhook_url") or "").strip()
    if url:
        return url
    env_user = os.getenv(f"DISCORD_WEBHOOK_URL_{user_id.upper()}", "").strip()
    if env_user:
        return env_user
    if user_id.lower() == "user1":
        return os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    return ""


def resolve_telegram_config(notif_cfg: Dict[str, Any], user_id: str = "user1") -> tuple:
    """
    유저별 텔레그램 봇 토큰 및 채팅 ID를 해석합니다.
    """
    tg = notif_cfg.get("telegram", {}) if isinstance(notif_cfg, dict) else {}
    token = (tg.get("bot_token") or "").strip()
    chat_id = (tg.get("chat_id") or "").strip()
    if not token:
        token = os.getenv(f"TELEGRAM_BOT_TOKEN_{user_id.upper()}", "").strip()
        if not token and user_id.lower() == "user1":
            token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not chat_id:
        chat_id = os.getenv(f"TELEGRAM_CHAT_ID_{user_id.upper()}", "").strip()
        if not chat_id and user_id.lower() == "user1":
            chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    return token, chat_id


def format_seoul_diff_text(
    target_name: str,
    event_type: str,
    service: Dict[str, Any],
    prev_status: str,
    curr_status: str
) -> str:
    """
    서울시 예약 변동 텍스트 메시지 생성 (텔레그램, 콘솔용)
    """
    title = service.get("title", "")
    use_date = service.get("use_date", "")
    rcpt_date = service.get("rcpt_date", "")
    direct_url = service.get("direct_url", "")
    login_url = service.get("login_url", SEOUL_LOGIN_URL)

    if event_type == "cancel_slot":
        icon = "🔵"
        action_title = f"{icon} [취소표 발생! 지금 예약가능]"
    elif event_type == "new_open":
        icon = "🔥"
        action_title = f"{icon} [신규 월 예약 오픈!]"
    elif event_type == "new_schedule":
        icon = "📢"
        action_title = f"{icon} [신규 월 일정 등록 공지]"
    elif event_type == "closed":
        icon = "🔴"
        action_title = f"{icon} [예약 마감]"
    else:
        icon = "ℹ️"
        action_title = f"{icon} [상태 변동]"

    lines = [
        f"{action_title} {target_name}",
        f"📌 서비스: {title}",
        f"🔄 상태: {prev_status} ➔ {curr_status}",
        f"📅 이용기간: {use_date}",
        f"⏰ 접수기간: {rcpt_date}",
        "",
        f"⚡ 원클릭 예약 바로가기:\n{direct_url}",
        f"🔑 로그인 유지 확인:\n{login_url}"
    ]
    return "\n".join(lines)


def send_discord_seoul_diff(
    webhook_url: str,
    target_name: str,
    event_type: str,
    service: Dict[str, Any],
    prev_status: str,
    curr_status: str,
    user_name: Optional[str] = None
) -> bool:
    """
    디스코드 웹훅으로 서울시 글램핑존 상태 변동 Embed 전송
    """
    user_prefix = f"[{user_name}] " if user_name else ""
    title = service.get("title", "")
    use_date = service.get("use_date", "")
    rcpt_date = service.get("rcpt_date", "")
    direct_url = service.get("direct_url", "")
    login_url = service.get("login_url", SEOUL_LOGIN_URL)

    if event_type == "cancel_slot":
        embed_color = 3447003  # Blue
        header_text = f"🔵 **{user_prefix}[{target_name}] 취소표 발생! 지금 즉시 예약 가능**"
        status_label = f"🔴 {prev_status} ➔ 🔵 **{curr_status} (예약가능)**"
    elif event_type == "new_open":
        embed_color = 15105570  # Orange
        header_text = f"🔥 **{user_prefix}[{target_name}] 신규 월 예약 오픈!**"
        status_label = f"🟡 {prev_status} ➔ 🔵 **{curr_status} (오픈완료)**"
    elif event_type == "new_schedule":
        embed_color = 10181046  # Purple
        header_text = f"📢 **{user_prefix}[{target_name}] 신규 월 일정 등록 공지**"
        status_label = f"🟡 **{curr_status} (접수 대기 중)**"
    elif event_type == "closed":
        embed_color = 15158332  # Red
        header_text = f"🔴 **{user_prefix}[{target_name}] 예약 마감**"
        status_label = f"🔵 {prev_status} ➔ 🔴 **{curr_status}**"
    else:
        embed_color = 9807270
        header_text = f"ℹ️ **{user_prefix}[{target_name}] 상태 변경**"
        status_label = f"{prev_status} ➔ **{curr_status}**"

    embed_fields = [
        {"name": "🏕️ 시설 서비스명", "value": f"**{title}**", "inline": False},
        {"name": "🔄 상태 변동", "value": status_label, "inline": True},
        {"name": "📅 이용 기간", "value": use_date or "정보 없음", "inline": True},
        {"name": "⏰ 접수 기간", "value": rcpt_date or "정보 없음", "inline": False},
        {
            "name": "⚡ 원클릭 링크",
            "value": f"[⚡ 즉시예약 페이지 바로가기]({direct_url})\n[🔑 로그인 상태 확인/유지]({login_url})",
            "inline": False
        }
    ]

    embed = {
        "title": f"🏕️ 서울시 공공예약: {target_name}",
        "url": direct_url,
        "color": embed_color,
        "fields": embed_fields,
        "footer": {
            "text": "서울시 공공서비스예약 실시간 빈자리 알림 봇 (무료·자동 추적)"
        }
    }

    payload = {
        "content": header_text,
        "embeds": [embed]
    }
    return notifier.send_discord_webhook(webhook_url, payload)


def send_seoul_diff_notification(
    notification_cfg: Dict[str, Any],
    target_name: str,
    event_type: str,
    service: Dict[str, Any],
    prev_status: str,
    curr_status: str,
    user_id: str = "user1",
    user_name: Optional[str] = None
):
    """
    설정된 모든 채널로 서울시 글램핑존 변동 알림 발송
    """
    text_msg = format_seoul_diff_text(target_name, event_type, service, prev_status, curr_status)

    # 1. 디스코드
    dc_cfg = notification_cfg.get("discord", {}) if isinstance(notification_cfg, dict) else {}
    if dc_cfg.get("enabled", True):
        webhook_url = resolve_discord_webhook(notification_cfg, user_id)
        if webhook_url:
            success = send_discord_seoul_diff(
                webhook_url, target_name, event_type, service, prev_status, curr_status, user_name
            )
            if success:
                print(f"[알림 성공] 디스코드 전송 완료: {target_name} ({event_type})")

    # 2. 텔레그램
    tg_cfg = notification_cfg.get("telegram", {}) if isinstance(notification_cfg, dict) else {}
    if tg_cfg.get("enabled", False):
        bot_token, chat_id = resolve_telegram_config(notification_cfg, user_id)
        if bot_token and chat_id:
            success = notifier.send_telegram_message(bot_token, chat_id, text_msg)
            if success:
                print(f"[알림 성공] 텔레그램 전송 완료: {target_name} ({event_type})")


def format_seoul_daily_text(
    target_name: str,
    services: List[Dict[str, Any]]
) -> str:
    """
    정기 브리핑 텍스트 생성 (06시/18시용)
    """
    lines = [
        f"📊 [서울시 공공예약 정기 종합 리포트 (06시/18시)]",
        f"📍 대상: {target_name} (총 {len(services)}개 월간 일정 추적 중)",
        "-" * 30
    ]

    for s in services:
        status_icon = "🔵" if s.get("status") == "접수중" else ("🟡" if s.get("status") == "안내중" else "🔴")
        lines.append(f"{status_icon} [{s.get('status')}] {s.get('title')}")
        lines.append(f"  • 이용기간: {s.get('use_date')}")
        lines.append(f"  • 접수기간: {s.get('rcpt_date')}")
        lines.append(f"  • 바로가기: {s.get('direct_url')}")
        lines.append("")

    lines.append("=" * 30)
    lines.append(f"🔑 서울시 예약 로그인 확인:\n{SEOUL_LOGIN_URL}")
    return "\n".join(lines)


def send_discord_seoul_daily(
    webhook_url: str,
    target_name: str,
    services: List[Dict[str, Any]],
    user_name: Optional[str] = None
) -> bool:
    """
    디스코드 웹훅으로 서울시 정기 종합 브리핑 Embed 전송
    """
    user_prefix = f"[{user_name}] " if user_name else ""
    avail_count = sum(1 for s in services if s.get("status") == "접수중")

    embed_fields = []
    for s in services:
        status_str = s.get("status", "")
        if status_str == "접수중":
            val_status = "🔵 **접수중 (즉시예약 가능!)**"
        elif status_str == "안내중":
            val_status = "🟡 **안내중 (오픈 대기)**"
        else:
            val_status = "🔴 **예약마감 (취소표 대기)**"

        field_content = (
            f"• 상태: {val_status}\n"
            f"• 이용기간: {s.get('use_date')}\n"
            f"• 접수기간: {s.get('rcpt_date')}\n"
            f"• [⚡ 예약 바로가기]({s.get('direct_url')})"
        )
        embed_fields.append({
            "name": f"🏕️ {s.get('title')}",
            "value": field_content,
            "inline": False
        })

    embed_fields.append({
        "name": "🔑 로그인 바로가기",
        "value": f"[🔑 서울시 예약 로그인 상태 유지]({SEOUL_LOGIN_URL})",
        "inline": False
    })

    embed_color = 3447003 if avail_count > 0 else 10070709
    header_content = f"📊 **{user_prefix}[{target_name}] 정기 빈자리 종합 리포트 (06시/18시)**"

    embed = {
        "title": f"🏕️ 서울시 공공예약: {target_name}",
        "url": SEOUL_LOGIN_URL,
        "color": embed_color,
        "fields": embed_fields,
        "footer": {
            "text": "서울시 공공서비스예약 정기 리포트 (06시/18시 KST)"
        }
    }

    payload = {
        "content": header_content,
        "embeds": [embed]
    }
    return notifier.send_discord_webhook(webhook_url, payload)


def send_seoul_daily_report(
    notification_cfg: Dict[str, Any],
    target_name: str,
    services: List[Dict[str, Any]],
    user_id: str = "user1",
    user_name: Optional[str] = None
):
    """
    정기 브리핑을 설정된 모든 채널로 발송
    """
    text_msg = format_seoul_daily_text(target_name, services)

    dc_cfg = notification_cfg.get("discord", {}) if isinstance(notification_cfg, dict) else {}
    if dc_cfg.get("enabled", True):
        webhook_url = resolve_discord_webhook(notification_cfg, user_id)
        if webhook_url:
            success = send_discord_seoul_daily(webhook_url, target_name, services, user_name)
            if success:
                print(f"[정기 리포트] 디스코드 전송 완료: {target_name}")

    tg_cfg = notification_cfg.get("telegram", {}) if isinstance(notification_cfg, dict) else {}
    if tg_cfg.get("enabled", False):
        bot_token, chat_id = resolve_telegram_config(notification_cfg, user_id)
        if bot_token and chat_id:
            success = notifier.send_telegram_message(bot_token, chat_id, text_msg)
            if success:
                print(f"[정기 리포트] 텔레그램 전송 완료: {target_name}")
