import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../data/eco_data.dart';
import '../models/eco_config.dart';

class EcoTab extends StatefulWidget {
  final EcoConfig config;
  final VoidCallback onConfigChanged;

  const EcoTab({
    super.key,
    required this.config,
    required this.onConfigChanged,
  });

  @override
  State<EcoTab> createState() => _EcoTabState();
}

class _EcoTabState extends State<EcoTab> {
  final List<String> allWeekdays = ['월', '화', '수', '목', '금', '토', '일'];
  final List<int> standardCapacities = [2, 3, 4, 6, 8];

  void _addEcoCenterDialog() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    '🏡 생태탐방원 추가',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(ctx),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              ConstrainedBox(
                constraints: BoxConstraints(
                  maxHeight: MediaQuery.of(context).size.height * 0.6,
                ),
                child: ListView.separated(
                  shrinkWrap: true,
                  itemCount: allEcoCenters.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (context, idx) {
                    final item = allEcoCenters[idx];
                    final isAlreadyAdded = widget.config.ecoCenters.any((c) => c.name == item.name);

                    return ListTile(
                      title: Text(
                        item.centerName,
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: isAlreadyAdded ? Colors.grey : Colors.black87,
                        ),
                      ),
                      subtitle: Text('${item.region} | ${item.location}'),
                      trailing: isAlreadyAdded
                          ? const Text('등록됨', style: TextStyle(color: Colors.grey, fontSize: 13))
                          : const Icon(Icons.add_circle_outline, color: Color(0xFF0F766E)),
                      onTap: isAlreadyAdded
                          ? null
                          : () {
                              setState(() {
                                widget.config.ecoCenters.add(
                                  EcoCenterItem(
                                    name: item.name,
                                    deptId: item.deptId,
                                    capacities: [],
                                  ),
                                );
                              });
                              widget.onConfigChanged();
                              Navigator.pop(ctx);
                            },
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _pickDateRange() async {
    DateTime initialStart = DateTime.now();
    DateTime initialEnd = DateTime.now().add(const Duration(days: 30));

    try {
      if (widget.config.filters.startDate.isNotEmpty) {
        initialStart = DateFormat('yyyy-MM-dd').parse(widget.config.filters.startDate);
      }
      if (widget.config.filters.endDate.isNotEmpty) {
        initialEnd = DateFormat('yyyy-MM-dd').parse(widget.config.filters.endDate);
      }
    } catch (_) {}

    final picked = await showDateRangePicker(
      context: context,
      initialDateRange: DateTimeRange(start: initialStart, end: initialEnd),
      firstDate: DateTime.now().subtract(const Duration(days: 1)),
      lastDate: DateTime.now().add(const Duration(days: 120)),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: const ColorScheme.light(
              primary: Color(0xFF0F766E),
              onPrimary: Colors.white,
              onSurface: Colors.black87,
            ),
          ),
          child: child!,
        );
      },
    );

    if (picked != null) {
      setState(() {
        widget.config.filters.startDate = DateFormat('yyyy-MM-dd').format(picked.start);
        widget.config.filters.endDate = DateFormat('yyyy-MM-dd').format(picked.end);
      });
      widget.onConfigChanged();
    }
  }

  @override
  Widget build(BuildContext context) {
    final ecoCenters = widget.config.ecoCenters;
    final filters = widget.config.filters;
    final notification = widget.config.notification;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. 감시 생태탐방원 목록
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '감시 생태탐방원 (${ecoCenters.length}개)',
                style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (ecoCenters.isEmpty)
            Card(
              elevation: 0,
              color: Colors.grey.shade100,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              child: const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(
                  child: Text(
                    '등록된 감시 생태탐방원이 없습니다.\n아래 버튼을 눌러 추가하세요.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.black54),
                  ),
                ),
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: ecoCenters.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (context, idx) {
                final item = ecoCenters[idx];
                final capStr = item.capacities.isNotEmpty
                    ? item.capacities.map((c) => '$c인실').join(', ')
                    : '전체 인실';

                return Card(
                  elevation: 1.5,
                  shadowColor: Colors.black12,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              '${item.name} 생태탐방원',
                              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                            ),
                            InkWell(
                              borderRadius: BorderRadius.circular(20),
                              onTap: () {
                                setState(() => ecoCenters.removeAt(idx));
                                widget.onConfigChanged();
                              },
                              child: const Padding(
                                padding: EdgeInsets.all(4),
                                child: Icon(Icons.close, size: 20, color: Colors.grey),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: const Color(0xFFE0E7FF),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                capStr,
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF4338CA),
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                            const Spacer(),
                            TextButton.icon(
                              style: TextButton.styleFrom(
                                padding: EdgeInsets.zero,
                                visualDensity: VisualDensity.compact,
                              ),
                              icon: const Icon(Icons.tune, size: 16, color: Color(0xFF0F766E)),
                              label: const Text('인실 변경', style: TextStyle(fontSize: 12)),
                              onPressed: () => _editCapacityDialog(item),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),

          const SizedBox(height: 10),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 12),
              side: const BorderSide(color: Color(0xFF0F766E), width: 1.2),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            icon: const Icon(Icons.add, color: Color(0xFF0F766E)),
            label: const Text(
              '생태탐방원 추가',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.bold,
                color: Color(0xFF0F766E),
              ),
            ),
            onPressed: _addEcoCenterDialog,
          ),

          const SizedBox(height: 24),

          // 2. 일정 및 요일 설정
          const Text(
            '감시 일정 및 요일',
            style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Card(
            elevation: 1.5,
            shadowColor: Colors.black12,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  InkWell(
                    borderRadius: BorderRadius.circular(10),
                    onTap: _pickDateRange,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      decoration: BoxDecoration(
                        color: Colors.grey.shade100,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: Colors.grey.shade300),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.calendar_month, color: Color(0xFF0F766E)),
                          const SizedBox(width: 12),
                          Text(
                            (filters.startDate.isNotEmpty && filters.endDate.isNotEmpty)
                                ? '${filters.startDate} ~ ${filters.endDate}'
                                : '날짜 범위 선택 (터치)',
                            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  const Text('요일 필터', style: TextStyle(fontSize: 13, color: Colors.black54)),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    children: allWeekdays.map((w) {
                      final isSelected = filters.targetWeekdays.contains(w);
                      return ChoiceChip(
                        label: Text(w),
                        selected: isSelected,
                        selectedColor: const Color(0xFF0F766E),
                        labelStyle: TextStyle(
                          color: isSelected ? Colors.white : Colors.black87,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        ),
                        onSelected: (selected) {
                          setState(() {
                            if (selected) {
                              filters.targetWeekdays.add(w);
                            } else {
                              filters.targetWeekdays.remove(w);
                            }
                          });
                          widget.onConfigChanged();
                        },
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // 3. 알림 조건 설정
          const Text(
            '알림 조건 설정',
            style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Card(
            elevation: 1.5,
            shadowColor: Colors.black12,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            child: Column(
              children: [
                SwitchListTile(
                  activeColor: const Color(0xFF0F766E),
                  title: const Text(
                    '🐕 반려동물 동반 객실만 감시',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                  ),
                  subtitle: const Text(
                    '반려견 동반 입실 가능한 생활관만 선별하여 알림',
                    style: TextStyle(fontSize: 12, color: Colors.black54),
                  ),
                  value: filters.petOnly,
                  onChanged: (val) {
                    setState(() => filters.petOnly = val);
                    widget.onConfigChanged();
                  },
                ),
                const Divider(height: 1),
                SwitchListTile(
                  activeColor: const Color(0xFF0F766E),
                  title: const Text(
                    '🔥 주말 2박(금,토) 연박 알림',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                  ),
                  subtitle: const Text(
                    '동일 객실에서 금+토 2박 가능 시 단독 긴급 알림',
                    style: TextStyle(fontSize: 12, color: Colors.black54),
                  ),
                  value: notification.notifyConsecutiveWeekend,
                  onChanged: (val) {
                    setState(() => notification.notifyConsecutiveWeekend = val);
                    widget.onConfigChanged();
                  },
                ),
                const Divider(height: 1),
                SwitchListTile(
                  activeColor: const Color(0xFF0F766E),
                  title: const Text(
                    '🔴 객실 마감 알림',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                  ),
                  subtitle: const Text(
                    '남아있던 객실이 예약되어 마감되었을 때도 알림 수신',
                    style: TextStyle(fontSize: 12, color: Colors.black54),
                  ),
                  value: notification.notifyClosedSlots,
                  onChanged: (val) {
                    setState(() => notification.notifyClosedSlots = val);
                    widget.onConfigChanged();
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 30),
        ],
      ),
    );
  }

  void _editCapacityDialog(EcoCenterItem item) {
    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setDlgState) {
            return AlertDialog(
              title: Text('${item.name} 감시 인실 선택'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '선택하지 않으면 전체 인실을 감시합니다.',
                    style: TextStyle(fontSize: 13, color: Colors.black54),
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    children: standardCapacities.map((cap) {
                      final isSelected = item.capacities.contains(cap);
                      return FilterChip(
                        label: Text('$cap인실'),
                        selected: isSelected,
                        selectedColor: const Color(0xFF99F6E4),
                        onSelected: (selected) {
                          setDlgState(() {
                            if (selected) {
                              item.capacities.add(cap);
                            } else {
                              item.capacities.remove(cap);
                            }
                          });
                        },
                      );
                    }).toList(),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () {
                    setDlgState(() => item.capacities.clear());
                  },
                  child: const Text('전체 초기화', style: TextStyle(color: Colors.red)),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0F766E)),
                  onPressed: () {
                    widget.onConfigChanged();
                    setState(() {});
                    Navigator.pop(ctx);
                  },
                  child: const Text('완료', style: TextStyle(color: Colors.white)),
                ),
              ],
            );
          },
        );
      },
    );
  }
}
