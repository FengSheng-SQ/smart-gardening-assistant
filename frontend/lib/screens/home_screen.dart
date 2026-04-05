import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:image_picker/image_picker.dart';
import '../models/chat_state.dart';
import '../services/websocket_service.dart';
import '../services/audio_service.dart';
import '../services/api_service.dart';
import '../services/location_service.dart';
import '../services/auth_service.dart';
import '../widgets/chat_mode_selector.dart';
import 'calendar_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final ImagePicker _imagePicker = ImagePicker();
  final FocusNode _focusNode = FocusNode(); // 添加焦点管理

  WebSocketService? _wsService;
  AudioService? _audioService;
  ApiService? _apiService;
  LocationService? _locationService;

  String? _currentImagePath;
  Map<String, dynamic>? _currentLocation;
  String _username = '';
  String _token = '';
  int? _userId;
  bool _isLoggedIn = false;
  bool _isRecording = false;
  bool _isVoiceMode = false; // true = voice input mode, false = text input mode
  String _recordingTime = '0:00';
  Timer? _recordingTimer;
  int _recordingSeconds = 0;
  bool _isConnected = false;
  StreamSubscription<bool>? _connectionSubscription;
  String? _recordedAudioPath; // 存储录制完成的音频路径
  bool _isPreviewPlaying = false; // 是否正在预览播放
  int _previewPosition = 0; // 播放进度（秒）
  Timer? _previewTimer; // 播放进度计时器
  String? _pendingAudioFilename; // 等待接收音频字节的AI回复文件名

  // 消息音频播放状态管理
  final Map<String, bool> _messageAudioPlaying = {}; // messageId -> 是否正在播放
  final Map<String, int> _messageAudioPosition = {}; // messageId -> 播放位置（秒）
  final Map<String, Timer?> _messageAudioTimers = {}; // messageId -> 播放计时器
  final Map<String, int> _messageAudioDuration = {}; // messageId -> 音频总时长（秒）

  // 状态弹窗管理
  ScaffoldFeatureController? _statusSnackBar; // 当前显示的状态弹窗
  String? _currentStatus; // 当前状态文本

  @override
  void initState() {
    super.initState();
    _initializeServices();
    _initApp();  // 统一的初始化流程
  }

  /// 应用初始化流程
  Future<void> _initApp() async {
    // 1. 先加载登录状态（必须等待完成）
    await _checkLoginStatus();

    // 2. 登录状态加载完成后，再连接WebSocket
    // 3. 确保UI已经准备好
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _connectWebSocket();
    });
  }

  Future<void> _initializeServices() async {
    print('🔧 开始初始化服务...');

    // 初始化服务
    _audioService = AudioService();
    _apiService = ApiService();
    _locationService = LocationService();

    // 请求权限
    print('📋 请求权限...');
    await _requestPermissions();
    print('✅ 权限请求完成');

    // 获取GPS位置
    print('📍 开始获取GPS位置...');
    await _getCurrentLocation();
  }

  Future<void> _requestPermissions() async {
    await [
      Permission.microphone,
      Permission.camera,
      Permission.location,
    ].request();
  }

  Future<void> _getCurrentLocation() async {
    try {
      print('📍 [GPS] 开始获取GPS位置...');

      // 检查权限
      final hasPermission = await _locationService!.hasPermission();
      print('📍 [GPS] 权限检查结果: $hasPermission');

      if (!hasPermission) {
        print('❌ [GPS] 没有位置权限');
        setState(() {
          _currentLocation = null;
        });
        return;
      }

      print('📍 [GPS] 开始调用 getCurrentPosition...');
      final location = await _locationService!.getCurrentLocation();

      print('✅ [GPS] 位置获取成功:');
      print('   - 纬度: ${location['latitude']}');
      print('   - 经度: ${location['longitude']}');
      print('   - 城市: ${location['city']}');
      print('   - 来源: ${location['source']}');

      setState(() {
        _currentLocation = location;
      });

      print('✅ [GPS] 状态已更新');
    } catch (e, stackTrace) {
      print('❌ [GPS] 位置获取异常: $e');
      print('❌ [GPS] 堆栈跟踪: $stackTrace');

      setState(() {
        _currentLocation = null;
      });

      print('⚠️ [GPS] 位置设置为null，应用可继续使用');
    }
  }

  Future<void> _checkLoginStatus() async {
    // 从本地存储读取登录状态
    final loginInfo = await AuthService.loadLoginInfo();

    if (!mounted) return;

    if (loginInfo != null) {
      // 有缓存的登录信息
      final chatState = context.read<ChatState>();

      // 先提取到局部变量
      final username = loginInfo['username'] as String;
      final token = loginInfo['token'] as String;
      final userId = loginInfo['userId'] as int;

      print('📂 从缓存加载用户信息: username=$username, userId=$userId');

      // 先更新ChatState（使用局部变量，不要依赖setState的异步更新）
      chatState.login(
        username,
        token: token,
        userId: userId,
      );

      print('✅ ChatState已更新: userId=${chatState.userId}');

      // 然后更新UI状态
      setState(() {
        _username = username;
        _token = token;
        _userId = userId;
        _isLoggedIn = true;
      });

      print('✅ 已从缓存恢复登录状态: $username, userId=$userId');

      // 加载聊天历史
      await _loadChatHistory();
    } else {
      // 没有缓存的登录信息
      setState(() {
        _isLoggedIn = false;
        _isConnected = false;
      });
    }
  }

  Future<void> _loadChatHistory() async {
    final chatState = context.read<ChatState>();
    final userId = chatState.userId;

    if (userId == null) {
      print('📜 未登录，跳过加载聊天历史');
      return;
    }

    print('📜 开始加载聊天历史: userId=$userId');

    try {
      final response = await _apiService!.getChatHistory(userId, limit: 500);

      if (!mounted) return;

      if (response.success && response.messages.isNotEmpty) {
        print('✅ 成功加载 ${response.messages.length} 条历史消息');

        // 清空当前消息
        chatState.clearMessages();

        // 将历史消息转换为ChatMessage并添加到状态
        for (var msg in response.messages) {
          String? localImagePath;

          // 如果有图片，从服务器下载到本地
          if (msg.imageFilename != null && msg.imageFilename!.isNotEmpty) {
            print('📥 下载历史图片: ${msg.imageFilename}');
            try {
              final imageBytes = await _apiService!.downloadFile(msg.imageFilename!);
              if (imageBytes != null) {
                // 保存到本地临时目录
                final tempDir = Directory.systemTemp;
                localImagePath = '${tempDir.path}/${msg.imageFilename}';
                final imageFile = File(localImagePath);
                await imageFile.writeAsBytes(imageBytes);
                print('✅ 历史图片下载完成: ${imageBytes.length} bytes');
              }
            } catch (e) {
              print('❌ 历史图片下载失败: $e');
            }
          }

          final chatMessage = ChatMessage(
            id: msg.id.toString(),
            role: msg.isUser ? MessageRole.user : MessageRole.assistant,
            content: msg.messageText,
            imagePath: localImagePath, // 使用下载后的本地路径
            timestamp: msg.createdAt,
            mode: ChatMode.fast, // 历史消息默认使用快速模式
            audioUrl: msg.audioFilename,
          );
          chatState.addMessage(chatMessage);
        }

        print('✅ 聊天历史已添加到界面');
        _scrollToBottom();
      } else {
        print('📜 没有历史消息或加载失败');
      }
    } catch (e) {
      print('❌ 加载聊天历史失败: $e');
      if (mounted) {
        _showError('加载聊天历史失败: $e');
      }
    }
  }

  Future<void> _connectWebSocket() async {
    // 游客模式使用 null userId，已登录用户使用实际 userId
    final chatState = context.read<ChatState>();

    // 优先使用ChatState的状态来判断是否应该带userId
    final shouldUseUserId = chatState.isLoggedIn;
    final targetUserId = shouldUseUserId ? chatState.userId : null;

    print('🔗 准备连接WebSocket');
    print('   chatState.isLoggedIn: ${chatState.isLoggedIn}');
    print('   _isLoggedIn: $_isLoggedIn');
    print('   chatState.userId: ${chatState.userId}');
    print('   shouldUseUserId: $shouldUseUserId');
    print('   targetUserId: $targetUserId');

    // 检查是否需要重新连接
    bool needReconnect = false;
    if (_wsService == null) {
      print('🔗 首次连接');
      needReconnect = true;
    } else if (!_wsService!.isConnected) {
      print('🔗 连接已断开，需要重连');
      needReconnect = true;
    } else if (_wsService!.currentUserId != targetUserId) {
      print('🔗 用户ID发生变化，需要重新连接');
      print('   旧用户ID: ${_wsService!.currentUserId}');
      print('   新用户ID: $targetUserId');
      needReconnect = true;
    }

    if (!needReconnect) {
      print('🔗 WebSocket已连接且用户ID匹配，跳过重复连接');
      return;
    }

    // 如果有旧连接，先清理
    if (_wsService != null) {
      print('🔗 清理旧WebSocket连接');
      _connectionSubscription?.cancel();
      _wsService!.disconnect();
      // 等待断开完成
      await Future.delayed(const Duration(milliseconds: 100));
    }

    _wsService = WebSocketService();

    await _wsService!.connectWithUserId(targetUserId);

    _wsService!.messageStream.listen((message) {
      _handleIncomingMessage(message);
    });

    // 监听音频流
    _wsService!.audioStream.listen((audioBytes) {
      _handleIncomingAudio(audioBytes);
    });

    // 监听连接状态变化
    _connectionSubscription?.cancel();
    _connectionSubscription = _wsService!.connectionState.listen((isConnected) {
      print('🔗 连接状态变化: $isConnected');
      if (mounted) {
        setState(() {
          _isConnected = isConnected;
        });
      }
    });
  }

  void _handleIncomingMessage(Map<String, dynamic> messageData) {
    final chatState = context.read<ChatState>();

    // Parse the message data
    final type = messageData['type'] as String?;

    print('🔍 处理消息类型: $type');

    if (type == 'text' || type == 'image' || type == 'response') {
      // 收到AI回复，关闭状态弹窗
      _hideStatusSnackBar();

      final content = messageData['text'] as String? ?? '';
      final imagePath = messageData['image_path'] as String?;
      final audioFilename = messageData['audio_filename'] as String?;
      final mode = ChatMode.values.firstWhere(
        (m) => m.name == (messageData['chat_mode'] as String? ?? 'fast'),
        orElse: () => ChatMode.fast,
      );

      // 如果回复文本为空且没有图片和音频，则跳过这个消息
      if (content.isEmpty && imagePath == null && audioFilename == null) {
        print('⚠️  收到空回复消息，跳过显示');
        return;
      }

      print('✅ 创建助手消息: ${content.substring(0, content.length > 50 ? 50 : content.length)}...');

      final message = ChatMessage(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        role: MessageRole.assistant,
        content: content,
        imagePath: imagePath,
        timestamp: DateTime.now(),
        audioUrl: audioFilename,
        mode: mode,
      );

      chatState.addMessage(message);

      print('✅ 消息已添加到聊天状态');

      // 如果有音频文件名，等待音频字节到达后再播放
      if (audioFilename != null) {
        setState(() {
          _pendingAudioFilename = audioFilename;
        });
        print('🎵 等待接收音频字节: $audioFilename');
      }

      _scrollToBottom();
    } else if (type == 'transcription') {
      // 处理语音识别结果
      final text = messageData['text'] as String?;
      if (text != null && text.isNotEmpty) {
        print('🎤 语音识别结果: $text');

        // 更新最后一条用户消息，显示识别的文字
        final messages = chatState.messages;
        if (messages.isNotEmpty) {
          final lastMessage = messages.last;
          if (lastMessage.role == MessageRole.user) {
            // 创建更新后的消息
            final updatedMessage = ChatMessage(
              id: lastMessage.id,
              role: lastMessage.role,
              content: '[语音] $text',
              imagePath: lastMessage.imagePath,
              timestamp: lastMessage.timestamp,
              audioUrl: lastMessage.audioUrl,
              mode: lastMessage.mode,
            );

            // 使用ChatState的方法来更新消息
            chatState.removeMessage(lastMessage.id);
            chatState.addMessage(updatedMessage);
          }
        }
      }
    } else if (type == 'error') {
      // 收到错误，关闭状态弹窗并显示错误信息
      _hideStatusSnackBar();

      final errorMessage = messageData['message'] as String?;
      if (errorMessage != null) {
        print('❌ 错误: $errorMessage');
        _showErrorSnackBar(errorMessage);
      }
    } else if (type == 'status') {
      // 状态消息，显示加载状态弹窗
      final statusMessage = messageData['message'] as String?;
      if (statusMessage != null) {
        print('📊 状态: $statusMessage');
        _showStatusSnackBar(statusMessage);
      }
    } else if (type == 'connected') {
      print('✅ 服务器确认连接成功');
      // 连接成功状态已经在connectionState中处理
    } else {
      print('⚠️ 未知消息类型: $type');
    }
  }

  void _handleIncomingAudio(List<int> audioBytes) async {
    print('🎵 收到音频字节: ${audioBytes.length} bytes');

    if (_pendingAudioFilename == null) {
      print('⚠️  没有等待的音频文件名，忽略音频字节');
      return;
    }

    if (_audioService == null) {
      print('⚠️  AudioService未初始化');
      return;
    }

    if (!mounted) return;

    try {
      // 保存音频到临时文件
      final tempDir = Directory.systemTemp;
      final audioPath = '${tempDir.path}/$_pendingAudioFilename';

      final file = File(audioPath);
      await file.writeAsBytes(audioBytes);

      print('✅ 音频已保存到: $audioPath');

      // 找到对应的AI消息
      if (!mounted) return;
      final chatState = context.read<ChatState>();
      final messages = chatState.messages;
      if (messages.isNotEmpty) {
        final lastAssistantMessage = messages.lastWhere(
          (msg) => msg.role == MessageRole.assistant,
          orElse: () => messages.last,
        );

        // 播放音频
        await _audioService!.playAudio(audioPath);

        // 标记为正在播放并估算音频时长
        if (mounted) {
          setState(() {
            _messageAudioPlaying[lastAssistantMessage.id] = true;
            _messageAudioPosition[lastAssistantMessage.id] = 0;
            _messageAudioDuration[lastAssistantMessage.id] = audioBytes.length ~/ 32000;
          });
        }

        // 监听播放进度
        _messageAudioTimers[lastAssistantMessage.id]?.cancel();
        _messageAudioTimers[lastAssistantMessage.id] = Timer.periodic(const Duration(seconds: 1), (timer) async {
          if (!mounted) {
            timer.cancel();
            return;
          }

          if (!_messageAudioPlaying[lastAssistantMessage.id]!) {
            timer.cancel();
            return;
          }

          // 检查是否还在播放
          if (!_audioService!.isPlaying) {
            timer.cancel();
            if (mounted) {
              setState(() {
                _messageAudioPlaying[lastAssistantMessage.id] = false;
                _messageAudioPosition[lastAssistantMessage.id] = 0;
              });
            }
            return;
          }

          // 更新播放位置
          if (mounted) {
            setState(() {
              _messageAudioPosition[lastAssistantMessage.id] =
                  (_messageAudioPosition[lastAssistantMessage.id] ?? 0) + 1;
            });
          }
        });
      }

      // 清除等待状态
      if (mounted) {
        setState(() {
          _pendingAudioFilename = null;
        });
      }

      print('✅ 音频播放已开始');
    } catch (e) {
      print('❌ 处理音频失败: $e');
      if (mounted) {
        setState(() {
          _pendingAudioFilename = null;
        });
      }
    }
  }

  Future<void> _sendMessage() async {
    // 收起键盘
    _focusNode.unfocus();

    final text = _textController.text.trim();
    if (text.isEmpty && _currentImagePath == null) return;

    final chatState = context.read<ChatState>();

    // 检查游客模式限制
    if (!_isLoggedIn && (chatState.currentMode == ChatMode.thinking || chatState.currentMode == ChatMode.expert)) {
      _showError('游客模式只能使用快速模式，已自动切换');
      chatState.setMode(ChatMode.fast);
    }

    // 先保存到局部变量，避免被提前清除
    final imagePath = _currentImagePath;

    // 添加用户消息
    final userMessage = ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      role: MessageRole.user,
      content: text,
      imagePath: imagePath,
      timestamp: DateTime.now(),
      mode: chatState.currentMode,
    );
    chatState.addMessage(userMessage);

    _textController.clear();
    setState(() {
      _currentImagePath = null;
    });

    chatState.setLoading(true);

    try {
      if (_wsService == null) {
        await _connectWebSocket();
      }

      if (imagePath != null) {
        // 发送图片
        print('📸 准备发送图片: $imagePath');
        final imageBytes = await File(imagePath).readAsBytes();
        final base64Image = base64Encode(imageBytes);
        print('📸 图片大小: ${imageBytes.length} bytes, Base64大小: ${base64Image.length} 字符');

        _wsService!.sendImage(
          base64Image,
          question: text.isNotEmpty ? text : null,
          mode: chatState.currentMode,
          location: _currentLocation,
        );
        print('✅ 图片已发送');
      } else {
        // 发送文本
        print('📝 发送文本消息: $text');
        _wsService!.sendText(
          text,
          mode: chatState.currentMode,
          location: _currentLocation,
        );
      }
    } catch (e) {
      _showError('发送失败: $e');
    } finally {
      chatState.setLoading(false);
    }

    _scrollToBottom();
  }

  Future<void> _pickImage() async {
    final ImageSource? source = await showDialog<ImageSource>(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('选择图片来源'),
        children: [
          SimpleDialogOption(
            onPressed: () => Navigator.pop(context, ImageSource.camera),
            child: const Text('拍照'),
          ),
          SimpleDialogOption(
            onPressed: () => Navigator.pop(context, ImageSource.gallery),
            child: const Text('从相册选择'),
          ),
        ],
      ),
    );

    if (source != null) {
      final pickedFile = await _imagePicker.pickImage(source: source);
      if (pickedFile != null) {
        setState(() {
          _currentImagePath = pickedFile.path;
        });
      }
    }
  }

  Future<void> _startRecording() async {
    if (_audioService == null) return;

    final hasPermission = await _audioService!.hasPermission();
    if (!hasPermission) {
      _showError('需要麦克风权限');
      return;
    }

    final tempDir = Directory.systemTemp;
    final path = '${tempDir.path}/recording_${DateTime.now().millisecondsSinceEpoch}.wav';

    await _audioService!.startRecording(path);

    setState(() {
      _isRecording = true;
      _recordedAudioPath = null;
      _recordingSeconds = 0;
      _recordingTime = '0:00';
    });

    _recordingTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        _recordingSeconds++;
        final minutes = _recordingSeconds ~/ 60;
        final seconds = _recordingSeconds % 60;
        _recordingTime = '$minutes:${seconds.toString().padLeft(2, '0')}';
      });
    });
  }

  Future<void> _stopRecording() async {
    if (_audioService == null) return;

    _recordingTimer?.cancel();

    final path = await _audioService!.stopRecording();

    setState(() {
      _isRecording = false;
      _recordedAudioPath = path;
    });
  }

  Future<void> _cancelRecording() async {
    if (_audioService == null) return;

    _recordingTimer?.cancel();

    await _audioService!.cancelRecording();

    setState(() {
      _isRecording = false;
      _recordedAudioPath = null;
      _recordingSeconds = 0;
      _recordingTime = '0:00';
    });
  }

  Future<void> _previewRecording() async {
    if (_recordedAudioPath == null || _audioService == null) return;

    if (_isPreviewPlaying) {
      // 暂停播放
      await _audioService!.pauseAudio();
      setState(() {
        _isPreviewPlaying = false;
      });
      _previewTimer?.cancel();
    } else {
      // 从头开始播放
      await _audioService!.stopAudio(); // 先停止之前的播放
      await _audioService!.playAudio(_recordedAudioPath!);
      setState(() {
        _isPreviewPlaying = true;
        _previewPosition = 0; // 重置播放位置
      });

      // 监听播放进度
      _previewTimer?.cancel();
      _previewTimer = Timer.periodic(const Duration(seconds: 1), (timer) async {
        if (!_isPreviewPlaying) {
          timer.cancel();
          return;
        }

        // 检查是否还在播放
        if (!_audioService!.isPlaying) {
          timer.cancel();
          setState(() {
            _isPreviewPlaying = false;
            _previewPosition = 0;
          });
          return;
        }

        // 更新播放位置
        setState(() {
          _previewPosition++;
        });
      });
    }
  }

  // 消息音频播放控制
  Future<void> _toggleMessageAudio(ChatMessage message) async {
    if (message.audioUrl == null || _audioService == null) return;

    final messageId = message.id;
    final isPlaying = _messageAudioPlaying[messageId] ?? false;

    if (isPlaying) {
      // 暂停播放
      await _audioService!.pauseAudio();
      _messageAudioTimers[messageId]?.cancel();
      setState(() {
        _messageAudioPlaying[messageId] = false;
      });
    } else {
      // 从头开始播放
      String audioPath = message.audioUrl!;

      // 检查是否需要从服务器下载音频
      if (!audioPath.contains('/') && !audioPath.contains('\\')) {
        // 是文件名，需要检查本地是否存在
        final tempDir = Directory.systemTemp;
        final localPath = '${tempDir.path}/$audioPath';
        final localFile = File(localPath);

        if (await localFile.exists()) {
          // 本地文件存在，直接使用
          audioPath = localPath;
        } else {
          // 本地文件不存在，从服务器下载
          print('📥 从服务器下载音频: $audioPath');
          try {
            final audioBytes = await _apiService!.downloadFile(audioPath);
            if (audioBytes != null) {
              await localFile.writeAsBytes(audioBytes);
              audioPath = localPath;
              print('✅ 音频下载完成: ${audioBytes.length} bytes');
            } else {
              print('❌ 音频下载失败');
              return;
            }
          } catch (e) {
            print('❌ 音频下载异常: $e');
            return;
          }
        }
      }

      // 停止其他正在播放的消息
      for (var mid in _messageAudioPlaying.keys) {
        if (_messageAudioPlaying[mid] == true && mid != messageId) {
          _messageAudioTimers[mid]?.cancel();
          setState(() {
            _messageAudioPlaying[mid] = false;
          });
        }
      }

      await _audioService!.playAudio(audioPath);
      setState(() {
        _messageAudioPlaying[messageId] = true;
        _messageAudioPosition[messageId] = 0;
      });

      // 监听播放进度
      _messageAudioTimers[messageId]?.cancel();
      _messageAudioTimers[messageId] = Timer.periodic(const Duration(seconds: 1), (timer) async {
        if (!_messageAudioPlaying[messageId]!) {
          timer.cancel();
          return;
        }

        // 检查是否还在播放
        if (!_audioService!.isPlaying) {
          timer.cancel();
          setState(() {
            _messageAudioPlaying[messageId] = false;
            _messageAudioPosition[messageId] = 0;
          });
          return;
        }

        // 更新播放位置
        setState(() {
          _messageAudioPosition[messageId] = (_messageAudioPosition[messageId] ?? 0) + 1;
        });
      });
    }
  }

  String _getMessageAudioButtonText(ChatMessage message) {
    final messageId = message.id;
    final isPlaying = _messageAudioPlaying[messageId] ?? false;

    return isPlaying ? '暂停' : '播放';
  }

  Future<void> _sendVoiceMessage() async {
    // 收起键盘
    _focusNode.unfocus();

    if (_recordedAudioPath == null || _wsService == null) return;

    final chatState = context.read<ChatState>();

    // 检查游客模式限制
    if (!_isLoggedIn && (chatState.currentMode == ChatMode.thinking || chatState.currentMode == ChatMode.expert)) {
      _showError('游客模式只能使用快速模式，已自动切换');
      chatState.setMode(ChatMode.fast);
    }

    // 读取音频文件
    final audioFile = File(_recordedAudioPath!);
    final audioBytes = await audioFile.readAsBytes();

    // 添加用户消息标记
    final userMessage = ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      role: MessageRole.user,
      content: '[语音消息]',
      audioUrl: _recordedAudioPath,
      timestamp: DateTime.now(),
      mode: chatState.currentMode,
    );
    chatState.addMessage(userMessage);

    // 清除录音
    setState(() {
      _recordedAudioPath = null;
    });

    chatState.setLoading(true);

    try {
      // 直接发送二进制音频数据到服务器
      _wsService!.sendAudio(audioBytes);
      print('✅ 音频数据已发送: ${audioBytes.length} bytes');
    } catch (e) {
      _showError('发送失败: $e');
    } finally {
      chatState.setLoading(false);
    }

    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w500),
        ),
        backgroundColor: Colors.lightBlue, // 天蓝色背景
        behavior: SnackBarBehavior.floating,
        margin: EdgeInsets.only(
          bottom: MediaQuery.of(context).size.height - 178,
          left: 16,
          right: 16,
        ),
        duration: const Duration(seconds: 2),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
    );
  }

  /// 显示错误弹窗（红色背景）
  void _showErrorSnackBar(String errorMessage) {
    // 提取友好的错误信息
    String friendlyMessage = _extractFriendlyErrorMessage(errorMessage);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.error_outline, color: Colors.white),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                friendlyMessage,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w500),
              ),
            ),
          ],
        ),
        backgroundColor: Colors.red, // 红色背景表示错误
        behavior: SnackBarBehavior.floating,
        margin: EdgeInsets.only(
          bottom: MediaQuery.of(context).size.height - 178,
          left: 16,
          right: 16,
        ),
        duration: const Duration(seconds: 4), // 错误信息显示时间稍长
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
    );
  }

  /// 从错误消息中提取友好的提示信息
  String _extractFriendlyErrorMessage(String errorMessage) {
    // 根据错误类型返回友好的提示
    if (errorMessage.contains('401') || errorMessage.contains('Unauthorized')) {
      return '认证失败，请检查API密钥配置';
    } else if (errorMessage.contains('Connection') || errorMessage.contains('connect')) {
      return '网络连接失败，请检查网络设置';
    } else if (errorMessage.contains('timeout')) {
      return '请求超时，请稍后重试';
    } else if (errorMessage.contains('rate') || errorMessage.contains('limit')) {
      return '请求过于频繁，请稍后再试';
    } else if (errorMessage.contains('model')) {
      return 'AI模型错误，请稍后重试';
    }

    // 如果错误信息太长，截取前面部分
    if (errorMessage.length > 50) {
      return errorMessage.substring(0, 50) + '...';
    }

    return errorMessage;
  }

  /// 显示持续的状态弹窗（正在思考、正在识别等）
  void _showStatusSnackBar(String status) {
    // 如果状态没有变化，不重复显示
    if (_currentStatus == status && _statusSnackBar != null) {
      return;
    }

    // 关闭之前的弹窗
    _hideStatusSnackBar();

    _currentStatus = status;
    _statusSnackBar = ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                status,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w500),
              ),
            ),
          ],
        ),
        backgroundColor: Colors.orange, // 橙色背景表示正在处理
        behavior: SnackBarBehavior.floating,
        margin: EdgeInsets.only(
          bottom: MediaQuery.of(context).size.height - 178,
          left: 16,
          right: 16,
        ),
        duration: const Duration(days: 1), // 持续显示，直到手动关闭
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
    );
  }

  /// 关闭状态弹窗
  void _hideStatusSnackBar() {
    _statusSnackBar?.close();
    _statusSnackBar = null;
    _currentStatus = null;
  }

  void _showLoginDialog() {
    final usernameController = TextEditingController();
    final passwordController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('登录'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: usernameController,
              decoration: const InputDecoration(labelText: '用户名'),
            ),
            TextField(
              controller: passwordController,
              decoration: const InputDecoration(labelText: '密码'),
              obscureText: true,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () async {
              try {
                final chatState = context.read<ChatState>();
                final result = await _apiService!.login(
                  usernameController.text,
                  passwordController.text,
                );

                if (result.success) {
                  // 确保userId不为null
                  final userId = result.userId;
                  if (userId == null) {
                    if (!mounted) return;
                    _showError('登录失败: 用户ID缺失');
                    return;
                  }

                  setState(() {
                    _username = usernameController.text;
                    _token = result.token ?? '';
                    _userId = userId;
                    _isLoggedIn = true;
                  });

                  // Update ChatState with user info
                  chatState.login(
                    usernameController.text,
                    token: result.token ?? '',
                    userId: userId,
                  );

                  // 保存登录信息到本地缓存
                  await AuthService.saveLoginInfo(
                    username: usernameController.text,
                    token: result.token ?? '',
                    userId: userId,
                  );

                  if (!mounted) return;
                  Navigator.pop(context);

                  // 加载聊天历史
                  await _loadChatHistory();

                  // 连接WebSocket
                  await _connectWebSocket();
                } else {
                  if (!mounted) return;
                  _showError(result.message);
                }
              } catch (e) {
                if (!mounted) return;
                _showError('登录失败: $e');
              }
            },
            child: const Text('登录'),
          ),
        ],
      ),
    );
  }

  void _showAboutDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('关于'),
        content: const Text('智能种植助手 v0.1.0\n\n基于AI的园艺助手应用'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('确定'),
          ),
        ],
      ),
    );
  }

  void _showClearHistoryDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('清空聊天记录'),
        content: const Text('确定要清空所有聊天记录吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () async {
              final chatState = context.read<ChatState>();
              final userId = chatState.userId;
              if (userId == null) {
                _showError('请先登录');
                return;
              }
              try {
                await _apiService!.clearChatHistory(userId);
                if (!mounted) return;
                chatState.clearMessages();
                Navigator.pop(context);
                _showError('聊天记录已清空');
              } catch (e) {
                if (!mounted) return;
                _showError('清空失败: $e');
              }
            },
            child: const Text('确定'),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteSelectedMessages(ChatState chatState) async {
    final selectedIds = chatState.selectedMessageIds.toList();

    if (selectedIds.isEmpty) {
      return;
    }

    // 确认删除
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认删除'),
        content: Text('确定要删除选中的 ${selectedIds.length} 条消息吗？\n\n此操作将从服务器永久删除。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(
              foregroundColor: Colors.red,
            ),
            child: const Text('删除'),
          ),
        ],
      ),
    );

    if (confirmed != true) {
      return;
    }

    try {
      final userId = chatState.userId;
      if (userId == null) {
        _showError('请先登录');
        return;
      }

      // 显示加载状态
      chatState.setLoading(true);

      // 转换String ID为int
      final messageIdsInt = selectedIds.map((id) => int.tryParse(id) ?? 0).toList();

      // 调用API删除消息
      final success = await _apiService!.deleteChatMessages(messageIdsInt, userId);

      if (!mounted) return;

      if (success) {
        // 从本地状态中移除
        chatState.removeSelectedMessages();

        // 退出选择模式
        chatState.exitSelectionMode();

        _showError('已删除 ${selectedIds.length} 条消息');
      } else {
        _showError('删除失败，请稍后重试');
      }
    } catch (e) {
      if (!mounted) return;
      _showError('删除失败: $e');
    } finally {
      if (mounted) {
        chatState.setLoading(false);
      }
    }
  }

  Future<void> _refreshConnectionStatus() async {
    if (_wsService == null) {
      setState(() {
        _isConnected = false;
      });
      _showError('未连接到服务器');
      return;
    }

    // 检查连接状态
    setState(() {
      _isConnected = _wsService!.isConnected;
    });

    if (!_isConnected && _isLoggedIn) {
      _showError('服务器连接已断开，正在尝试重连...');
      try {
        await _connectWebSocket();
      } catch (e) {
        _showError('重连失败: $e');
      }
    } else if (_isConnected) {
      _showError('服务器连接正常');
    }
  }

  @override
  Widget build(BuildContext context) {
    final chatState = context.watch<ChatState>();

    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.primary,
        title: const Text('智能种植助手'),
        actions: [
          IconButton(
            icon: const Icon(Icons.calendar_today),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => CalendarScreen(userId: _userId)),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refreshConnectionStatus,
            tooltip: '刷新连接状态',
          ),
        ],
      ),
      drawer: Drawer(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            DrawerHeader(
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primary,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const CircleAvatar(
                    radius: 32,
                    child: Icon(Icons.person, size: 32),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    _isLoggedIn ? _username : '未登录',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _isLoggedIn ? '已登录' : '点击登录',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.8),
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
            if (!_isLoggedIn)
              ListTile(
                leading: const Icon(Icons.login),
                title: const Text('登录'),
                onTap: () {
                  Navigator.pop(context);
                  _showLoginDialog();
                },
              ),
            if (_isLoggedIn)
              ListTile(
                leading: const Icon(Icons.logout),
                title: const Text('退出登录'),
                onTap: () async {
                  // 在async操作前获取chatState
                  final chatState = context.read<ChatState>();
                  Navigator.pop(context);

                  // 清除本地缓存的登录信息
                  await AuthService.clearLoginInfo();

                  if (!mounted) return;

                  // 清除ChatState中的登录信息
                  chatState.logout();

                  setState(() {
                    _isLoggedIn = false;
                    _username = '';
                    _token = '';
                    _userId = null;
                  });

                  // 断开旧连接
                  _wsService?.disconnect();

                  // 以游客模式重新连接服务器
                  print('🔗 退出登录，以游客模式重新连接...');
                  await Future.delayed(const Duration(milliseconds: 500));
                  if (!mounted) return;
                  await _connectWebSocket();
                },
              ),
            ListTile(
              leading: const Icon(Icons.calendar_today),
              title: const Text('种植日历'),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => CalendarScreen(userId: _userId)),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.delete_outline),
              title: const Text('清空聊天'),
              onTap: () {
                Navigator.pop(context);
                _showClearHistoryDialog();
              },
            ),
            ListTile(
              leading: const Icon(Icons.info_outline),
              title: const Text('关于'),
              onTap: () {
                Navigator.pop(context);
                _showAboutDialog();
              },
            ),
          ],
        ),
      ),
      body: GestureDetector(
        onTap: () {
          // 点击空白处时收起键盘
          _focusNode.unfocus();
        },
        child: Column(
          children: [
          // 批量操作栏
          Consumer<ChatState>(
            builder: (context, chatState, child) {
              if (!chatState.isSelectionMode) {
                return const SizedBox.shrink();
              }

              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  border: Border(
                    bottom: BorderSide(
                      color: Theme.of(context).colorScheme.primary,
                      width: 1,
                    ),
                  ),
                ),
                child: Row(
                  children: [
                    Text(
                      '已选择 ${chatState.selectedCount} 条',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                    ),
                    const Spacer(),
                    // 全选/取消全选按钮
                    TextButton.icon(
                      onPressed: () {
                        if (chatState.isAllSelected) {
                          chatState.deselectAllMessages();
                        } else {
                          chatState.selectAllMessages();
                        }
                      },
                      icon: Icon(
                        chatState.isAllSelected ? Icons.deselect : Icons.select_all,
                      ),
                      label: Text(chatState.isAllSelected ? '取消全选' : '全选'),
                    ),
                    // 删除按钮
                    TextButton.icon(
                      onPressed: chatState.selectedCount > 0
                          ? () => _deleteSelectedMessages(chatState)
                          : null,
                      icon: const Icon(Icons.delete),
                      label: const Text('删除'),
                      style: TextButton.styleFrom(
                        foregroundColor: Colors.red,
                      ),
                    ),
                    // 取消按钮
                    IconButton(
                      onPressed: () => chatState.exitSelectionMode(),
                      icon: const Icon(Icons.close),
                      tooltip: '取消选择',
                    ),
                  ],
                ),
              );
            },
          ),
          // 连接状态栏
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: _isConnected ? Colors.green.shade50 : Colors.red.shade50,
              border: Border(
                bottom: BorderSide(
                  color: _isConnected ? Colors.green.shade200 : Colors.red.shade200,
                  width: 1,
                ),
              ),
            ),
            child: Row(
              children: [
                Icon(
                  _isConnected ? Icons.cloud_done : Icons.cloud_off,
                  size: 20,
                  color: _isConnected ? Colors.green.shade700 : Colors.red.shade700,
                ),
                const SizedBox(width: 8),
                Text(
                  _isConnected ? '服务器已连接' : '服务器未连接',
                  style: TextStyle(
                    color: _isConnected ? Colors.green.shade700 : Colors.red.shade700,
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(width: 16),
                // GPS位置状态
                Icon(
                  _currentLocation != null ? Icons.location_on : Icons.location_off,
                  size: 16,
                  color: _currentLocation != null ? Colors.blue.shade700 : Colors.grey.shade400,
                ),
                const SizedBox(width: 4),
                Text(
                  _currentLocation != null ? 'GPS已定位' : 'GPS未定位',
                  style: TextStyle(
                    color: _currentLocation != null ? Colors.blue.shade700 : Colors.grey.shade400,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              itemCount: chatState.messages.length,
              itemBuilder: (context, index) {
                final message = chatState.messages[index];
                final isUser = message.role == MessageRole.user;
                final isSelected = chatState.isSelectionMode &&
                    chatState.selectedMessageIds.contains(message.id);

                return GestureDetector(
                  onLongPress: () {
                    if (!chatState.isSelectionMode) {
                      chatState.enterSelectionMode();
                      chatState.toggleMessageSelection(message.id);
                    }
                  },
                  onTap: () {
                    if (chatState.isSelectionMode) {
                      chatState.toggleMessageSelection(message.id);
                    }
                  },
                  child: Stack(
                    children: [
                      Align(
                        alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 12),
                          padding: const EdgeInsets.all(12),
                          constraints: const BoxConstraints(maxWidth: 280),
                          decoration: BoxDecoration(
                            color: isUser
                                ? Theme.of(context).colorScheme.primaryContainer
                                : Theme.of(context).colorScheme.surfaceContainerHighest,
                            borderRadius: BorderRadius.circular(12),
                            border: isSelected
                                ? Border.all(
                                    color: Theme.of(context).colorScheme.primary,
                                    width: 2,
                                  )
                                : null,
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (message.imagePath != null)
                                ClipRRect(
                                  borderRadius: BorderRadius.circular(8),
                                  child: Image.file(
                                    File(message.imagePath!),
                                    width: double.infinity,
                                    fit: BoxFit.cover,
                                  ),
                                ),
                              if (message.content.isNotEmpty)
                                Text(
                                  message.content,
                                  style: const TextStyle(fontSize: 14),
                                ),
                              if (message.error != null)
                                Text(
                                  message.error!,
                                  style: TextStyle(
                                    color: Theme.of(context).colorScheme.error,
                                    fontSize: 12,
                                  ),
                                ),
                              // 音频播放控制
                              if (message.audioUrl != null)
                                Padding(
                                  padding: const EdgeInsets.only(top: 8),
                                  child: InkWell(
                                    onTap: () => _toggleMessageAudio(message),
                                    borderRadius: BorderRadius.circular(8),
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                      decoration: BoxDecoration(
                                        color: (_messageAudioPlaying[message.id] ?? false)
                                            ? Colors.orange.shade50
                                            : Colors.blue.shade50,
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(
                                          color: (_messageAudioPlaying[message.id] ?? false)
                                              ? Colors.orange.shade200
                                              : Colors.blue.shade200,
                                        ),
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Icon(
                                            (_messageAudioPlaying[message.id] ?? false)
                                                ? Icons.pause
                                                : Icons.play_arrow,
                                            color: (_messageAudioPlaying[message.id] ?? false)
                                                ? Colors.orange
                                                : Colors.blue,
                                            size: 18,
                                          ),
                                          const SizedBox(width: 6),
                                          Text(
                                            _getMessageAudioButtonText(message),
                                            style: TextStyle(
                                              color: (_messageAudioPlaying[message.id] ?? false)
                                                  ? Colors.orange.shade700
                                                  : Colors.blue.shade700,
                                              fontSize: 13,
                                              fontWeight: FontWeight.w500,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ),
                              Text(
                                _formatTime(message.timestamp),
                                style: TextStyle(
                                  color: Colors.grey.shade600,
                                  fontSize: 10,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      // 选择模式下显示复选框
                      if (chatState.isSelectionMode)
                        Positioned(
                          top: 4,
                          left: isUser ? null : 4,
                          right: isUser ? 4 : null,
                          child: Container(
                            decoration: BoxDecoration(
                              color: Colors.white,
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: isSelected
                                    ? Theme.of(context).colorScheme.primary
                                    : Colors.grey.shade400,
                                width: 2,
                              ),
                            ),
                            child: Checkbox(
                              value: isSelected,
                              onChanged: (_) {
                                chatState.toggleMessageSelection(message.id);
                              },
                              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              visualDensity: VisualDensity.compact,
                            ),
                          ),
                        ),
                    ],
                  ),
                );
              },
            ),
          ),
          if (chatState.isLoading)
            const Padding(
              padding: EdgeInsets.all(16),
              child: CircularProgressIndicator(),
            ),
          Consumer<ChatState>(
            builder: (context, chatState, child) {
              return ChatModeSelector(
                currentMode: chatState.currentMode,
                onModeChanged: (mode) {
                  chatState.setMode(mode);
                },
                isLoggedIn: _isLoggedIn,
              );
            },
          ),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.05),
                  blurRadius: 4,
                  offset: const Offset(0, -2),
                ),
              ],
            ),
            child: SafeArea(
              child: Column(
                children: [
                  // 图片预览
                  if (_currentImagePath != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Stack(
                        alignment: Alignment.topRight,
                        children: [
                          ClipRRect(
                            borderRadius: BorderRadius.circular(8),
                            child: Image.file(
                              File(_currentImagePath!),
                              height: 100,
                              width: double.infinity,
                              fit: BoxFit.cover,
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.close),
                            onPressed: () {
                              setState(() {
                                _currentImagePath = null;
                              });
                            },
                          ),
                        ],
                      ),
                    ),

                  // 输入区域 - 单行按钮布局
                  Row(
                    children: [
                      // 图片按钮
                      IconButton(
                        icon: const Icon(Icons.image),
                        onPressed: _pickImage,
                      ),

                      const SizedBox(width: 4),

                      // 文本/语音切换按钮
                      Container(
                        decoration: BoxDecoration(
                          color: _isVoiceMode
                              ? Theme.of(context).colorScheme.primary
                              : Colors.grey.shade200,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: IconButton(
                          icon: Icon(_isVoiceMode ? Icons.mic : Icons.keyboard),
                          color: _isVoiceMode ? Colors.white : Colors.grey.shade700,
                          onPressed: () {
                            setState(() {
                              _isVoiceMode = !_isVoiceMode;
                            });
                          },
                          iconSize: 20,
                        ),
                      ),

                      const SizedBox(width: 8),

                      // 中间区域：文本输入框、录音按钮、或预览按钮
                      Expanded(
                        child: _isVoiceMode
                            ? // 语音模式
                            _recordedAudioPath == null
                                ? // 未录音：显示录音按钮
                                Container(
                                    height: 48,
                                    decoration: BoxDecoration(
                                      color: _isRecording
                                          ? Colors.red.shade100
                                          : Colors.grey.shade100,
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(
                                        color: _isRecording
                                            ? Colors.red.shade300
                                            : Colors.grey.shade300,
                                      ),
                                    ),
                                    child: InkWell(
                                      onTap: () {
                                        if (_isRecording) {
                                          _stopRecording();
                                        } else {
                                          _startRecording();
                                        }
                                      },
                                      borderRadius: BorderRadius.circular(8),
                                      child: Center(
                                        child: Row(
                                          mainAxisAlignment: MainAxisAlignment.center,
                                          children: [
                                            Icon(
                                              _isRecording ? Icons.stop : Icons.mic,
                                              color: _isRecording ? Colors.red : Colors.grey.shade600,
                                            ),
                                            const SizedBox(width: 8),
                                            Text(
                                              _isRecording ? '停止录音' : '点击录音',
                                              style: TextStyle(
                                                color: _isRecording ? Colors.red.shade700 : Colors.grey.shade600,
                                                fontSize: 15,
                                                fontWeight: FontWeight.w500,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),
                                  )
                                : // 已录音：显示预览和重新录音按钮
                                Row(
                                    children: [
                                      // 预览按钮
                                      Expanded(
                                        child: Container(
                                          height: 48,
                                          decoration: BoxDecoration(
                                            color: Colors.blue.shade50,
                                            borderRadius: BorderRadius.circular(8),
                                            border: Border.all(color: Colors.blue.shade200),
                                          ),
                                          child: InkWell(
                                            onTap: _previewRecording,
                                            borderRadius: BorderRadius.circular(8),
                                            child: Center(
                                              child: Row(
                                                mainAxisAlignment: MainAxisAlignment.center,
                                                children: [
                                                  Icon(
                                                    _isPreviewPlaying ? Icons.pause : Icons.play_arrow,
                                                    color: _isPreviewPlaying ? Colors.orange : Colors.blue.shade700,
                                                    size: 20,
                                                  ),
                                                  const SizedBox(width: 6),
                                                  Text(
                                                    _getPreviewButtonText(),
                                                    style: TextStyle(
                                                      color: _isPreviewPlaying ? Colors.orange : Colors.blue.shade700,
                                                      fontSize: 14,
                                                      fontWeight: FontWeight.w500,
                                                    ),
                                                  ),
                                                ],
                                              ),
                                            ),
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      // 重新录音按钮
                                      Container(
                                        height: 48,
                                        width: 100,
                                        decoration: BoxDecoration(
                                          color: Colors.grey.shade100,
                                          borderRadius: BorderRadius.circular(8),
                                          border: Border.all(color: Colors.grey.shade300),
                                        ),
                                        child: InkWell(
                                          onTap: _cancelRecording,
                                          borderRadius: BorderRadius.circular(8),
                                          child: Center(
                                            child: Row(
                                              mainAxisAlignment: MainAxisAlignment.center,
                                              children: [
                                                Icon(Icons.refresh, size: 18, color: Colors.grey.shade600),
                                                SizedBox(width: 4),
                                                Text(
                                                  '重录',
                                                  style: TextStyle(
                                                    color: Colors.grey.shade600,
                                                    fontSize: 14,
                                                    fontWeight: FontWeight.w500,
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ),
                                        ),
                                      ),
                                    ],
                                  )
                            : // 文本模式：文本输入框
                            Container(
                              height: 48,
                              child: TextField(
                                controller: _textController,
                                focusNode: _focusNode,
                                autofocus: false,
                                decoration: const InputDecoration(
                                  hintText: '输入消息...',
                                  border: OutlineInputBorder(),
                                  contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                                ),
                                maxLines: 1,
                                minLines: 1,
                                textInputAction: TextInputAction.send,
                                onSubmitted: (_) => _sendMessage(),
                              ),
                            ),
                      ),

                      const SizedBox(width: 8),

                      // 发送按钮
                      IconButton(
                        icon: const Icon(Icons.send),
                        onPressed: _isVoiceMode && _recordedAudioPath != null
                            ? _sendVoiceMessage
                            : _sendMessage,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
      ),
    );
  }

  String _formatTime(DateTime time) {
    return '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
  }

  String _getPreviewButtonText() {
    if (_isPreviewPlaying) {
      // 计算剩余时间
      final remainingSeconds = _recordingSeconds - _previewPosition;
      final minutes = remainingSeconds ~/ 60;
      final seconds = remainingSeconds % 60;
      final remainingTime = '$minutes:${seconds.toString().padLeft(2, '0')}';
      return '剩余 $remainingTime';
    } else {
      return '预览 $_recordingTime';
    }
  }

  @override
  void dispose() {
    _connectionSubscription?.cancel();
    _textController.dispose();
    _scrollController.dispose();
    _focusNode.dispose(); // 释放FocusNode
    _hideStatusSnackBar(); // 关闭状态弹窗
    _wsService?.dispose();
    _audioService?.dispose();
    _recordingTimer?.cancel();
    _previewTimer?.cancel();

    // 清理所有消息音频计时器
    for (var timer in _messageAudioTimers.values) {
      timer?.cancel();
    }

    super.dispose();
  }
}
