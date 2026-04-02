"""
聊天模式基础抽象类
所有聊天模式都需要继承此类并实现 process 方法
"""
from abc import ABC, abstractmethod
import logging


class BaseChatMode(ABC):
    """聊天模式基础抽象类"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def process(self, message: str, user_id: int, image_base64: str = None) -> str:
        """
        处理用户消息并生成AI回复

        Args:
            message: 用户消息文本
            user_id: 用户ID
            image_base64: 图片的base64编码（可选）

        Returns:
            AI回复文本
        """
        pass

    def get_mode_name(self) -> str:
        """获取模式名称"""
        return self.__class__.__name__.replace('Mode', '').lower()

    def _log_process_start(self, message: str, user_id: int):
        """记录处理开始日志"""
        self.logger.info(f"🚀 {self.get_mode_name().upper()} 模式开始处理: user_id={user_id}")
        self.logger.info(f"📝 用户消息: {message[:100]}...")

    def _log_process_end(self, response: str):
        """记录处理结束日志"""
        self.logger.info(f"✅ {self.get_mode_name().upper()} 模式处理完成")
        self.logger.info(f"💬 AI回复: {response[:100]}...")
