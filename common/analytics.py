"""
국립공원 빈자리 취소표 골든타임 통계 분석 모듈
- 2분마다 감지되는 빈자리 전환(마감 ➔ 예약가능) 이벤트를 누적 수집
- 요일별 / 시간대별(골든타임) / 리드타임(D-Day) 피크 패턴 분석
- 정기 브리핑(06시/18시) 및 STATUS.md 대시보드 시각화 제공
"""

import re
from datetime import datetime
from collections import Counter
from typing import Dict, Any, List, Optional

WEEKDAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]
MAX_CANCELLATION_EVENTS = 10000  # 약 1년치 취소표 누적 표본 보관 (~1.5MB)


def record_cancellation_events(state: Dict[str, Any], new_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    새로 발생한 취소표 이벤트를 state['cancellation_events']에 누적 저장합니다 (최대 10,000건 보관).
    """
    if not new_events:
        return state.get("cancellation_events", [])

    events = state.setdefault("cancellation_events", [])
    events.extend(new_events)

    if len(events) > MAX_CANCELLATION_EVENTS:
        events = events[-MAX_CANCELLATION_EVENTS:]
    state["cancellation_events"] = events
    return events


def seed_from_history_if_needed(state: Dict[str, Any]):
    """
    기존에 state['history']에 쌓여있던 이전 알림 내역을 파싱하여
    cancellation_events의 초기 데이터셋으로 자동 마이그레이션(시딩)합니다.
    """
    events = state.setdefault("cancellation_events", [])
    if events:
        return

    history = state.get("history", [])
    for h in history:
        ts_str = h.get("timestamp", "")
        if not ts_str:
            continue
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue

        cancel_dow = WEEKDAYS_KO[dt.weekday()]
        cancel_hour = dt.hour
        camp_raw = h.get("camp") or h.get("center", "")
        camp_clean = re.sub(r"\[.*?\]|\(.*?\)", "", camp_raw).strip()

        for d in h.get("details", []):
            if "🔵" in d or "즉시예약" in d or "예약가능" in d:
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", d)
                target_date = date_match.group(1) if date_match else None
                lead_days = None
                if target_date:
                    try:
                        td = datetime.strptime(target_date, "%Y-%m-%d").date()
                        lead_days = (td - dt.date()).days
                    except Exception:
                        pass
                events.append({
                    "timestamp": ts_str,
                    "camp": camp_clean,
                    "target_date": target_date,
                    "cancel_dow": cancel_dow,
                    "cancel_hour": cancel_hour,
                    "lead_days": lead_days
                })

    state["cancellation_events"] = events


def analyze_cancellation_stats(
    events: List[Dict[str, Any]],
    camp_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    누적된 취소표 이벤트 데이터를 분석하여 골든타임 지표를 반환합니다.
    """
    filtered = []
    for e in events:
        c_name = e.get("camp", "")
        if camp_filter:
            if camp_filter in c_name or c_name in camp_filter:
                filtered.append(e)
        else:
            filtered.append(e)

    total_count = len(filtered)
    if total_count < 2:
        return {
            "has_enough_data": False,
            "total_count": total_count,
            "top_dow": None,
            "top_dow_pct": 0,
            "top_block": None,
            "top_block_pct": 0,
            "top_lead": None,
            "summary_tip": f"취소표 표본 수집 중입니다 ({total_count}건 누적됨). 데이터가 쌓이면 피크 시간대가 분석됩니다."
        }

    # 1. 요일 통계
    dow_counter = Counter(e["cancel_dow"] for e in filtered if e.get("cancel_dow"))
    top_dow, dow_cnt = dow_counter.most_common(1)[0]
    top_dow_pct = round(dow_cnt / total_count * 100)

    # 2. 2시간 단위 시간대 블록 통계
    hour_blocks = Counter()
    for e in filtered:
        h = e.get("cancel_hour")
        if h is not None:
            block_start = (int(h) // 2) * 2
            hour_blocks[f"{block_start:02d}:00~{block_start+2:02d}:00"] += 1

    top_block, blk_cnt = hour_blocks.most_common(1)[0]
    top_block_pct = round(blk_cnt / total_count * 100)

    # 3. 리드타임 (D-Day) 통계
    leads = [e["lead_days"] for e in filtered if e.get("lead_days") is not None and e.get("lead_days") >= 0]
    lead_counter = Counter(leads)
    top_lead = None
    if lead_counter:
        top_lead_val, _ = lead_counter.most_common(1)[0]
        top_lead = f"D-{top_lead_val} (입실 {top_lead_val}일 전)"

    camp_label = f"[{camp_filter}] " if camp_filter else ""
    summary_tip = (
        f"{camp_label}취소표는 주로 **{top_dow}요일({top_dow_pct}%)**, "
        f"**{top_block}({top_block_pct}%)** 시간대에 가장 집중 발생했습니다. (표본 {total_count}건)"
    )

    return {
        "has_enough_data": True,
        "total_count": total_count,
        "top_dow": f"{top_dow}요일",
        "top_dow_pct": top_dow_pct,
        "top_block": top_block,
        "top_block_pct": top_block_pct,
        "top_lead": top_lead or "분석 중",
        "summary_tip": summary_tip
    }


def generate_golden_time_summary_text(
    state: Dict[str, Any],
    camp_name: Optional[str] = None
) -> str:
    """
    정기 브리핑 알림 메시지에 삽입할 골든타임 공략 팁 텍스트를 반환합니다.
    """
    seed_from_history_if_needed(state)
    events = state.get("cancellation_events", [])
    stats = analyze_cancellation_stats(events, camp_filter=camp_name)
    return stats["summary_tip"]


def generate_golden_time_markdown_table(
    state: Dict[str, Any],
    camps_list: Optional[List[str]] = None,
    category_label: str = "야영장"
) -> str:
    """
    STATUS.md 대시보드에 렌더링할 골든타임 통계 분석 표 마크다운을 반환합니다.
    """
    seed_from_history_if_needed(state)
    events = state.get("cancellation_events", [])
    if not events:
        return f"*{category_label} 취소표 발생 표본 데이터 수집 중입니다.*"

    # 타겟 시설 목록 구성
    if not camps_list:
        all_camps = set(e.get("camp", "") for e in events if e.get("camp"))
        camps_list = sorted(list(all_camps))

    lines = [
        f"## 📈 {category_label}별 취소표 골든타임 통계 분석 (피크 방출 시간대)",
        "",
        "> 💡 **데이터 기반 공략 팁**: 2분마다 감지된 실제 취소표 방출 시점 데이터를 누적 분석한 결과입니다. 아래 피크 시간대에 스마트폰을 집중 주시하세요!",
        "",
        f"| 대상 {category_label} | 취소표 최다 요일 | 피크 시간대 (골든타임) | 주요 취소 시점 (D-Day) | 분석 표본 |",
        "|:---:|:---:|:---:|:---:|:---:|"
    ]

    has_row = False
    for camp in camps_list:
        stats = analyze_cancellation_stats(events, camp_filter=camp)
        if stats["total_count"] == 0:
            continue
        has_row = True
        dow_str = f"🥇 {stats['top_dow']} ({stats['top_dow_pct']}%)" if stats["top_dow"] else "-"
        block_str = f"⏰ **{stats['top_block']}** ({stats['top_block_pct']}%)" if stats["top_block"] else "-"
        lead_str = stats.get("top_lead") or "-"
        lines.append(f"| **{camp}** | {dow_str} | {block_str} | {lead_str} | {stats['total_count']}건 |")

    if not has_row:
        return "*현재 감시 대상 야영장의 취소표 표본 수집 중입니다.*"

    lines.append("")
    return "\n".join(lines)
