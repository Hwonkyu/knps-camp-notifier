"""
국립공원공단(KNPS) 전체 야영장 메타데이터 목록 및 검색 헬퍼 모듈
"""

CAMPSITES = [
    {"park_name": "가야산", "camp_name": "백운동", "dept_id": "B131002"},
    {"park_name": "가야산", "camp_name": "삼정", "dept_id": "B131001"},
    {"park_name": "가야산", "camp_name": "치인", "dept_id": "B131003"},
    {"park_name": "계룡산", "camp_name": "갑사", "dept_id": "B161004"},
    {"park_name": "계룡산", "camp_name": "동학사", "dept_id": "B161001"},
    {"park_name": "내장산", "camp_name": "가인", "dept_id": "B041001"},
    {"park_name": "내장산", "camp_name": "내장", "dept_id": "B042001"},
    {"park_name": "내장산", "camp_name": "내장호", "dept_id": "B042004"},
    {"park_name": "다도해해상", "camp_name": "구계등", "dept_id": "B091004"},
    {"park_name": "다도해해상", "camp_name": "시목", "dept_id": "B092003"},
    {"park_name": "다도해해상", "camp_name": "염포", "dept_id": "B091003"},
    {"park_name": "다도해해상", "camp_name": "팔영산", "dept_id": "B091001"},
    {"park_name": "덕유산", "camp_name": "덕유대1", "dept_id": "B051002"},
    {"park_name": "덕유산", "camp_name": "덕유대2", "dept_id": "B051007"},
    {"park_name": "덕유산", "camp_name": "덕유대3", "dept_id": "B051006"},
    {"park_name": "무등산", "camp_name": "도원", "dept_id": "B172002"},
    {"park_name": "변산반도", "camp_name": "고사포1", "dept_id": "B181002"},
    {"park_name": "변산반도", "camp_name": "고사포2", "dept_id": "B181004"},
    {"park_name": "변산반도", "camp_name": "직소천", "dept_id": "B181005"},
    {"park_name": "북한산", "camp_name": "사기막", "dept_id": "B141003"},
    {"park_name": "설악산", "camp_name": "설악동", "dept_id": "B031005"},
    {"park_name": "소백산", "camp_name": "남천", "dept_id": "B122001"},
    {"park_name": "소백산", "camp_name": "삼가", "dept_id": "B121001"},
    {"park_name": "오대산", "camp_name": "소금강산", "dept_id": "B061001"},
    {"park_name": "월악산", "camp_name": "닷돈재1", "dept_id": "B111003"},
    {"park_name": "월악산", "camp_name": "닷돈재2", "dept_id": "B111001"},
    {"park_name": "월악산", "camp_name": "덕주", "dept_id": "B111007"},
    {"park_name": "월악산", "camp_name": "송계", "dept_id": "B111002"},
    {"park_name": "월악산", "camp_name": "용하", "dept_id": "B111004"},
    {"park_name": "월악산", "camp_name": "하선암", "dept_id": "B111008"},
    {"park_name": "월출산", "camp_name": "천황", "dept_id": "B201001"},
    {"park_name": "주왕산", "camp_name": "상의", "dept_id": "B071001"},
    {"park_name": "지리산", "camp_name": "내원", "dept_id": "B011005"},
    {"park_name": "지리산", "camp_name": "달궁1", "dept_id": "B012005"},
    {"park_name": "지리산", "camp_name": "달궁2", "dept_id": "B012002"},
    {"park_name": "지리산", "camp_name": "덕동", "dept_id": "B012003"},
    {"park_name": "지리산", "camp_name": "백무동", "dept_id": "B011007"},
    {"park_name": "지리산", "camp_name": "소막골", "dept_id": "B011006"},
    {"park_name": "지리산", "camp_name": "학천", "dept_id": "B012010"},
    {"park_name": "치악산", "camp_name": "구룡", "dept_id": "B101001"},
    {"park_name": "치악산", "camp_name": "금대", "dept_id": "B101002"},
    {"park_name": "태백산", "camp_name": "소도", "dept_id": "B221004"},
    {"park_name": "태안해안", "camp_name": "몽산포", "dept_id": "B081002"},
    {"park_name": "태안해안", "camp_name": "학암포", "dept_id": "B081001"},
    {"park_name": "팔공산", "camp_name": "갓바위", "dept_id": "B252001"},
    {"park_name": "팔공산", "camp_name": "도학", "dept_id": "B251001"},
    {"park_name": "한려해상", "camp_name": "덕신", "dept_id": "B022003"},
    {"park_name": "한려해상", "camp_name": "학동", "dept_id": "B021001"},
]

def find_campsite(query: str):
    """
    공원명, 야영장명, 또는 야영장 코드(dept_id)로 야영장을 검색합니다.
    일치하거나 포함되는 첫 번째 야영장을 반환합니다.
    """
    query_clean = query.strip()
    if not query_clean:
        return None

    # 1. dept_id 정확 매칭
    for c in CAMPSITES:
        if c["dept_id"].lower() == query_clean.lower():
            return c

    # 2. 야영장명 정확 매칭
    for c in CAMPSITES:
        if c["camp_name"] == query_clean:
            return c

    # 3. '공원명 야영장명' 복합 매칭 (예: '치악산 구룡')
    for c in CAMPSITES:
        full_name = f"{c['park_name']} {c['camp_name']}"
        if query_clean == full_name or query_clean == f"{c['park_name']}-{c['camp_name']}":
            return c

    # 4. 부분 포함 매칭
    for c in CAMPSITES:
        if query_clean in c["camp_name"] or query_clean in f"{c['park_name']} {c['camp_name']}":
            return c

    return None

def resolve_campsite(park_name: str = "", camp_name: str = "", dept_id: str = ""):
    """
    설정에 주어진 정보(dept_id, park_name, camp_name)를 바탕으로 야영장 정보를 정규화합니다.
    """
    if dept_id:
        c = find_campsite(dept_id)
        if c:
            return c

    if camp_name:
        for c in CAMPSITES:
            if c["camp_name"] == camp_name:
                if not park_name or c["park_name"] == park_name:
                    return c
        c = find_campsite(camp_name)
        if c:
            return c

    if park_name:
        c = find_campsite(park_name)
        if c:
            return c

    return None
