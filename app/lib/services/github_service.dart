import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class GitHubService {
  static const String keyOwner = 'github_owner';
  static const String keyRepo = 'github_repo';
  static const String keyBranch = 'github_branch';
  static const String keyToken = 'github_token';

  String owner = 'Hwonkyu';
  String repo = 'knps-camp-notifier';
  String branch = 'main';
  String token = '';

  static final GitHubService _instance = GitHubService._internal();
  factory GitHubService() => _instance;
  GitHubService._internal();

  Future<void> loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    owner = prefs.getString(keyOwner) ?? 'Hwonkyu';
    repo = prefs.getString(keyRepo) ?? 'knps-camp-notifier';
    branch = prefs.getString(keyBranch) ?? 'main';
    token = prefs.getString(keyToken) ?? '';
  }

  Future<void> saveSettings({
    required String owner,
    required String repo,
    required String branch,
    required String token,
  }) async {
    this.owner = owner.trim();
    this.repo = repo.trim();
    this.branch = branch.trim();
    this.token = token.trim();

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(keyOwner, this.owner);
    await prefs.setString(keyRepo, this.repo);
    await prefs.setString(keyBranch, this.branch);
    await prefs.setString(keyToken, this.token);
  }

  Map<String, String> get _headers => {
        'Accept': 'application/vnd.github.v3+json',
        if (token.trim().isNotEmpty) 'Authorization': 'Bearer ${token.trim()}',
        'User-Agent': 'KNPS-Mobile-App/1.0',
      };

  /// 연결 테스트 (저장소 접근 권한 확인 및 구체적 원인 반환)
  Future<ConnectionResult> testConnection() async {
    try {
      final cleanToken = token.trim();
      final cleanOwner = owner.trim();
      final cleanRepo = repo.trim();

      if (cleanToken.isEmpty) {
        return ConnectionResult(
          success: false,
          message: '토큰(PAT)을 입력해주세요.',
        );
      }
      if (cleanOwner.isEmpty || cleanRepo.isEmpty) {
        return ConnectionResult(
          success: false,
          message: 'GitHub 아이디(Owner)와 저장소(Repo)를 입력해주세요.',
        );
      }

      final url = Uri.parse('https://api.github.com/repos/$cleanOwner/$cleanRepo');
      final resp = await http.get(url, headers: {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': 'Bearer $cleanToken',
        'User-Agent': 'KNPS-Mobile-App/1.0',
      }).timeout(const Duration(seconds: 10));

      if (resp.statusCode == 200) {
        final scopes = resp.headers['x-oauth-scopes'] ?? 'repo';
        return ConnectionResult(
          success: true,
          message: 'GitHub 저장소 연결 성공! (권한: $scopes) ✅',
        );
      } else if (resp.statusCode == 401) {
        return ConnectionResult(
          success: false,
          message: '인증 실패 (401): 토큰이 만료되었거나 복사가 잘못되었습니다.',
        );
      } else if (resp.statusCode == 404) {
        return ConnectionResult(
          success: false,
          message: '저장소를 찾을 수 없음 (404): 아이디($cleanOwner) 또는 저장소($cleanRepo) 확인',
        );
      } else if (resp.statusCode == 403) {
        return ConnectionResult(
          success: false,
          message: '권한 부족 (403): 토큰에 repo 권한이 부여되지 않았습니다.',
        );
      } else {
        return ConnectionResult(
          success: false,
          message: '연결 실패: HTTP 상태 코드 ${resp.statusCode}',
        );
      }
    } catch (e) {
      return ConnectionResult(
        success: false,
        message: '통신 오류 ($e)',
      );
    }
  }

  /// 파일 내용 및 SHA 조회
  Future<Map<String, dynamic>?> fetchFile(String path) async {
    try {
      final cleanOwner = owner.trim();
      final cleanRepo = repo.trim();
      final cleanBranch = branch.trim();
      final url = Uri.parse('https://api.github.com/repos/$cleanOwner/$cleanRepo/contents/$path?ref=$cleanBranch');
      final resp = await http.get(url, headers: _headers).timeout(const Duration(seconds: 10));

      if (resp.statusCode == 200) {
        final data = json.decode(resp.body);
        final String rawBase64 = (data['content'] as String).replaceAll('\n', '').replaceAll('\r', '');
        final String decodedContent = utf8.decode(base64.decode(rawBase64));
        final String sha = data['sha'] ?? '';
        return {
          'content': decodedContent,
          'sha': sha,
        };
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  /// 파일 커밋 & 푸시
  Future<bool> updateFile({
    required String path,
    required String newContent,
    required String sha,
    required String commitMessage,
  }) async {
    try {
      final cleanOwner = owner.trim();
      final cleanRepo = repo.trim();
      final cleanBranch = branch.trim();
      final url = Uri.parse('https://api.github.com/repos/$cleanOwner/$cleanRepo/contents/$path');
      final base64Content = base64.encode(utf8.encode(newContent));

      final Map<String, dynamic> bodyMap = {
        'message': commitMessage,
        'content': base64Content,
        'branch': cleanBranch,
      };
      if (sha.isNotEmpty) {
        bodyMap['sha'] = sha;
      }

      final body = json.encode(bodyMap);
      final resp = await http.put(url, headers: _headers, body: body).timeout(const Duration(seconds: 15));
      return resp.statusCode == 200 || resp.statusCode == 201;
    } catch (_) {
      return false;
    }
  }
}

class ConnectionResult {
  final bool success;
  final String message;

  ConnectionResult({required this.success, required this.message});
}
