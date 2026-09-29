import 'package:flutter/material.dart';
import '../models/campsite_config.dart';
import '../models/eco_config.dart';
import '../services/github_service.dart';

class SettingsTab extends StatefulWidget {
  final VoidCallback onSettingsSaved;
  final CampsiteUser? activeUser;
  final EcoUser? activeEcoUser;
  final VoidCallback? onUserConfigChanged;

  const SettingsTab({
    super.key,
    required this.onSettingsSaved,
    this.activeUser,
    this.activeEcoUser,
    this.onUserConfigChanged,
  });

  @override
  State<SettingsTab> createState() => _SettingsTabState();
}

class _SettingsTabState extends State<SettingsTab> {
  final _service = GitHubService();
  final _tokenController = TextEditingController();
  final _ownerController = TextEditingController();
  final _repoController = TextEditingController();
  final _branchController = TextEditingController();
  final _webhookController = TextEditingController();

  bool _obscureToken = true;
  bool _isTesting = false;
  String? _testResult;
  bool _testSuccess = false;

  @override
  void initState() {
    super.initState();
    _loadValues();
  }

  @override
  void didUpdateWidget(SettingsTab oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.activeUser != oldWidget.activeUser) {
      _webhookController.text = widget.activeUser?.notification.discordWebhookUrl ?? '';
    }
  }

  void _loadValues() {
    _tokenController.text = _service.token;
    _ownerController.text = _service.owner;
    _repoController.text = _service.repo;
    _branchController.text = _service.branch;
    _webhookController.text = widget.activeUser?.notification.discordWebhookUrl ?? '';
  }

  Future<void> _save() async {
    await _service.saveSettings(
      owner: _ownerController.text.trim(),
      repo: _repoController.text.trim(),
      branch: _branchController.text.trim(),
      token: _tokenController.text.trim(),
    );

    widget.onSettingsSaved();

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('설정이 안전하게 저장되었습니다 ✅'),
        backgroundColor: Color(0xFF0F766E),
      ),
    );
  }

  Future<void> _testConnection() async {
    setState(() {
      _isTesting = true;
      _testResult = null;
    });

    await _service.saveSettings(
      owner: _ownerController.text.trim(),
      repo: _repoController.text.trim(),
      branch: _branchController.text.trim(),
      token: _tokenController.text.trim(),
    );

    final res = await _service.testConnection();

    if (!mounted) return;
    setState(() {
      _isTesting = false;
      _testSuccess = res.success;
      _testResult = res.message;
    });
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 👤 현재 이용자 개인 알림 설정 카드
          if (widget.activeUser != null) ...[
            Text(
              '👤 현재 이용자 (${widget.activeUser!.name}) 알림 채널',
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            const Text(
              '각 이용자마다 원하는 디스코드 웹훅 주소를 개별 등록하여 나만의 알림을 받을 수 있습니다.',
              style: TextStyle(fontSize: 12.5, color: Colors.black54),
            ),
            const SizedBox(height: 12),

            Card(
              elevation: 1.5,
              shadowColor: Colors.black12,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            CircleAvatar(
                              radius: 14,
                              backgroundColor: const Color(0xFF0F766E),
                              foregroundColor: Colors.white,
                              child: Text(
                                widget.activeUser!.name.isNotEmpty ? widget.activeUser!.name[0] : 'U',
                                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              widget.activeUser!.name,
                              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                        Row(
                          children: [
                            Text(
                              widget.activeUser!.enabled ? '알림 ON' : '알림 OFF',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: widget.activeUser!.enabled ? const Color(0xFF0F766E) : Colors.grey,
                              ),
                            ),
                            const SizedBox(width: 4),
                            Switch(
                              value: widget.activeUser!.enabled,
                              activeColor: const Color(0xFF0F766E),
                              onChanged: (val) {
                                setState(() {
                                  widget.activeUser!.enabled = val;
                                  if (widget.activeEcoUser != null) {
                                    widget.activeEcoUser!.enabled = val;
                                  }
                                });
                                widget.onUserConfigChanged?.call();
                              },
                            ),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _webhookController,
                      decoration: InputDecoration(
                        labelText: '개인 Discord 웹훅 URL (선택)',
                        hintText: 'https://discord.com/api/webhooks/...',
                        helperText: '비워두면 GitHub 기본 웹훅(User 1)으로 전송되거나 대기합니다.',
                        prefixIcon: const Icon(Icons.webhook, color: Color(0xFF5865F2)),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                      onChanged: (val) {
                        widget.activeUser!.notification.discordWebhookUrl = val.trim();
                        if (widget.activeEcoUser != null) {
                          widget.activeEcoUser!.notification.discordWebhookUrl = val.trim();
                        }
                        widget.onUserConfigChanged?.call();
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
          ],

          // 🔑 GitHub 저장소 연동 설정 카드
          const Text(
            '🔑 GitHub 저장소 연동 설정',
            style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          const Text(
            '모바일에서 설정을 변경하면 GitHub Actions가 즉시 새 설정을 감지하여 동작합니다.',
            style: TextStyle(fontSize: 12.5, color: Colors.black54),
          ),
          const SizedBox(height: 12),

          Card(
            elevation: 1.5,
            shadowColor: Colors.black12,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextField(
                    controller: _tokenController,
                    obscureText: _obscureToken,
                    decoration: InputDecoration(
                      labelText: 'Personal Access Token (PAT)',
                      hintText: 'github_pat_... 또는 ghp_...',
                      prefixIcon: const Icon(Icons.key, color: Color(0xFF0F766E)),
                      suffixIcon: IconButton(
                        icon: Icon(_obscureToken ? Icons.visibility_off : Icons.visibility),
                        onPressed: () => setState(() => _obscureToken = !_obscureToken),
                      ),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _ownerController,
                          decoration: InputDecoration(
                            labelText: 'GitHub 아이디 (Owner)',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: TextField(
                          controller: _branchController,
                          decoration: InputDecoration(
                            labelText: '브랜치',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: _repoController,
                    decoration: InputDecoration(
                      labelText: '저장소 이름 (Repo)',
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                  const SizedBox(height: 16),

                  if (_testResult != null)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(
                        color: _testSuccess ? const Color(0xFFECFDF5) : const Color(0xFFFEF2F2),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: _testSuccess ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                        ),
                      ),
                      child: Text(
                        _testResult!,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: _testSuccess ? const Color(0xFF065F46) : const Color(0xFF991B1B),
                        ),
                      ),
                    ),

                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          icon: _isTesting
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.wifi_protected_setup),
                          label: const Text('연결 테스트'),
                          onPressed: _isTesting ? null : _testConnection,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF0F766E),
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          icon: const Icon(Icons.save),
                          label: const Text('설정 저장'),
                          onPressed: _save,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 20),

          // 토큰 발급 가이드 카드
          Card(
            elevation: 0,
            color: const Color(0xFFF8FAFC),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
              side: BorderSide(color: Colors.grey.shade300),
            ),
            child: const Padding(
              padding: EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.security, color: Color(0xFF0369A1), size: 20),
                      SizedBox(width: 8),
                      Text(
                        '1분 만에 GitHub 토큰(PAT) 발급받기',
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF0369A1),
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 10),
                  Text(
                    '🛡️ [보안 추천] Fine-grained 토큰 (이 저장소 1개만 접근):\n'
                    '1. GitHub 로그인 ➔ 우측 상단 프로필 ➔ Settings\n'
                    '2. 좌측 최하단 Developer settings ➔ Personal access tokens ➔ Fine-grained tokens\n'
                    '3. Generate new token 클릭\n'
                    '4. Repository access: [Only select repositories] ➔ [knps-camp-notifier] 선택\n'
                    '5. Permissions: [Repository permissions] ➔ [Contents]를 [Read and write]로 설정\n'
                    '6. 발급된 github_pat_... 토큰을 복사하여 위 입력창에 붙여넣기\n\n'
                    '⚙️ [간편 방식] Classic 토큰:\n'
                    'Tokens (classic) ➔ [repo] 체크 후 ghp_... 토큰 발급',
                    style: TextStyle(fontSize: 12, height: 1.55, color: Colors.black87),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 30),
        ],
      ),
    );
  }
}
