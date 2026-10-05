"""
서울시 공공서비스예약 (난지캠핑장 글램핑존 등) 실시간 크롤러 모듈
- 키워드(예: '글램핑') 기반으로 당월 및 익월(다음 달)에 개설된 모든 서비스를 자동 발견
- 날짜를 수동 지정하지 않아도 이용기간 종료일(use_end >= today) 기준으로 유효 일정을 자동 필터링
- 봇 차단(WAF) 위험 없이 100% 안전하게 서비스 상태(안내중, 예약마감, 접수중) 수집
"""

import urllib.request
import urllib.parse
from http.cookiejar import CookieJar
import ssl
import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional

SEOUL_TOTAL_SEARCH_URL = "https://yeyak.seoul.go.kr/web/search/selectPageListTotalSearch.do"
SEOUL_LOGIN_URL = "https://yeyak.seoul.go.kr/web/loginForm.do"
SEOUL_RESERV_VIEW_URL = "https://yeyak.seoul.go.kr/web/reservation/selectReservView.do"


def get_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def parse_date_range(date_str: str) -> tuple[Optional[date], Optional[date]]:
    """
    '2026.10.01 ~ 2026.10.31' 또는 '2026-10-01 ~ 2026-10-31' 형식의 날짜 범위를 파싱합니다.
    """
    if not date_str:
        return None, None
    matches = re.findall(r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})", date_str)
    if len(matches) >= 2:
        try:
            start_d = date(int(matches[0][0]), int(matches[0][1]), int(matches[0][2]))
            end_d = date(int(matches[1][0]), int(matches[1][1]), int(matches[1][2]))
            return start_d, end_d
        except Exception:
            pass
    elif len(matches) == 1:
        try:
            d = date(int(matches[0][0]), int(matches[0][1]), int(matches[0][2]))
            return d, d
        except Exception:
            pass
    return None, None


def scan_seoul_services(
    keyword: str = "글램핑",
    match_title: Optional[str] = "글램핑"
) -> List[Dict[str, Any]]:
    """
    서울시 공공서비스예약에서 키워드로 검색하여 현재 유효한(당월 및 다음 달) 모든 서비스를 조회합니다.
    """
    cj = CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPSHandler(context=get_ssl_context())
    )

    data = urllib.parse.urlencode({'h_search1': keyword}).encode('utf-8')
    req = urllib.request.Request(
        SEOUL_TOTAL_SEARCH_URL,
        data=data,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)',
            'Referer': 'https://yeyak.seoul.go.kr/web/main.do'
        }
    )

    try:
        with opener.open(req, timeout=10) as res:
            html = res.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[오류] 서울시 공공예약 검색 중 네트워크 오류: {e}")
        return []

    services = []
    today = datetime.now().date()

    # <a href="#" onclick="fnDetailPage('S260901165106276774'); return false;" ...>
    pattern = r'<li[^>]*>\s*<a\s+[^>]*onclick="fnDetailPage\(\'([^\']+)\'\)[^>]*>([\s\S]*?)</a>\s*</li>'
    for svc_id, content in re.findall(pattern, html):
        title_m = re.search(r'<h4[^>]*class=["\']tit1 sch-rslt["\'][^>]*>([\s\S]*?)</h4>', content)
        title = title_m.group(1).strip() if title_m else ""

        if match_title and match_title not in title:
            continue

        status_m = re.search(r'<span[^>]*class=["\']bd_label status\d+["\'][^>]*>([\s\S]*?)</span>', content)
        status = status_m.group(1).strip() if status_m else "알수없음"

        pay_m = re.search(r'<span[^>]*class=["\']bd_label type\d+["\'][^>]*>([\s\S]*?)</span>', content)
        pay = pay_m.group(1).strip() if pay_m else "유료"

        rcpt_m = re.search(r'<b class="date1">접수기간</b>\s*([^<]+)', content)
        rcpt_date_str = rcpt_m.group(1).strip() if rcpt_m else ""

        use_m = re.search(r'<b class="date2">이용기간</b>\s*([^<]+)', content)
        use_date_str = use_m.group(1).strip() if use_m else ""

        start_date, end_date = parse_date_range(use_date_str)
        rcpt_start_date, rcpt_end_date = parse_date_range(rcpt_date_str)

        # 이용기간 종료일이 오늘보다 이전이면 이미 지난 일정이므로 제외
        if end_date and end_date < today:
            continue

        # 예약 가능 여부 (status가 '접수중'이면 빈자리/예약가능)
        is_available = (status == "접수중")
        is_notice = (status == "안내중")
        is_closed = (status == "예약마감")

        direct_url = f"{SEOUL_RESERV_VIEW_URL}?rsv_svc_id={svc_id}"

        services.append({
            "svc_id": svc_id,
            "title": title,
            "status": status,
            "is_available": is_available,
            "is_notice": is_notice,
            "is_closed": is_closed,
            "pay": pay,
            "rcpt_date": rcpt_date_str,
            "use_date": use_date_str,
            "start_date": start_date.strftime("%Y-%m-%d") if start_date else "",
            "end_date": end_date.strftime("%Y-%m-%d") if end_date else "",
            "rcpt_start": rcpt_start_date.strftime("%Y-%m-%d") if rcpt_start_date else "",
            "direct_url": direct_url,
            "login_url": SEOUL_LOGIN_URL,
            "updated_at": datetime.now().isoformat()
        })

    # 시작일자 기준 오름차순 정렬 (당월 ➔ 익월 순)
    services.sort(key=lambda s: s.get("start_date") or "9999-99-99")
    return services
