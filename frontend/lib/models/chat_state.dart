import 'package:flutter/foundation.dart';

enum ChatMode { fast, thinking, expert }
enum MessageRole { user, assistant }

class ChatMessage {
  final String id;
  final MessageRole role;
  final String content;
  final String? imagePath;
  final DateTime timestamp;
  final String? audioUrl;
  final ChatMode mode;
  final String? error;

  ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    this.imagePath,
    required this.timestamp,
    this.audioUrl,
    required this.mode,
    this.error,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'role': role.name,
      'content': content,
      'image_path': imagePath,
      'timestamp': timestamp.toIso8601String(),
      'audio_url': audioUrl,
      'mode': mode.name,
      'error': error,
    };
  }

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'] as String,
      role: MessageRole.values.firstWhere(
        (e) => e.name == json['role'],
        orElse: () => MessageRole.user,
      ),
      content: json['content'] as String? ?? '',
      imagePath: json['image_path'] as String?,
      timestamp: DateTime.parse(json['timestamp'] as String),
      audioUrl: json['audio_url'] as String?,
      mode: ChatMode.values.firstWhere(
        (e) => e.name == json['mode'],
        orElse: () => ChatMode.fast,
      ),
      error: json['error'] as String?,
    );
  }

  ChatMessage copyWith({
    String? id,
    MessageRole? role,
    String? content,
    String? imagePath,
    DateTime? timestamp,
    String? audioUrl,
    ChatMode? mode,
    String? error,
  }) {
    return ChatMessage(
      id: id ?? this.id,
      role: role ?? this.role,
      content: content ?? this.content,
      imagePath: imagePath ?? this.imagePath,
      timestamp: timestamp ?? this.timestamp,
      audioUrl: audioUrl ?? this.audioUrl,
      mode: mode ?? this.mode,
      error: error ?? this.error,
    );
  }
}

class ChatState extends ChangeNotifier {
  final List<ChatMessage> _messages = [];
  ChatMode _currentMode = ChatMode.fast;
  bool _isLoading = false;
  String? _errorMessage;

  // 用户认证信息
  String _username = '';
  String _token = '';
  int? _userId;
  bool _isLoggedIn = false;

  // 选择模式
  bool _isSelectionMode = false;
  final Set<String> _selectedMessageIds = {};

  List<ChatMessage> get messages => List.unmodifiable(_messages);
  ChatMode get currentMode => _currentMode;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  // 用户信息getters
  String get username => _username;
  String get token => _token;
  int? get userId => _userId;
  bool get isLoggedIn => _isLoggedIn;

  // 选择模式getters
  bool get isSelectionMode => _isSelectionMode;
  Set<String> get selectedMessageIds => Set.unmodifiable(_selectedMessageIds);
  int get selectedCount => _selectedMessageIds.length;
  bool get isAllSelected => _messages.isNotEmpty && _selectedMessageIds.length == _messages.length;

  void addMessage(ChatMessage message) {
    _messages.add(message);
    notifyListeners();
  }

  void clearMessages() {
    _messages.clear();
    notifyListeners();
  }

  void removeMessage(String messageId) {
    _messages.removeWhere((msg) => msg.id == messageId);
    notifyListeners();
  }

  void setMode(ChatMode mode) {
    _currentMode = mode;
    notifyListeners();
  }

  void setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  void setError(String? error) {
    _errorMessage = error;
    notifyListeners();
  }

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }

  // 用户认证方法
  void login(String username, {required String token, int? userId}) {
    _username = username;
    _token = token;
    _userId = userId;
    _isLoggedIn = true;
    notifyListeners();
  }

  void logout() {
    _username = '';
    _token = '';
    _userId = null;
    _isLoggedIn = false;
    _messages.clear();
    notifyListeners();
  }

  void updateUserId(int userId) {
    _userId = userId;
    notifyListeners();
  }

  // 选择模式方法
  void enterSelectionMode() {
    _isSelectionMode = true;
    _selectedMessageIds.clear();
    notifyListeners();
  }

  void exitSelectionMode() {
    _isSelectionMode = false;
    _selectedMessageIds.clear();
    notifyListeners();
  }

  void toggleMessageSelection(String messageId) {
    if (_selectedMessageIds.contains(messageId)) {
      _selectedMessageIds.remove(messageId);
    } else {
      _selectedMessageIds.add(messageId);
    }
    notifyListeners();
  }

  void selectAllMessages() {
    _selectedMessageIds.clear();
    for (var message in _messages) {
      _selectedMessageIds.add(message.id);
    }
    notifyListeners();
  }

  void deselectAllMessages() {
    _selectedMessageIds.clear();
    notifyListeners();
  }

  void removeSelectedMessages() {
    _messages.removeWhere((msg) => _selectedMessageIds.contains(msg.id));
    _selectedMessageIds.clear();
    _isSelectionMode = false;
    notifyListeners();
  }
}
