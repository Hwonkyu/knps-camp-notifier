import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../data/campsites_data.dart';
import '../models/campsite_config.dart';

class CampsiteTab extends StatefulWidget {
  final CampsiteConfig config;
  final VoidCallback onConfigChanged;

  const CampsiteTab({
    super.key,
    required this.config,
    required this.onConfigChanged,
  });

  @override
  State<CampsiteTab> createState() => _CampsiteTabState();
}

class _CampsiteTabState extends State<CampsiteTab> {
  final List<String> allWeekdays = ['월', '화', '수', '목', '금', '토', '일'];

  void _addCampsiteDialog() {
    String searchQuery = '';
    CampsiteMeta? selectedMeta;
    final List<String> selectedTypes = [];

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            final filteredList = allCampsites.where((c) {
              if (searchQuery.isEmpty) return true;
              return c.displayName.contains(searchQuery) ||
                  c.deptId.toLowerCase().contains(searchQuery.toLowerCase());
            }).toList();

            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom,
                top: 20,
                left: 20,
                right: 20,
              ),
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  maxHeight: MediaQuery.of(context).size.height * 0.75,
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          '🏕️ 야영장 추가',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close),
                          onPressed: () => Navigator.pop(ctx),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      decoration: InputDecoration(
                        hintText: '공원명 또는 야영장명 검색 (예: 고사포, 설악동)',
                        prefixIcon: const Icon(Icons.search),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 16),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      onChanged: (val) {
                        setSheetState(() => searchQuery = val.trim());
                      },
                    ),
                    const SizedBox(height: 12),
                    Expanded(
                      child: ListView.builder(
                        itemCount: filteredList.length,
                        itemBuilder: (context, idx) {
                          final item = filteredList[idx];
                          final isSelected = selectedMeta?.deptId == item.deptId;

                          return ListTile(
                            dense: true,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8),
                            ),
                            selected: isSelected,
                            selectedTileColor: const Color(0xFFCCFBF1),
                            title: Text(
                              item.displayName,
                              style: TextStyle(
                                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                                color: isSelected ? const Color(0xFF0F766E) : Colors.black87,
                              ),
                            ),
                            subtitle: Text('코드: ${item.deptId}'),
                            trailing: isSelected
                                ? const Icon(Icons.check_circle, color: Color(0xFF0F766E))
                                : null,
                            onTap: () {
                              setSheetState(() {
                                selectedMeta = item;
                                selectedTypes.clear();
                              });
                            },
                          );
                        },
                      ),
                    ),
                    if (selectedMeta != null) ...[
                      const Divider(height: 24),
                      const Text(
                        '시설 유형 선택 (미선택 시 전체 감시)',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        children: selectedMeta!.availableTypes.map((type) {
                          final isChipSelected = selectedTypes.contains(type);
                          return FilterChip(
                            label: Text(type),
                            selected: isChipSelected,
                            selectedColor: const Color(0xFF99F6E4),
                            onSelected: (selected) {
                              setSheetState(() {
                                if (selected) {
                                  selectedTypes.add(type);
                                } else {
                                  selectedTypes.remove(type);
                                }
                              });
                            },
                          );
                        }).toList(),
                      ),
                    ],
                    const SizedBox(height: 16),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF0F766E),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      onPressed: selectedMeta == null
                          ? null
                          : () {
                              setState(() {
                                widget.config.campsites.add(
                                  CampsiteItem(
                                    parkName: selectedMeta!.parkName,
                                    campName: selectedMeta!.campName,
                                    deptId: selectedMeta!.deptId,
                                    types: List.from(selectedTypes),
                                  ),
                                );
                              });
                              widget.onConfigChanged();
                              Navigator.pop(ctx);
                            },
                      child: const Text('야영장 목록에 등록', style: TextStyle(fontSize: 15)),
                    ),
                    const SizedBox(height: 16),
                  ],
                ),
              ),
            );
          },
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
    final campsites = widget.config.campsites;
    final filters = widget.config.filters;
    final notification = widget.config.notification;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. 감시 야영장 섹션
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '감시 야영장 (${campsites.length}개)',
                style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (campsites.isEmpty)
            Card(
              elevation: 0,
              color: Colors.grey.shade100,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              child: const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(
                  child: Text(
                    '등록된 감시 야영장이 없습니다.\n아래 버튼을 눌러 추가하세요.',
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
              itemCount: campsites.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (context, idx) {
                final item = campsites[idx];
                final typesStr = item.types.isNotEmpty ? item.types.join(', ') : '전체 시설';

                return Card(
                  elevation: 1.5,
                  shadowColor: Colors.black12,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              '${item.parkName} - ${item.campName}',
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            InkWell(
                              borderRadius: BorderRadius.circular(20),
                              onTap: () {
                                setState(() => campsites.removeAt(idx));
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
                        Wrap(
                          spacing: 6,
                          children: [
                            _buildBadge(item.parkName, const Color(0xFFE0F2FE), const Color(0xFF0369A1)),
                            _buildBadge(item.campName, const Color(0xFFF1F5F9), Colors.black87),
                            _buildBadge(typesStr, const Color(0xFFCCFBF1), const Color(0xFF0F766E)),
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
              '야영장 추가',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.bold,
                color: Color(0xFF0F766E),
              ),
            ),
            onPressed: _addCampsiteDialog,
          ),

          const SizedBox(height: 24),

          // 2. 감시 일정 및 요일 섹션
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
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                            ),
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
                    '🔥 주말 2박(금,토) 즉시 연박 알림',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                  ),
                  subtitle: const Text(
                    '금+토 양일 모두 즉시 예약 가능(R) 시 단독 긴급 알림',
                    style: TextStyle(fontSize: 12, color: Colors.black54),
                  ),
                  value: notification.notifyConsecutiveWeekend,
                  onChanged: (val) {
                    setState(() {
                      notification.notifyConsecutiveWeekend = val;
                      notification.consecutiveIncludeWaiting = false; // 엄격화 규칙 준수
                    });
                    widget.onConfigChanged();
                  },
                ),
                const Divider(height: 1),
                SwitchListTile(
                  activeColor: const Color(0xFF0F766E),
                  title: const Text(
                    '🟡 대기접수(W) 포함 여부',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                  ),
                  subtitle: const Text(
                    '즉시예약 외에 대기예약 접수 가능 자리도 알림 수신',
                    style: TextStyle(fontSize: 12, color: Colors.black54),
                  ),
                  value: filters.includeWaiting,
                  onChanged: (val) {
                    setState(() => filters.includeWaiting = val);
                    widget.onConfigChanged();
                  },
                ),
                const Divider(height: 1),
                SwitchListTile(
                  activeColor: const Color(0xFF0F766E),
                  title: const Text(
                    '🔴 예약 마감(취소표 소진) 알림',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                  ),
                  subtitle: const Text(
                    '빈자리가 마감되어 사라졌을 때도 알림 수신',
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

  Widget _buildBadge(String text, Color bgColor, Color textColor) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        text,
        style: TextStyle(fontSize: 12, color: textColor, fontWeight: FontWeight.w500),
      ),
    );
  }
}
