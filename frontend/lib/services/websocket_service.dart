import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:http/http.dart' as http;
import '../models/config.dart';
import '../models/chat_state.dart';


class WebSocketService {
  WebSocketChannel? _channel;
  final _messageController = StreamController<Map<String, dynamic>>.broadcast();
  final _audioController = StreamController<List<int>>.broadcast();
  final _connectionStateController = StreamController<bool>.broadcast();

  Stream<Map<String, dynamic>> get messageStream => _messageController.stream;
  Stream<List<int>> get audioStream => _audioController.stream;
  Stream<bool> get connectionState => _connectionStateController.stream;

  bool isConnected = false;
  Timer? _connectionTimeoutTimer;
  int? _currentUserId; // 当前登录的用户ID

  /// 获取当前连接的用户ID
  int? get currentUserId => _currentUserId;

  Future<void> connect() async {
    return connectWithUserId(_currentUserId);
  }

  Future<void> connectWithUserId(int? userId) async {
    _currentUserId = userId;
    try {
      // 先标记为未连接
      isConnected = false;
      _connectionStateController.add(false);

      // 构建WebSocket URL，带用户ID参数
      final url = AppConfig.buildWebSocketUrl(userId: userId);

      print('🔗 正在连接: $url');
      print('🔗 用户ID: $userId');

      _channel = WebSocketChannel.connect(Uri.parse(url));
      print('🔗 WebSocketChannel已创建');

      // 设置连接超时（10秒）
      _connectionTimeoutTimer?.cancel();
      _connectionTimeoutTimer = Timer(const Duration(seconds: 10), () {
        if (!isConnected) {
          print('❌ 连接超时');
          isConnected = false;
          _connectionStateController.add(false);
          _messageController.add({
            'type': 'error',
            'message': '连接超时，请检查服务器是否运行'
          });
        }
      });

      // 监听连接状态
      _channel!.ready.then((_) {
        print('✅ WebSocket连接已建立');
        // 注意：这里只是TCP连接建立，还需要等待服务器返回"connected"消息
      }).catchError((error) {
        print('❌ WebSocket连接失败: $error');
        isConnected = false;
        _connectionStateController.add(false);
        _connectionTimeoutTimer?.cancel();
      });

      // 监听消息
      _channel!.stream.listen(
        (message) {
          print('📥 收到数据类型: ${message.runtimeType}');
          if (message is List<int>) {
            // 音频数据
            print('📥 收到音频: ${message.length} bytes');
            _audioController.add(message);
          } else if (message is String) {
            // JSON消息
            print('📥 收到JSON消息: ${message.length} 字符');
            print('📥 消息内容: $message');
            try {
              final data = jsonDecode(message) as Map<String, dynamic>;
              _messageController.add(data);

              // 收到connected消息才算真正连接成功
              if (data['type'] == 'connected') {
                print('✅ 服务器确认连接成功');
                isConnected = true;
                _connectionStateController.add(true);
                _connectionTimeoutTimer?.cancel();
              }
            } catch (e) {
              print('❌ JSON解析失败: $e');
              print('❌ 原始消息: $message');
            }
          }
        },
        onError: (error) {
          print('❌ WebSocket错误: $error');
          isConnected = false;
          _connectionStateController.add(false);
          _connectionTimeoutTimer?.cancel();
          _messageController.add({
            'type': 'error',
            'message': '连接错误: $error'
          });
        },
        onDone: () {
          print('🔌 WebSocket连接已关闭');
          isConnected = false;
          _connectionStateController.add(false);
          _connectionTimeoutTimer?.cancel();
        },
        cancelOnError: false,
      );
    } catch (e) {
      print('❌ 连接失败: $e');
      isConnected = false;
      _connectionStateController.add(false);
      _messageController.add({
        'type': 'error',
        'message': '连接失败: $e'
      });
    }
  }

  void disconnect() {
    print('🔌 断开WebSocket连接');
    _connectionTimeoutTimer?.cancel();
    _channel?.sink.close();
    _channel = null;
    isConnected = false;
    _connectionStateController.add(false);
  }

  // 发送文本消息
  void sendText(String text, {ChatMode? mode, Map<String, dynamic>? location}) {
    if (!isConnected) {
      print('❌ WebSocket未连接，无法发送消息');
      return;
    }

    // 验证location数据：后端只需要city和source两个字段
    Map<String, dynamic>? validatedLocation;
    if (location != null && location.containsKey('city') && location.containsKey('source')) {
      final cityValue = location['city'].toString();
      final sourceValue = location['source'].toString();

      // 额外验证：确保city和source不为空
      if (cityValue.isNotEmpty && sourceValue.isNotEmpty) {
        validatedLocation = {
          'city': cityValue,
          'source': sourceValue,
          // 可选字段，如果存在就包含
          if (location.containsKey('latitude')) 'latitude': location['latitude'],
          if (location.containsKey('longitude')) 'longitude': location['longitude'],
        };
        print('✅ 位置信息验证通过:');
        print('   - city: "$cityValue" (长度: ${cityValue.length})');
        print('   - source: "$sourceValue" (长度: ${sourceValue.length})');
        if (validatedLocation.containsKey('latitude')) {
          print('   - latitude: ${validatedLocation['latitude']}');
        }
        if (validatedLocation.containsKey('longitude')) {
          print('   - longitude: ${validatedLocation['longitude']}');
        }
      } else {
        print('⚠️  位置字段值为空:');
        print('   - city: "$cityValue" (长度: ${cityValue.length})');
        print('   - source: "$sourceValue" (长度: ${sourceValue.length})');
        print('   不发送location给服务器');
      }
    } else if (location != null) {
      print('⚠️  位置信息缺少必需字段:');
      print('   - 有city: ${location.containsKey('city')}');
      print('   - 有source: ${location.containsKey('source')}');
      print('   不发送location给服务器');
    }

    final message = {
      'type': 'text',
      'text': text,
      'chat_mode': mode?.name ?? 'fast',
      if (validatedLocation != null) 'location': validatedLocation,
    };

    final jsonString = jsonEncode(message);
    print('📤 发送文本消息: "$text"');
    print('📤 消息模式: ${mode?.name ?? 'fast'}');
    print('📤 发送JSON (${jsonString.length} 字符)');
    _channel?.sink.add(jsonString);
  }

  // 发送图片消息
  void sendImage(String imageBase64, {String? question, ChatMode? mode, Map<String, dynamic>? location}) {
    if (!isConnected) {
      print('❌ WebSocket未连接，无法发送图片');
      return;
    }

    // 验证location数据：后端只需要city和source两个字段
    Map<String, dynamic>? validatedLocation;
    if (location != null && location.containsKey('city') && location.containsKey('source')) {
      validatedLocation = {
        'city': location['city'].toString(),
        'source': location['source'].toString(),
        if (location.containsKey('latitude')) 'latitude': location['latitude'],
        if (location.containsKey('longitude')) 'longitude': location['longitude'],
      };
      print('✅ 图片消息位置验证通过: city=${validatedLocation['city']}');
    } else if (location != null) {
      print('⚠️  图片消息位置缺少必需字段，不发送location');
    }

    final message = {
      'type': 'image',
      'image': imageBase64,
      if (question != null) 'question': question,
      'chat_mode': mode?.name ?? 'fast',
      if (validatedLocation != null) 'location': validatedLocation,
    };

    print('📤 发送图片消息: mode=${mode?.name ?? 'fast'}');
    _channel?.sink.add(jsonEncode(message));
  }

  // 准备图片+语音模式（先发送图片，等待音频）
  void prepareImageWithAudio(String imageBase64) {
    if (!isConnected) {
      print('❌ WebSocket未连接，无法准备图片');
      return;
    }

    final message = {
      'type': 'prepare_image_with_audio',
      'image': imageBase64,
    };

    print('📸 准备图片+语音模式');
    _channel?.sink.add(jsonEncode(message));
  }

  // 发送音频数据
  void sendAudio(List<int> audioBytes) {
    if (!isConnected) {
      print('❌ WebSocket未连接，无法发送音频');
      return;
    }

    print('📤 发送音频数据: ${audioBytes.length} bytes');
    _channel?.sink.add(audioBytes);
  }

  // 发送语音消息（带元数据）
  void sendVoiceMessage(String audioBase64, {ChatMode? mode, Map<String, dynamic>? location}) {
    if (!isConnected) {
      print('❌ WebSocket未连接，无法发送语音消息');
      return;
    }

    // 验证location数据：后端只需要city和source两个字段
    Map<String, dynamic>? validatedLocation;
    if (location != null && location.containsKey('city') && location.containsKey('source')) {
      validatedLocation = {
        'city': location['city'].toString(),
        'source': location['source'].toString(),
        if (location.containsKey('latitude')) 'latitude': location['latitude'],
        if (location.containsKey('longitude')) 'longitude': location['longitude'],
      };
      print('✅ 语音消息位置验证通过: city=${validatedLocation['city']}');
    } else if (location != null) {
      print('⚠️  语音消息位置缺少必需字段，不发送location');
    }

    final message = {
      'type': 'audio',
      'audio': audioBase64,
      'chat_mode': mode?.name ?? 'fast',
      if (validatedLocation != null) 'location': validatedLocation,
    };

    print('📤 发送语音消息: mode=${mode?.name ?? 'fast'}');
    _channel?.sink.add(jsonEncode(message));
  }

  // 清空聊天历史
  Future<void> clearChatHistory() async {
    if (_currentUserId == null) {
      print('⚠️ 用户未登录，无法清空历史');
      return;
    }

    try {
      final uri = Uri.parse('${AppConfig.httpServerUrl}/v1/chat/clear?user_id=$_currentUserId');
      final response = await http.delete(uri);

      if (response.statusCode == 200) {
        print('✅ 聊天历史已清空');
      } else {
        print('❌ 清空聊天历史失败: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ 清空聊天历史失败: $e');
    }
  }

  void dispose() {
    _connectionTimeoutTimer?.cancel();
    _messageController.close();
    _audioController.close();
    _connectionStateController.close();
    disconnect();
  }
}
