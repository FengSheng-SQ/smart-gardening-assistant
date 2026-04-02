import asyncio
import os
from typing import Optional
from funasr import AutoModel
from app.core.config import settings


class ASRService:
    _instance: Optional["ASRService"] = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self):
        """初始化FunASR模型"""
        if self._model is None:
            await asyncio.to_thread(
                self._load_model
            )

    def _load_model(self):
        """加载FunASR模型"""
        # 设置模型缓存目录到统一位置
        os.environ["MODELSCOPE_CACHE"] = str(settings.FUNASR_MODEL_DIR)

        self._model = AutoModel(
            model=settings.FUNASR_MODEL,
            device=settings.FUNASR_DEVICE,
        )

    async def transcribe(self, audio_path: str) -> str:
        """将音频转换为文本"""
        if self._model is None:
            await self.initialize()

        result = await asyncio.to_thread(
            self._model.generate,
            input=audio_path
        )
        return result[0]["text"]


asr_service = ASRService()
