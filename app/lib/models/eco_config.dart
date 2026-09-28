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
    this.startDate = '',
    this.endDate = '',
    List<String>? targetWeekdays,
    this.petOnly = false,
  })  : targetDates = targetDates ?? [],
        targetWeekdays = targetWeekdays ?? ['금', '토'];
}

class EcoNotification {
  bool onlyNewSlots;
  bool notifyClosedSlots;
  bool notifyConsecutiveWeekend;

  EcoNotification({
    this.onlyNewSlots = true,
    this.notifyClosedSlots = true,
    this.notifyConsecutiveWeekend = true,
  });
}

class EcoConfig {
  List<EcoCenterItem> ecoCenters;
  EcoFilters filters;
  EcoNotification notification;

  EcoConfig({
    List<EcoCenterItem>? ecoCenters,
    EcoFilters? filters,
    EcoNotification? notification,
  })  : ecoCenters = ecoCenters ?? [],
        filters = filters ?? EcoFilters(),
        notification = notification ?? EcoNotification();

  static EcoConfig parse(String yamlStr) {
    final lines = yamlStr.split('\n');
    final config = EcoConfig();

    String currentSection = '';
    EcoCenterItem? currentCenter;

    for (int i = 0; i < lines.length; i++) {
      final line = lines[i].trim();
      if (line.isEmpty || line.startsWith('#')) continue;

      if (line.startsWith('eco_centers:')) {
        currentSection = 'eco_centers';
        continue;
      } else if (line.startsWith('filters:')) {
        currentSection = 'filters';
        continue;
      } else if (line.startsWith('notification:')) {
        currentSection = 'notification';
        continue;
      }

      if (currentSection == 'eco_centers') {
        if (line.startsWith('- name:') || line.startsWith('-')) {
          currentCenter = EcoCenterItem(name: '', deptId: '');
          config.ecoCenters.add(currentCenter);
        }

        if (currentCenter != null) {
          if (line.contains('name:')) {
            currentCenter.name = _extractValue(line, 'name:');
          } else if (line.contains('dept_id:')) {
            currentCenter.deptId = _extractValue(line, 'dept_id:');
          } else if (line.contains('capacities:')) {
            currentCenter.capacities = _extractIntList(line, 'capacities:');
          }
        }
      } else if (currentSection == 'filters') {
        if (line.startsWith('start_date:')) {
          config.filters.startDate = _extractValue(line, 'start_date:');
        } else if (line.startsWith('end_date:')) {
          config.filters.endDate = _extractValue(line, 'end_date:');
        } else if (line.startsWith('target_weekdays:')) {
          config.filters.targetWeekdays = _extractList(line, 'target_weekdays:');
        } else if (line.startsWith('pet_only:')) {
          config.filters.petOnly = _extractBool(line);
        }
      } else if (currentSection == 'notification') {
        if (line.startsWith('only_new_slots:')) {
          config.notification.onlyNewSlots = _extractBool(line);
        } else if (line.startsWith('notify_closed_slots:')) {
          config.notification.notifyClosedSlots = _extractBool(line);
        } else if (line.startsWith('notify_consecutive_weekend:')) {
          config.notification.notifyConsecutiveWeekend = _extractBool(line);
        }
      }
    }

    return config;
  }

  static String _extractValue(String line, String key) {
    final idx = line.indexOf(key);
    if (idx == -1) return '';
    String val = line.substring(idx + key.length).trim();
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

  static List<int> _extractIntList(String line, String key) {
    final list = _extractList(line, key);
    return list.map((e) => int.tryParse(e) ?? 0).where((n) => n > 0).toList();
  }

  String toYaml({String? originalYaml}) {
    final sb = StringBuffer();
    sb.writeln('# 국립공원 생태탐방원 모니터링 설정 파일 (모바일 앱 생성)');
    sb.writeln();
    sb.writeln('# 1. 감시할 생태탐방원 목록');
    sb.writeln('eco_centers:');
    if (ecoCenters.isEmpty) {
      sb.writeln('  []');
    } else {
      for (final c in ecoCenters) {
        sb.writeln('  - name: "${c.name}"');
        sb.writeln('    dept_id: "${c.deptId}"');
        if (c.capacities.isNotEmpty) {
          sb.writeln('    capacities: [${c.capacities.join(', ')}]');
        } else {
          sb.writeln('    capacities: []');
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

    sb.writeln('  pet_only: ${filters.petOnly}');
    sb.writeln();

    sb.writeln('# 3. 알림 설정');
    sb.writeln('notification:');
    sb.writeln('  only_new_slots: ${notification.onlyNewSlots}');
    sb.writeln('  notify_closed_slots: ${notification.notifyClosedSlots}');
    sb.writeln('  notify_consecutive_weekend: ${notification.notifyConsecutiveWeekend}');
    sb.writeln();
    sb.writeln('  discord:');
    sb.writeln('    enabled: true');
    sb.writeln('    webhook_url: ""');
    sb.writeln();
    sb.writeln('  telegram:');
    sb.writeln('    enabled: false');
    sb.writeln('    bot_token: ""');
    sb.writeln('    chat_id: ""');
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
