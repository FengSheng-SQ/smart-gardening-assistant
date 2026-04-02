"""
Agent基础抽象类
所有Agent都需要继承此类
"""
from abc import ABC, abstractmethod
import logging


class BaseAgent(ABC):
    """Agent基础抽象类"""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @abstractmethod
    async def execute(self, context: dict) -> dict:
        """
        执行Agent任务

        Args:
            context: 上下文信息，包含用户消息、位置、天气等

        Returns:
            Agent执行结果字典
        """
        pass

    def get_name(self) -> str:
        """获取Agent名称"""
        return self.name
