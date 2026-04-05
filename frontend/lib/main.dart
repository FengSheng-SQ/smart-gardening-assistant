import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'models/chat_state.dart';
import 'models/config.dart';
import 'screens/home_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AppConfig.load();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => ChatState(),
      child: MaterialApp(
        title: '智能种植助手',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          primaryColor: const Color(0xFF077D20), // 直接设置主色调为 #077d20
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF077D20),
            brightness: Brightness.light,
          ).copyWith(
            primary: const Color(0xFF077D20), // 确保 primary 使用这个颜色
          ),
          useMaterial3: true,
        ),
        darkTheme: ThemeData(
          primaryColor: const Color(0xFF077D20),
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF077D20),
            brightness: Brightness.dark,
          ).copyWith(
            primary: const Color(0xFF077D20),
          ),
          useMaterial3: true,
        ),
        themeMode: ThemeMode.system,
        home: const HomeScreen(),
      ),
    );
  }
}
