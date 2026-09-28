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
        if (token.isNotEmpty) 'Authorization': 'Bearer $token',
        'User-Agent': 'KNPS-Mobile-App/1.0',
      };

  /// 연결 테스트 (저장소 접근 권한 확인)
  Future<bool> testConnection() async {
    try {
      final url = Uri.parse('https://api.github.com/repos/$owner/$repo');
      final resp = await http.get(url, headers: _headers);
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// 파일 내용 및 SHA 조회
  Future<Map<String, dynamic>?> fetchFile(String path) async {
    try {
      final url = Uri.parse('https://api.github.com/repos/$owner/$repo/contents/$path?ref=$branch');
      final resp = await http.get(url, headers: _headers);

      if (resp.statusCode == 200) {
        final data = json.decode(resp.body);
        final String rawBase64 = (data['content'] as String).replaceAll('\n', '');
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
      final url = Uri.parse('https://api.github.com/repos/$owner/$repo/contents/$path');
      final base64Content = base64.encode(utf8.encode(newContent));

      final body = json.encode({
        'message': commitMessage,
        'content': base64Content,
        'sha': sha,
        'branch': branch,
      });

      final resp = await http.put(url, headers: _headers, body: body);
      return resp.statusCode == 200 || resp.statusCode == 201;
    } catch (_) {
      return false;
    }
  }
}
