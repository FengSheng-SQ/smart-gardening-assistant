import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import '../models/config.dart';


/// API配置
class ApiConfig {
  static String get baseUrl => AppConfig.httpServerUrl;
  static const String apiVersion = '/v1';
}

/// 用户登录响应
class LoginResponse {
  final bool success;
  final String message;
  final int? userId;
  final String? username;
  final String? token;

  LoginResponse({
    required this.success,
    required this.message,
    this.userId,
    this.username,
    this.token,
  });

  factory LoginResponse.fromJson(Map<String, dynamic> json) {
    return LoginResponse(
      success: json['success'] ?? false,
      message: json['message'] ?? '',
      userId: json['user_id'],
      username: json['username'],
      token: json['token'],
    );
  }
}

/// 聊天消息
class ChatMessageApi {
  final String id; // 改为String类型，匹配schemas.py中的定义
  final String messageText;
  final bool isUser;
  final String? audioFilename;
  final String? imageFilename;
  final DateTime createdAt;

  ChatMessageApi({
    required this.id,
    required this.messageText,
    required this.isUser,
    this.audioFilename,
    this.imageFilename,
    required this.createdAt,
  });

  factory ChatMessageApi.fromJson(Map<String, dynamic> json) {
    return ChatMessageApi(
      id: json['id'].toString(), // 确保转换为String
      messageText: json['message_text'] ?? '',
      isUser: json['is_user'] == 1 || json['is_user'] == true,
      audioFilename: json['audio_filename'],
      imageFilename: json['image_filename'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

/// 聊天历史响应
class ChatHistoryResponse {
  final bool success;
  final List<ChatMessageApi> messages;

  ChatHistoryResponse({
    required this.success,
    required this.messages,
  });

  factory ChatHistoryResponse.fromJson(Map<String, dynamic> json) {
    var messagesList = <ChatMessageApi>[];
    if (json['messages'] != null) {
      messagesList = (json['messages'] as List)
          .map((msg) => ChatMessageApi.fromJson(msg))
          .toList();
    }
    return ChatHistoryResponse(
      success: json['success'] ?? false,
      messages: messagesList,
    );
  }
}

/// API服务
class ApiService {
  final String baseUrl = ApiConfig.baseUrl;

  /// 用户登录
  Future<LoginResponse> login(String username, String password) async {
    try {
      final url = '$baseUrl${ApiConfig.apiVersion}/auth/login';
      print('🔐 登录API: $url');
      print('🔐 用户名: $username');

      final response = await http.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': username,
          'password': password,
        }),
      );

      print('🔐 响应状态: ${response.statusCode}');
      print('🔐 响应内容: ${response.body}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return LoginResponse.fromJson(data);
      } else {
        return LoginResponse(
          success: false,
          message: '登录失败: ${response.statusCode}',
        );
      }
    } catch (e) {
      print('❌ 登录异常: $e');
      return LoginResponse(
        success: false,
        message: '网络错误: $e',
      );
    }
  }

  /// 用户注册
  Future<LoginResponse> register(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl${ApiConfig.apiVersion}/auth/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': username,
          'password': password,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return LoginResponse(
          success: data['success'] ?? false,
          message: data['message'] ?? '',
          userId: data['user_id'],
        );
      } else {
        return LoginResponse(
          success: false,
          message: '注册失败: ${response.statusCode}',
        );
      }
    } catch (e) {
      return LoginResponse(
        success: false,
        message: '网络错误: $e',
      );
    }
  }

  /// 获取聊天历史
  Future<ChatHistoryResponse> getChatHistory(int userId, {int limit = 500}) async {
    try {
      final url = '$baseUrl${ApiConfig.apiVersion}/chat/history?user_id=$userId&limit=$limit';
      print('📜 获取聊天历史: $url');

      final response = await http.get(
        Uri.parse(url),
      );

      print('📜 响应状态: ${response.statusCode}');
      print('📜 响应内容: ${response.body}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return ChatHistoryResponse.fromJson(data);
      } else {
        print('❌ 获取聊天历史失败，状态码: ${response.statusCode}');
        return ChatHistoryResponse(success: false, messages: []);
      }
    } catch (e) {
      print('❌ 获取聊天历史异常: $e');
      return ChatHistoryResponse(success: false, messages: []);
    }
  }

  /// 清空聊天历史
  Future<bool> clearChatHistory(int userId) async {
    try {
      final response = await http.delete(
        Uri.parse(
          '$baseUrl${ApiConfig.apiVersion}/chat/clear?user_id=$userId',
        ),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['success'] ?? false;
      }
      return false;
    } catch (e) {
      print('清空聊天历史失败: $e');
      return false;
    }
  }

  /// 删除单条聊天消息
  Future<bool> deleteChatMessage(int messageId, int userId) async {
    try {
      final url = '$baseUrl${ApiConfig.apiVersion}/chat/message/$messageId?user_id=$userId';
      print('🗑️  删除消息: $url');

      final response = await http.delete(
        Uri.parse(url),
      );

      print('🗑️ 响应状态: ${response.statusCode}');
      print('🗑️ 响应内容: ${response.body}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['success'] ?? false;
      }
      return false;
    } catch (e) {
      print('❌ 删除消息失败: $e');
      return false;
    }
  }

  /// 批量删除聊天消息
  Future<bool> deleteChatMessages(List<int> messageIds, int userId) async {
    try {
      final idsStr = messageIds.join(',');
      final url = '$baseUrl${ApiConfig.apiVersion}/chat/messages?user_id=$userId&message_ids=$idsStr';
      print('🗑️ 批量删除消息: $url');

      final response = await http.delete(
        Uri.parse(url),
      );

      print('🗑️ 响应状态: ${response.statusCode}');
      print('🗑️ 响应内容: ${response.body}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['success'] ?? false;
      }
      return false;
    } catch (e) {
      print('❌ 批量删除消息失败: $e');
      return false;
    }
  }

  /// 下载文件（图片或音频）
  Future<Uint8List?> downloadFile(String filename) async {
    try {
      // 根据文件扩展名确定子目录
      final extension = filename.split('.').last.toLowerCase();
      String subdir = '';
      if (extension == 'wav' || extension == 'mp3') {
        subdir = 'audio/';
      } else if (extension == 'jpg' || extension == 'jpeg' || extension == 'png') {
        subdir = 'images/';
      }

      final url = '$baseUrl/data/$subdir$filename';
      print('📥 下载文件: $url');

      final response = await http.get(
        Uri.parse(url),
      );

      print('📥 响应状态: ${response.statusCode}');

      if (response.statusCode == 200) {
        print('✅ 文件下载成功: ${response.bodyBytes.length} bytes');
        return Uint8List.fromList(response.bodyBytes);
      } else {
        print('❌ 下载失败: ${response.statusCode}');
        return null;
      }
    } catch (e) {
      print('❌ 下载异常: $e');
      return null;
    }
  }
}
