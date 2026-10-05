"""
서울시 공공서비스예약 모니터링 실시간 현황 및 알림 이력을 STATUS.md 파일로 생성/관리하는 리포터 모듈
"""

import os
from datetime import datetime
from typing import Dict, Any, List

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SEOUL_STATUS_MD_FILE = os.path.join(CURRENT_DIR, "STATUS.md")
SEOUL_LOGIN_URL = "https://yeyak.seoul.go.kr/web/loginForm.do"
SEOUL_TOTAL_SEARCH_URL = "https://yeyak.seoul.go.kr/web/search/selectPageListTotalSearch.do"


def add_seoul_history_entry(
    state: Dict[str, Any],
    target_name: str,
    summary: str,
    details: List[str]
):
    """
    최근 알림 발송 이력을 state['history']에 추가합니다 (최대 30개 보관).
    """
    history = state.setdefault("history", [])
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "target": target_name,
        "summary": summary,
        "details": details[:10]
    }
    history.insert(0, entry)
    state["history"] = history[:30]


def generate_seoul_status_markdown(
    state: Dict[str, Any],
    config: Dict[str, Any]
) -> str:
    """
    현재 state와 config를 바탕으로 표(Table) 형태의 seoul/STATUS.md 마크다운 문서를 생성합니다.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    user_names = []
    if "users" in config and isinstance(config["users"], list):
        for u in config["users"]:
            if u.get("enabled", True):
                user_names.append(u.get("name", u.get("id", "")))
    user_line = f"> 👤 **활성 사용자**: {', '.join(user_names)}  \n" if user_names else ""

    targets = config.get("targets", [])
    target_names = [t.get("name", "글램핑존") for t in targets if t.get("enabled", True)]
    target_display = ", ".join(target_names) if target_names else "난지캠핑장 글램핑존"

    lines = [
        "# 🏕️ 서울시 공공서비스예약 (글램핑존) 실시간 현황 및 알림",
        "",
        f"> 🕒 **마지막 모니터링 시각**: `{now_str}` (KST)  ",
        user_line,
        f"> 🎯 **감시 대상 시설**: **{target_display}**  ",
        f"> ⚙️ **추적 방식**: **당월 및 익월(다음 달) 일정 100% 자동 감지** (날짜 수동 지정 불필요)  ",
        f"> ⚡ **원클릭 링크**: [🔑 로그인 상태 확인/유지]({SEOUL_LOGIN_URL}) | [🔍 서울시 공공예약 통합검색]({SEOUL_TOTAL_SEARCH_URL})",
        "",
        "---",
        "",
        "## 📊 현재 추적 중인 글램핑존 월별 예약 현황",
        ""
    ]

    services = state.get("services", {})
    service_list = list(services.values())
    service_list.sort(key=lambda s: s.get("start_date") or "9999-99-99")

    if service_list:
        lines.append("| 시설 서비스명 | 현재 예약 상태 | 접수 기간 | 이용 기간 (이용월) | 요금 | 원클릭 예약 |")
        lines.append("|:---|:---:|:---:|:---:|:---:|:---:|")
        for s in service_list:
            status = s.get("status", "")
            if status == "접수중":
                status_badge = "🔵 **접수중 (예약가능!)**"
            elif status == "안내중":
                status_badge = "🟡 **안내중 (오픈예정)**"
            else:
                status_badge = "🔴 **예약마감**"

            direct_link = f"[⚡ 즉시예약]({s.get('direct_url')})" if s.get("direct_url") else "-"
            lines.append(
                f"| **{s.get('title')}** | {status_badge} | {s.get('rcpt_date')} | "
                f"**{s.get('use_date')}** | {s.get('pay', '유료')} | {direct_link} |"
            )
        lines.append("")
    else:
        lines.append("*현재 활성화된 글램핑존 서비스가 없습니다 (스캔 대기 중).*")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 📜 최근 알림 발송 히스토리 (최근 20건)")
    lines.append("")

    history = state.get("history", [])
    if history:
        lines.append("| 발송 일시 (KST) | 대상 시설 | 변동 요약 | 세부 변동 내역 |")
        lines.append("|:---:|:---:|:---:|:---|")
        for h in history[:20]:
            details_str = "<br>".join(h.get("details", [])) if h.get("details") else "상세 내역 없음"
            lines.append(f"| {h.get('timestamp')} | {h.get('target')} | **{h.get('summary')}** | {details_str} |")
        lines.append("")
    else:
        lines.append("*아직 발송된 알림 내역이 없습니다.*")
        lines.append("")

    lines.append("---")
    lines.append("*이 문서는 서울시 공공서비스예약 자동 알림 봇에 의해 실시간 변동 발생 시 자동으로 업데이트됩니다.*")
    lines.append("")

    return "\n".join(lines)


def update_seoul_status_file(
    state: Dict[str, Any],
    config: Dict[str, Any],
    file_path: str = SEOUL_STATUS_MD_FILE
):
    """
    seoul/STATUS.md 파일로 현황 마크다운을 저장합니다.
    """
    content = generate_seoul_status_markdown(state, config)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
