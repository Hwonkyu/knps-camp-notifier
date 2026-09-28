import 'package:flutter/material.dart';
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

  bool _isLoading = true;
  bool _isSaving = false;
  bool _hasUnsavedChanges = false;

  @override
  void initState() {
    super.initState();
    _fetchConfigsFromGitHub();
  }

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
    } catch (_) {}

    setState(() {
      _isLoading = false;
      _hasUnsavedChanges = false;
    });
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Text('🏕️ ', style: TextStyle(fontSize: 20)),
            Text(
              '국립공원 알림 설정',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
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
                  config: _campsiteConfig,
                  onConfigChanged: () => setState(() => _hasUnsavedChanges = true),
                ),
                EcoTab(
                  config: _ecoConfig,
                  onConfigChanged: () => setState(() => _hasUnsavedChanges = true),
                ),
                SettingsTab(
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
