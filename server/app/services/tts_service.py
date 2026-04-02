import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# 尝试导入 Coqui TTS
try:
    from app.services.coqui_tts_service import getCoquiTts
    COQUI_TTS_AVAILABLE = True
except ImportError:
    COQUI_TTS_AVAILABLE = False
    logger.warning("⚠️ Coqui TTS未安装，语音合成功能不可用")


class TTSService:
    """
    TTS服务包装器
    使用 Coqui TTS 进行语音合成
    """
    _instance: "TTSService" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._coqui_tts = None

    async def synthesize(self, text: str, output_path: str) -> str:
        """
        将文本转换为语音

        Args:
            text: 要转换的文本
            output_path: 输出音频文件路径

        Returns:
            音频文件路径

        Raises:
            RuntimeError: 如果TTS不可用
        """
        if not COQUI_TTS_AVAILABLE:
            raise RuntimeError("TTS功能不可用，请安装 Coqui TTS: pip install TTS")

        # 获取或初始化 Coqui TTS
        if self._coqui_tts is None:
            self._coqui_tts = getCoquiTts()
            if self._coqui_tts is None or not self._coqui_tts.is_available:
                raise RuntimeError("Coqui TTS初始化失败，请检查配置")

        logger.info(f"📢 TTS合成: {text[:50]}...")
        return self._coqui_tts.synthesize(text, output_path)

    @property
    def is_available(self) -> bool:
        """检查TTS是否可用"""
        return COQUI_TTS_AVAILABLE and self._coqui_tts is not None


tts_service = TTSService()
