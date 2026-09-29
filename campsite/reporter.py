"""
국립공원 야영장 모니터링 실시간 현황 및 알림 이력을 STATUS.md 파일로 생성/관리하는 리포터 모듈
"""

import os
from datetime import datetime
from typing import Dict, Any, List

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_MD_FILE = os.path.join(CURRENT_DIR, "STATUS.md")
RESERVATION_URL = "https://reservation.knps.or.kr/reservation/searchSimpleCampReservation.do"


def add_history_entry(
    state: Dict[str, Any],
    camp_name_str: str,
    summary: str,
    details: List[str]
):
    """
    최근 알림 발송 이력을 state['history']에 추가합니다 (최대 30개 보관).
    """
    history = state.setdefault("history", [])
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "camp": camp_name_str,
        "summary": summary,
        "details": details[:10]  # 최대 10개 상세 항목
    }
    history.insert(0, entry)
    state["history"] = history[:30]


def generate_status_markdown(
    state: Dict[str, Any],
    config: Dict[str, Any]
) -> str:
    """
    현재 state와 config를 바탕으로 표(Table) 형태의 STATUS.md 마크다운 문서를 생성합니다.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "users" in config and isinstance(config["users"], list):
        campsites_cfg = []
        dows_set = set()
        user_names = []
        for u in config["users"]:
            if u.get("enabled", True):
                user_names.append(u.get("name", u.get("id", "")))
                campsites_cfg.extend(u.get("campsites", []))
                for d in u.get("filters", {}).get("target_weekdays", []):
                    dows_set.add(d)
        dows_str = ", ".join(sorted(list(dows_set))) or "전체 요일"
        user_line = f"> 👤 **활성 사용자**: {', '.join(user_names)}  \n" if user_names else ""
        waiting_str = "유저별 설정"
        consec_str = "활성화"
    else:
        campsites_cfg = config.get("campsites", [])
        filters_cfg = config.get("filters", {})
        notif_cfg = config.get("notification", {})
        dows_str = ", ".join(filters_cfg.get("target_weekdays", [])) or "전체 요일"
        user_line = ""
        waiting_str = "포함 (R+W)" if filters_cfg.get("include_waiting", True) else "미포함 (R만)"
        consec_str = "활성화 (금+토 2박 단독 알림)" if notif_cfg.get("notify_consecutive_weekend", True) else "비활성화"

    camp_names_list = []
    seen_camps = set()
    for c in campsites_cfg:
        key = (c.get("park_name"), c.get("camp_name"))
        if key in seen_camps:
            continue
        seen_camps.add(key)
        t_str = f"[{', '.join(c.get('types', []))}]" if c.get("types") else ""
        camp_names_list.append(f"**{c.get('park_name')} {c.get('camp_name')}**{t_str}")
    camps_display = ", ".join(camp_names_list) if camp_names_list else "설정된 야영장 없음"

    lines = [
        "# 🏕️ 국립공원 야영장 실시간 잔여석 및 알림 현황",
        "",
        f"> 🕒 **마지막 모니터링 시각**: `{now_str}` (KST)  ",
        user_line,
        f"> 🎯 **감시 야영장**: {camps_display}  ",
        f"> ⚙️ **필터 조건**: 요일: `{dows_str}` | 대기예약: `{waiting_str}` | 2박 연박 감지: `{consec_str}`",
        "",
        "---",
        "",
        "## 🔥 주말 2박(금,토) 연박 가능 영지 (2박 3일)",
        ""
    ]

    # 1. 2박 연박 목록 취합
    camp_states = state.get("campsites", {})
    if not camp_states and "users" in state:
        camp_states = {}
        for u_id, u_st in state["users"].items():
            camp_states.update(u_st.get("campsites", {}))
    all_consecutive = []
    for s_key, c_data in camp_states.items():
        pairs = c_data.get("consecutive_pairs_data", [])
        for p in pairs:
            all_consecutive.append(p)

    if all_consecutive:
        # 우선순위 정렬 (날짜 -> 케이스 우선순위 3, 2, 1, 4 -> 영지)
        priority_map = {3: 0, 2: 1, 1: 2, 4: 3}
        all_consecutive.sort(key=lambda x: (
            x.get("fri_date", ""),
            priority_map.get(x.get("case_num", 3), 99),
            x.get("site_type", ""),
            x.get("site_num", "")
        ))

        lines.append("| 공원명 | 야영장 | 시설타입 | 사이트 번호 | 연박 일정 | 유형 배지 | 금요일 상태 | 토요일 상태 | 요금 합계 | 바로가기 |")
        lines.append("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
        for p in all_consecutive:
            f_stat = p.get("fri_status", "예약가능")
            s_stat = p.get("sat_status", "예약가능")
            lines.append(
                f"| {p.get('park_name')} | {p.get('camp_name')} | {p.get('site_type')} | "
                f"**{p.get('site_num')}번** | {p.get('fri_date')}(금) ~ {p.get('sat_date')}(토) | "
                f"{p.get('case_badge', '')} | {f_stat} | {s_stat} | "
                f"{p.get('price_total', 0):,}원 | [👉 예약하기]({RESERVATION_URL}) |"
            )
        lines.append("")
    else:
        lines.append("*현재 감시 대상 야영장 중 주말 2박(금,토) 연박 가능한 자리가 없습니다.*")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 📊 현재 예약/대기 가능한 전체 잔여석 현황")
    lines.append("")

    # 2. 전체 잔여석 목록 취합
    all_slots = []
    for s_key, c_data in camp_states.items():
        slots_map = c_data.get("slots", {})
        for k, s in slots_map.items():
            all_slots.append(s)

    if all_slots:
        all_slots.sort(key=lambda x: (
            x.get("date", ""),
            x.get("park_name", ""),
            x.get("camp_name", ""),
            x.get("site_type", ""),
            x.get("site_num", "")
        ))

        lines.append("| 공원명 | 야영장 | 날짜 (요일) | 시설타입 | 사이트 번호 | 예약 상태 | 1박 요금 | 바로가기 |")
        lines.append("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
        for s in all_slots:
            stat_icon = "🔵 예약가능" if s.get("status") == "R" else "🟡 대기예약"
            lines.append(
                f"| {s.get('park_name')} | {s.get('camp_name')} | {s.get('date')} ({s.get('dow')}) | "
                f"{s.get('site_type')} | **{s.get('site_num')}** | {stat_icon} | "
                f"{s.get('price', 0):,}원 | [👉 예약하기]({RESERVATION_URL}) |"
            )
        lines.append("")
    else:
        lines.append("*현재 감시 필터 조건에 부합하는 빈자리/대기자리가 없습니다.*")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 📜 최근 알림 발송 히스토리 (최근 20건)")
    lines.append("")

    history = state.get("history", [])
    if history:
        lines.append("| 발송 일시 (KST) | 대상 야영장 | 변동 요약 | 세부 변동 내역 |")
        lines.append("|:---:|:---:|:---:|:---|")
        for h in history[:20]:
            details_str = "<br>".join(h.get("details", [])) if h.get("details") else "상세 내역 없음"
            lines.append(f"| {h.get('timestamp')} | {h.get('camp')} | **{h.get('summary')}** | {details_str} |")
        lines.append("")
    else:
        lines.append("*아직 발송된 알림 내역이 없습니다.*")
        lines.append("")

    lines.append("---")
    lines.append("*이 문서는 국립공원 야영장 빈자리 자동 알림 봇에 의해 실시간 변동 발생 시 자동으로 업데이트됩니다.*")
    lines.append("")

    return "\n".join(lines)


def update_status_file(
    state: Dict[str, Any],
    config: Dict[str, Any],
    file_path: str = STATUS_MD_FILE
):
    """
    STATUS.md 파일로 현황 마크다운을 저장합니다.
    """
    content = generate_status_markdown(state, config)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
