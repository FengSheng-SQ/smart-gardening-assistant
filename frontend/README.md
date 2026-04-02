# 🌱 智能种植助手 - 移动应用

基于 Flutter 开发的智能园艺助手移动应用，提供语音对话、图像识别、种植建议等功能。

## ✨ 核心功能

- **🤖 AI智能对话**: 三种聊天模式切换
- **🎙️ 语音输入**: 实时语音录制和识别
- **🔊 语音播报**: TTS语音播放
- **📸 拍照识别**: 植物照片拍摄和分析
- **📅 种植日历**: 植物成长记录与追踪
- **📍 位置服务**: GPS定位和地理编码
- **💬 聊天历史**: 完整的对话记录

## 🏗️ 系统架构

```
frontend/
├── lib/
│   ├── main.dart                # 应用入口
│   ├── models/                  # 数据模型
│   ├── screens/                 # 页面
│   ├── services/                # 服务层
│   └── widgets/                 # 组件
├── assets/.env              # 环境配置
├── android/                 # Android平台代码
├── ios/                     # iOS平台代码
└── pubspec.yaml             # 项目配置
```

## 💻 环境要求

- **Flutter SDK**: 3.0.0 或更高版本
- **Dart SDK**: 3.0.0 或更高版本
- **Android**: minSdkVersion 21 (Android 5.0)
- **iOS**: 12.0 或更高版本

## 🚀 快速开始

### 1. 安装Flutter

访问 [Flutter官网](https://flutter.dev/docs/get-started/install) 下载并安装。

验证安装:
```bash
flutter doctor
```

### 2. 克隆项目

```bash
git clone https://github.com/FengSheng-SQ/smart-gardening-assistant.git
cd smart-gardening-assistant/frontend
```

### 3. 安装依赖

```bash
flutter pub get
```

### 4. 配置环境变量

创建或编辑 `assets/.env` 文件:

```bash
# HTTP服务器地址（用于REST API）
SERVER_HTTP_URL=http://YOUR_SERVER_IP:8000

# WebSocket服务器地址（用于WebSocket通信）
SERVER_WS_URL=ws://YOUR_SERVER_IP:8000/v1/ws

# 客户端标识符
CLIENT_ID=flutter_app

# WebSocket安全Token（需与服务器一致）
WS_TOKEN=your-secret-token
```

### 5. 运行应用

```bash
# 查看可用设备
flutter devices

# 运行应用
flutter run

# Release模式运行
flutter run --release
```

### 6. 构建应用

```bash
# Android APK
flutter build apk --release

# iOS IPA (需要macOS)
flutter build ios --release
```

## ⚙️ 配置说明

### 必需权限

**Android** (`android/app/src/main/AndroidManifest.xml`):
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
```

**iOS** (`ios/Runner/Info.plist`):
```xml
<key>NSMicrophoneUsageDescription</key>
<string>需要使用麦克风进行语音对话</string>
<key>NSCameraUsageDescription</key>
<string>需要使用相机拍照识别植物</string>
<key>NSLocationWhenInUseUsageDescription</key>
<string>需要获取位置信息提供本地化建议</string>
```

## 🔧 技术栈

- **Flutter 3.0+**: 移动应用框架
- **Provider**: 状态管理
- **WebSocket**: 实时通信
- **record**: 音频录制
- **audioplayers**: 音频播放
- **image_picker**: 图片选择
- **geolocator**: 位置服务

## 📄 许可证

MIT License - 详见 [LICENSE](../LICENSE)

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📮 联系方式

- **GitHub Issues**: [提交问题](https://github.com/FengSheng-SQ/smart-gardening-assistant/issues)
- **作者**: [FengSheng-SQ](https://github.com/FengSheng-SQ)
