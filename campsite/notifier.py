"""
국립공원 야영장 빈자리 알림 전송 모듈
- 텔레그램(Telegram) 봇
- 디스코드(Discord) 웹훅
- 이메일(SMTP)
순수 파이썬 표준 라이브러리(urllib, json, smtplib, email)로 구현되어 외부 패키지 설치 없이 동작합니다.
"""

import os
import json
import urllib.request
import urllib.parse
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Union

RESERVATION_URL = "https://reservation.knps.or.kr/reservation/searchSimpleCampReservation.do"
LOGIN_URL = "https://reservation.knps.or.kr/mmb/mmbLogin.do"


def get_campsite_direct_url(campsite_info: Dict[str, Any]) -> str:
    """
    국립공원 야영장 원클릭 다이렉트 딥링크(Deep Link)를 생성합니다.
    deptId 파라미터가 포함되어 있어, 접속 시 해당 야영장이 즉시 선택되고 잔여석 표가 바로 로드됩니다.
    """
    dept_id = (campsite_info or {}).get("dept_id")
    if dept_id:
        return f"https://reservation.knps.or.kr/reservation/searchSimpleCampReservation.do?deptId={dept_id}"
    return RESERVATION_URL


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

def format_notification_message(
    campsite_info: Dict[str, Any],
    available_slots: List[Dict[str, Any]],
    is_daily: bool = False,
    consecutive_pairs: List[Dict[str, Any]] = None,
    golden_time_text: str = None
) -> str:
    """
    사용자가 한눈에 보기 편하도록 텍스트/마크다운 형태의 알림 메시지를 생성합니다.
    """
    park_name = campsite_info.get("park_name", "")
    camp_name = campsite_info.get("camp_name", "")
    camp_types = campsite_info.get("types")
    types_label = f" [{', '.join(camp_types)}]" if camp_types else ""

    user_name = campsite_info.get("user_name")
    user_prefix = f"[{user_name}] " if user_name else ""

    lines = []
    if is_daily:
        lines.append(f"📊 {user_prefix}[국립공원 야영장 정기 빈자리 리포트 (06시/18시)]")
        lines.append(f"📍 대상: {park_name} - {camp_name}{types_label}")
    else:
        lines.append(f"🏕️ {user_prefix}[국립공원 야영장 빈자리 실시간 알림]")
        lines.append(f"📍 대상: {park_name} - {camp_name}{types_label} ({len(available_slots)}자리 발견)")
    if user_name:
        lines.append(f"👤 수신자: {user_name}")
    lines.append("-" * 30)

    if consecutive_pairs:
        lines.append(f"\n🔥 [주말 2박(금,토) 연박 가능 영지 ({len(consecutive_pairs)}개)]")
        for p in consecutive_pairs[:10]:
            badge = p.get("case_badge", f"[{p.get('status_summary', '')}]")
            lines.append(f"  • {p['site_type']} {p['site_num']}: {p['fri_date']}(금) ~ {p['sat_date']}(토) {badge}")

    if not available_slots:
        lines.append("\nℹ️ 현재 조건에 부합하는 빈자리(또는 대기자리)가 없습니다.")
    else:
        # 날짜별로 그룹핑
        by_date: Dict[str, List[Dict[str, Any]]] = {}
        for s in available_slots:
            d_key = f"{s['date']} ({s['dow']})"
            if d_key not in by_date:
                by_date[d_key] = []
            by_date[d_key].append(s)

        for d_key, slots in sorted(by_date.items()):
            lines.append(f"\n📅 {d_key}")
            # 타입별로 정리
            by_type: Dict[str, List[str]] = {}
            for s in slots:
                stype = s.get("site_type") or "일반"
                snum = s.get("site_num") or s.get("full_title", "")
                stat = " [대기]" if s.get("status") == "W" else ""
                if stype not in by_type:
                    by_type[stype] = []
                by_type[stype].append(f"{snum}{stat}")

            for stype, sites in by_type.items():
                lines.append(f"  • {stype}: {', '.join(sites[:10])}{' 외' if len(sites) > 10 else ''}")

    if is_daily and golden_time_text:
        lines.append("\n" + "-" * 30)
        lines.append(f"📈 [💡 취소표 골든타임 공략 팁]\n  • {golden_time_text}")

    direct_url = get_campsite_direct_url(campsite_info)
    lines.append("\n" + "=" * 30)
    lines.append(f"⚡ 원클릭 예약 바로가기:\n{direct_url}\n🔑 로그인 유지 확인:\n{LOGIN_URL}")

    return "\n".join(lines)


def send_telegram(bot_token: str, chat_id: str, message: str) -> bool:
    """
    텔레그램 봇으로 메시지를 전송합니다.
    """
    if not bot_token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": True
    }
    data = json.dumps(payload).encode("utf-8")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[Notifier Error] Telegram 전송 실패: {e}")
        return False


def send_discord(
    webhook_url: str,
    message: str,
    campsite_info: Dict[str, Any],
    slots: List[Dict[str, Any]],
    is_daily: bool = False,
    consecutive_pairs: List[Dict[str, Any]] = None,
    golden_time_text: str = None
) -> bool:
    """
    디스코드 웹훅으로 깔끔한 Embed 메시지를 전송합니다.
    """
    if not webhook_url:
        return False

    park_name = campsite_info.get("park_name", "")
    camp_name = campsite_info.get("camp_name", "")
    camp_types = campsite_info.get("types")
    type_suffix = f" ({', '.join(camp_types)})" if camp_types else ""

    # Embed 필드 구성
    embed_fields = []
    if consecutive_pairs:
        pair_desc = []
        for p in consecutive_pairs[:10]:
            badge = p.get("case_badge", "")
            pair_desc.append(f"• **{p['site_type']} {p['site_num']}**: {p['fri_date']}(금) ~ {p['sat_date']}(토) {badge}")
        embed_fields.append({
            "name": f"🔥 주말 2박(금,토) 연박 가능 ({len(consecutive_pairs)}자리)",
            "value": "\n".join(pair_desc)[:1020],
            "inline": False
        })

    if slots:
        by_date: Dict[str, List[Dict[str, Any]]] = {}
        for s in slots:
            d_key = f"{s['date']} ({s['dow']})"
            by_date.setdefault(d_key, []).append(s)

        for d_key, d_slots in sorted(by_date.items())[:15]: # 최대 15개 필드 제한
            desc_list = []
            for s in d_slots[:6]:
                stype = s.get("site_type") or "일반"
                snum = s.get("site_num") or ""
                stat = " [대기]" if s.get("status") == "W" else ""
                desc_list.append(f"{stype} {snum}{stat}")
            if len(d_slots) > 6:
                desc_list.append(f"... 외 {len(d_slots) - 6}개")

            embed_fields.append({
                "name": f"📅 {d_key}",
                "value": "\n".join(desc_list) if desc_list else "자리 있음",
                "inline": True
            })

    if is_daily and golden_time_text:
        embed_fields.append({
            "name": "📈 💡 취소표 골든타임 공략 팁",
            "value": golden_time_text[:1020],
            "inline": False
        })

    user_name = campsite_info.get("user_name")
    user_prefix = f"[{user_name}] " if user_name else ""

    direct_url = get_campsite_direct_url(campsite_info)

    if is_daily:
        if slots:
            header_content = f"📊 **{user_prefix}[{park_name} {camp_name}{type_suffix}] 정기 빈자리 종합 리포트 ({len(slots)}자리)**"
            embed_color = 3447003 # Blue
            embed_desc = f"⚡ **[👉 {camp_name} 즉시 예약창 바로가기 (원클릭)]({direct_url})**\n🔑 [로그인 유지 확인하기]({LOGIN_URL})"
        else:
            header_content = f"📊 **{user_prefix}[{park_name} {camp_name}{type_suffix}] 정기 빈자리 리포트 (06시/18시)**"
            embed_color = 8421504 # Gray
            embed_desc = f"현재 설정된 조건에 부합하는 빈자리가 없습니다.\n⚡ **[👉 {camp_name} 예약시스템 확인하기]({direct_url})**"
    else:
        header_content = f"🚨 **{user_prefix}[{park_name} {camp_name}{type_suffix}] 실시간 빈자리 예약 가능!**"
        embed_color = 3066993 # Green
        embed_desc = f"⚡ **[👉 {camp_name} 즉시 예약창 바로가기 (원클릭)]({direct_url})**\n🔑 [로그인 유지 확인하기]({LOGIN_URL})"

    payload = {
        "content": header_content,
        "embeds": [
            {
                "title": f"🏕️ {user_prefix}{park_name} - {camp_name}{type_suffix} ({len(slots)}자리)",
                "description": embed_desc,
                "color": embed_color,
                "fields": embed_fields,
                "footer": {"text": "국립공원 빈자리 모니터링 (GitHub Actions)"}
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
        headers={"Content-Type": "application/json", "User-Agent": "KNPSNotifier/1.0"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"[Notifier Error] Discord 전송 실패: {e}")
        return False


def send_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    to_email: str,
    subject: str,
    body: str,
    use_tls: bool = True
) -> bool:
    """
    이메일(SMTP)로 알림을 전송합니다.
    """
    if not smtp_host or not smtp_user or not smtp_pass or not to_email:
        return False

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            if use_tls:
                server.starttls()

        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"[Notifier Error] 이메일 전송 실패: {e}")
        return False


def _format_slots_text(slots: List[Dict[str, Any]]) -> str:
    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for s in slots:
        d_key = f"{s['date']} ({s['dow']})"
        by_date.setdefault(d_key, []).append(s)

    lines = []
    for d_key, d_slots in sorted(by_date.items()):
        lines.append(f"  📅 {d_key}")
        by_type: Dict[str, List[str]] = {}
        for s in d_slots:
            stype = s.get("site_type") or "일반"
            snum = s.get("site_num") or s.get("full_title", "")
            stat = " [대기]" if s.get("status") == "W" else ""
            by_type.setdefault(stype, []).append(f"{snum}{stat}")

        for stype, sites in by_type.items():
            site_str = ", ".join(sites[:10])
            if len(sites) > 10:
                site_str += f" 외 {len(sites) - 10}개"
            lines.append(f"    • {stype}: {site_str}")
    return "\n".join(lines)


def _format_slots_discord(slots: List[Dict[str, Any]]) -> str:
    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for s in slots:
        d_key = f"{s['date']} ({s['dow']})"
        by_date.setdefault(d_key, []).append(s)

    lines = []
    for d_key, d_slots in sorted(by_date.items())[:10]:
        by_type: Dict[str, List[str]] = {}
        for s in d_slots:
            stype = s.get("site_type") or "일반"
            snum = s.get("site_num") or s.get("full_title", "")
            stat = " [대기]" if s.get("status") == "W" else ""
            by_type.setdefault(stype, []).append(f"{snum}{stat}")

        type_strs = []
        for stype, sites in by_type.items():
            s_str = ", ".join(sites[:6])
            if len(sites) > 6:
                s_str += f" 외 {len(sites)-6}개"
            type_strs.append(f"• {stype}: {s_str}")

        lines.append(f"📅 **{d_key}**\n" + "\n".join(type_strs))

    return "\n\n".join(lines) if lines else "없음"


def _format_transition_items_text(items: List[Dict[str, Any]]) -> str:
    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        s = item.get("slot") or item
        d_key = f"{s['date']} ({s['dow']})"
        by_date.setdefault(d_key, []).append(item)

    lines = []
    for d_key, d_items in sorted(by_date.items()):
        lines.append(f"  📅 {d_key}")
        for it in d_items[:10]:
            s = it.get("slot") or it
            stype = s.get("site_type") or "일반"
            snum = s.get("site_num") or s.get("full_title", "")
            p_txt = it.get("prev_status_text", "")
            c_txt = it.get("curr_status_text", "")
            if p_txt and c_txt:
                lines.append(f"    • {stype} {snum}: {p_txt} ➔ {c_txt}")
            elif c_txt:
                lines.append(f"    • {stype} {snum}: {c_txt}")
            else:
                lines.append(f"    • {stype} {snum}")
        if len(d_items) > 10:
            lines.append(f"    ... 외 {len(d_items) - 10}개")
    return "\n".join(lines)


def _format_transition_items_discord(items: List[Dict[str, Any]], direct_url: str = None) -> str:
    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        s = item.get("slot") or item
        d_key = f"{s['date']} ({s['dow']})"
        by_date.setdefault(d_key, []).append(item)

    link_tag = f" [⚡예약]({direct_url})" if direct_url else ""
    lines = []
    for d_key, d_items in sorted(by_date.items())[:10]:
        type_strs = []
        for it in d_items[:6]:
            s = it.get("slot") or it
            stype = s.get("site_type") or "일반"
            snum = s.get("site_num") or s.get("full_title", "")
            p_txt = it.get("prev_status_text", "")
            c_txt = it.get("curr_status_text", "")
            if p_txt and c_txt:
                type_strs.append(f"• {stype} {snum}: **{p_txt} ➔ {c_txt}**{link_tag}")
            elif c_txt:
                type_strs.append(f"• {stype} {snum}: **{c_txt}**{link_tag}")
            else:
                type_strs.append(f"• {stype} {snum}{link_tag}")
        if len(d_items) > 6:
            type_strs.append(f"... 외 {len(d_items)-6}개")
        lines.append(f"📅 **{d_key}**\n" + "\n".join(type_strs))

    return "\n\n".join(lines) if lines else "없음"


def format_diff_message(
    campsite_info: Dict[str, Any],
    blue_slots: List[Dict[str, Any]],
    yellow_slots: List[Dict[str, Any]],
    red_slots: List[Dict[str, Any]],
    total_remaining_count: Union[int, str],
    consecutive_pairs: List[Dict[str, Any]] = None
) -> str:
    """
    빈자리 변동(🔵 파란 불: 즉시예약 / 🟡 노란 불: 대기접수 / 🔴 빨간 불: 완전마감) 알림 메시지를 생성합니다.
    """
    park_name = campsite_info.get("park_name", "")
    camp_name = campsite_info.get("camp_name", "")
    camp_types = campsite_info.get("types")
    types_label = f" [{', '.join(camp_types)}]" if camp_types else ""

    blue_slots = blue_slots or []
    yellow_slots = yellow_slots or []
    red_slots = red_slots or []

    parts = []
    if consecutive_pairs: parts.append(f"🔥 {len(consecutive_pairs)}개 2박연박")
    if blue_slots: parts.append(f"🔵 +{len(blue_slots)} 즉시예약")
    if yellow_slots: parts.append(f"🟡 {len(yellow_slots)} 대기접수")
    if red_slots: parts.append(f"🔴 -{len(red_slots)} 완전마감")
    summary_str = " / ".join(parts) if parts else "변동 감지"

    rem_str = str(total_remaining_count)
    if isinstance(total_remaining_count, int) or rem_str.isdigit():
        rem_str = f"{rem_str}자리"

    user_name = campsite_info.get("user_name")
    user_prefix = f"[{user_name}] " if user_name else ""

    lines = [
        f"🚨 {user_prefix}[국립공원 야영장 빈자리 변동 알림 ({summary_str})]",
        f"📍 대상: {park_name} - {camp_name}{types_label} (현재 잔여: {rem_str})",
    ]
    if user_name:
        lines.append(f"👤 수신자: {user_name}")
    lines.append("-" * 30)

    if consecutive_pairs:
        lines.append(f"\n🔥 [주말 2박(금,토) 연박 가능 영지 ({len(consecutive_pairs)}개 발견!)]")
        for p in consecutive_pairs[:10]:
            badge = p.get("case_badge", f"[{p.get('status_summary', '')}]")
            lines.append(f"  • {p['site_type']} {p['site_num']}: {p['fri_date']}(금) ~ {p['sat_date']}(토) {badge}")

    if blue_slots:
        lines.append(f"\n🔵 즉시 예약 가능 (+{len(blue_slots)}자리)")
        lines.append(_format_transition_items_text(blue_slots))

    if yellow_slots:
        lines.append(f"\n🟡 대기 접수 가능 ({len(yellow_slots)}자리)")
        lines.append(_format_transition_items_text(yellow_slots))

    if red_slots:
        lines.append(f"\n🔴 예약 완전 마감 (-{len(red_slots)}자리)")
        lines.append(_format_transition_items_text(red_slots))

    direct_url = get_campsite_direct_url(campsite_info)
    lines.append("\n" + "=" * 30)
    lines.append(f"⚡ 원클릭 예약 바로가기:\n{direct_url}\n🔑 로그인 유지 확인:\n{LOGIN_URL}")
    return "\n".join(lines)


def send_discord_diff(
    webhook_url: str,
    campsite_info: Dict[str, Any],
    blue_slots: List[Dict[str, Any]],
    yellow_slots: List[Dict[str, Any]],
    red_slots: List[Dict[str, Any]],
    total_remaining_count: Union[int, str],
    consecutive_pairs: List[Dict[str, Any]] = None
) -> bool:
    """
    디스코드 웹훅으로 빈자리 변동(🔵 즉시예약 / 🟡 대기접수 / 🔴 완전마감) 내역을 Embed 형태로 전송합니다.
    """
    if not webhook_url:
        return False

    park_name = campsite_info.get("park_name", "")
    camp_name = campsite_info.get("camp_name", "")
    camp_types = campsite_info.get("types")
    type_suffix = f" ({', '.join(camp_types)})" if camp_types else ""
    user_name = campsite_info.get("user_name")
    user_prefix = f"[{user_name}] " if user_name else ""
    direct_url = get_campsite_direct_url(campsite_info)

    blue_slots = blue_slots or []
    yellow_slots = yellow_slots or []
    red_slots = red_slots or []

    embed_fields = []

    if consecutive_pairs:
        pair_desc = []
        for p in consecutive_pairs[:8]:
            badge = p.get("case_badge", "")
            pair_desc.append(f"• **{p['site_type']} {p['site_num']}**: {p['fri_date']}(금) ~ {p['sat_date']}(토) {badge} [⚡예약]({direct_url})")
        embed_fields.append({
            "name": f"🔥 주말 2박(금,토) 연박 가능! ({len(consecutive_pairs)}자리)",
            "value": "\n".join(pair_desc)[:1020],
            "inline": False
        })

    if blue_slots:
        desc = _format_transition_items_discord(blue_slots, direct_url)
        embed_fields.append({
            "name": f"🔵 즉시 예약 가능 (+{len(blue_slots)}자리)",
            "value": desc[:1020],
            "inline": False
        })

    if yellow_slots:
        desc = _format_transition_items_discord(yellow_slots)
        embed_fields.append({
            "name": f"🟡 대기 접수 가능 ({len(yellow_slots)}자리)",
            "value": desc[:1020],
            "inline": False
        })

    if red_slots:
        desc = _format_transition_items_discord(red_slots)
        embed_fields.append({
            "name": f"🔴 예약 완전 마감 (-{len(red_slots)}자리)",
            "value": desc[:1020],
            "inline": False
        })

    parts = []
    if consecutive_pairs: parts.append(f"🔥 {len(consecutive_pairs)}개 2박연박")
    if blue_slots: parts.append(f"🔵 +{len(blue_slots)}")
    if yellow_slots: parts.append(f"🟡 {len(yellow_slots)}대기")
    if red_slots: parts.append(f"🔴 -{len(red_slots)}")
    summary_str = " / ".join(parts) if parts else "변동 감지"

    if consecutive_pairs or blue_slots:
        header_content = f"🚀 **{user_prefix}[{park_name} {camp_name}{type_suffix}] 즉시 예약 가능한 빈자리 발견! ({summary_str})**"
        embed_color = 3447003  # Blue
    elif yellow_slots:
        header_content = f"🟡 **{user_prefix}[{park_name} {camp_name}{type_suffix}] 대기 접수 가능한 빈자리 변동! ({summary_str})**"
        embed_color = 16766720  # Yellow / Gold
    else:
        header_content = f"ℹ️ **{user_prefix}[{park_name} {camp_name}{type_suffix}] 빈자리 예약 마감 ({summary_str})**"
        embed_color = 15158332 # Red

    rem_str = str(total_remaining_count)
    if isinstance(total_remaining_count, int) or rem_str.isdigit():
        rem_str = f"{rem_str}자리"

    embed_desc = (
        f"현재 잔여석: **{rem_str}**\n"
        f"⚡ **[👉 {camp_name} 즉시 예약창 바로가기 (원클릭)]({direct_url})**\n"
        f"🔑 [로그인 유지 확인하기]({LOGIN_URL})"
    )

    payload = {
        "content": header_content,
        "embeds": [
            {
                "title": f"🏕️ {user_prefix}{park_name} - {camp_name}{type_suffix}",
                "description": embed_desc,
                "color": embed_color,
                "fields": embed_fields,
                "footer": {"text": "국립공원 빈자리 실시간 모니터링"}
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
        headers={"Content-Type": "application/json", "User-Agent": "KNPSNotifier/1.0"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"[Notifier Error] Discord Diff 전송 실패: {e}")
        return False


def dispatch_diff_notifications(
    config: Dict[str, Any],
    campsite_info: Dict[str, Any],
    blue_slots: List[Dict[str, Any]],
    yellow_slots: List[Dict[str, Any]],
    red_slots: List[Dict[str, Any]],
    total_remaining_count: Union[int, str],
    consecutive_pairs: List[Dict[str, Any]] = None
) -> Dict[str, bool]:
    """
    설정에 활성화된 알림 채널(텔레그램, 디스코드, 이메일)로 변동(🔵 즉시예약 / 🟡 대기접수 / 🔴 완전마감) 내역을 전송합니다.
    """
    results = {}
    blue_slots = blue_slots or []
    yellow_slots = yellow_slots or []
    red_slots = red_slots or []
    message = format_diff_message(
        campsite_info,
        blue_slots,
        yellow_slots,
        red_slots,
        total_remaining_count,
        consecutive_pairs=consecutive_pairs
    )
    user_id = campsite_info.get("user_id", "user1")
    user_name = campsite_info.get("user_name", user_id)
    notif_cfg = config.get("notification", {}) if "notification" in config else config

    # 1. 텔레그램
    tg_cfg = notif_cfg.get("telegram", {})
    if tg_cfg.get("enabled", False):
        bot_token, chat_id = resolve_telegram_config(notif_cfg, user_id)
        if not bot_token or not chat_id:
            print(f"ℹ️ [{user_name}] 텔레그램 봇 토큰/채팅ID가 설정되지 않아 알림 발송을 건너뜁니다.")
        else:
            results["telegram"] = send_telegram(bot_token, chat_id, message)

    # 2. 디스코드
    dc_cfg = notif_cfg.get("discord", {})
    if dc_cfg.get("enabled", False):
        webhook_url = resolve_discord_webhook(notif_cfg, user_id)
        if not webhook_url:
            print(f"ℹ️ [{user_name}] 디스코드 웹훅 주소가 비어 있어 알림 발송을 건너뜁니다.")
        else:
            results["discord"] = send_discord_diff(
                webhook_url,
                campsite_info,
                blue_slots,
                yellow_slots,
                red_slots,
                total_remaining_count,
                consecutive_pairs=consecutive_pairs
            )

    # 3. 이메일
    em_cfg = notif_cfg.get("email", {})
    if em_cfg.get("enabled", False):
        p_name = campsite_info.get('park_name', '')
        c_name = campsite_info.get('camp_name', '')
        camp_types = campsite_info.get('types')
        type_suffix = f" [{', '.join(camp_types)}]" if camp_types else ""
        parts = []
        if consecutive_pairs: parts.append(f"🔥 {len(consecutive_pairs)}개 2박연박")
        if blue_slots: parts.append(f"+{len(blue_slots)} 즉시예약")
        if yellow_slots: parts.append(f"{len(yellow_slots)} 대기접수")
        if red_slots: parts.append(f"-{len(red_slots)} 완전마감")
        subject = f"[국립공원 빈자리 변동] {p_name} {c_name}{type_suffix} ({' / '.join(parts)})"

        results["email"] = send_email(
            smtp_host=em_cfg.get("smtp_host", "smtp.gmail.com"),
            smtp_port=int(em_cfg.get("smtp_port", 587)),
            smtp_user=em_cfg.get("smtp_user", ""),
            smtp_pass=em_cfg.get("smtp_pass", ""),
            to_email=em_cfg.get("to_email", ""),
            subject=subject,
            body=message,
            use_tls=em_cfg.get("use_tls", True)
        )

    return results


def dispatch_notifications(
    config: Dict[str, Any],
    campsite_info: Dict[str, Any],
    available_slots: List[Dict[str, Any]],
    is_daily: bool = False,
    consecutive_pairs: List[Dict[str, Any]] = None,
    golden_time_text: str = None
) -> Dict[str, bool]:
    """
    설정에 활성화된 알림 채널(텔레그램, 디스코드, 이메일)로 일괄 알림을 전송합니다.
    """
    results = {}
    message = format_notification_message(
        campsite_info,
        available_slots,
        is_daily=is_daily,
        consecutive_pairs=consecutive_pairs,
        golden_time_text=golden_time_text
    )
    user_id = campsite_info.get("user_id", "user1")
    user_name = campsite_info.get("user_name", user_id)
    notif_cfg = config.get("notification", {}) if "notification" in config else config

    # 1. 텔레그램
    tg_cfg = notif_cfg.get("telegram", {})
    if tg_cfg.get("enabled", False):
        bot_token, chat_id = resolve_telegram_config(notif_cfg, user_id)
        if not bot_token or not chat_id:
            print(f"ℹ️ [{user_name}] 텔레그램 봇 토큰/채팅ID가 설정되지 않아 알림 발송을 건너뜁니다.")
        else:
            results["telegram"] = send_telegram(bot_token, chat_id, message)

    # 2. 디스코드
    dc_cfg = notif_cfg.get("discord", {})
    if dc_cfg.get("enabled", False):
        webhook_url = resolve_discord_webhook(notif_cfg, user_id)
        if not webhook_url:
            print(f"ℹ️ [{user_name}] 디스코드 웹훅 주소가 비어 있어 알림 발송을 건너뜁니다.")
        else:
            results["discord"] = send_discord(
                webhook_url,
                message,
                campsite_info,
                available_slots,
                is_daily=is_daily,
                consecutive_pairs=consecutive_pairs,
                golden_time_text=golden_time_text
            )

    # 3. 이메일
    em_cfg = notif_cfg.get("email", {})
    if em_cfg.get("enabled", False):
        p_name = campsite_info.get('park_name', '')
        c_name = campsite_info.get('camp_name', '')
        camp_types = campsite_info.get('types')
        type_suffix = f" [{', '.join(camp_types)}]" if camp_types else ""
        if is_daily:
            con_str = f" (🔥2박연박 {len(consecutive_pairs)}개)" if consecutive_pairs else ""
            subject = f"[국립공원 정기 리포트] {p_name} {c_name}{type_suffix} 잔여 {len(available_slots)}자리{con_str} 현황"
        else:
            subject = f"[국립공원 빈자리 알림] {p_name} {c_name}{type_suffix} {len(available_slots)}자리 오픈!"
        results["email"] = send_email(
            smtp_host=em_cfg.get("smtp_host", "smtp.gmail.com"),
            smtp_port=int(em_cfg.get("smtp_port", 587)),
            smtp_user=em_cfg.get("smtp_user", ""),
            smtp_pass=em_cfg.get("smtp_pass", ""),
            to_email=em_cfg.get("to_email", ""),
            subject=subject,
            body=message,
            use_tls=em_cfg.get("use_tls", True)
        )

    return results


def format_consecutive_message(
    campsite_info: Dict[str, Any],
    consecutive_pairs: List[Dict[str, Any]]
) -> str:
    """
    주말 2박(금,토) 연박 예약 가능 전용 긴급 알림 메시지를 생성합니다.
    """
    park_name = campsite_info.get("park_name", "")
    camp_name = campsite_info.get("camp_name", "")
    camp_types = campsite_info.get("types")
    types_label = f" [{', '.join(camp_types)}]" if camp_types else ""

    user_name = campsite_info.get("user_name")
    user_prefix = f"[{user_name}] " if user_name else ""

    lines = [
        f"🔥 {user_prefix}[국립공원 주말 2박(금,토) 연박 예약 가능 알림!]",
        f"📍 대상: {park_name} - {camp_name}{types_label} ({len(consecutive_pairs)}개 영지 발견)",
    ]
    if user_name:
        lines.append(f"👤 수신자: {user_name}")
    lines.append("-" * 30)

    for p in consecutive_pairs:
        f_s = p.get("fri_slot", {})
        s_s = p.get("sat_slot", {})
        f_txt = f_s.get("status_text", "예약가능" if f_s.get("status") == "R" else "대기예약")
        s_txt = s_s.get("status_text", "예약가능" if s_s.get("status") == "R" else "대기예약")
        badge = p.get("case_badge", "")

        lines.append(f"\n🏕️ {p['site_type']} {p['site_num']}번 [2박 연박] {badge}")
        lines.append(f"📅 일정: {p['fri_date']} (금) ~ {p['sat_date']} (토)")
        lines.append(f"• 금요일: {f_txt} ({f_s.get('price', 0):,}원)")
        lines.append(f"• 토요일: {s_txt} ({s_s.get('price', 0):,}원)")

    direct_url = get_campsite_direct_url(campsite_info)
    lines.append("\n" + "=" * 30)
    lines.append("⚡ 2박 연박 자리는 경쟁이 매우 치열하므로 빠른 예약을 권장합니다!")
    lines.append(f"⚡ 원클릭 예약 바로가기:\n{direct_url}\n🔑 로그인 유지 확인:\n{LOGIN_URL}")
    return "\n".join(lines)


def send_discord_consecutive(
    webhook_url: str,
    campsite_info: Dict[str, Any],
    consecutive_pairs: List[Dict[str, Any]]
) -> bool:
    """
    디스코드 웹훅으로 주말 2박(금,토) 연박 전용 긴급 알림(Embed)을 전송합니다.
    (1.대기+예약 / 2.예약+대기 / 3.예약+예약 / 4.대기+대기 4가지 유형 완벽 지원)
    """
    if not webhook_url or not consecutive_pairs:
        return False

    park_name = campsite_info.get("park_name", "")
    camp_name = campsite_info.get("camp_name", "")
    camp_types = campsite_info.get("types")
    type_suffix = f" ({', '.join(camp_types)})" if camp_types else ""
    user_name = campsite_info.get("user_name")
    user_prefix = f"[{user_name}] " if user_name else ""
    direct_url = get_campsite_direct_url(campsite_info)

    c3_cnt = sum(1 for p in consecutive_pairs if p.get("case_num") == 3)
    c12_cnt = sum(1 for p in consecutive_pairs if p.get("case_num") in (1, 2))
    c4_cnt = sum(1 for p in consecutive_pairs if p.get("case_num") == 4)

    stat_parts = []
    if c3_cnt: stat_parts.append(f"🔵 즉시2박 {c3_cnt}개")
    if c12_cnt: stat_parts.append(f"🟡 예약+대기 {c12_cnt}개")
    if c4_cnt: stat_parts.append(f"🟠 대기2박 {c4_cnt}개")
    stat_summary = f" ({', '.join(stat_parts)})" if stat_parts else f" ({len(consecutive_pairs)}개)"

    embed_fields = []
    for p in consecutive_pairs[:15]:
        f_s = p.get("fri_slot", {})
        s_s = p.get("sat_slot", {})
        f_txt = f_s.get("status_text", "예약가능" if f_s.get("status") == "R" else "대기예약")
        s_txt = s_s.get("status_text", "예약가능" if s_s.get("status") == "R" else "대기예약")
        badge = p.get("case_badge", "")
        embed_fields.append({
            "name": f"🏕️ {p['site_type']} {p['site_num']}번 {badge}",
            "value": (
                f"📅 **{p['fri_date']} (금) ~ {p['sat_date']} (토)**\n"
                f"• 금: **{f_txt}** | 토: **{s_txt}**\n"
                f"• 요금 합계: **{p.get('price_total', 0):,}원**\n"
                f"[⚡ 즉시 예약창 열기]({direct_url})"
            ),
            "inline": True
        })

    header_content = f"🔥 **{user_prefix}[{park_name} {camp_name}{type_suffix}] 주말 2박(금,토) 연박 가능 자리 발견!{stat_summary}**"
    embed_color = 16737792 if c3_cnt > 0 else (16753920 if c12_cnt > 0 else 16744448)
    embed_desc = (
        f"🎉 **금요일과 토요일 연속 2박 숙박이 가능한 자리가 나왔습니다!**\n"
        f"2박 연박은 가장 먼저 마감되므로 지금 바로 예약하세요.\n\n"
        f"⚡ **[👉 {camp_name} 즉시 예약창 바로가기 (원클릭)]({direct_url})**\n"
        f"🔑 [로그인 유지 확인하기]({LOGIN_URL})"
    )

    payload = {
        "content": header_content,
        "embeds": [
            {
                "title": f"🔥 {user_prefix}2박 3일(금+토) 연속 숙박 가능한 영지!",
                "description": embed_desc,
                "color": embed_color,
                "fields": embed_fields,
                "footer": {"text": "국립공원 주말 2박 연박 긴급 알림"}
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
        headers={"Content-Type": "application/json", "User-Agent": "KNPSNotifier/1.0"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"[Notifier Error] Discord Consecutive 전송 실패: {e}")
        return False


def dispatch_consecutive_notifications(
    config: Dict[str, Any],
    campsite_info: Dict[str, Any],
    consecutive_pairs: List[Dict[str, Any]]
) -> Dict[str, bool]:
    """
    주말 2박(금,토) 연박 발생 시 활성화된 알림 채널로 단독 긴급 알림을 전송합니다.
    """
    if not consecutive_pairs:
        return {}

    results = {}
    message = format_consecutive_message(campsite_info, consecutive_pairs)
    user_id = campsite_info.get("user_id", "user1")
    user_name = campsite_info.get("user_name", user_id)
    notif_cfg = config.get("notification", {}) if "notification" in config else config

    # 1. 텔레그램
    tg_cfg = notif_cfg.get("telegram", {})
    if tg_cfg.get("enabled", False):
        bot_token, chat_id = resolve_telegram_config(notif_cfg, user_id)
        if not bot_token or not chat_id:
            print(f"ℹ️ [{user_name}] 텔레그램 봇 토큰/채팅ID가 설정되지 않아 알림 발송을 건너뜁니다.")
        else:
            results["telegram"] = send_telegram(bot_token, chat_id, message)

    # 2. 디스코드
    dc_cfg = notif_cfg.get("discord", {})
    if dc_cfg.get("enabled", False):
        webhook_url = resolve_discord_webhook(notif_cfg, user_id)
        if not webhook_url:
            print(f"ℹ️ [{user_name}] 디스코드 웹훅 주소가 비어 있어 알림 발송을 건너뜁니다.")
        else:
            results["discord"] = send_discord_consecutive(webhook_url, campsite_info, consecutive_pairs)

    # 3. 이메일
    em_cfg = notif_cfg.get("email", {})
    if em_cfg.get("enabled", False):
        p_name = campsite_info.get('park_name', '')
        c_name = campsite_info.get('camp_name', '')
        camp_types = campsite_info.get('types')
        type_suffix = f" [{', '.join(camp_types)}]" if camp_types else ""
        subject = f"[🔥 주말 2박 연박 긴급] {p_name} {c_name}{type_suffix} {len(consecutive_pairs)}개 영지 예약 가능!"

        results["email"] = send_email(
            smtp_host=em_cfg.get("smtp_host", "smtp.gmail.com"),
            smtp_port=int(em_cfg.get("smtp_port", 587)),
            smtp_user=em_cfg.get("smtp_user", ""),
            smtp_pass=em_cfg.get("smtp_pass", ""),
            to_email=em_cfg.get("to_email", ""),
            subject=subject,
            body=message,
            use_tls=em_cfg.get("use_tls", True)
        )

    return results
