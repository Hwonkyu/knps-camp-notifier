"""
국립공원 전국 10개 생태탐방원 메타데이터 및 유틸리티 모듈
"""

from typing import List, Dict, Any, Optional

# 전국 국립공원 10개 생태탐방원 전체 목록
ECO_CENTERS: List[Dict[str, Any]] = [
    {
        "name": "북한산",
        "center_name": "북한산 생태탐방원",
        "dept_id": "B971002",
        "region": "수도권",
        "location": "서울 도봉구",
        "desc": "도봉산 자락 위치, 북한산 국립공원 자연 체험",
    },
    {
        "name": "설악산",
        "center_name": "설악산 생태탐방원",
        "dept_id": "B301002",
        "region": "강원권",
        "location": "강원 인제군",
        "desc": "설악산 국립공원 인근 자연 체험 및 생태 교육",
    },
    {
        "name": "지리산",
        "center_name": "지리산 생태탐방원",
        "dept_id": "B014003",
        "region": "전남권",
        "location": "전남 구례군",
        "desc": "노고단/화엄사 인근, 섬진강 조망",
    },
    {
        "name": "소백산",
        "center_name": "소백산 생태탐방원",
        "dept_id": "B123002",
        "region": "경북권",
        "location": "경북 영주시",
        "desc": "소백산 자락 풍기 온천 및 생태 탐방",
    },
    {
        "name": "계룡산",
        "center_name": "계룡산 생태탐방원",
        "dept_id": "B163001",
        "region": "충남권",
        "location": "충남 공주시",
        "desc": "동학사/갑사 인근 생태 체험",
    },
    {
        "name": "한려해상",
        "center_name": "한려해상 생태탐방원",
        "dept_id": "B024002",
        "region": "경남권",
        "location": "경남 통영시",
        "desc": "통영 바다 전망 객실 및 해양 생태 체험",
    },
    {
        "name": "무등산",
        "center_name": "무등산 생태탐방원",
        "dept_id": "B231002",
        "region": "광주권",
        "location": "광주 북구",
        "desc": "무등산 원효계곡 인근 생태 탐방",
    },
    {
        "name": "가야산",
        "center_name": "가야산 생태탐방원",
        "dept_id": "B133002",
        "region": "경북권",
        "location": "경북 성주군",
        "desc": "가야산 홍류동 계곡 및 해인사 인근",
    },
    {
        "name": "내장산",
        "center_name": "내장산 생태탐방원",
        "dept_id": "B331001",
        "region": "전북권",
        "location": "전북 정읍시",
        "desc": "내장산 단풍 생태 및 자연 교육",
    },
    {
        "name": "변산반도",
        "center_name": "변산반도 생태탐방원",
        "dept_id": "B183001",
        "region": "전북권",
        "location": "전북 부안군",
        "desc": "서해 바다 및 변산반도 해안 생태 탐방",
    },
]

# 빠른 검색을 위한 매핑 딕셔너리
_BY_DEPT_ID: Dict[str, Dict[str, Any]] = {c["dept_id"]: c for c in ECO_CENTERS}
_BY_NAME: Dict[str, Dict[str, Any]] = {c["name"]: c for c in ECO_CENTERS}


def get_all_centers() -> List[Dict[str, Any]]:
    """전체 생태탐방원 목록 반환"""
    return ECO_CENTERS


def find_eco_center(query: str) -> Optional[Dict[str, Any]]:
    """
    이름, 센터명, 또는 dept_id로 생태탐방원을 검색합니다.
    """
    if not query:
        return None
    q = query.strip()
    if q in _BY_DEPT_ID:
        return _BY_DEPT_ID[q]
    if q in _BY_NAME:
        return _BY_NAME[q]

    for c in ECO_CENTERS:
        if q in c["center_name"] or q in c["name"] or q == c["dept_id"]:
            return c
    return None
