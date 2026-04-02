import os
import tempfile
import logging
import re
from typing import Optional
from pathlib import Path

try:
    from TTS.api import TTS
    COQUI_TTS_AVAILABLE = True
except ImportError:
    COQUI_TTS_AVAILABLE = False
    print("⚠️ TTS未安装，请运行: pip install TTS")

logger = logging.getLogger(__name__)


class CoquiTTSService:
    """
    Coqui TTS服务
    使用Coqui TTS进行离线语音合成
    """
    _instance: "CoquiTTSService" = None
    _tts = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not COQUI_TTS_AVAILABLE:
            raise RuntimeError("TTS未安装")

        if self._tts is None:
            self._initialize_tts()

    @staticmethod
    def _clean_text_for_tts(text: str) -> str:
        """
        清理文本以用于TTS合成
        移除emoji表情符号和其他特殊字符
        """
        import emoji

        # 使用emoji库移除emoji（更准确）
        text = emoji.replace_emoji(text, replace='')

        # 移除其他特殊符号（保留汉字、字母、数字、空格、常见中文标点）
        # 保留：汉字、字母、数字、空格、常见中文标点
        text = re.sub(r'[^\u4e00-\u9fff\u3400-\u4dbfa-zA-Z0-9\s，。！？、；：""''（）《》【】\-—–.,!?;:]', '', text)

        # 清理多余的空白字符
        text = re.sub(r'\s+', ' ', text).strip()

        # 如果清理后文本为空，返回默认文本
        if not text:
            text = "您好"
            return text

        # 检查末尾是否有标点符号，如果没有则添加
        # 中文标点：。，！？；：
        # 英文标点：.!?;
        ending_punctuation = ['。', '！', '？', '；', '：', '.', '!', '?', ';']
        if text[-1] not in ending_punctuation:
            # 根据文本内容判断使用中文还是英文标点
            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
            if has_chinese:
                text += '。'  # 中文文本添加中文句号
            else:
                text += '。'  # 英文文本也用中文句号（TTS效果更好）

        return text

    def _initialize_tts(self):
        """初始化TTS模型"""
        from app.core.config import settings

        logger.info("📢 加载Coqui TTS模型...")

        try:
            # 设置模型目录到统一位置
            model_dir = settings.COQUI_MODEL_DIR
            model_dir.mkdir(parents=True, exist_ok=True)

            # 设置环境变量，让TTS使用指定目录
            os.environ["TTS_HOME"] = str(model_dir)

            model_name = settings.COQUI_MODEL_NAME

            logger.info(f"📁 模型目录: {model_dir}")
            logger.info(f"📥 正在加载模型: {model_name}")
            logger.info("首次运行会自动下载模型，请耐心等待...")

            # 初始化TTS
            device = "cuda" if settings.COQUI_USE_GPU else "cpu"

            self._tts = TTS(model_name=model_name).to(device)

            logger.info(f"✅ Coqui TTS初始化成功 (model={model_name}, device={device})")
        except Exception as e:
            logger.error(f"❌ Coqui TTS初始化失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def synthesize(self, text: str, output_path: Optional[str] = None) -> str:
        """
        将文本转换为语音

        Args:
            text: 要转换的文本
            output_path: 输出音频文件路径，如果为None则创建临时文件

        Returns:
            音频文件路径
        """
        if not self._tts:
            raise RuntimeError("TTS未初始化")

        # 清理文本，移除emoji和特殊字符
        cleaned_text = self._clean_text_for_tts(text)
        logger.info(f"原始文本: {text}")
        logger.info(f"清理后文本: {cleaned_text}")

        # 如果没有指定输出路径，创建临时文件
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".wav")

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # 调用Coqui TTS进行语音合成，优化参数以减少拖音和机械感
        # temperature: 越低越确定性，越高越有变化（建议0.5-0.7）
        # length_scale: 控制语速，1.0为正常，小于1.0更快
        # noise_scale: 控制语音变化程度（建议0.6-0.8）
        self._tts.tts_to_file(
            text=cleaned_text,
            file_path=output_path,
            temperature=0.7,          # 增加随机性，更自然
            length_scale=0.8,         # 加快20%语速，显著减少拖音
            noise_scale=0.8,          # 增加变化，减少机械感
            noise_scale_w=0.8,        # 控制音高变化
        )

        # 后处理：裁剪尾部的静音和拖音
        self._trim_trailing_silence(output_path)

        return output_path

    def _trim_trailing_silence(self, audio_path: str, threshold_db: float = -30.0):
        """
        裁剪音频尾部的静音和拖音

        Args:
            audio_path: 音频文件路径
            threshold_db: 静音阈值（分贝）
        """
        try:
            import numpy as np
            from scipy.io import wavfile

            # 读取音频文件
            sample_rate, audio_data = wavfile.read(audio_path)

            # 转换为浮点数并计算分贝
            if audio_data.dtype == np.int16:
                audio_float = audio_data.astype(np.float32) / 32768.0
            else:
                audio_float = audio_data.astype(np.float32)

            # 计算每个样本的能量
            frame_length = int(0.05 * sample_rate)  # 50ms帧
            energy = []
            for i in range(0, len(audio_float), frame_length):
                frame = audio_float[i:i+frame_length]
                if len(frame) > 0:
                    frame_energy = 10 * np.log10(np.mean(frame**2) + 1e-10)
                    energy.append(frame_energy)

            # 从后向前查找最后一个高能量点
            if energy:
                # 找到最后一个超过阈值的帧
                last_speech_frame = len(energy) - 1
                for i in range(len(energy) - 1, -1, -1):
                    if energy[i] > threshold_db:
                        last_speech_frame = i
                        break

                # 添加100ms的缓冲
                end_sample = min((last_speech_frame + 2) * frame_length, len(audio_data))
                trimmed_audio = audio_data[:end_sample]

                # 保存裁剪后的音频
                wavfile.write(audio_path, sample_rate, trimmed_audio)
                logger.debug(f"裁剪尾部静音: {len(audio_data)} -> {len(trimmed_audio)} samples")
        except ImportError:
            logger.warning("scipy未安装，跳过音频后处理。安装: pip install scipy")
        except Exception as e:
            logger.warning(f"音频后处理失败: {e}")

    @property
    def is_available(self) -> bool:
        """检查TTS是否可用"""
        return COQUI_TTS_AVAILABLE and self._tts is not None


# 全局实例（懒加载）
_coqui_tts_instance: Optional[CoquiTTSService] = None


def getCoquiTts() -> Optional[CoquiTTSService]:
    """获取Coqui TTS实例"""
    global _coqui_tts_instance
    if _coqui_tts_instance is None:
        try:
            _coqui_tts_instance = CoquiTTSService()
        except Exception as e:
            logger.error(f"❌ 初始化Coqui TTS失败: {e}")
            return None
    return _coqui_tts_instance
