"""
국립공원 생태탐방원 빈자리 알림 전송 모듈
- 디스코드(Discord) 웹훅 (Embed 형식)
- 텔레그램(Telegram) 봇
- 이메일(SMTP)
"""

import json
import urllib.request
import ssl
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from typing import Dict, Any, List, Optional, Union
from common import notifier

ECO_RESERVATION_URL = "https://res.knps.or.kr/eco/searchEcoReservation.do"
ECO_LOGIN_URL = "https://res.knps.or.kr/mmb/mmbLogin.do"


def get_eco_direct_url(center_info: Dict[str, Any]) -> str:
    """
    국립공원 생태탐방원 원클릭 다이렉트 딥링크(Deep Link)를 생성합니다.
    deptId 파라미터가 포함되어 있어, 접속 시 해당 생태탐방원이 즉시 선택되고 객실 목록이 바로 로드됩니다.
    """
    dept_id = (center_info or {}).get("dept_id")
    if dept_id:
        return f"https://res.knps.or.kr/eco/searchEcoReservation.do?deptId={dept_id}"
    return ECO_RESERVATION_URL


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


def format_eco_diff_text(
    center_info: Dict[str, Any],
    blue_slots: List[Dict[str, Any]],
    red_slots: List[Dict[str, Any]],
    total_remaining: Union[int, str],
    consecutive_pairs: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    생태탐방원 빈자리 변동 텍스트 메시지 생성 (텔레그램, 콘솔, 이메일용)
    """
    center_name = center_info.get("name") or center_info.get("center_name", "")
    user_name = center_info.get("user_name")
    user_prefix = f"[{user_name}] " if user_name else ""

    blue_slots = blue_slots or []
    red_slots = red_slots or []
    consecutive_pairs = consecutive_pairs or []

    parts = []
    if consecutive_pairs:
        parts.append(f"🔥 {len(consecutive_pairs)}개 2박연박")
    if blue_slots:
        parts.append(f"🔵 +{len(blue_slots)} 예약가능")
    if red_slots:
        parts.append(f"🔴 -{len(red_slots)} 마감")
    summary_str = " / ".join(parts) if parts else "변동 감지"

    rem_str = str(total_remaining)
    if isinstance(total_remaining, int) or rem_str.isdigit():
        rem_str = f"{rem_str}실"

    lines = [
        f"🚨 {user_prefix}[국립공원 생태탐방원 빈자리 변동 알림 ({summary_str})]",
        f"📍 대상: {center_name} 생태탐방원 (현재 잔여: {rem_str})",
    ]
    if user_name:
        lines.append(f"👤 수신자: {user_name}")
    lines.append("-" * 30)

    # 주말 2박 연박
    if consecutive_pairs:
        lines.append(f"\n🔥 [주말 2박(금,토) 연박 가능 객실 ({len(consecutive_pairs)}개 발견!)]")
        for p in consecutive_pairs[:10]:
            pet_tag = " [🐕반려동물]" if p.get("pet_allowed") else ""
            lines.append(
                f"  • {p['room_name']} ({p['capacity']}인실): {p['fri_date']}(금)~{p['sat_date']}(토) "
                f"2박 {p['price_total']:,}원{pet_tag}"
            )

    # 신규 예약 가능 객실
    if blue_slots:
        lines.append(f"\n🔵 즉시 예약 가능 (+{len(blue_slots)}실)")
        by_date: Dict[str, List[Dict[str, Any]]] = {}
        for s in blue_slots:
            d_key = f"{s['date']} ({s['dow']})"
            by_date.setdefault(d_key, []).append(s)

        for d_key, slots in sorted(by_date.items()):
            lines.append(f"  📅 {d_key}")
            for r in slots[:10]:
                pet_tag = " [🐕반려동물]" if r.get("pet_allowed") else ""
                lines.append(f"    • {r['prd_name']} ({r['capacity']}인실) - {r['price']:,}원{pet_tag}")
            if len(slots) > 10:
                lines.append(f"    ... 외 {len(slots) - 10}개")

    # 예약 마감 객실
    if red_slots:
        lines.append(f"\n🔴 예약 마감 (-{len(red_slots)}실)")
        by_date_red: Dict[str, List[Dict[str, Any]]] = {}
        for s in red_slots:
            d_key = f"{s['date']} ({s['dow']})"
            by_date_red.setdefault(d_key, []).append(s)

        for d_key, slots in sorted(by_date_red.items()):
            lines.append(f"  📅 {d_key}")
            for r in slots[:10]:
                lines.append(f"    • {r['prd_name']} ({r['capacity']}인실) 마감")
            if len(slots) > 10:
                lines.append(f"    ... 외 {len(slots) - 10}개")

    direct_url = get_eco_direct_url(center_info)
    lines.append("\n" + "=" * 30)
    lines.append(f"⚡ 원클릭 예약 바로가기:\n{direct_url}\n🔑 로그인 유지 확인:\n{ECO_LOGIN_URL}")
    return "\n".join(lines)


def send_discord_eco_diff(
    webhook_url: str,
    center_info: Dict[str, Any],
    blue_slots: List[Dict[str, Any]],
    red_slots: List[Dict[str, Any]],
    total_remaining: Union[int, str],
    consecutive_pairs: Optional[List[Dict[str, Any]]] = None
) -> bool:
    """
    디스코드 웹훅으로 생태탐방원 빈자리 변동 내역을 Embed 형태로 전송합니다.
    """
    if not webhook_url:
        return False

    center_name = center_info.get("name") or center_info.get("center_name", "")
    direct_url = get_eco_direct_url(center_info)
    blue_slots = blue_slots or []
    red_slots = red_slots or []
    consecutive_pairs = consecutive_pairs or []

    embed_fields = []

    # 1. 주말 2박 연박 필드
    if consecutive_pairs:
        pair_lines = []
        for p in consecutive_pairs[:8]:
            pet_tag = " `[🐕반려동물]`" if p.get("pet_allowed") else ""
            pair_lines.append(
                f"• **{p['room_name']}** ({p['capacity']}인실): {p['fri_date']}(금)~{p['sat_date']}(토) "
                f"**2박 {p['price_total']:,}원**{pet_tag} [⚡예약]({direct_url})"
            )
        embed_fields.append({
            "name": f"🔥 주말 2박(금,토) 연박 가능! ({len(consecutive_pairs)}개 객실)",
            "value": "\n".join(pair_lines)[:1020],
            "inline": False
        })

    # 2. 신규 예약 가능 객실 필드
    if blue_slots:
        by_date: Dict[str, List[Dict[str, Any]]] = {}
        for s in blue_slots:
            d_key = f"{s['date']} ({s['dow']})"
            by_date.setdefault(d_key, []).append(s)

        date_blocks = []
        for d_key, slots in sorted(by_date.items())[:10]:
            room_strs = []
            for r in slots[:6]:
                pet_tag = " [🐕]" if r.get("pet_allowed") else ""
                room_strs.append(f"• {r['prd_name']} ({r['capacity']}인실, {r['price']:,}원){pet_tag} [⚡예약]({direct_url})")
            if len(slots) > 6:
                room_strs.append(f"... 외 {len(slots)-6}개")
            date_blocks.append(f"📅 **{d_key}**\n" + "\n".join(room_strs))

        embed_fields.append({
            "name": f"🔵 즉시 예약 가능 (+{len(blue_slots)}실)",
            "value": "\n\n".join(date_blocks)[:1020],
            "inline": False
        })

    # 3. 마감된 객실 필드
    if red_slots:
        by_date_red: Dict[str, List[Dict[str, Any]]] = {}
        for s in red_slots:
            d_key = f"{s['date']} ({s['dow']})"
            by_date_red.setdefault(d_key, []).append(s)

        red_blocks = []
        for d_key, slots in sorted(by_date_red.items())[:6]:
            room_strs = [f"• {r['prd_name']} ({r['capacity']}인실) 마감" for r in slots[:5]]
            if len(slots) > 5:
                room_strs.append(f"... 외 {len(slots)-5}개")
            red_blocks.append(f"📅 **{d_key}**\n" + "\n".join(room_strs))

        embed_fields.append({
            "name": f"🔴 예약 마감 (-{len(red_slots)}실)",
            "value": "\n\n".join(red_blocks)[:1020],
            "inline": False
        })

    # 헤더 및 색상 결정
    parts = []
    if consecutive_pairs: parts.append(f"🔥 {len(consecutive_pairs)}개 2박연박")
    if blue_slots: parts.append(f"🔵 +{len(blue_slots)}")
    if red_slots: parts.append(f"🔴 -{len(red_slots)}")
    summary_str = " / ".join(parts) if parts else "변동 감지"

    user_name = center_info.get("user_name")
    user_prefix = f"[{user_name}] " if user_name else ""

    if consecutive_pairs or blue_slots:
        header_content = f"🚀 **{user_prefix}[{center_name} 생태탐방원] 즉시 예약 가능한 빈자리 발견! ({summary_str})**"
        embed_color = 3066993  # Green / Teal
    else:
        header_content = f"ℹ️ **{user_prefix}[{center_name} 생태탐방원] 객실 예약 마감 ({summary_str})**"
        embed_color = 15158332 # Red

    rem_str = str(total_remaining)
    if isinstance(total_remaining, int) or rem_str.isdigit():
        rem_str = f"{rem_str}실"

    embed_desc = (
        f"현재 예약 가능 객실: **{rem_str}**\n"
        f"⚡ **[👉 {center_name} 생태탐방원 즉시 예약창 바로가기 (원클릭)]({direct_url})**\n"
        f"🔑 [로그인 유지 확인하기]({ECO_LOGIN_URL})"
    )

    payload = {
        "content": header_content,
        "embeds": [
            {
                "title": f"🏡 {user_prefix}{center_name} 생태탐방원 빈자리 현황",
                "description": embed_desc,
                "color": embed_color,
                "fields": embed_fields,
                "footer": {"text": "국립공원 생태탐방원 모니터링 (GitHub Actions)"}
            }
        ]
    }
    data = json.dumps(payload).encode("utf-8")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "KNPSEcoNotifier/1.0"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"[Eco Notifier Error] Discord 전송 실패: {e}")
        return False


def send_eco_change_notification(
    notification_cfg: Dict[str, Any],
    center_info: Dict[str, Any],
    blue_slots: List[Dict[str, Any]],
    red_slots: List[Dict[str, Any]],
    total_remaining: Union[int, str],
    consecutive_pairs: Optional[List[Dict[str, Any]]] = None
):
    """
    설정된 알림 채널(Discord, Telegram, Email)로 생태탐방원 변동 알림을 일괄 전송합니다.
    """
    center_name = center_info.get("name") or center_info.get("center_name", "")
    user_id = center_info.get("user_id", "user1")
    user_name = center_info.get("user_name", user_id)
    text_msg = format_eco_diff_text(
        center_info, blue_slots, red_slots, total_remaining, consecutive_pairs
    )

    # 1. 디스코드 전송
    dc_cfg = notification_cfg.get("discord", {}) if isinstance(notification_cfg, dict) else {}
    if dc_cfg.get("enabled"):
        webhook_url = resolve_discord_webhook(notification_cfg, user_id)
        if not webhook_url:
            print(f"ℹ️ [{user_name}] 디스코드 웹훅 주소가 비어 있어 알림 발송을 건너뜁니다.")
        else:
            success = send_discord_eco_diff(
                webhook_url,
                center_info,
                blue_slots,
                red_slots,
                total_remaining,
                consecutive_pairs
            )
            if success:
                print(f"[알림 성공] 디스코드 전송 완료: {center_name} 생태탐방원")

    # 2. 텔레그램 전송
    tg_cfg = notification_cfg.get("telegram", {}) if isinstance(notification_cfg, dict) else {}
    if tg_cfg.get("enabled"):
        bot_token, chat_id = resolve_telegram_config(notification_cfg, user_id)
        if not bot_token or not chat_id:
            print(f"ℹ️ [{user_name}] 텔레그램 봇 토큰/채팅ID가 설정되지 않아 알림 발송을 건너뜁니다.")
        else:
            success = notifier.send_telegram(
                bot_token,
                chat_id,
                text_msg
            )
            if success:
                print(f"[알림 성공] 텔레그램 전송 완료: {center_name} 생태탐방원")

    # 3. 이메일 전송
    em_cfg = notification_cfg.get("email", {})
    if em_cfg.get("enabled"):
        subject = f"[국립공원 생태탐방원] {center_name} 빈자리 변동 알림"
        notifier.send_email(
            em_cfg.get("smtp_host", "smtp.gmail.com"),
            em_cfg.get("smtp_port", 587),
            em_cfg.get("smtp_user", ""),
            em_cfg.get("smtp_pass", ""),
            em_cfg.get("to_email", ""),
            subject,
            text_msg,
            em_cfg.get("use_tls", True)
        )


def format_eco_daily_text(
    center_info: Dict[str, Any],
    available_rooms: List[Dict[str, Any]],
    consecutive_pairs: Optional[List[Dict[str, Any]]] = None,
    golden_time_text: Optional[str] = None
) -> str:
    """
    생태탐방원 일일 종합 브리핑 텍스트 생성 (텔레그램, 콘솔, 이메일용)
    """
    center_name = center_info.get("name") or center_info.get("center_name", "")
    user_name = center_info.get("user_name")
    user_prefix = f"[{user_name}] " if user_name else ""
    available_rooms = available_rooms or []
    consecutive_pairs = consecutive_pairs or []

    lines = [
        f"📊 {user_prefix}[국립공원 생태탐방원 정기 빈자리 리포트 (06시/18시)]",
        f"📍 대상: {center_name} 생태탐방원 (총 {len(available_rooms)}실 예약가능)",
    ]
    if user_name:
        lines.append(f"👤 수신자: {user_name}")
    lines.append("-" * 30)

    if consecutive_pairs:
        lines.append(f"\n🔥 [주말 2박(금,토) 연박 가능 객실 ({len(consecutive_pairs)}개)]")
        for p in consecutive_pairs[:10]:
            pet_tag = " [🐕반려동물]" if p.get("pet_allowed") else ""
            lines.append(
                f"  • {p['room_name']} ({p['capacity']}인실): {p['fri_date']}(금)~{p['sat_date']}(토) "
                f"2박 {p['price_total']:,}원{pet_tag}"
            )

    if not available_rooms:
        lines.append("\nℹ️ 현재 설정된 조건에 부합하는 빈자리 객실이 없습니다.")
    else:
        by_date: Dict[str, List[Dict[str, Any]]] = {}
        for s in available_rooms:
            d_key = f"{s['date']} ({s['dow']})"
            by_date.setdefault(d_key, []).append(s)

        for d_key, slots in sorted(by_date.items()):
            lines.append(f"\n📅 {d_key}")
            for r in slots[:10]:
                pet_tag = " [🐕반려동물]" if r.get("pet_allowed") else ""
                lines.append(f"  • {r['prd_name']} ({r['capacity']}인실) - {r['price']:,}원{pet_tag}")
            if len(slots) > 10:
                lines.append(f"  ... 외 {len(slots) - 10}개")

    if golden_time_text:
        lines.append("\n" + "-" * 30)
        lines.append(f"📈 [💡 취소표 골든타임 공략 팁]\n  • {golden_time_text}")

    direct_url = get_eco_direct_url(center_info)
    lines.append("\n" + "=" * 30)
    lines.append(f"⚡ 원클릭 예약 바로가기:\n{direct_url}\n🔑 로그인 유지 확인:\n{ECO_LOGIN_URL}")
    return "\n".join(lines)


def send_discord_eco_daily(
    webhook_url: str,
    center_info: Dict[str, Any],
    available_rooms: List[Dict[str, Any]],
    consecutive_pairs: Optional[List[Dict[str, Any]]] = None,
    golden_time_text: Optional[str] = None
) -> bool:
    """
    디스코드 웹훅으로 생태탐방원 일일 종합 브리핑 Embed 전송
    """
    if not webhook_url:
        return False

    center_name = center_info.get("name") or center_info.get("center_name", "")
    user_name = center_info.get("user_name")
    user_prefix = f"[{user_name}] " if user_name else ""
    direct_url = get_eco_direct_url(center_info)
    available_rooms = available_rooms or []
    consecutive_pairs = consecutive_pairs or []

    embed_fields = []
    if consecutive_pairs:
        pair_lines = []
        for p in consecutive_pairs[:8]:
            pet_tag = " `[🐕반려동물]`" if p.get("pet_allowed") else ""
            pair_lines.append(
                f"• **{p['room_name']}** ({p['capacity']}인실): {p['fri_date']}(금)~{p['sat_date']}(토) "
                f"**2박 {p['price_total']:,}원**{pet_tag} [⚡예약]({direct_url})"
            )
        embed_fields.append({
            "name": f"🔥 주말 2박(금,토) 연박 가능! ({len(consecutive_pairs)}개 객실)",
            "value": "\n".join(pair_lines)[:1020],
            "inline": False
        })

    if available_rooms:
        by_date: Dict[str, List[Dict[str, Any]]] = {}
        for s in available_rooms:
            d_key = f"{s['date']} ({s['dow']})"
            by_date.setdefault(d_key, []).append(s)

        date_blocks = []
        for d_key, slots in sorted(by_date.items())[:10]:
            room_strs = []
            for r in slots[:6]:
                pet_tag = " [🐕]" if r.get("pet_allowed") else ""
                room_strs.append(f"• {r['prd_name']} ({r['capacity']}인실, {r['price']:,}원){pet_tag} [⚡예약]({direct_url})")
            if len(slots) > 6:
                room_strs.append(f"... 외 {len(slots)-6}개")
            date_blocks.append(f"📅 **{d_key}**\n" + "\n".join(room_strs))

        embed_fields.append({
            "name": f"🔵 예약 가능 객실 현황 ({len(available_rooms)}실)",
            "value": "\n\n".join(date_blocks)[:1020],
            "inline": False
        })

    if golden_time_text:
        embed_fields.append({
            "name": "📈 💡 취소표 골든타임 공략 팁",
            "value": golden_time_text[:1020],
            "inline": False
        })

    if available_rooms:
        header_content = f"📊 **{user_prefix}[{center_name} 생태탐방원] 정기 빈자리 종합 리포트 ({len(available_rooms)}실)**"
        embed_color = 3447003  # Blue
        embed_desc = (
            f"⚡ **[👉 {center_name} 생태탐방원 즉시 예약창 바로가기 (원클릭)]({direct_url})**\n"
            f"🔑 [로그인 유지 확인하기]({ECO_LOGIN_URL})"
        )
    else:
        header_content = f"📊 **{user_prefix}[{center_name} 생태탐방원] 정기 빈자리 종합 리포트 (06시/18시)**"
        embed_color = 8421504  # Gray
        embed_desc = (
            f"현재 설정된 조건에 부합하는 빈자리 객실이 없습니다.\n"
            f"⚡ **[👉 {center_name} 생태탐방원 예약시스템 확인하기]({direct_url})**\n"
            f"🔑 [로그인 유지 확인하기]({ECO_LOGIN_URL})"
        )

    payload = {
        "content": header_content,
        "embeds": [
            {
                "title": f"🏡 {user_prefix}{center_name} 생태탐방원 정기 브리핑 (06시/18시)",
                "description": embed_desc,
                "color": embed_color,
                "fields": embed_fields,
                "footer": {"text": "국립공원 생태탐방원 정기 리포트 (GitHub Actions)"}
            }
        ]
    }
    data = json.dumps(payload).encode("utf-8")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "KNPSEcoNotifier/1.0"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"[Eco Notifier Error] Discord 정기 리포트 전송 실패: {e}")
        return False


def send_eco_daily_report(
    notification_cfg: Dict[str, Any],
    center_info: Dict[str, Any],
    available_rooms: List[Dict[str, Any]],
    consecutive_pairs: Optional[List[Dict[str, Any]]] = None,
    golden_time_text: Optional[str] = None
):
    """
    생태탐방원 일일 종합 브리핑을 설정된 모든 채널로 발송
    """
    center_name = center_info.get("name") or center_info.get("center_name", "")
    user_id = center_info.get("user_id", "user1")
    user_name = center_info.get("user_name", user_id)
    text_msg = format_eco_daily_text(center_info, available_rooms, consecutive_pairs, golden_time_text=golden_time_text)

    # 1. 디스코드
    dc_cfg = notification_cfg.get("discord", {}) if isinstance(notification_cfg, dict) else {}
    if dc_cfg.get("enabled"):
        webhook_url = resolve_discord_webhook(notification_cfg, user_id)
        if not webhook_url:
            print(f"ℹ️ [{user_name}] 디스코드 웹훅 주소가 비어 있어 알림 발송을 건너뜁니다.")
        else:
            success = send_discord_eco_daily(
                webhook_url,
                center_info,
                available_rooms,
                consecutive_pairs,
                golden_time_text=golden_time_text
            )
            if success:
                print(f"[정기 리포트] 디스코드 전송 완료: {center_name} 생태탐방원")

    # 2. 텔레그램
    tg_cfg = notification_cfg.get("telegram", {}) if isinstance(notification_cfg, dict) else {}
    if tg_cfg.get("enabled"):
        bot_token, chat_id = resolve_telegram_config(notification_cfg, user_id)
        if not bot_token or not chat_id:
            print(f"ℹ️ [{user_name}] 텔레그램 봇 토큰/채팅ID가 설정되지 않아 알림 발송을 건너뜁니다.")
        else:
            success = notifier.send_telegram(
                bot_token,
                chat_id,
                text_msg
            )
            if success:
                print(f"[정기 리포트] 텔레그램 전송 완료: {center_name} 생태탐방원")

    # 3. 이메일
    em_cfg = notification_cfg.get("email", {})
    if em_cfg.get("enabled"):
        subject = f"[국립공원 생태탐방원] {center_name} 정기 종합 빈자리 리포트 (06시/18시)"
        notifier.send_email(
            em_cfg.get("smtp_host", "smtp.gmail.com"),
            em_cfg.get("smtp_port", 587),
            em_cfg.get("smtp_user", ""),
            em_cfg.get("smtp_pass", ""),
            em_cfg.get("to_email", ""),
            subject,
            text_msg,
            em_cfg.get("use_tls", True)
        )
