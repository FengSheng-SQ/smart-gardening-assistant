import 'package:shared_preferences/shared_preferences.dart';

/// 认证服务 - 管理用户登录状态缓存
class AuthService {
  static const String _keyUsername = 'auth_username';
  static const String _keyToken = 'auth_token';
  static const String _keyUserId = 'auth_user_id';
  static const String _keyIsLoggedIn = 'auth_is_logged_in';

  /// 保存登录信息
  static Future<void> saveLoginInfo({
    required String username,
    required String token,
    required int userId,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyUsername, username);
    await prefs.setString(_keyToken, token);
    await prefs.setInt(_keyUserId, userId);
    await prefs.setBool(_keyIsLoggedIn, true);
    print('💾 登录信息已保存: username=$username, userId=$userId');
  }

  /// 加载登录信息
  static Future<Map<String, dynamic>?> loadLoginInfo() async {
    final prefs = await SharedPreferences.getInstance();
    final isLoggedIn = prefs.getBool(_keyIsLoggedIn) ?? false;

    if (!isLoggedIn) {
      print('📂 未找到已保存的登录信息');
      return null;
    }

    final username = prefs.getString(_keyUsername);
    final token = prefs.getString(_keyToken);
    final userId = prefs.getInt(_keyUserId);

    if (username == null || token == null || userId == null) {
      print('⚠️  登录信息不完整，清除缓存');
      await clearLoginInfo();
      return null;
    }

    print('📂 已加载登录信息: username=$username, userId=$userId');
    return {
      'username': username,
      'token': token,
      'userId': userId,
    };
  }

  /// 清除登录信息
  static Future<void> clearLoginInfo() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_keyUsername);
    await prefs.remove(_keyToken);
    await prefs.remove(_keyUserId);
    await prefs.remove(_keyIsLoggedIn);
    print('🗑️  登录信息已清除');
  }

  /// 更新Token（用于刷新token）
  static Future<void> updateToken(String newToken) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyToken, newToken);
    print('🔄 Token已更新');
  }

  /// 检查是否已登录
  static Future<bool> isLoggedIn() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_keyIsLoggedIn) ?? false;
  }

  /// 获取当前用户名
  static Future<String?> getUsername() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyUsername);
  }

  /// 获取当前Token
  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyToken);
  }

  /// 获取当前用户ID
  static Future<int?> getUserId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(_keyUserId);
  }
}
