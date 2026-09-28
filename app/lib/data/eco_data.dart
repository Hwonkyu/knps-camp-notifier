/// 전국 10개 국립공원 생태탐방원 메타데이터
class EcoCenterMeta {
  final String name;
  final String centerName;
  final String deptId;
  final String region;
  final String location;

  const EcoCenterMeta({
    required this.name,
    required this.centerName,
    required this.deptId,
    required this.region,
    required this.location,
  });
}

const List<EcoCenterMeta> allEcoCenters = [
  EcoCenterMeta(
    name: "북한산",
    centerName: "북한산 생태탐방원",
    deptId: "B971002",
    region: "수도권",
    location: "서울 도봉구",
  ),
  EcoCenterMeta(
    name: "설악산",
    centerName: "설악산 생태탐방원",
    deptId: "B301002",
    region: "강원권",
    location: "강원 인제군",
  ),
  EcoCenterMeta(
    name: "지리산",
    centerName: "지리산 생태탐방원",
    deptId: "B014003",
    region: "전남권",
    location: "전남 구례군",
  ),
  EcoCenterMeta(
    name: "소백산",
    centerName: "소백산 생태탐방원",
    deptId: "B123002",
    region: "경북권",
    location: "경북 영주시",
  ),
  EcoCenterMeta(
    name: "계룡산",
    centerName: "계룡산 생태탐방원",
    deptId: "B163001",
    region: "충남권",
    location: "충남 공주시",
  ),
  EcoCenterMeta(
    name: "한려해상",
    centerName: "한려해상 생태탐방원",
    deptId: "B024002",
    region: "경남권",
    location: "경남 통영시",
  ),
  EcoCenterMeta(
    name: "내장산",
    centerName: "내장산 생태탐방원",
    deptId: "B331001",
    region: "전북권",
    location: "전북 정읍시",
  ),
  EcoCenterMeta(
    name: "가야산",
    centerName: "가야산 생태탐방원",
    deptId: "B133002",
    region: "경북권",
    location: "경북 성주군",
  ),
  EcoCenterMeta(
    name: "변산반도",
    centerName: "변산반도 생태탐방원",
    deptId: "B183001",
    region: "전북권",
    location: "전북 부안군",
  ),
  EcoCenterMeta(
    name: "무등산",
    centerName: "무등산 생태탐방원",
    deptId: "B231002",
    region: "전남/광주",
    location: "광주 북구",
  ),
];
