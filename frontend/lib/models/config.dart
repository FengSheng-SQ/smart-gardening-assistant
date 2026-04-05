import 'package:flutter_dotenv/flutter_dotenv.dart';

class AppConfig {
  static Future<void> load() async {
    await dotenv.load(fileName: "assets/.env");
  }

  /// HTTP服务器地址（用于REST API）
  static String get httpServerUrl => dotenv.env['SERVER_HTTP_URL'] ?? 'http://localhost:8000';

  /// WebSocket服务器地址（用于WebSocket通信）
  static String get wsServerUrl => dotenv.env['SERVER_WS_URL'] ?? 'ws://localhost:8000/v1/ws';

  /// 客户端ID
  static String get clientId => dotenv.env['CLIENT_ID'] ?? 'flutter_app';

  /// WebSocket Token
  static String get wsToken => dotenv.env['WS_TOKEN'] ?? 'change-me-in-production';

  /// 构建带Token的WebSocket URL
  static String buildWebSocketUrl({int? userId}) {
    final baseUrl = wsServerUrl;
    final cid = clientId;
    final token = wsToken;

    // 如果提供了user_id，添加到URL参数
    if (userId != null) {
      return '$baseUrl/$cid?token=$token&user_id=$userId';
    }
    return '$baseUrl/$cid?token=$token';
  }
}
