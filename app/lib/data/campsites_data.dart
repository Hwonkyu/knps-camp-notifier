/// 전국 48개 국립공원 야영장 메타데이터 목록
class CampsiteMeta {
  final String parkName;
  final String campName;
  final String deptId;
  final List<String> availableTypes;

  const CampsiteMeta({
    required this.parkName,
    required this.campName,
    required this.deptId,
    this.availableTypes = const ["일반", "자동차야영장", "특화야영장", "카라반"],
  });

  String get displayName => "$parkName - $campName";
}

const List<CampsiteMeta> allCampsites = [
  CampsiteMeta(parkName: "가야산", campName: "백운동", deptId: "B131002"),
  CampsiteMeta(parkName: "가야산", campName: "삼정", deptId: "B131001"),
  CampsiteMeta(parkName: "가야산", campName: "치인", deptId: "B131003"),
  CampsiteMeta(parkName: "계룡산", campName: "갑사", deptId: "B161004"),
  CampsiteMeta(parkName: "계룡산", campName: "동학사", deptId: "B161001"),
  CampsiteMeta(parkName: "내장산", campName: "가인", deptId: "B041001"),
  CampsiteMeta(parkName: "내장산", campName: "내장", deptId: "B042001"),
  CampsiteMeta(parkName: "내장산", campName: "내장호", deptId: "B042004"),
  CampsiteMeta(parkName: "다도해해상", campName: "구계등", deptId: "B091004"),
  CampsiteMeta(parkName: "다도해해상", campName: "시목", deptId: "B092003"),
  CampsiteMeta(parkName: "다도해해상", campName: "염포", deptId: "B091003"),
  CampsiteMeta(parkName: "다도해해상", campName: "팔영산", deptId: "B091001"),
  CampsiteMeta(parkName: "덕유산", campName: "덕유대1", deptId: "B051002"),
  CampsiteMeta(parkName: "덕유산", campName: "덕유대2", deptId: "B051007"),
  CampsiteMeta(parkName: "덕유산", campName: "덕유대3", deptId: "B051006"),
  CampsiteMeta(parkName: "무등산", campName: "도원", deptId: "B172002"),
  CampsiteMeta(parkName: "변산반도", campName: "고사포1", deptId: "B181002"),
  CampsiteMeta(parkName: "변산반도", campName: "고사포2", deptId: "B181004"),
  CampsiteMeta(parkName: "변산반도", campName: "직소천", deptId: "B181005"),
  CampsiteMeta(parkName: "북한산", campName: "사기막", deptId: "B141003"),
  CampsiteMeta(parkName: "설악산", campName: "설악동", deptId: "B031005"),
  CampsiteMeta(parkName: "소백산", campName: "남천", deptId: "B122001"),
  CampsiteMeta(parkName: "소백산", campName: "삼가", deptId: "B121001"),
  CampsiteMeta(parkName: "오대산", campName: "소금강산", deptId: "B061001"),
  CampsiteMeta(parkName: "월악산", campName: "닷돈재1", deptId: "B111003"),
  CampsiteMeta(parkName: "월악산", campName: "닷돈재2", deptId: "B111001"),
  CampsiteMeta(parkName: "월악산", campName: "덕주", deptId: "B111007"),
  CampsiteMeta(parkName: "월악산", campName: "송계", deptId: "B111002"),
  CampsiteMeta(parkName: "월악산", campName: "용하", deptId: "B111004"),
  CampsiteMeta(parkName: "월악산", campName: "하선암", deptId: "B111008"),
  CampsiteMeta(parkName: "월출산", campName: "천황", deptId: "B201001"),
  CampsiteMeta(parkName: "주왕산", campName: "상의", deptId: "B071001"),
  CampsiteMeta(parkName: "지리산", campName: "내원", deptId: "B011005"),
  CampsiteMeta(parkName: "지리산", campName: "달궁1", deptId: "B012005"),
  CampsiteMeta(parkName: "지리산", campName: "달궁2", deptId: "B012002"),
  CampsiteMeta(parkName: "지리산", campName: "덕동", deptId: "B012003"),
  CampsiteMeta(parkName: "지리산", campName: "백무동", deptId: "B011007"),
  CampsiteMeta(parkName: "지리산", campName: "소막골", deptId: "B011006"),
  CampsiteMeta(parkName: "지리산", campName: "학천", deptId: "B012010"),
  CampsiteMeta(parkName: "치악산", campName: "구룡", deptId: "B101001"),
  CampsiteMeta(parkName: "치악산", campName: "금대", deptId: "B101002"),
  CampsiteMeta(parkName: "태백산", campName: "소도", deptId: "B221004"),
  CampsiteMeta(parkName: "태안해안", campName: "몽산포", deptId: "B081002"),
  CampsiteMeta(parkName: "태안해안", campName: "학암포", deptId: "B081001"),
  CampsiteMeta(parkName: "팔공산", campName: "갓바위", deptId: "B252001"),
  CampsiteMeta(parkName: "팔공산", campName: "도학", deptId: "B251001"),
  CampsiteMeta(parkName: "한려해상", campName: "덕신", deptId: "B022003"),
  CampsiteMeta(parkName: "한려해상", campName: "학동", deptId: "B021001"),
];
