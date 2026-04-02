"""
位置工具
获取用户地理位置信息
"""
import httpx
import logging
from typing import Dict, Optional


logger = logging.getLogger(__name__)


class LocationTool:
    """位置工具类"""

    def __init__(self, default_city: str = "北京", default_lat: float = 39.9042, default_lon: float = 116.4074):
        self.default_city = default_city
        self.default_lat = default_lat
        self.default_lon = default_lon

    async def get_client_location(self, client_ip: str = None) -> Dict[str, any]:
        """
        获取客户端位置信息

        Args:
            client_ip: 客户端IP地址

        Returns:
            位置信息字典
        """
        # 如果没有IP或是本地IP，使用默认位置
        if not client_ip or client_ip in ["127.0.0.1", "::1", "localhost", "unknown"]:
            logger.info(f"使用默认位置: {self.default_city}")
            return self.get_default_location()

        # 尝试通过IP获取位置
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # 使用免费的IP定位API
                response = await client.get(
                    f"http://ip-api.com/json/{client_ip}"
                )
                data = response.json()

                if data.get("status") == "success":
                    return {
                        "ip": client_ip,
                        "country": data.get("country"),
                        "region": data.get("regionName"),
                        "city": data.get("city"),
                        "lat": data.get("lat"),
                        "lon": data.get("lon"),
                        "timezone": data.get("timezone"),
                        "source": "ip_api"
                    }
                else:
                    logger.warning(f"IP定位失败: {data.get('message')}")
                    return self.get_default_location()

        except Exception as e:
            logger.error(f"获取位置失败: {e}")
            return self.get_default_location()

    def get_default_location(self) -> Dict[str, any]:
        """获取默认位置"""
        return {
            "city": self.default_city,
            "country": "中国",
            "region": self.default_city,
            "lat": self.default_lat,
            "lon": self.default_lon,
            "timezone": "Asia/Shanghai",
            "source": "default"
        }


# 全局实例
def get_location_tool(default_city: str = "北京", default_lat: float = 39.9042, default_lon: float = 116.4074):
    """获取位置工具实例"""
    return LocationTool(default_city, default_lat, default_lon)
