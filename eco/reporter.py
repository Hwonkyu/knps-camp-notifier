"""
국립공원 생태탐방원 모니터링 실시간 현황 및 알림 이력을 ECO_STATUS.md 파일로 생성/관리하는 리포터 모듈
"""

import os
from datetime import datetime
from typing import Dict, Any, List

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ECO_STATUS_MD_FILE = os.path.join(CURRENT_DIR, "STATUS.md")
ECO_RESERVATION_URL = "https://res.knps.or.kr/eco/searchEcoReservation.do"


def add_eco_history_entry(
    state: Dict[str, Any],
    center_name_str: str,
    summary: str,
    details: List[str]
):
    """
    최근 알림 발송 이력을 state['history']에 추가합니다 (최대 30개 보관).
    """
    history = state.setdefault("history", [])
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "center": center_name_str,
        "summary": summary,
        "details": details[:10]
    }
    history.insert(0, entry)
    state["history"] = history[:30]


def generate_eco_status_markdown(
    state: Dict[str, Any],
    config: Dict[str, Any]
) -> str:
    """
    현재 state와 config를 바탕으로 표(Table) 형태의 ECO_STATUS.md 마크다운 문서를 생성합니다.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "users" in config and isinstance(config["users"], list):
        centers_cfg = []
        dows_set = set()
        user_names = []
        for u in config["users"]:
            if u.get("enabled", True):
                user_names.append(u.get("name", u.get("id", "")))
                centers_cfg.extend(u.get("eco_centers", []))
                for d in u.get("filters", {}).get("target_weekdays", []):
                    dows_set.add(d)
        dows_str = ", ".join(sorted(list(dows_set))) or "전체 요일"
        user_line = f"> 👤 **활성 사용자**: {', '.join(user_names)}  \n" if user_names else ""
        pet_str = "유저별 설정"
        consec_str = "활성화"
    else:
        centers_cfg = config.get("eco_centers", [])
        filters_cfg = config.get("filters", {})
        notif_cfg = config.get("notification", {})
        dows_str = ", ".join(filters_cfg.get("target_weekdays", [])) or "전체 요일"
        user_line = ""
        pet_str = "반려동물 전용만" if filters_cfg.get("pet_only") else "전체 (반려동물/일반)"
        consec_str = "활성화 (금+토 2박 단독 감지)" if notif_cfg.get("notify_consecutive_weekend", True) else "비활성화"

    center_names_list = []
    seen_centers = set()
    for c in centers_cfg:
        c_name = c.get("name") or c.get("center_name", "")
        if c_name in seen_centers:
            continue
        seen_centers.add(c_name)
        caps = c.get("capacities")
        cap_str = f"[{', '.join(str(x) + '인' for x in caps)}]" if caps else ""
        center_names_list.append(f"**{c_name} 생태탐방원**{cap_str}")
    centers_display = ", ".join(center_names_list) if center_names_list else "설정된 탐방원 없음"

    lines = [
        "# 🏡 국립공원 생태탐방원 실시간 잔여 객실 및 알림 현황",
        "",
        f"> 🕒 **마지막 모니터링 시각**: `{now_str}` (KST)  ",
        user_line,
        f"> 🎯 **감시 생태탐방원**: {centers_display}  ",
        f"> ⚙️ **필터 조건**: 요일: `{dows_str}` | 객실유형: `{pet_str}` | 2박 연박 감지: `{consec_str}`",
        "",
        "---",
        "",
        "## 🔥 주말 2박(금,토) 연박 가능 객실 (2박 3일)",
        ""
    ]

    # 1. 주말 2박 연박 목록 취합
    centers_data = state.get("centers", {})
    if not centers_data and "users" in state:
        centers_data = {}
        for u_id, u_st in state["users"].items():
            for c_id, c_val in u_st.get("centers", {}).items():
                if c_id not in centers_data:
                    centers_data[c_id] = c_val
    all_consecutive = []
    for c_id, c_data in centers_data.items():
        pairs = c_data.get("consecutive_pairs", [])
        for p in pairs:
            all_consecutive.append(p)

    if all_consecutive:
        all_consecutive.sort(key=lambda x: (
            x.get("fri_date", ""),
            x.get("center_name", ""),
            x.get("capacity", 0),
            x.get("room_name", "")
        ))

        lines.append("| 생태탐방원 | 객실명 | 인실 | 연박 일정 | 2박 총요금 | 반려동물 | 바로가기 |")
        lines.append("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
        for p in all_consecutive:
            pet_icon = "🐕 가능" if p.get("pet_allowed") else "-"
            lines.append(
                f"| **{p.get('center_name')}** | {p.get('room_name')} | {p.get('capacity')}인실 | "
                f"{p.get('fri_date')}(금) ~ {p.get('sat_date')}(토) | "
                f"**{p.get('price_total', 0):,}원** | {pet_icon} | [👉 예약하기]({ECO_RESERVATION_URL}) |"
            )
        lines.append("")
    else:
        lines.append("*현재 감시 대상 생태탐방원 중 주말 2박(금,토) 연박 가능한 객실이 없습니다.*")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 📊 현재 예약 가능한 전체 잔여 객실 현황")
    lines.append("")

    # 2. 전체 잔여 객실 목록 취합
    all_rooms = []
    for c_id, c_data in centers_data.items():
        rooms_map = c_data.get("rooms", {})
        for r_id, r in rooms_map.items():
            if r.get("is_available"):
                all_rooms.append(r)

    if all_rooms:
        all_rooms.sort(key=lambda x: (
            x.get("date", ""),
            x.get("center_name", ""),
            x.get("capacity", 0),
            x.get("prd_name", "")
        ))

        lines.append("| 생태탐방원 | 날짜 (요일) | 객실명 | 인실 | 1박 요금 | 반려동물 | 예약 상태 | 바로가기 |")
        lines.append("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
        for r in all_rooms:
            pet_icon = "🐕 가능" if r.get("pet_allowed") else "-"
            lines.append(
                f"| **{r.get('center_name')}** | {r.get('date')} ({r.get('dow')}) | "
                f"{r.get('prd_name')} | {r.get('capacity')}인실 | "
                f"{r.get('price', 0):,}원 | {pet_icon} | 🔵 예약가능 | [👉 예약하기]({ECO_RESERVATION_URL}) |"
            )
        lines.append("")
    else:
        lines.append("*현재 감시 필터 조건에 부합하는 빈자리 객실이 없습니다.*")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 📜 최근 알림 발송 히스토리 (최근 20건)")
    lines.append("")

    history = state.get("history", [])
    if history:
        lines.append("| 발송 일시 (KST) | 대상 탐방원 | 변동 요약 | 세부 변동 내역 |")
        lines.append("|:---:|:---:|:---:|:---|")
        for h in history[:20]:
            details_str = "<br>".join(h.get("details", [])) if h.get("details") else "상세 내역 없음"
            lines.append(f"| {h.get('timestamp')} | {h.get('center')} | **{h.get('summary')}** | {details_str} |")
        lines.append("")
    else:
        lines.append("*아직 발송된 알림 내역이 없습니다.*")
        lines.append("")

    lines.append("---")
    lines.append("*이 문서는 국립공원 생태탐방원 빈자리 자동 알림 봇에 의해 실시간 변동 발생 시 자동으로 업데이트됩니다.*")
    lines.append("")

    return "\n".join(lines)


def update_eco_status_file(
    state: Dict[str, Any],
    config: Dict[str, Any],
    file_path: str = ECO_STATUS_MD_FILE
):
    """
    ECO_STATUS.md 파일로 현황 마크다운을 저장합니다.
    """
    content = generate_eco_status_markdown(state, config)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
