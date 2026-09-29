import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'models/campsite_config.dart';
import 'models/eco_config.dart';
import 'screens/campsite_tab.dart';
import 'screens/eco_tab.dart';
import 'screens/settings_tab.dart';
import 'screens/splash_screen.dart';
import 'services/github_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await GitHubService().loadSettings();
  runApp(const KnpsApp());
}

class KnpsApp extends StatelessWidget {
  const KnpsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '국립공원 알림 설정',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0F766E),
          primary: const Color(0xFF0F766E),
          surface: Colors.white,
          surfaceContainerLowest: const Color(0xFFF8FAFC),
        ),
        scaffoldBackgroundColor: const Color(0xFFF8FAFC),
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.white,
          foregroundColor: Colors.black87,
          elevation: 0.5,
          centerTitle: false,
        ),
      ),
      home: const SplashScreen(),
    );
  }
}

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _currentIndex = 0;
  final _github = GitHubService();

  CampsiteConfig _campsiteConfig = CampsiteConfig();
  String _campsiteSha = '';

  EcoConfig _ecoConfig = EcoConfig();
  String _ecoSha = '';

  String _selectedUserId = 'user1';

  bool _isLoading = true;
  bool _isSaving = false;
  bool _hasUnsavedChanges = false;

  @override
  void initState() {
    super.initState();
    _loadSelectedUser();
    _fetchConfigsFromGitHub();
  }

  Future<void> _loadSelectedUser() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _selectedUserId = prefs.getString('active_user_id') ?? 'user1';
    });
  }

  Future<void> _selectUser(String userId) async {
    setState(() => _selectedUserId = userId);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('active_user_id', userId);
  }

  CampsiteUser get _activeCampsiteUser => _campsiteConfig.getUser(_selectedUserId);
  EcoUser get _activeEcoUser => _ecoConfig.getUser(_selectedUserId);

  Future<void> _fetchConfigsFromGitHub() async {
    setState(() => _isLoading = true);

    if (_github.token.isEmpty) {
      setState(() {
        _isLoading = false;
        _currentIndex = 2; // 설정 탭으로 자동 이동하여 토큰 입력을 유도
      });
      return;
    }

    try {
      // 1. 야영장 설정 로드
      final campData = await _github.fetchFile('campsite/config.yaml');
      if (campData != null) {
        _campsiteConfig = CampsiteConfig.parse(campData['content']);
        _campsiteSha = campData['sha'];
      }

      // 2. 생태탐방원 설정 로드
      final ecoData = await _github.fetchFile('eco/config.yaml');
      if (ecoData != null) {
        _ecoConfig = EcoConfig.parse(ecoData['content']);
        _ecoSha = ecoData['sha'];
      }

      // 사용자 목록 동기화 확인
      _syncUserLists();
    } catch (_) {}

    setState(() {
      _isLoading = false;
      _hasUnsavedChanges = false;
    });
  }

  void _syncUserLists() {
    // campsite와 eco 양쪽에 동일한 유저 목록이 유지되도록 동기화
    final campUserIds = _campsiteConfig.users.map((u) => u.id).toSet();
    final ecoUserIds = _ecoConfig.users.map((u) => u.id).toSet();

    for (final cu in _campsiteConfig.users) {
      if (!ecoUserIds.contains(cu.id)) {
        _ecoConfig.users.add(EcoUser(id: cu.id, name: cu.name, enabled: cu.enabled));
      }
    }

    for (final eu in _ecoConfig.users) {
      if (!campUserIds.contains(eu.id)) {
        _campsiteConfig.users.add(CampsiteUser(id: eu.id, name: eu.name, enabled: eu.enabled));
      }
    }

    // 선택된 유저가 목록에 없으면 첫 번째 유저로 변경
    if (!_campsiteConfig.users.any((u) => u.id == _selectedUserId)) {
      _selectedUserId = _campsiteConfig.users.first.id;
    }
  }

  Future<void> _saveAllToGitHub() async {
    if (_github.token.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('하단 [설정] 탭에서 GitHub Token(PAT)을 먼저 등록해 주세요.'),
          backgroundColor: Colors.orange,
        ),
      );
      setState(() => _currentIndex = 2);
      return;
    }

    setState(() => _isSaving = true);

    bool campOk = true;
    bool ecoOk = true;

    // 1. 야영장 저장
    final newCampYaml = _campsiteConfig.toYaml();
    final resCamp = await _github.updateFile(
      path: 'campsite/config.yaml',
      newContent: newCampYaml,
      sha: _campsiteSha,
      commitMessage: 'chore(campsite): 모바일 앱에서 야영장 모니터링 설정 업데이트 [자동]',
    );
    campOk = resCamp;

    // 2. 생태탐방원 저장
    final newEcoYaml = _ecoConfig.toYaml();
    final resEco = await _github.updateFile(
      path: 'eco/config.yaml',
      newContent: newEcoYaml,
      sha: _ecoSha,
      commitMessage: 'chore(eco): 모바일 앱에서 생태탐방원 모니터링 설정 업데이트 [자동]',
    );
    ecoOk = resEco;

    // 저장 후 최신 SHA 갱신을 위해 재조회
    await _fetchConfigsFromGitHub();

    setState(() => _isSaving = false);

    if (!mounted) return;

    if (campOk && ecoOk) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('🎉 GitHub 저장소에 성공적으로 반영되었습니다!\n다음 5분 주기부터 바뀐 설정으로 작동합니다.'),
          backgroundColor: Color(0xFF0F766E),
          duration: Duration(seconds: 4),
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('저장 실패: ${!campOk ? '야영장 실패 ' : ''}${!ecoOk ? '생태탐방원 실패' : ''} (토큰 권한 확인 필요)'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _showUserSwitchDialog() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            return SafeArea(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.people_alt_outlined, color: Color(0xFF0F766E)),
                            SizedBox(width: 8),
                            Text(
                              '이용자 선택 및 관리',
                              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                        IconButton(
                          icon: const Icon(Icons.close),
                          onPressed: () => Navigator.pop(ctx),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      '각 이용자마다 원하는 야영장과 디스코드 알림을 독립적으로 설정할 수 있습니다.',
                      style: TextStyle(fontSize: 12.5, color: Colors.black54),
                    ),
                    const SizedBox(height: 16),
                    ..._campsiteConfig.users.map((u) {
                      final isSelected = u.id == _selectedUserId;
                      final ecoU = _ecoConfig.getUser(u.id);

                      return Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        decoration: BoxDecoration(
                          color: isSelected ? const Color(0xFFF0FDFA) : const Color(0xFFF8FAFC),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: isSelected ? const Color(0xFF0F766E) : Colors.grey.shade300,
                            width: isSelected ? 1.5 : 1,
                          ),
                        ),
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: isSelected ? const Color(0xFF0F766E) : Colors.grey.shade400,
                            foregroundColor: Colors.white,
                            child: Text(
                              u.name.isNotEmpty ? u.name[0] : 'U',
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                          ),
                          title: Row(
                            children: [
                              Text(
                                u.name,
                                style: TextStyle(
                                  fontWeight: isSelected ? FontWeight.bold : FontWeight.w600,
                                  color: isSelected ? const Color(0xFF0F766E) : Colors.black87,
                                ),
                              ),
                              const SizedBox(width: 8),
                              if (!u.enabled)
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: Colors.grey.shade200,
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: const Text('알림 OFF', style: TextStyle(fontSize: 10, color: Colors.grey)),
                                ),
                            ],
                          ),
                          subtitle: Text(
                            '야영장 ${u.campsites.length}곳 · 생태탐방원 ${ecoU.ecoCenters.length}곳',
                            style: const TextStyle(fontSize: 12),
                          ),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                icon: const Icon(Icons.edit, size: 18, color: Colors.black54),
                                tooltip: '이름 변경',
                                onPressed: () {
                                  _showEditUserNameDialog(u, () {
                                    setSheetState(() {});
                                    setState(() {});
                                  });
                                },
                              ),
                              if (isSelected)
                                const Icon(Icons.check_circle, color: Color(0xFF0F766E))
                              else
                                OutlinedButton(
                                  style: OutlinedButton.styleFrom(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    minimumSize: Size.zero,
                                  ),
                                  onPressed: () {
                                    _selectUser(u.id);
                                    Navigator.pop(ctx);
                                  },
                                  child: const Text('선택', style: TextStyle(fontSize: 12)),
                                ),
                            ],
                          ),
                          onTap: () {
                            _selectUser(u.id);
                            Navigator.pop(ctx);
                          },
                        ),
                      );
                    }),
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                      icon: const Icon(Icons.person_add_alt_1, color: Color(0xFF0F766E)),
                      label: const Text('+ 새 이용자 추가 (User 3...)', style: TextStyle(color: Color(0xFF0F766E))),
                      onPressed: () {
                        Navigator.pop(ctx);
                        _showAddUserDialog();
                      },
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  void _showAddUserDialog() {
    final nextNum = _campsiteConfig.users.length + 1;
    final nameController = TextEditingController(text: 'User $nextNum');

    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Text('새 이용자 추가', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          content: TextField(
            controller: nameController,
            autofocus: true,
            decoration: InputDecoration(
              labelText: '이용자 이름 (예: User 3, 친구이름)',
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('취소'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF0F766E),
                foregroundColor: Colors.white,
              ),
              onPressed: () {
                final newName = nameController.text.trim();
                if (newName.isNotEmpty) {
                  final nextNum = _campsiteConfig.users.length + 1;
                  final newId = 'user$nextNum';
                  setState(() {
                    _campsiteConfig.addUser(newName);
                    _ecoConfig.addUser(newName);
                    _selectedUserId = newId;
                    _hasUnsavedChanges = true;
                  });
                  _selectUser(newId);
                }
                Navigator.pop(ctx);
              },
              child: const Text('추가'),
            ),
          ],
        );
      },
    );
  }

  void _showEditUserNameDialog(CampsiteUser u, VoidCallback onUpdated) {
    final nameController = TextEditingController(text: u.name);

    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Text('이용자 이름 변경', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          content: TextField(
            controller: nameController,
            autofocus: true,
            decoration: InputDecoration(
              labelText: '이용자 이름',
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('취소'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF0F766E),
                foregroundColor: Colors.white,
              ),
              onPressed: () {
                final newName = nameController.text.trim();
                if (newName.isNotEmpty) {
                  setState(() {
                    u.name = newName;
                    _ecoConfig.getUser(u.id).name = newName;
                    _hasUnsavedChanges = true;
                  });
                  onUpdated();
                }
                Navigator.pop(ctx);
              },
              child: const Text('변경'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            // 이용자 전환 드롭다운 칩
            InkWell(
              onTap: _showUserSwitchDialog,
              borderRadius: BorderRadius.circular(20),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: const Color(0xFFCCFBF1),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: const Color(0xFF0F766E).withOpacity(0.3)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.person, size: 16, color: Color(0xFF0F766E)),
                    const SizedBox(width: 4),
                    Text(
                      _activeCampsiteUser.name,
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                        color: Color(0xFF0F766E),
                      ),
                    ),
                    const Icon(Icons.arrow_drop_down, size: 18, color: Color(0xFF0F766E)),
                  ],
                ),
              ),
            ),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF0F766E),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20),
                ),
                elevation: 0,
              ),
              icon: _isSaving
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.cloud_upload_outlined, size: 16),
              label: Text(
                _isSaving ? '반영 중...' : '저장 (GitHub 반영)',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
              ),
              onPressed: _isSaving ? null : _saveAllToGitHub,
            ),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(color: Color(0xFF0F766E)),
                  SizedBox(height: 16),
                  Text('GitHub에서 최신 설정을 불러오는 중...', style: TextStyle(color: Colors.black54)),
                ],
              ),
            )
          : IndexedStack(
              index: _currentIndex,
              children: [
                CampsiteTab(
                  key: ValueKey('camp_${_activeCampsiteUser.id}'),
                  user: _activeCampsiteUser,
                  onConfigChanged: () => setState(() => _hasUnsavedChanges = true),
                ),
                EcoTab(
                  key: ValueKey('eco_${_activeEcoUser.id}'),
                  user: _activeEcoUser,
                  onConfigChanged: () => setState(() => _hasUnsavedChanges = true),
                ),
                SettingsTab(
                  activeUser: _activeCampsiteUser,
                  activeEcoUser: _activeEcoUser,
                  onUserConfigChanged: () => setState(() => _hasUnsavedChanges = true),
                  onSettingsSaved: () {
                    _fetchConfigsFromGitHub();
                  },
                ),
              ],
            ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        indicatorColor: const Color(0xFFCCFBF1),
        onDestinationSelected: (idx) => setState(() => _currentIndex = idx),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.holiday_village_outlined),
            selectedIcon: Icon(Icons.holiday_village, color: Color(0xFF0F766E)),
            label: '야영장',
          ),
          NavigationDestination(
            icon: Icon(Icons.eco_outlined),
            selectedIcon: Icon(Icons.eco, color: Color(0xFF0F766E)),
            label: '생태탐방원',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings, color: Color(0xFF0F766E)),
            label: '설정 (GitHub PAT)',
          ),
        ],
      ),
    );
  }
}
