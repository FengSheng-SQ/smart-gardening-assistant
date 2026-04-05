import 'package:flutter/material.dart';
import 'package:table_calendar/table_calendar.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';

class CalendarScreen extends StatefulWidget {
  final int? userId;

  const CalendarScreen({Key? key, this.userId}) : super(key: key);

  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  DateTime _focusedDay = DateTime.now();
  DateTime? _selectedDay;
  Map<String, List<Map<String, dynamic>>> _photosByDate = {};
  bool _isLoading = false;
  final ApiService _apiService = ApiService();

  @override
  void initState() {
    super.initState();
    _selectedDay = _focusedDay;
    _loadPhotosForMonth(_focusedDay);
  }

  Future<void> _loadPhotosForMonth(DateTime month) async {
    if (widget.userId == null) {
      setState(() {
        _photosByDate = {};
        _isLoading = false;
      });
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      // 获取聊天历史，最大500条
      final response = await _apiService.getChatHistory(widget.userId!, limit: 500);

      if (response.success && response.messages.isNotEmpty) {
        // 过滤出包含图片的消息
        final Map<String, List<Map<String, dynamic>>> photos = {};

        for (var msg in response.messages) {
          // 只显示用户上传的图片
          if (msg.isUser && msg.imageFilename != null && msg.imageFilename!.isNotEmpty) {
            final dateKey = _formatDateKey(msg.createdAt);

            if (!photos.containsKey(dateKey)) {
              photos[dateKey] = [];
            }

            // 构建图片URL
            final imageUrl = '${ApiService().baseUrl}/data/images/${msg.imageFilename}';

            photos[dateKey]!.add({
              'image_url': imageUrl,
              'message_text': msg.messageText,
              'created_at': _formatDateTime(msg.createdAt),
              'image_filename': msg.imageFilename,
            });
          }
        }

        setState(() {
          _photosByDate = photos;
          _isLoading = false;
        });

        print('📸 加载了 ${photos.length} 天的图片数据');
      } else {
        setState(() {
          _photosByDate = {};
          _isLoading = false;
        });
      }
    } catch (e) {
      print('❌ 加载图片失败: $e');
      setState(() {
        _photosByDate = {};
        _isLoading = false;
      });
    }
  }

  String _formatDateKey(DateTime date) {
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
  }

  String _formatDateTime(DateTime date) {
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
  }

  List<Map<String, dynamic>> _getPhotosForDay(DateTime day) {
    final key = '${day.year}-${day.month.toString().padLeft(2, '0')}-${day.day.toString().padLeft(2, '0')}';
    return _photosByDate[key] ?? [];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('种植日历'),
      ),
      body: Column(
        children: [
          TableCalendar(
            firstDay: DateTime.utc(2020, 1, 1),
            lastDay: DateTime.utc(2030, 12, 31),
            focusedDay: _focusedDay,
            selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
            calendarFormat: CalendarFormat.month,
            availableCalendarFormats: const {
              CalendarFormat.month: 'Month',
            },
            onDaySelected: (selectedDay, focusedDay) {
              setState(() {
                _selectedDay = selectedDay;
                _focusedDay = focusedDay;
              });
            },
            onPageChanged: (focusedDay) {
              _focusedDay = focusedDay;
              _loadPhotosForMonth(focusedDay);
            },
            calendarStyle: CalendarStyle(
              todayDecoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primary,
                shape: BoxShape.circle,
              ),
              selectedDecoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer,
                shape: BoxShape.circle,
              ),
              markerDecoration: BoxDecoration(
                color: Theme.of(context).colorScheme.secondary,
                shape: BoxShape.circle,
              ),
            ),
            eventLoader: _getPhotosForDay,
          ),
          const Divider(height: 1),
          Expanded(
            child: _buildPhotosList(),
          ),
        ],
      ),
    );
  }

  Widget _buildPhotosList() {
    if (_selectedDay == null) {
      return const Center(child: Text('请选择日期'));
    }

    final photos = _getPhotosForDay(_selectedDay!);

    if (photos.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.photo_library_outlined,
              size: 64,
              color: Colors.grey.shade400,
            ),
            const SizedBox(height: 16),
            Text(
              '这一天没有照片记录',
              style: TextStyle(
                fontSize: 16,
                color: Colors.grey.shade600,
              ),
            ),
          ],
        ),
      );
    }

    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
      ),
      itemCount: photos.length,
      itemBuilder: (context, index) {
        final photo = photos[index];
        return GestureDetector(
          onTap: () => _showPhotoDetail(photo),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Image.network(
              photo['image_url'] ?? '',
              fit: BoxFit.cover,
            ),
          ),
        );
      },
    );
  }

  void _showPhotoDetail(Map<String, dynamic> photo) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 500, maxHeight: 700),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Expanded(
                child: InteractiveViewer(
                  child: Image.network(
                    photo['image_url'] ?? '',
                    fit: BoxFit.contain,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      photo['message_text'] ?? '暂无消息文本',
                      style: const TextStyle(fontSize: 14),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      photo['created_at'] ?? '',
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.grey.shade600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
