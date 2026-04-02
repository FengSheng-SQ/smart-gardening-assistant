"""
天气Agent
支持通过MCP Host或直接API获取天气信息
"""
from app.services.agents.base_agent import BaseAgent
from app.services.mcp.mcp_host import get_mcp_host
from app.core.config import settings
import httpx
import logging


class WeatherAgent(BaseAgent):
    """天气Agent - 通过MCP或API获取天气信息"""

    def __init__(self):
        super().__init__("WeatherAgent")
        self.mcp_host = get_mcp_host()
        self.api_base = "https://wttr.in"
        self.user_agent = "smart-gardening-assistant/1.0"

    async def execute(self, context: dict) -> dict:
        """
        获取天气信息

        Args:
            context: 上下文信息，必须包含location

        Returns:
            天气信息字典
        """
        self.logger.info("🌤️ WeatherAgent 执行中...")

        try:
            # 从上下文获取位置信息
            location = context.get("location", {})
            if not location:
                raise ValueError("缺少位置信息")

            city = location.get("city", "未知")

            # 根据配置选择获取天气的方式
            if settings.WEATHER_USE_MCP:
                # 通过MCP Host获取天气
                result_text = await self._get_weather_via_mcp(city)
            else:
                # 直接调用WTTR.in API
                result_text = await self._get_weather_via_api(city)

            if result_text:
                # 解析返回的文本结果
                weather = self._parse_weather_result(result_text, city)
                self.logger.info(f"✅ WeatherAgent 完成: {weather.get('condition', '未知')}, {weather.get('temperature', 'N/A')}°C")

                return {
                    "agent": self.name,
                    "success": True,
                    "data": weather
                }
            else:
                raise Exception("获取天气信息失败")

        except Exception as e:
            self.logger.error(f"❌ WeatherAgent 失败: {e}")
            return {
                "agent": self.name,
                "success": False,
                "error": str(e),
                "data": {
                    "condition": "未知",
                    "temperature": "N/A",
                    "description": "天气信息获取失败"
                }
            }

    async def _get_weather_via_mcp(self, city: str) -> str | None:
        """通过MCP Host获取天气"""
        try:
            result_text = await self.mcp_host.call_tool(
                "get_current_weather",
                {"city": city}
            )
            return result_text
        except Exception as e:
            self.logger.error(f"MCP获取天气失败: {e}")
            return None

    async def _get_weather_via_api(self, city: str) -> str | None:
        """直接调用WTTR.in API获取天气"""
        try:
            url = f"{self.api_base}/{city}"
            params = {
                "format": "j1",  # JSON 格式
                "lang": "zh",    # 中文
                "m": "",         # 公制单位
            }

            headers = {"User-Agent": self.user_agent}

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers, timeout=30.0)
                response.raise_for_status()
                data = response.json()

            # 解析当前天气数据
            current = data["current_condition"][0]
            area = data.get('nearest_area', [{}])[0]
            location_name = area.get('areaName', [{}])[0].get('value', city)

            temp_c = current.get('temp_C', 'N/A')
            humidity = current.get('humidity', 'N/A')
            weather_desc = current.get('lang_zh', [{}])[0].get('value', current.get('weatherDesc', [{}])[0].get('value', '未知'))
            wind_speed_kmh = current.get('windspeedKmph', 'N/A')
            wind_dir = current.get('winddir16Point', 'N/A')
            pressure = current.get('pressure', 'N/A')
            feels_like_c = current.get('FeelsLikeC', 'N/A')

            # 风力等级描述
            wind_level = "无风"
            try:
                wind_speed_num = float(wind_speed_kmh)
                if wind_speed_num < 10:
                    wind_level = "无风"
                elif wind_speed_num < 30:
                    wind_level = "微风"
                elif wind_speed_num < 50:
                    wind_level = "和风"
                elif wind_speed_num < 80:
                    wind_level = "强风"
                else:
                    wind_level = "大风"
            except:
                pass

            return f"""
{location_name}当前天气：

🌡️ 温度：{temp_c}°C（体感 {feels_like_c}°C）
🌤️ 天气：{weather_desc}
💧 湿度：{humidity}%
💨 风力：{wind_level} {wind_speed_kmh}km/h ({wind_dir})
🌀 气压：{pressure}hPa
"""

        except Exception as e:
            self.logger.error(f"API获取天气失败: {e}")
            return None

        except Exception as e:
            self.logger.error(f"❌ WeatherAgent 失败: {e}")
            return {
                "agent": self.name,
                "success": False,
                "error": str(e),
                "data": {
                    "condition": "未知",
                    "temperature": "N/A",
                    "description": "天气信息获取失败，请确保MCP已启用"
                }
            }

    def _parse_weather_result(self, result: str, city: str) -> dict:
        """
        解析天气文本结果（支持MCP和API两种格式）

        Args:
            result: 返回的天气文本
            city: 城市名称

        Returns:
            天气数据字典
        """
        try:
            weather_data = {
                "city": city,
                "condition": "未知",
                "temperature": "N/A",
                "humidity": "N/A",
                "wind": "N/A",
                "feels_like": "N/A",
                "pressure": "N/A",
                "description": result.strip(),
                "source": "MCP" if settings.WEATHER_USE_MCP else "API",
                "timestamp": None
            }

            lines = result.strip().split('\n')
            for line in lines:
                line = line.strip()

                # 解析温度（支持多种格式）
                if '🌡️ 温度：' in line or '温度：' in line:
                    try:
                        # 提取主要温度
                        if '°C' in line:
                            temp_str = line.split('°C')[0].split('：')[-1].strip()
                            weather_data["temperature"] = int(float(temp_str))
                    except:
                        pass

                    # 提取体感温度
                    if '体感' in line:
                        try:
                            feels_like = line.split('体感')[-1].split('°C')[0].strip()
                            weather_data["feels_like"] = int(float(feels_like))
                        except:
                            pass

                # 解析天气状况
                elif '🌤️ 天气：' in line or '天气：' in line:
                    condition = line.split('：')[-1].strip()
                    weather_data["condition"] = condition

                # 解析湿度
                elif '💧 湿度：' in line or '湿度：' in line:
                    try:
                        humidity_str = line.split('：')[-1].split('%')[0].strip()
                        weather_data["humidity"] = int(humidity_str)
                    except:
                        pass

                # 解析风力
                elif '💨 风力：' in line or '风力：' in line:
                    wind_info = line.split('：')[-1].strip()
                    weather_data["wind"] = wind_info

                # 解析气压
                elif '🌀 气压：' in line or '气压：' in line:
                    try:
                        pressure_str = line.split('：')[-1].split('hPa')[0].strip()
                        weather_data["pressure"] = int(pressure_str)
                    except:
                        pass

            return weather_data

        except Exception as e:
            self.logger.error(f"解析天气结果失败: {e}")
            return {
                "city": city,
                "condition": "未知",
                "temperature": "N/A",
                "description": result,
                "source": "API" if not settings.WEATHER_USE_MCP else "MCP"
            }
