import 'package:yaml/yaml.dart';

class CampsiteItem {
  String parkName;
  String campName;
  String deptId;
  List<String> types;

  CampsiteItem({
    required this.parkName,
    required this.campName,
    required this.deptId,
    List<String>? types,
  }) : types = types ?? [];

  Map<String, dynamic> toMap() => {
        'park_name': parkName,
        'camp_name': campName,
        'dept_id': deptId,
        'types': types,
      };
}

class CampsiteFilters {
  List<String> targetDates;
  String startDate;
  String endDate;
  List<String> targetWeekdays;
  List<String> targetTypes;
  List<String> targetSites;
  bool includeWaiting;

  CampsiteFilters({
    List<String>? targetDates,
    this.startDate = '2026-10-01',
    this.endDate = '2026-10-31',
    List<String>? targetWeekdays,
    List<String>? targetTypes,
    List<String>? targetSites,
    this.includeWaiting = true,
  })  : targetDates = targetDates ?? [],
        targetWeekdays = targetWeekdays ?? ['금', '토'],
        targetTypes = targetTypes ?? [],
        targetSites = targetSites ?? [];
}

class CampsiteNotification {
  bool onlyNewSlots;
  bool notifyClosedSlots;
  bool notifyStatusChanges;
  bool notifyConsecutiveWeekend;
  bool consecutiveIncludeWaiting;
  bool discordEnabled;
  String discordWebhookUrl;
  bool telegramEnabled;
  String telegramBotToken;
  String telegramChatId;

  CampsiteNotification({
    this.onlyNewSlots = true,
    this.notifyClosedSlots = true,
    this.notifyStatusChanges = true,
    this.notifyConsecutiveWeekend = true,
    this.consecutiveIncludeWaiting = false,
    this.discordEnabled = true,
    this.discordWebhookUrl = '',
    this.telegramEnabled = false,
    this.telegramBotToken = '',
    this.telegramChatId = '',
  });
}

class CampsiteUser {
  String id;
  String name;
  bool enabled;
  List<CampsiteItem> campsites;
  CampsiteFilters filters;
  CampsiteNotification notification;

  CampsiteUser({
    required this.id,
    required this.name,
    this.enabled = true,
    List<CampsiteItem>? campsites,
    CampsiteFilters? filters,
    CampsiteNotification? notification,
  })  : campsites = campsites ?? [],
        filters = filters ?? CampsiteFilters(),
        notification = notification ?? CampsiteNotification();
}

class CampsiteConfig {
  List<CampsiteUser> users;

  CampsiteConfig({List<CampsiteUser>? users})
      : users = users ?? [
          CampsiteUser(id: 'user1', name: 'User 1'),
          CampsiteUser(id: 'user2', name: 'User 2'),
        ];

  CampsiteUser getUser(String id) {
    return users.firstWhere(
      (u) => u.id == id,
      orElse: () => users.isNotEmpty ? users.first : CampsiteUser(id: id, name: id),
    );
  }

  void addUser(String name) {
    final nextNum = users.length + 1;
    final newId = 'user$nextNum';
    users.add(CampsiteUser(id: newId, name: name));
  }

  void removeUser(String id) {
    if (users.length <= 1) return;
    users.removeWhere((u) => u.id == id);
  }

  static CampsiteConfig parse(String yamlStr) {
    final config = CampsiteConfig(users: []);
    try {
      final doc = loadYaml(yamlStr);
      if (doc is! Map) return CampsiteConfig();

      if (doc['users'] is List) {
        for (final uMap in doc['users']) {
          if (uMap is! Map) continue;
          config.users.add(_parseUser(uMap));
        }
      } else {
        // 기존 단일 유저 설정 파일 호환
        config.users.add(_parseLegacyUser(doc));
        config.users.add(CampsiteUser(id: 'user2', name: 'User 2'));
      }
    } catch (e) {
      // 파싱 실패 시 기본값
    }

    if (config.users.isEmpty) {
      config.users = [
        CampsiteUser(id: 'user1', name: 'User 1'),
        CampsiteUser(id: 'user2', name: 'User 2'),
      ];
    }
    return config;
  }

  static CampsiteUser _parseUser(Map map) {
    final id = map['id']?.toString() ?? 'user1';
    final name = map['name']?.toString() ?? 'User';
    final enabled = map['enabled'] == null ? true : (map['enabled'] as bool);

    final campsites = <CampsiteItem>[];
    if (map['campsites'] is List) {
      for (final item in map['campsites']) {
        if (item is Map) {
          final typesList = <String>[];
          if (item['types'] is List) {
            typesList.addAll((item['types'] as List).map((e) => e.toString()));
          }
          campsites.add(CampsiteItem(
            parkName: item['park_name']?.toString() ?? '',
            campName: item['camp_name']?.toString() ?? '',
            deptId: item['dept_id']?.toString() ?? '',
            types: typesList,
          ));
        }
      }
    }

    final filters = CampsiteFilters();
    if (map['filters'] is Map) {
      final fMap = map['filters'] as Map;
      filters.startDate = fMap['start_date']?.toString() ?? '2026-10-01';
      filters.endDate = fMap['end_date']?.toString() ?? '2026-10-31';
      filters.includeWaiting = fMap['include_waiting'] == true;
      if (fMap['target_weekdays'] is List) {
        filters.targetWeekdays = (fMap['target_weekdays'] as List).map((e) => e.toString()).toList();
      }
      if (fMap['target_types'] is List) {
        filters.targetTypes = (fMap['target_types'] as List).map((e) => e.toString()).toList();
      }
    }

    final notif = CampsiteNotification();
    if (map['notification'] is Map) {
      final nMap = map['notification'] as Map;
      notif.onlyNewSlots = nMap['only_new_slots'] ?? true;
      notif.notifyClosedSlots = nMap['notify_closed_slots'] ?? true;
      notif.notifyStatusChanges = nMap['notify_status_changes'] ?? true;
      notif.notifyConsecutiveWeekend = nMap['notify_consecutive_weekend'] ?? true;
      notif.consecutiveIncludeWaiting = nMap['consecutive_include_waiting'] ?? false;

      if (nMap['discord'] is Map) {
        final dMap = nMap['discord'] as Map;
        notif.discordEnabled = dMap['enabled'] ?? true;
        notif.discordWebhookUrl = dMap['webhook_url']?.toString() ?? '';
      }
      if (nMap['telegram'] is Map) {
        final tMap = nMap['telegram'] as Map;
        notif.telegramEnabled = tMap['enabled'] ?? false;
        notif.telegramBotToken = tMap['bot_token']?.toString() ?? '';
        notif.telegramChatId = tMap['chat_id']?.toString() ?? '';
      }
    }

    return CampsiteUser(
      id: id,
      name: name,
      enabled: enabled,
      campsites: campsites,
      filters: filters,
      notification: notif,
    );
  }

  static CampsiteUser _parseLegacyUser(Map doc) {
    final campsites = <CampsiteItem>[];
    if (doc['campsites'] is List) {
      for (final item in doc['campsites']) {
        if (item is Map) {
          final typesList = <String>[];
          if (item['types'] is List) {
            typesList.addAll((item['types'] as List).map((e) => e.toString()));
          }
          campsites.add(CampsiteItem(
            parkName: item['park_name']?.toString() ?? '',
            campName: item['camp_name']?.toString() ?? '',
            deptId: item['dept_id']?.toString() ?? '',
            types: typesList,
          ));
        }
      }
    }

    final filters = CampsiteFilters();
    if (doc['filters'] is Map) {
      final fMap = doc['filters'] as Map;
      filters.startDate = fMap['start_date']?.toString() ?? '2026-10-01';
      filters.endDate = fMap['end_date']?.toString() ?? '2026-10-31';
      filters.includeWaiting = fMap['include_waiting'] == true;
      if (fMap['target_weekdays'] is List) {
        filters.targetWeekdays = (fMap['target_weekdays'] as List).map((e) => e.toString()).toList();
      }
      if (fMap['target_types'] is List) {
        filters.targetTypes = (fMap['target_types'] as List).map((e) => e.toString()).toList();
      }
    }

    final notif = CampsiteNotification();
    if (doc['notification'] is Map) {
      final nMap = doc['notification'] as Map;
      notif.onlyNewSlots = nMap['only_new_slots'] ?? true;
      notif.notifyClosedSlots = nMap['notify_closed_slots'] ?? true;
      notif.notifyStatusChanges = nMap['notify_status_changes'] ?? true;
      notif.notifyConsecutiveWeekend = nMap['notify_consecutive_weekend'] ?? true;
      notif.consecutiveIncludeWaiting = nMap['consecutive_include_waiting'] ?? false;
      if (nMap['discord'] is Map) {
        notif.discordEnabled = nMap['discord']['enabled'] ?? true;
        notif.discordWebhookUrl = nMap['discord']['webhook_url']?.toString() ?? '';
      }
    }

    return CampsiteUser(
      id: 'user1',
      name: 'User 1',
      enabled: true,
      campsites: campsites,
      filters: filters,
      notification: notif,
    );
  }

  String toYaml() {
    final buf = StringBuffer();
    buf.writeln('# 국립공원 야영장 모니터링 설정 파일 (멀티 유저 지원)\n');
    buf.writeln('users:');
    for (final user in users) {
      buf.writeln('  - id: "${user.id}"');
      buf.writeln('    name: "${user.name}"');
      buf.writeln('    enabled: ${user.enabled}');
      buf.writeln('    notification:');
      buf.writeln('      only_new_slots: ${user.notification.onlyNewSlots}');
      buf.writeln('      notify_closed_slots: ${user.notification.notifyClosedSlots}');
      buf.writeln('      notify_status_changes: ${user.notification.notifyStatusChanges}');
      buf.writeln('      notify_consecutive_weekend: ${user.notification.notifyConsecutiveWeekend}');
      buf.writeln('      consecutive_include_waiting: ${user.notification.consecutiveIncludeWaiting}');
      buf.writeln('      discord:');
      buf.writeln('        enabled: ${user.notification.discordEnabled}');
      buf.writeln('        webhook_url: "${user.notification.discordWebhookUrl}"');
      buf.writeln('      telegram:');
      buf.writeln('        enabled: ${user.notification.telegramEnabled}');
      buf.writeln('        bot_token: "${user.notification.telegramBotToken}"');
      buf.writeln('        chat_id: "${user.notification.telegramChatId}"');

      buf.writeln('    campsites:');
      if (user.campsites.isEmpty) {
        buf.writeln('      []');
      } else {
        for (final c in user.campsites) {
          buf.writeln('      - park_name: "${c.parkName}"');
          buf.writeln('        camp_name: "${c.campName}"');
          buf.writeln('        dept_id: "${c.deptId}"');
          if (c.types.isEmpty) {
            buf.writeln('        types: []');
          } else {
            buf.writeln('        types: [${c.types.map((t) => '"$t"').join(', ')}]');
          }
        }
      }

      buf.writeln('    filters:');
      buf.writeln('      target_dates: []');
      buf.writeln('      start_date: "${user.filters.startDate}"');
      buf.writeln('      end_date: "${user.filters.endDate}"');
      buf.writeln('      target_weekdays: [${user.filters.targetWeekdays.map((w) => '"$w"').join(', ')}]');
      buf.writeln('      target_types: [${user.filters.targetTypes.map((t) => '"$t"').join(', ')}]');
      buf.writeln('      target_sites: [${user.filters.targetSites.map((s) => '"$s"').join(', ')}]');
      buf.writeln('      include_waiting: ${user.filters.includeWaiting}');
      buf.writeln();
    }
    return buf.toString();
  }
}
