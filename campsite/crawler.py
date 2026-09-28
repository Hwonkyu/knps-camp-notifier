"""
국립공원공단(KNPS) 야영장 실시간 예약 가능 현황 크롤러 모듈
순수 표준 라이브러리(urllib, re, json, datetime)를 사용하여 외부 의존성 없이 동작합니다.
"""

import urllib.request
import urllib.parse
import ssl
import re
import socket
import time
import concurrent.futures
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# 소켓 레벨 전역 타임아웃 10초 설정 (네트워크 행 방지)
socket.setdefaulttimeout(10)

BASE_URL = "https://reservation.knps.or.kr"
CAMPSITE_LIST_URL = f"{BASE_URL}/reservation/campsiteList.do"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": f"{BASE_URL}/reservation/searchSimpleCampReservation.do",
    "Origin": BASE_URL,
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept": "text/html, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Ch-Ua": "\"Chromium\";v=\"122\", \"Not(A:Brand\";v=\"24\", \"Google Chrome\";v=\"122\"",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "\"Windows\"",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "X-Requested-With": "XMLHttpRequest",
}

import threading

def _execute_http_request(encoded_data: bytes, ctx: ssl.SSLContext, timeout: int) -> str:
    req = urllib.request.Request(
        CAMPSITE_LIST_URL,
        data=encoded_data,
        headers=HEADERS,
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_campsite_html(
    park_name: str,
    camp_name: str,
    dept_id: str,
    timeout: int = 8,
    max_retries: int = 2
) -> str:
    """
    국립공원 야영장 잔여석 HTML 데이터를 비동기 엔드포인트에서 가져옵니다.
    공단 서버의 지연 및 패킷 드롭 방지를 위해 데몬 스레드(daemon thread) 기반의 강제 절대 타임아웃을 적용하며,
    실패 시 최대 max_retries회 지수 백오프로 재시도합니다.
    """
    payload = {
        "dept_id": dept_id,
        "dept_name": camp_name,
        "parent_dept_name": park_name,
        "prd_ctg_id": "",
        "isGreenpoint": "N",
    }
    encoded_data = urllib.parse.urlencode(payload).encode("utf-8")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    last_err = None
    for attempt in range(max_retries + 1):
        result_holder = []
        error_holder = []

        def worker():
            try:
                res = _execute_http_request(encoded_data, ctx, timeout)
                result_holder.append(res)
            except Exception as ex:
                error_holder.append(ex)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            last_err = TimeoutError(f"HTTP 요청 절대 타임아웃({timeout}초) 초과")
        elif error_holder:
            last_err = error_holder[0]
        elif result_holder:
            return result_holder[0]
        else:
            last_err = TimeoutError("응답 없음")

        if attempt < max_retries:
            # 점진적 백오프: 1차 실패 시 2.0초, 2차 실패 시 3.0초 대기 (WAF 쿨다운 및 일시적 혼잡 해소)
            wait_seconds = 2.0 if attempt == 0 else 3.0
            print(f"      ⚠️ [{camp_name}] 일시적 응답 지연/오류 ({last_err}), {wait_seconds}초 후 재시도 ({attempt + 1}/{max_retries})...")
            time.sleep(wait_seconds)
            continue
        raise last_err

def parse_campsite_types(html: str) -> List[Dict[str, str]]:
    """
    해당 야영장에 존재하는 시설 유형(예: 자동차야영장, 카라반, 특화야영장 등)을 파싱합니다.
    """
    pattern = r"<input[^>]*name=['\"]campGnbChk['\"][^>]*value=['\"]([^'\"]*)['\"][^>]*>.*?<label[^>]*>(.*?)</label>"
    matches = re.findall(pattern, html, re.DOTALL)
    results = []
    for val, lbl in matches:
        clean_lbl = re.sub(r"<[^>]+>", "", lbl).strip()
        results.append({"code": val.strip(), "name": clean_lbl})
    return results

def parse_available_slots(html: str) -> List[Dict[str, Any]]:
    """
    HTML 내에서 예약 가능('R') 또는 대기 예약('W') 상태의 모든 슬롯을 파싱합니다.
    """
    # <i> 태그 내 속성 추출
    # 예: <i title="A13 : 2026-09-23" class="icon-reservation ..." data-title="..." data-reser_tp='R' data-use_df='20260923' ...>
    i_tag_pattern = r"<i\b([^>]*)>"
    tags = re.findall(i_tag_pattern, html, re.DOTALL)

    slots = []

    for tag in tags:
        # data-reser_tp 확인 ('R': 예약가능, 'W': 대기예약)
        tp_match = re.search(r"data-reser_tp=['\"]([A-Z])['\"]", tag)
        if not tp_match:
            continue
        reser_tp = tp_match.group(1)
        if reser_tp not in ("R", "W"):
            continue

        # data-title: 가야산-백운동-자동차야영장-A13
        title_match = re.search(r"data-title=['\"]([^'\"]+)['\"]", tag)
        full_title = title_match.group(1).strip() if title_match else ""

        # data-payment-title: 자동차야영장 A13
        pay_title_match = re.search(r"data-payment-title=['\"]([^'\"]+)['\"]", tag)
        payment_title = pay_title_match.group(1).strip() if pay_title_match else ""

        # data-use_df: 20260923
        use_df_match = re.search(r"data-use_df=['\"](\d{8})['\"]", tag)
        raw_date = use_df_match.group(1).strip() if use_df_match else ""
        if not raw_date:
            continue

        # Format date as YYYY-MM-DD
        formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

        # data-ctrt-dow: 요일 (수, 목 등)
        dow_match = re.search(r"data-ctrt-dow=['\"]([^'\"]+)['\"]", tag)
        dow = dow_match.group(1).strip() if dow_match else ""

        # data-sal-amt: 요금 (30000)
        sal_match = re.search(r"data-sal-amt=['\"](\d+)['\"]", tag)
        price = int(sal_match.group(1)) if sal_match else 0

        # data-prod-id: 상품ID
        prod_id_match = re.search(r"data-prod-id=['\"]([^'\"]+)['\"]", tag)
        prod_id = prod_id_match.group(1).strip() if prod_id_match else ""

        # 타이틀 분해
        parts = full_title.split("-")
        park_name = parts[0] if len(parts) > 0 else ""
        camp_name = parts[1] if len(parts) > 1 else ""
        site_type = parts[2] if len(parts) > 2 else ""
        site_num = "-".join(parts[3:]) if len(parts) > 3 else ""

        slot_id = f"{raw_date}_{prod_id or full_title}_{reser_tp}"
        site_key = f"{raw_date}_{prod_id or full_title}"

        slots.append({
            "slot_id": slot_id,
            "site_key": site_key,
            "park_name": park_name,
            "camp_name": camp_name,
            "site_type": site_type,
            "site_num": site_num,
            "full_title": full_title,
            "payment_title": payment_title,
            "date": formatted_date,
            "raw_date": raw_date,
            "dow": dow,
            "status": reser_tp, # 'R' or 'W'
            "status_text": "예약가능" if reser_tp == "R" else "대기예약",
            "price": price,
            "prod_id": prod_id,
        })

    return slots

def filter_slots(
    slots: List[Dict[str, Any]],
    target_dates: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    target_dows: Optional[List[str]] = None,
    target_types: Optional[List[str]] = None,
    target_sites: Optional[List[str]] = None,
    include_waiting: bool = False
) -> List[Dict[str, Any]]:
    """
    사용자가 설정한 조건에 부합하는 빈자리 슬롯만 필터링합니다.
    """
    filtered = []

    # 날짜 형식 통일 (YYYYMMDD or YYYY-MM-DD -> YYYY-MM-DD)
    normalized_target_dates = set()
    if target_dates:
        for d in target_dates:
            d_clean = str(d).strip().replace(".", "-").replace("/", "")
            if len(d_clean) == 8 and d_clean.isdigit():
                d_clean = f"{d_clean[:4]}-{d_clean[4:6]}-{d_clean[6:8]}"
            normalized_target_dates.add(d_clean)

    for s in slots:
        # 1. 상태 필터 (기본은 'R' 예약가능만, include_waiting=True인 경우 'W' 대기예약도 포함)
        if not include_waiting and s["status"] != "R":
            continue

        # 2. 특정 날짜 목록 필터
        if normalized_target_dates:
            if s["date"] not in normalized_target_dates:
                continue

        # 3. 날짜 범위 필터 (start_date, end_date)
        if start_date and s["date"] < start_date:
            continue
        if end_date and s["date"] > end_date:
            continue

        # 4. 요일 필터 (예: ['금', '토', '일'])
        if target_dows:
            if s["dow"] not in target_dows:
                continue

        # 5. 시설 타입 필터 (예: ['자동차야영장', '카라반'])
        if target_types:
            type_matched = any(t in s["site_type"] or t in s["full_title"] for t in target_types)
            if not type_matched:
                continue

        # 6. 특정 사이트 번호 필터 (예: ['A13', 'A14'])
        if target_sites:
            site_matched = any(site in s["site_num"] or site in s["full_title"] for site in target_sites)
            if not site_matched:
                continue

        filtered.append(s)

    return filtered


def find_consecutive_weekend_slots(
    slots: List[Dict[str, Any]],
    include_waiting: bool = False
) -> List[Dict[str, Any]]:
    """
    동일 야영장 내 동일 영지(site_type + site_num)에서 금요일과 토요일 연속 2박이 가능한 슬롯 쌍을 찾습니다.
    사용자 요구사항에 따라 양일 모두 '즉시 예약 가능(R)'인 경우만 2박 연박으로 판정합니다. (대기예약은 2박 연박에서 제외)
    """
    spots: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for s in slots:
        if not include_waiting and s.get("status") != "R":
            continue

        stype = s.get("site_type", "")
        snum = s.get("site_num", "")
        if stype and snum:
            spot_id = f"{stype}_{snum}"
        else:
            spot_id = s.get("prod_id") or s.get("full_title", "")

        date_str = s.get("date", "")
        if spot_id and date_str:
            spots.setdefault(spot_id, {})[date_str] = s

    pairs = []
    for spot_id, dates_map in spots.items():
        for d_str, fri_slot in dates_map.items():
            if fri_slot.get("dow") == "금":
                try:
                    fri_date = datetime.strptime(d_str, "%Y-%m-%d").date()
                    expected_sat_str = (fri_date + timedelta(days=1)).strftime("%Y-%m-%d")
                    if expected_sat_str in dates_map:
                        sat_slot = dates_map[expected_sat_str]
                        if sat_slot.get("dow") == "토":
                            f_stat = fri_slot.get("status", "R")
                            s_stat = sat_slot.get("status", "R")

                            # 둘 다 즉시 예약가능(R)인 경우만 2박 연박으로 인정
                            if not include_waiting and (f_stat != "R" or s_stat != "R"):
                                continue

                            both_direct = (f_stat == "R" and s_stat == "R")
                            case_num = 3 if both_direct else 1
                            case_name = "예약가능 + 예약가능" if both_direct else "대기 포함"
                            case_badge = "🔵 [즉시 2박 예약]" if both_direct else "🟡 [대기 포함]"
                            status_summary = "금:예약 / 토:예약 (즉시2박)" if both_direct else f"금:{f_stat} / 토:{s_stat}"

                            pair_id = f"{d_str}_{expected_sat_str}_{spot_id}_{f_stat}_{s_stat}"

                            pairs.append({
                                "pair_id": pair_id,
                                "spot_id": spot_id,
                                "case_num": case_num,
                                "case_name": case_name,
                                "case_badge": case_badge,
                                "park_name": fri_slot.get("park_name", ""),
                                "camp_name": fri_slot.get("camp_name", ""),
                                "site_type": fri_slot.get("site_type") or sat_slot.get("site_type", ""),
                                "site_num": fri_slot.get("site_num") or sat_slot.get("site_num", ""),
                                "fri_date": d_str,
                                "sat_date": expected_sat_str,
                                "fri_slot": fri_slot,
                                "sat_slot": sat_slot,
                                "both_direct": both_direct,
                                "status_summary": status_summary,
                                "price_total": fri_slot.get("price", 0) + sat_slot.get("price", 0)
                            })
                except Exception:
                    continue

    # 정렬 우선순위: 날짜 순 -> 케이스 우선순위(Case 3: 예약+예약 -> Case 2 -> Case 1 -> Case 4) -> 영지 번호 순
    priority_map = {3: 0, 2: 1, 1: 2, 4: 3}
    pairs.sort(key=lambda x: (
        x["fri_date"],
        priority_map.get(x["case_num"], 99),
        x["site_type"],
        x["site_num"]
    ))
    return pairs
