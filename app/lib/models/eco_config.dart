import 'package:yaml/yaml.dart';

class EcoCenterItem {
  String name;
  String deptId;
  List<int> capacities;

  EcoCenterItem({
    required this.name,
    required this.deptId,
    List<int>? capacities,
  }) : capacities = capacities ?? [];
}

class EcoFilters {
  List<String> targetDates;
  String startDate;
  String endDate;
  List<String> targetWeekdays;
  bool petOnly;

  EcoFilters({
    List<String>? targetDates,
    this.startDate = '2026-10-01',
    this.endDate = '2026-10-31',
    List<String>? targetWeekdays,
    this.petOnly = false,
  })  : targetDates = targetDates ?? [],
        targetWeekdays = targetWeekdays ?? ['금', '토'];
}

class EcoNotification {
  bool onlyNewSlots;
  bool notifyClosedSlots;
  bool notifyConsecutiveWeekend;
  bool discordEnabled;
  String discordWebhookUrl;
  bool telegramEnabled;
  String telegramBotToken;
  String telegramChatId;

  EcoNotification({
    this.onlyNewSlots = true,
    this.notifyClosedSlots = true,
    this.notifyConsecutiveWeekend = true,
    this.discordEnabled = true,
    this.discordWebhookUrl = '',
    this.telegramEnabled = false,
    this.telegramBotToken = '',
    this.telegramChatId = '',
  });
}

class EcoUser {
  String id;
  String name;
  bool enabled;
  List<EcoCenterItem> ecoCenters;
  EcoFilters filters;
  EcoNotification notification;

  EcoUser({
    required this.id,
    required this.name,
    this.enabled = true,
    List<EcoCenterItem>? ecoCenters,
    EcoFilters? filters,
    EcoNotification? notification,
  })  : ecoCenters = ecoCenters ?? [],
        filters = filters ?? EcoFilters(),
        notification = notification ?? EcoNotification();
}

class EcoConfig {
  List<EcoUser> users;

  EcoConfig({List<EcoUser>? users})
      : users = users ?? [
          EcoUser(id: 'user1', name: 'User 1'),
          EcoUser(id: 'user2', name: 'User 2'),
        ];

  EcoUser getUser(String id) {
    return users.firstWhere(
      (u) => u.id == id,
      orElse: () => users.isNotEmpty ? users.first : EcoUser(id: id, name: id),
    );
  }

  void addUser(String name) {
    final nextNum = users.length + 1;
    final newId = 'user$nextNum';
    users.add(EcoUser(id: newId, name: name));
  }

  void removeUser(String id) {
    if (users.length <= 1) return;
    users.removeWhere((u) => u.id == id);
  }

  static EcoConfig parse(String yamlStr) {
    final config = EcoConfig(users: []);
    try {
      final doc = loadYaml(yamlStr);
      if (doc is! Map) return EcoConfig();

      if (doc['users'] is List) {
        for (final uMap in doc['users']) {
          if (uMap is! Map) continue;
          config.users.add(_parseUser(uMap));
        }
      } else {
        // 기존 단일 유저 설정 파일 호환
        config.users.add(_parseLegacyUser(doc));
        config.users.add(EcoUser(id: 'user2', name: 'User 2'));
      }
    } catch (e) {
      // 파싱 실패 시 기본값
    }

    if (config.users.isEmpty) {
      config.users = [
        EcoUser(id: 'user1', name: 'User 1'),
        EcoUser(id: 'user2', name: 'User 2'),
      ];
    }
    return config;
  }

  static EcoUser _parseUser(Map map) {
    final id = map['id']?.toString() ?? 'user1';
    final name = map['name']?.toString() ?? 'User';
    final enabled = map['enabled'] == null ? true : (map['enabled'] as bool);

    final centers = <EcoCenterItem>[];
    if (map['eco_centers'] is List) {
      for (final item in map['eco_centers']) {
        if (item is Map) {
          final caps = <int>[];
          if (item['capacities'] is List) {
            for (final c in item['capacities']) {
              final val = int.tryParse(c.toString());
              if (val != null) caps.add(val);
            }
          }
          centers.add(EcoCenterItem(
            name: item['name']?.toString() ?? '',
            deptId: item['dept_id']?.toString() ?? '',
            capacities: caps,
          ));
        }
      }
    }

    final filters = EcoFilters();
    if (map['filters'] is Map) {
      final fMap = map['filters'] as Map;
      filters.startDate = fMap['start_date']?.toString() ?? '2026-10-01';
      filters.endDate = fMap['end_date']?.toString() ?? '2026-10-31';
      filters.petOnly = fMap['pet_only'] == true;
      if (fMap['target_weekdays'] is List) {
        filters.targetWeekdays = (fMap['target_weekdays'] as List).map((e) => e.toString()).toList();
      }
    }

    final notif = EcoNotification();
    if (map['notification'] is Map) {
      final nMap = map['notification'] as Map;
      notif.onlyNewSlots = nMap['only_new_slots'] ?? true;
      notif.notifyClosedSlots = nMap['notify_closed_slots'] ?? true;
      notif.notifyConsecutiveWeekend = nMap['notify_consecutive_weekend'] ?? true;

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

    return EcoUser(
      id: id,
      name: name,
      enabled: enabled,
      ecoCenters: centers,
      filters: filters,
      notification: notif,
    );
  }

  static EcoUser _parseLegacyUser(Map doc) {
    final centers = <EcoCenterItem>[];
    if (doc['eco_centers'] is List) {
      for (final item in doc['eco_centers']) {
        if (item is Map) {
          final caps = <int>[];
          if (item['capacities'] is List) {
            for (final c in item['capacities']) {
              final val = int.tryParse(c.toString());
              if (val != null) caps.add(val);
            }
          }
          centers.add(EcoCenterItem(
            name: item['name']?.toString() ?? '',
            deptId: item['dept_id']?.toString() ?? '',
            capacities: caps,
          ));
        }
      }
    }

    final filters = EcoFilters();
    if (doc['filters'] is Map) {
      final fMap = doc['filters'] as Map;
      filters.startDate = fMap['start_date']?.toString() ?? '2026-10-01';
      filters.endDate = fMap['end_date']?.toString() ?? '2026-10-31';
      filters.petOnly = fMap['pet_only'] == true;
      if (fMap['target_weekdays'] is List) {
        filters.targetWeekdays = (fMap['target_weekdays'] as List).map((e) => e.toString()).toList();
      }
    }

    final notif = EcoNotification();
    if (doc['notification'] is Map) {
      final nMap = doc['notification'] as Map;
      notif.onlyNewSlots = nMap['only_new_slots'] ?? true;
      notif.notifyClosedSlots = nMap['notify_closed_slots'] ?? true;
      notif.notifyConsecutiveWeekend = nMap['notify_consecutive_weekend'] ?? true;
      if (nMap['discord'] is Map) {
        notif.discordEnabled = nMap['discord']['enabled'] ?? true;
        notif.discordWebhookUrl = nMap['discord']['webhook_url']?.toString() ?? '';
      }
    }

    return EcoUser(
      id: 'user1',
      name: 'User 1',
      enabled: true,
      ecoCenters: centers,
      filters: filters,
      notification: notif,
    );
  }

  String toYaml() {
    final buf = StringBuffer();
    buf.writeln('# 국립공원 생태탐방원 모니터링 설정 파일 (멀티 유저 지원)\n');
    buf.writeln('users:');
    for (final user in users) {
      buf.writeln('  - id: "${user.id}"');
      buf.writeln('    name: "${user.name}"');
      buf.writeln('    enabled: ${user.enabled}');
      buf.writeln('    notification:');
      buf.writeln('      only_new_slots: ${user.notification.onlyNewSlots}');
      buf.writeln('      notify_closed_slots: ${user.notification.notifyClosedSlots}');
      buf.writeln('      notify_consecutive_weekend: ${user.notification.notifyConsecutiveWeekend}');
      buf.writeln('      discord:');
      buf.writeln('        enabled: ${user.notification.discordEnabled}');
      buf.writeln('        webhook_url: "${user.notification.discordWebhookUrl}"');
      buf.writeln('      telegram:');
      buf.writeln('        enabled: ${user.notification.telegramEnabled}');
      buf.writeln('        bot_token: "${user.notification.telegramBotToken}"');
      buf.writeln('        chat_id: "${user.notification.telegramChatId}"');

      buf.writeln('    eco_centers:');
      if (user.ecoCenters.isEmpty) {
        buf.writeln('      []');
      } else {
        for (final c in user.ecoCenters) {
          buf.writeln('      - name: "${c.name}"');
          buf.writeln('        dept_id: "${c.deptId}"');
          buf.writeln('        capacities: [${c.capacities.join(', ')}]');
        }
      }

      buf.writeln('    filters:');
      buf.writeln('      target_dates: []');
      buf.writeln('      start_date: "${user.filters.startDate}"');
      buf.writeln('      end_date: "${user.filters.endDate}"');
      buf.writeln('      target_weekdays: [${user.filters.targetWeekdays.map((w) => '"$w"').join(', ')}]');
      buf.writeln('      pet_only: ${user.filters.petOnly}');
      buf.writeln();
    }
    return buf.toString();
  }
}
