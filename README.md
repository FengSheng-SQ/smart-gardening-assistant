# 🌱 智能种植助手 (Smart Gardening Assistant)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flutter](https://img.shields.io/badge/Flutter-3.0+-blue.svg)](https://flutter.dev)

一个基于AI的智能园艺助手应用，通过语音和图像识别技术，为用户提供专业的种植建议和园艺指导。

## ✨ 核心特性

### 🤖 AI智能对话
- **多模式聊天系统**
  - **快速模式**: 即时响应，轻量级对话
  - **思考模式**: 结合历史对话，理解上下文
  - **专家模式**: 多Agent协作，综合分析环境信息

### 🎙️ 语音交互
- **语音识别**: 支持多种ASR模型
- **语音合成**: 支持多种TTS模型
- **实时语音对话**: WebSocket实时通信，流畅对话体验

### 📸 图像识别
- **植物分析**: 支持多种视觉大模型
- **拍照识别**: 拍摄植物照片获取诊断建议
- **图片+语音**: 组合交互方式

### 🌍 环境感知
- **GPS定位**: 自动获取用户位置
- **天气查询**: 实时天气信息查询
- **时间感知**: 季节、日期等时间信息

### 💾 数据管理
- **用户认证**: 用户注册、登录系统
- **聊天历史**: 完整的对话历史记录
- **SQLite存储**: 本地数据库存储

### 📅 种植日历
- **月视图展示**: 直观的月历界面
- **照片记录**: 自动保存拍照识别的植物照片
- **日期标记**: 有照片记录的日期显示标记点
- **成长追踪**: 记录植物生长的全过程

## 🏗️ 系统架构

```
智能种植助手
├── server/              # Python后端服务
│   ├── app/
│   │   ├── api/        # API路由
│   │   │   ├── health.py       # 健康检查
│   │   │   └── v1/             # API v1
│   │   │       ├── auth.py     # 用户认证
│   │   │       ├── chat.py     # 聊天记录
│   │   │       └── websocket.py # WebSocket连接
│   │   ├── core/       # 核心配置
│   │   │   ├── config.py        # 配置管理
│   │   │   └── database.py      # 数据库配置
│   │   ├── models/     # 数据模型
│   │   │   └── schemas.py       # Pydantic模型
│   │   └── services/   # 业务逻辑
│   │       ├── agents/         # Agent系统
│   │       │   ├── base_agent.py       # Agent基类
│   │       │   ├── coordinator.py      # 协调器
│   │       │   ├── location_agent.py   # 位置服务
│   │       │   ├── weather_agent.py    # 天气服务
│   │       │   ├── time_agent.py       # 时间服务
│   │       │   └── planting_agent.py   # 种植建议
│   │       ├── chat_modes/    # 聊天模式
│   │       │   ├── base_mode.py      # 模式基类
│   │       │   ├── fast_mode.py      # 快速模式
│   │       │   ├── thinking_mode.py  # 思考模式
│   │       │   └── expert_mode.py    # 专家模式
│   │       ├── tools/         # 工具集
│   │       │   ├── location.py       # 位置工具
│   │       │   ├── weather.py        # 天气工具
│   │       │   └── date_time.py      # 时间工具
│   │       ├── mcp/           # MCP服务
│   │       │   ├── mcp_host.py        # MCP主机
│   │       │   └── weather_server.py  # 天气服务器
│   │       ├── asr_service.py        # 语音识别
│   │       ├── tts_service.py        # 语音合成
│   │       └── llm_service.py        # LLM服务
│   ├── data/           # 数据存储
│   └── requirements.txt
│
└── frontend/           # Flutter移动应用
    ├── lib/
    │   ├── main.dart             # 应用入口
    │   ├── models/               # 数据模型
    │   │   ├── config.dart       # 配置模型
    │   │   └── chat_state.dart   # 聊天状态
    │   ├── screens/              # 页面
    │   │   ├── home_screen.dart     # 主页面
    │   │   └── calendar_screen.dart # 日历页面
    │   ├── services/             # 服务层
    │   │   ├── api_service.dart        # API服务
    │   │   ├── audio_service.dart      # 音频服务
    │   │   ├── location_service.dart   # 定位服务
    │   │   └── websocket_service.dart  # WebSocket服务
    │   └── widgets/              # 组件
    │       └── chat_mode_selector.dart # 模式选择器
    ├── assets/.env        # 环境配置
    └── pubspec.yaml
```

### Agent系统架构

**ExpertCoordinator** - 协调多个Agent协作
- **LocationAgent**: 基于IP地址获取用户位置信息（城市、经纬度）
- **WeatherAgent**: 根据位置获取实时天气信息（支持MCP服务器和直接API两种方式）
- **TimeAgent**: 获取当前时间、季节等时间信息
- **PlantingAgent**: 综合所有信息生成专业的种植建议

**工作流程**:
1. 并行执行LocationAgent、TimeAgent获取基础信息
2. 基于位置信息执行WeatherAgent获取天气
3. 汇总所有上下文（位置、天气、时间、聊天历史）
4. 调用PlantingAgent生成最终建议

## 🚀 快速开始

### 环境要求

**后端服务器**:
- Python 3.11+
- CUDA (可选，用于GPU加速)

**移动端**:
- Flutter SDK 3.0+
- Android SDK / iOS SDK

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/FengSheng-SQ/smart-gardening-assistant.git
cd smart-gardening-assistant
```

#### 2. 配置后端服务器

```bash
cd server

# 创建Conda环境
conda create -n gardening-assistant python=3.11
conda activate gardening-assistant

# 安装Python依赖
pip install -r requirements.txt

# 复制环境配置文件
cp .env.example .env

# 编辑.env文件，配置必要的API密钥和Token
```

#### 3. 启动后端服务

```bash
python run.py
```

服务器将在 `http://localhost:8000` 启动

#### 4. 配置并运行移动应用

```bash
cd frontend

# 安装Flutter依赖
flutter pub get

# 配置 assets/.env 文件，设置服务器地址和Token

# 连接设备后运行（开发者模式）
flutter run

# 打包 Android APK
flutter build apk --release
```

详细配置说明请查看:
- [后端配置文档](server/README.md)
- [前端配置文档](frontend/README.md)

## 🔧 技术栈

**后端**:
- FastAPI + Uvicorn (Web框架)
- SQLite3 (数据库)
- 支持多种ASR/TTS模型
- 支持多种LLM和视觉模型API

**前端**:
- Flutter 3.0+
- Provider (状态管理)
- WebSocket实时通信
- 支持Android/iOS双平台

## 🎯 使用场景

- **园艺新手学习**: 通过语音对话获取种植知识
- **植物病害诊断**: 拍照识别植物病虫害
- **种植计划制定**: 根据位置、天气、季节获取建议
- **日常养护指导**: 获取浇水、施肥等养护建议
- **品种选择推荐**: 根据环境选择合适植物

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤:

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交Pull Request

## 👥 作者

- **FengSheng-SQ** - [GitHub](https://github.com/FengSheng-SQ)

## 📮 联系方式

如有问题或建议，请提交 [Issue](https://github.com/FengSheng-SQ/smart-gardening-assistant/issues)

## 🙏 致谢

- [智谱AI](https://open.bigmodel.cn/) - 提供GLM系列模型
- [FunASR](https://github.com/alibaba-damo-academy/FunASR) - 语音识别
- [Coqui TTS](https://github.com/coqui-ai/TTS) - 语音合成
- [FastAPI](https://fastapi.tiangolo.com/) - Web框架
- [Flutter](https://flutter.dev/) - 移动应用框架

---

⭐ 如果这个项目对你有帮助，请给个Star！
