"""
时间Agent
获取当前时间、季节等信息
"""
from app.services.agents.base_agent import BaseAgent
from app.services.tools.date_time import datetime_tool


class TimeAgent(BaseAgent):
    """时间Agent - 获取时间信息"""

    def __init__(self):
        super().__init__("TimeAgent")
        self.datetime_tool = datetime_tool

    async def execute(self, context: dict) -> dict:
        """
        获取时间信息

        Args:
            context: 上下文信息

        Returns:
            时间信息字典
        """
        self.logger.info("⏰ TimeAgent 执行中...")

        try:
            # 获取当前时间
            time_info = self.datetime_tool.get_current_time()

            # 获取季节信息
            seasonal_info = self.datetime_tool.get_seasonal_info()

            self.logger.info(f"✅ TimeAgent 完成: {seasonal_info['season']}")

            return {
                "agent": self.name,
                "success": True,
                "data": {
                    **time_info,
                    **seasonal_info
                }
            }

        except Exception as e:
            self.logger.error(f"❌ TimeAgent 失败: {e}")
            return {
                "agent": self.name,
                "success": False,
                "error": str(e)
            }
