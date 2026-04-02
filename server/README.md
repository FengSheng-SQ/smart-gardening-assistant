# 🌱 智能种植助手 - 后端服务器

基于 FastAPI 的智能园艺助手后端服务，提供语音识别、语音合成、AI对话、图像识别等功能。

## ✨ 核心功能

- **🤖 多模式AI对话**: 快速/思考/专家三种模式
- **🎙️ 语音识别**: 支持多种ASR模型
- **🔊 语音合成**: 支持多种TTS模型
- **👁️ 图像识别**: 支持多种视觉大模型
- **🌍 环境感知**: 位置/天气/时间等信息获取
- **👤 用户认证**: 用户注册、登录、权限管理
- **💾 数据持久化**: SQLite存储聊天历史

## 🏗️ 系统架构

```
server/
├── app/
│   ├── api/                    # API路由层
│   │   ├── health.py          # 健康检查
│   │   └── v1/                # API v1版本
│   │       ├── auth.py       # 用户认证
│   │       ├── chat.py       # 聊天记录
│   │       └── websocket.py  # WebSocket连接
│   ├── core/                   # 核心配置
│   │   ├── config.py          # 配置管理
│   │   └── database.py        # 数据库配置
│   ├── models/                 # 数据模型
│   │   └── schemas.py         # Pydantic模型
│   └── services/               # 业务逻辑层
│       ├── agents/            # Agent系统
│       │   ├── coordinator.py      # 协调器
│       │   ├── location_agent.py   # 位置服务
│       │   ├── weather_agent.py    # 天气服务
│       │   ├── time_agent.py       # 时间服务
│       │   └── planting_agent.py   # 种植建议
│       ├── chat_modes/        # 聊天模式
│       │   ├── fast_mode.py      # 快速模式
│       │   ├── thinking_mode.py  # 思考模式
│       │   └── expert_mode.py    # 专家模式
│       ├── tools/             # 工具集
│       ├── mcp/               # MCP服务
│       ├── asr_service.py     # 语音识别
│       ├── tts_service.py     # 语音合成
│       └── llm_service.py     # LLM服务
├── data/                      # 数据存储目录
├── run.py                     # 应用启动入口
├── requirements.txt           # Python依赖
├── environment.yml            # Conda环境配置
└── .env.example              # 环境变量示例
```

### Agent系统架构

**ExpertCoordinator** - 协调多个Agent协作
- **LocationAgent**: 基于IP地址获取用户位置信息
- **WeatherAgent**: 根据位置获取实时天气信息（支持MCP服务器和直接API两种方式）
- **TimeAgent**: 获取当前时间、季节等时间信息
- **PlantingAgent**: 综合所有信息生成专业的种植建议

## 💻 环境要求

- **Python**: 3.11+
- **操作系统**: Windows / Linux / macOS
- **内存**: 8GB+ 推荐
- **CUDA**: 11.0+ (可选，用于GPU加速)

## 🚀 快速开始

### 1. 安装依赖

```bash
# 使用 pip
pip install -r requirements.txt

# 或使用 Conda (推荐)
conda env create -f environment.yml
conda activate gardening_assistant
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，填写必要配置
```

**必需配置**:
- `LLM_API_KEY`: 大语言模型API密钥
- `WS_TOKEN`: WebSocket安全Token

### 3. 启动服务

```bash
python run.py
```

服务启动后:
- API服务: http://localhost:8000
- API文档: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/v1/ws

## ⚙️ 配置说明

### 核心配置项 (.env)

```bash
# LLM API配置 (必需)
LLM_API_KEY=your_api_key_here
LLM_API_URL=https://api.example.com/v1/chat/completions
LLM_MODEL=your_text_model
LLM_VISION_MODEL=your_vision_model

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# WebSocket安全
WS_TOKEN=your-secret-token-change-me-in-production

# 聊天模式
DEFAULT_CHAT_MODE=fast  # fast | thinking | expert
CHAT_HISTORY_LIMIT=20

# 专家模式
EXPERT_MODE_ENABLED=true
DEFAULT_CITY=北京
DEFAULT_LAT=39.9042
DEFAULT_LON=116.4074

# 天气服务
WEATHER_USE_MCP=false  # false=直接API, true=MCP服务器

# 模型配置 (可选)
FUNASR_DEVICE=cuda  # cuda 或 cpu
USE_COQUI_TTS=true
```

**支持的LLM API**:
- 智谱AI: https://open.bigmodel.cn/
- 通义千问: https://tongyi.aliyun.com/
- 文心一言: https://cloud.baidu.com/product/wenxinworkshop
- OpenAI: https://openai.com/

## 🔧 API端点

### REST API
- `GET /health` - 健康检查
- `POST /v1/auth/register` - 用户注册
- `POST /v1/auth/login` - 用户登录
- `GET /v1/chat/history` - 获取聊天历史
- `DELETE /v1/chat/clear` - 清空聊天历史
- `DELETE /v1/chat/message/{id}` - 删除单条消息

### WebSocket
```
ws://localhost:8000/v1/ws/{client_id}?token={token}&user_id={user_id}
```

详细API文档请启动服务后访问: http://localhost:8000/docs

## 📄 许可证

MIT License - 详见 [LICENSE](../LICENSE)

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📮 联系方式

- **GitHub Issues**: [提交问题](https://github.com/FengSheng-SQ/smart-gardening-assistant/issues)
- **作者**: [FengSheng-SQ](https://github.com/FengSheng-SQ)
