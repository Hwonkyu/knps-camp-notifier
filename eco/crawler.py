"""
국립공원 생태탐방원 실시간 예약 현황 크롤러 모듈
- 국립공원 생태탐방원 생활관(객실) API(getEcoLivingRoomInfo.do)를 순수 파이썬 표준 라이브러리로 조회합니다.
- HTML 파싱 없이 공식 JSON API를 직접 호출하므로 매우 빠르고 안정적입니다.
"""

import json
import urllib.request
import urllib.parse
import ssl
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

API_URL = "https://res.knps.or.kr/eco/getEcoLivingRoomInfo.do"
RESERVATION_PAGE_URL = "https://res.knps.or.kr/eco/searchEcoReservation.do"

WEEKDAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": RESERVATION_PAGE_URL,
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def _create_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_eco_living_rooms(
    dept_id: str,
    checkin_date: str,
    timeout: int = 10,
    max_retries: int = 2
) -> List[Dict[str, Any]]:
    """
    특정 생태탐방원의 지정 입실일(1박 2일)에 대한 전체 생활관(객실) 현황을 조회합니다.
    
    :param dept_id: 생태탐방원 기관 코드 (예: 북한산 B971002)
    :param checkin_date: 입실일 (YYYY-MM-DD)
    :return: 해당 날짜의 전체 객실 상태 목록
    """
    try:
        checkin_dt = datetime.strptime(checkin_date, "%Y-%m-%d")
    except ValueError:
        return []

    checkout_dt = checkin_dt + timedelta(days=1)
    checkout_date = checkout_dt.strftime("%Y-%m-%d")
    dow = WEEKDAYS_KO[checkin_dt.weekday()]

    payload = urllib.parse.urlencode({
        "deptId": dept_id,
        "useBgnDt": checkin_date,
        "useEndDt": checkout_date,
        "hrkPrdCtgId": "06001"  # 생활관(객실) 카테고리 고정
    }).encode("utf-8")

    ctx = _create_ssl_context()
    req = urllib.request.Request(API_URL, data=payload, headers=DEFAULT_HEADERS, method="POST")

    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                if resp.status != 200:
                    continue
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                raw_goods = data.get("insttGoodsInfo", [])

                rooms = []
                for g in raw_goods:
                    max_cnt = int(g.get("maxNopCnt") or 0)
                    rsvt_cnt = int(g.get("rsrvtCnt") or 0)
                    remaining = max_cnt - rsvt_cnt
                    rsvt_psbl = (g.get("rsvtPsblYn") == "Y")
                    sal_stcd = g.get("prdSalStcd")  # 'N': 판매중(정상), 'Y': 마감 등

                    is_available = (remaining > 0 and rsvt_psbl and sal_stcd == "N")
                    status = "R" if is_available else "NONE"
                    status_text = "예약가능" if is_available else "마감"

                    prd_id = str(g.get("prdId", ""))
                    prd_name = str(g.get("prdNm", "")).strip()
                    capacity = int(g.get("mmbMaxRqnpCnt") or 0)
                    price = int(g.get("salAmt") or 0)
                    pet_allowed = (g.get("petRsvtPsbYn") == "Y")
                    barrier_free = (g.get("brfeTerYn") == "Y")
                    category = str(g.get("prdCtgNm", "")).strip()

                    slot_id = f"{dept_id}_{checkin_date}_{prd_id}"

                    rooms.append({
                        "slot_id": slot_id,
                        "dept_id": dept_id,
                        "date": checkin_date,
                        "dow": dow,
                        "prd_id": prd_id,
                        "prd_name": prd_name,
                        "category": category,
                        "capacity": capacity,
                        "price": price,
                        "pet_allowed": pet_allowed,
                        "barrier_free": barrier_free,
                        "remaining": remaining,
                        "max_count": max_cnt,
                        "reserved_count": rsvt_cnt,
                        "status": status,
                        "status_text": status_text,
                        "is_available": is_available,
                    })

                return rooms
        except Exception as e:
            if attempt < max_retries:
                import time
                time.sleep(1.0)
            else:
                print(f"[Eco Crawler Error] {dept_id} ({checkin_date}) 조회 실패: {e}")
                return []
    return []


def generate_target_dates(filters: Dict[str, Any]) -> List[str]:
    """
    filters 설정에 따라 조회 대상 날짜 목록을 생성합니다.
    """
    # 1. target_dates 직접 지정 시 최우선 사용
    raw_targets = filters.get("target_dates") or []
    if raw_targets:
        return sorted(list(set(raw_targets)))

    # 2. start_date ~ end_date 범위 생성
    start_str = filters.get("start_date")
    end_str = filters.get("end_date")

    today = datetime.now().date()
    if start_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = today
    else:
        start_date = today

    if end_str:
        try:
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError:
            end_date = start_date + timedelta(days=30)
    else:
        end_date = start_date + timedelta(days=30)

    # 과거 날짜는 제외
    if start_date < today:
        start_date = today

    target_weekdays = set(filters.get("target_weekdays") or [])

    dates = []
    curr = start_date
    while curr <= end_date:
        dow = WEEKDAYS_KO[curr.weekday()]
        if not target_weekdays or dow in target_weekdays:
            dates.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)

    return dates


def scan_eco_center(
    center_info: Dict[str, Any],
    dates: List[str],
    capacities: Optional[List[int]] = None,
    pet_only: bool = False
) -> Dict[str, Any]:
    """
    단일 생태탐방원에 대해 대상 날짜들의 전체 객실을 스캔하고,
    빈자리 및 주말 2박(금,토) 연박 가능 객실을 감지합니다.
    """
    dept_id = center_info["dept_id"]
    center_name = center_info.get("name") or center_info.get("center_name", "")

    all_rooms_map: Dict[str, Dict[str, Any]] = {}
    available_rooms_map: Dict[str, Dict[str, Any]] = {}

    # 날짜별로 수집된 방 목록 (주말 연박 감지용: date -> {prd_id: room})
    rooms_by_date: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for d in dates:
        rooms = fetch_eco_living_rooms(dept_id, d)
        rooms_by_date[d] = {}

        for r in rooms:
            # 부가 정보 주입
            r["center_name"] = center_name

            # 필터 1: 인실/정원 필터
            if capacities and r["capacity"] not in capacities:
                continue

            # 필터 2: 반려동물 전용 필터
            if pet_only and not r["pet_allowed"]:
                continue

            slot_id = r["slot_id"]
            all_rooms_map[slot_id] = r
            rooms_by_date[d][r["prd_id"]] = r

            if r["is_available"]:
                available_rooms_map[slot_id] = r

    # 주말 2박(금,토) 연박 감지
    consecutive_pairs: List[Dict[str, Any]] = []
    for d_str, day_rooms in rooms_by_date.items():
        try:
            dt = datetime.strptime(d_str, "%Y-%m-%d")
        except ValueError:
            continue

        # 금요일인 경우 다음 날(토요일) 데이터 확인
        if dt.weekday() == 4:  # 금요일
            sat_str = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
            sat_rooms = rooms_by_date.get(sat_str, {})

            for prd_id, fri_room in day_rooms.items():
                if not fri_room["is_available"]:
                    continue

                sat_room = sat_rooms.get(prd_id)
                if sat_room and sat_room["is_available"]:
                    pair_id = f"eco_{dept_id}_{d_str}_{sat_str}_{prd_id}"
                    price_total = fri_room["price"] + sat_room["price"]
                    consecutive_pairs.append({
                        "pair_id": pair_id,
                        "dept_id": dept_id,
                        "center_name": center_name,
                        "prd_id": prd_id,
                        "room_name": fri_room["prd_name"],
                        "category": fri_room["category"],
                        "capacity": fri_room["capacity"],
                        "fri_date": d_str,
                        "sat_date": sat_str,
                        "fri_price": fri_room["price"],
                        "sat_price": sat_room["price"],
                        "price_total": price_total,
                        "pet_allowed": fri_room["pet_allowed"],
                        "barrier_free": fri_room["barrier_free"],
                        "case_badge": "🔵 [금:예약 + 토:예약 (즉시2박)]",
                    })

    return {
        "dept_id": dept_id,
        "center_name": center_name,
        "all_rooms": all_rooms_map,
        "available_rooms": available_rooms_map,
        "consecutive_pairs": consecutive_pairs,
    }
