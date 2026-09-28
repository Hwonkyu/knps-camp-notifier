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
    this.startDate = '',
    this.endDate = '',
    List<String>? targetWeekdays,
    List<String>? targetTypes,
    List<String>? targetSites,
    this.includeWaiting = false,
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

  CampsiteNotification({
    this.onlyNewSlots = true,
    this.notifyClosedSlots = true,
    this.notifyStatusChanges = true,
    this.notifyConsecutiveWeekend = true,
    this.consecutiveIncludeWaiting = false,
  });
}

class CampsiteConfig {
  List<CampsiteItem> campsites;
  CampsiteFilters filters;
  CampsiteNotification notification;

  CampsiteConfig({
    List<CampsiteItem>? campsites,
    CampsiteFilters? filters,
    CampsiteNotification? notification,
  })  : campsites = campsites ?? [],
        filters = filters ?? CampsiteFilters(),
        notification = notification ?? CampsiteNotification();

  static CampsiteConfig parse(String yamlStr) {
    final lines = yamlStr.split('\n');
    final config = CampsiteConfig();

    String currentSection = '';
    CampsiteItem? currentCamp;

    for (int i = 0; i < lines.length; i++) {
      final line = lines[i].trim();
      if (line.isEmpty || line.startsWith('#')) continue;

      if (line.startsWith('campsites:')) {
        currentSection = 'campsites';
        continue;
      } else if (line.startsWith('filters:')) {
        currentSection = 'filters';
        continue;
      } else if (line.startsWith('notification:')) {
        currentSection = 'notification';
        continue;
      }

      if (currentSection == 'campsites') {
        if (line.startsWith('- park_name:') || line.startsWith('-')) {
          currentCamp = CampsiteItem(parkName: '', campName: '', deptId: '');
          config.campsites.add(currentCamp);
        }

        if (currentCamp != null) {
          if (line.contains('park_name:')) {
            currentCamp.parkName = _extractValue(line, 'park_name:');
          } else if (line.contains('camp_name:')) {
            currentCamp.campName = _extractValue(line, 'camp_name:');
          } else if (line.contains('dept_id:')) {
            currentCamp.deptId = _extractValue(line, 'dept_id:');
          } else if (line.contains('types:')) {
            currentCamp.types = _extractList(line, 'types:');
          }
        }
      } else if (currentSection == 'filters') {
        if (line.startsWith('start_date:')) {
          config.filters.startDate = _extractValue(line, 'start_date:');
        } else if (line.startsWith('end_date:')) {
          config.filters.endDate = _extractValue(line, 'end_date:');
        } else if (line.startsWith('target_weekdays:')) {
          config.filters.targetWeekdays = _extractList(line, 'target_weekdays:');
        } else if (line.startsWith('include_waiting:')) {
          config.filters.includeWaiting = _extractBool(line);
        } else if (line.startsWith('target_types:')) {
          config.filters.targetTypes = _extractList(line, 'target_types:');
        } else if (line.startsWith('target_dates:')) {
          config.filters.targetDates = _extractList(line, 'target_dates:');
        }
      } else if (currentSection == 'notification') {
        if (line.startsWith('only_new_slots:')) {
          config.notification.onlyNewSlots = _extractBool(line);
        } else if (line.startsWith('notify_closed_slots:')) {
          config.notification.notifyClosedSlots = _extractBool(line);
        } else if (line.startsWith('notify_status_changes:')) {
          config.notification.notifyStatusChanges = _extractBool(line);
        } else if (line.startsWith('notify_consecutive_weekend:')) {
          config.notification.notifyConsecutiveWeekend = _extractBool(line);
        } else if (line.startsWith('consecutive_include_waiting:')) {
          config.notification.consecutiveIncludeWaiting = _extractBool(line);
        }
      }
    }

    return config;
  }

  static String _extractValue(String line, String key) {
    final idx = line.indexOf(key);
    if (idx == -1) return '';
    String val = line.substring(idx + key.length).trim();
    // remove trailing comments
    if (val.contains('#')) {
      val = val.substring(0, val.indexOf('#')).trim();
    }
    return val.replaceAll('"', '').replaceAll("'", "").trim();
  }

  static bool _extractBool(String line) {
    final lower = line.toLowerCase();
    return lower.contains('true');
  }

  static List<String> _extractList(String line, String key) {
    final idx = line.indexOf(key);
    if (idx == -1) return [];
    String val = line.substring(idx + key.length).trim();
    if (val.contains('#')) {
      val = val.substring(0, val.indexOf('#')).trim();
    }
    val = val.replaceAll('[', '').replaceAll(']', '').trim();
    if (val.isEmpty) return [];
    return val
        .split(',')
        .map((e) => e.replaceAll('"', '').replaceAll("'", "").trim())
        .where((e) => e.isNotEmpty)
        .toList();
  }

  String toYaml({String? originalYaml}) {
    final sb = StringBuffer();
    sb.writeln('# 국립공원 야영장 모니터링 설정 파일 (모바일 앱 생성)');
    sb.writeln();
    sb.writeln('# 1. 감시할 야영장 및 시설 타입 목록');
    sb.writeln('campsites:');
    if (campsites.isEmpty) {
      sb.writeln('  []');
    } else {
      for (final c in campsites) {
        sb.writeln('  - park_name: "${c.parkName}"');
        sb.writeln('    camp_name: "${c.campName}"');
        sb.writeln('    dept_id: "${c.deptId}"');
        if (c.types.isNotEmpty) {
          final typesStr = c.types.map((t) => '"$t"').join(', ');
          sb.writeln('    types: [$typesStr]');
        }
        sb.writeln();
      }
    }

    sb.writeln('# 2. 필터링 조건');
    sb.writeln('filters:');
    if (filters.targetDates.isEmpty) {
      sb.writeln('  target_dates: []');
    } else {
      final datesStr = filters.targetDates.map((d) => '"$d"').join(', ');
      sb.writeln('  target_dates: [$datesStr]');
    }

    sb.writeln('  start_date: "${filters.startDate}"');
    sb.writeln('  end_date: "${filters.endDate}"');

    final dowsStr = filters.targetWeekdays.map((w) => '"$w"').join(', ');
    sb.writeln('  target_weekdays: [$dowsStr]');

    final typesStr = filters.targetTypes.map((t) => '"$t"').join(', ');
    sb.writeln('  target_types: [$typesStr]');

    final sitesStr = filters.targetSites.map((s) => '"$s"').join(', ');
    sb.writeln('  target_sites: [$sitesStr]');

    sb.writeln('  include_waiting: ${filters.includeWaiting}');
    sb.writeln();

    sb.writeln('# 3. 알림 설정');
    sb.writeln('notification:');
    sb.writeln('  only_new_slots: ${notification.onlyNewSlots}');
    sb.writeln('  notify_closed_slots: ${notification.notifyClosedSlots}');
    sb.writeln('  notify_status_changes: ${notification.notifyStatusChanges}');
    sb.writeln('  notify_consecutive_weekend: ${notification.notifyConsecutiveWeekend}');
    sb.writeln('  consecutive_include_waiting: ${notification.consecutiveIncludeWaiting}');
    sb.writeln();
    sb.writeln('  telegram:');
    sb.writeln('    enabled: false');
    sb.writeln('    bot_token: ""');
    sb.writeln('    chat_id: ""');
    sb.writeln();
    sb.writeln('  discord:');
    sb.writeln('    enabled: true');
    sb.writeln('    webhook_url: ""');
    sb.writeln();
    sb.writeln('  email:');
    sb.writeln('    enabled: false');
    sb.writeln('    smtp_host: "smtp.gmail.com"');
    sb.writeln('    smtp_port: 587');
    sb.writeln('    smtp_user: ""');
    sb.writeln('    smtp_pass: ""');
    sb.writeln('    to_email: ""');
    sb.writeln('    use_tls: true');

    return sb.toString();
  }
}
