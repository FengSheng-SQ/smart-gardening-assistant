import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


# 统一模型目录
# 可通过环境变量 MODELS_DIR 自定义，默认使用项目目录下的 models 文件夹
import os
MODELS_BASE_DIR = Path(os.getenv('MODELS_DIR', os.path.join(os.path.dirname(__file__), '../../../models')))


class Settings(BaseSettings):
    # LLM API - 文本对话模型
    LLM_API_KEY: str
    LLM_API_URL: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    LLM_MODEL: str = "glm-4-plus"  # 文本对话模型：glm-4-plus, glm-4-0520, glm-4-air

    # LLM Vision API - 视觉模型（分析植株照片）
    LLM_VISION_MODEL: str = "glm-4v"  # 视觉模型：glm-4v, glm-4v-plus

    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # 模型存储目录（统一管理）
    MODELS_DIR: Path = MODELS_BASE_DIR

    # FunASR
    FUNASR_DEVICE: str = "cuda"
    FUNASR_MODEL: str = "paraformer-zh"
    FUNASR_MODEL_DIR: Path = MODELS_BASE_DIR / "funasr"

    # TTS - Coqui TTS（离线本地，推荐）
    USE_COQUI_TTS: bool = False  # 是否使用Coqui TTS
    COQUI_MODEL_NAME: str = "tts_models/zh-CN/baker/glow-tts"  # 中文模型（轻量Glow-TTS）
    COQUI_USE_GPU: bool = True  # 是否使用GPU加速
    COQUI_MODEL_DIR: Path = MODELS_BASE_DIR / "tts"  # TTS模型目录

    # 聊天模式配置
    DEFAULT_CHAT_MODE: str = "fast"  # 默认聊天模式: fast/thinking/expert
    CHAT_HISTORY_LIMIT: int = 20  # 聊天历史记录数量（思考模式和专家模式共用，建议范围：10-50）

    # 专家模式配置
    EXPERT_MODE_ENABLED: bool = True  # 是否启用专家模式
    DEFAULT_CITY: str = "北京"  # 默认城市（用于IP定位失败时）
    DEFAULT_LAT: float = 39.9042  # 默认纬度
    DEFAULT_LON: float = 116.4074  # 默认经度

    # 天气API配置
    WEATHER_USE_MCP: bool = False  # 是否使用MCP方式获取天气（false=直接API，true=通过MCP）
    WEATHER_MCP_COMMAND: str = "python -m app.services.mcp.weather_server"  # MCP服务器启动命令

    # WebSocket安全
    WS_TOKEN: str = "change-me-in-production"

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保模型目录存在
        self.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        self.FUNASR_MODEL_DIR.mkdir(parents=True, exist_ok=True)
        self.COQUI_MODEL_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
