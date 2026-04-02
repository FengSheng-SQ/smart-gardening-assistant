"""
位置Agent
获取用户地理位置信息
"""
from app.services.agents.base_agent import BaseAgent
from app.services.tools.location import get_location_tool
from app.core.config import settings


class LocationAgent(BaseAgent):
    """位置Agent - 获取地理位置"""

    def __init__(self):
        super().__init__("LocationAgent")
        self.location_tool = get_location_tool(
            default_city=settings.DEFAULT_CITY,
            default_lat=settings.DEFAULT_LAT,
            default_lon=settings.DEFAULT_LON
        )

    async def execute(self, context: dict) -> dict:
        """
        获取位置信息

        Args:
            context: 上下文信息，可能包含client_ip

        Returns:
            位置信息字典
        """
        self.logger.info("🌍 LocationAgent 执行中...")

        try:
            # 获取客户端IP（如果有）
            client_ip = context.get("client_ip")

            # 获取位置信息
            location = await self.location_tool.get_client_location(client_ip)

            self.logger.info(f"✅ LocationAgent 完成: {location.get('city', '未知')}")

            return {
                "agent": self.name,
                "success": True,
                "data": location
            }

        except Exception as e:
            self.logger.error(f"❌ LocationAgent 失败: {e}")
            return {
                "agent": self.name,
                "success": False,
                "error": str(e),
                "data": self.location_tool.get_default_location()
            }
