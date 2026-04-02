"""
自建MCP天气服务器
使用FastMCP实现MCP协议，提供天气查询工具
参考了weather-cli的实现
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# 导入FastMCP
from mcp.server.fastmcp import FastMCP


logger = logging.getLogger(__name__)


# 初始化FastMCP服务器
mcp = FastMCP("weather-service")

# 常量
WEATHER_API_BASE = "https://wttr.in"
USER_AGENT = "smart-gardening-assistant/1.0"

# 默认位置（北京）
DEFAULT_LATITUDE = 39.9042
DEFAULT_LONGITUDE = 116.4074
DEFAULT_CITY = "Beijing"

# 添加区域代码到城市映射
REGION_MAPPING = {
    "CN-11": ("北京", 39.9042, 116.4074),
    "CN-31": ("上海", 31.2304, 121.4737),
    "CN-44": ("广州", 23.1291, 113.2644),
    "CN-51": ("成都", 30.5728, 104.0668),
    "CN-42": ("武汉", 30.5928, 114.3055),
    "CN-61": ("西安", 34.3416, 108.9398),
    "CN-33": ("杭州", 30.2741, 120.1551),
}


async def make_weather_request(url: str, params: dict[str, Any]) -> str | None:
    """Make a request to the wttr.in API with proper error handling."""
    import httpx

    headers = {
        "User-Agent": USER_AGENT
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching weather data: {e}")
            return None


@mcp.tool()
async def get_forecast(latitude: float = DEFAULT_LATITUDE, longitude: float = DEFAULT_LONGITUDE) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location (default: Beijing)
        longitude: Longitude of the location (default: Beijing)
    """
    # 构建位置字符串
    location = f"{latitude},{longitude}"

    # 获取天气信息
    params = {
        "format": "%l:+%c+%t+%h+%w+%p+%m\n",  # 自定义输出格式
        "lang": "zh",  # 使用中文
        "m": "",      # 使用公制单位
    }

    weather_data = await make_weather_request(f"{WEATHER_API_BASE}/{location}", params)
    if not weather_data:
        return "无法获取该位置的天气预报"

    # 获取详细天气信息
    detailed_params = {
        "format": "j1",  # JSON 格式
        "lang": "zh",
        "m": "",
    }

    detailed_data = await make_weather_request(f"{WEATHER_API_BASE}/{location}", detailed_params)
    if not detailed_data:
        return weather_data

    try:
        data = json.loads(detailed_data)
        current = data["current_condition"][0]
        area_name = data.get('nearest_area', [{}])[0].get('areaName', [{}])[0].get('value', DEFAULT_CITY)

        return f"""
位置：{area_name}
当前天气：{current.get('lang_zh', [{}])[0].get('value', '未知')}
温度：{current.get('temp_C', 'N/A')}°C
体感温度：{current.get('FeelsLikeC', 'N/A')}°C
相对湿度：{current.get('humidity', 'N/A')}%
气压：{current.get('pressure', 'N/A')}hPa
风向：{current.get('winddir16Point', 'N/A')}
风速：{current.get('windspeedKmph', 'N/A')}km/h
能见度：{current.get('visibility', 'N/A')}km
降水量：{current.get('precipMM', 'N/A')}mm
云量：{current.get('cloudcover', 'N/A')}%
"""
    except Exception as e:
        logger.error(f"Error parsing weather data: {e}")
        return weather_data


@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a region.

    Args:
        state: Region code (e.g. CN-11 for Beijing)
    """
    if state not in REGION_MAPPING:
        return f"错误：不支持的区域代码 {state}。支持的区域代码包括：{', '.join(REGION_MAPPING.keys())}"

    city_name, lat, lon = REGION_MAPPING[state]

    # 获取天气预警信息
    params = {
        "format": "j1",  # JSON 格式
        "lang": "zh",    # 中文
    }

    weather_data = await make_weather_request(f"{WEATHER_API_BASE}/{lat},{lon}", params)
    if not weather_data:
        return f"无法获取 {city_name} 的天气预警信息"

    try:
        data = json.loads(weather_data)

        # 提取天气预警信息
        weather_desc = data["current_condition"][0]["lang_zh"][0]["value"]
        weather_alerts = []

        # 检查极端天气条件
        current = data["current_condition"][0]
        temp = float(current["temp_C"])
        humidity = float(current["humidity"])
        wind_speed = float(current["windspeedKmph"])
        precip = float(current["precipMM"])

        # 添加天气预警
        if temp >= 35:
            weather_alerts.append("高温预警：当前温度超过35°C，请注意防暑降温")
        elif temp <= 0:
            weather_alerts.append("低温预警：当前温度低于0°C，请注意防寒保暖")

        if humidity >= 85:
            weather_alerts.append("湿度预警：当前湿度较高，请注意防潮")

        if wind_speed >= 39:
            weather_alerts.append("大风预警：当前风速较大，请注意防风")

        if precip >= 50:
            weather_alerts.append("暴雨预警：当前降水量较大，请注意防涝")

        # 整理返回信息
        result = f"""
{city_name}天气预警信息：
当前天气：{weather_desc}
温度：{temp}°C
相对湿度：{humidity}%
风速：{wind_speed}km/h
降水量：{precip}mm

预警信息："""

        if weather_alerts:
            for alert in weather_alerts:
                result += f"\n- {alert}"
        else:
            result += "\n当前无特别预警信息"

        return result

    except Exception as e:
        logger.error(f"Error parsing weather alerts: {e}")
        return f"解析 {city_name} 的天气预警信息时出错：{str(e)}"


@mcp.tool()
async def get_current_weather(city: str) -> str:
    """获取指定城市的当前天气信息（支持中文城市名称）

    Args:
        city: 城市名称（支持中文，如"北京"、"上海"）
    """
    try:
        import httpx

        url = f"{WEATHER_API_BASE}/{city}"
        params = {
            "format": "j1",  # JSON 格式
            "lang": "zh",    # 中文
            "m": "",         # 公制单位
        }

        headers = {"User-Agent": USER_AGENT}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()

        # 解析当前天气数据
        current = data["current_condition"][0]
        area = data.get('nearest_area', [{}])[0]
        location_name = area.get('areaName', [{}])[0].get('value', city)
        country = area.get('country', [{}])[0].get('value', '')

        temp_c = current.get('temp_C', 'N/A')
        temp_f = current.get('temp_F', 'N/A')
        humidity = current.get('humidity', 'N/A')
        weather_desc = current.get('lang_zh', [{}])[0].get('value', current.get('weatherDesc', [{}])[0].get('value', '未知'))
        wind_speed_kmh = current.get('windspeedKmph', 'N/A')
        wind_dir = current.get('winddir16Point', 'N/A')
        pressure = current.get('pressure', 'N/A')
        uv_index = current.get('uvIndex', 'N/A')
        feels_like_c = current.get('FeelsLikeC', 'N/A')
        visibility = current.get('visibility', 'N/A')
        precip_mm = current.get('precipMM', 'N/A')
        cloudcover = current.get('cloudcover', 'N/A')

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
☀️ 紫外线指数：{uv_index}
👁️ 能见度：{visibility}km
🌧️ 降水量：{precip_mm}mm
☁️ 云量：{cloudcover}%
"""
    except Exception as e:
        logger.error(f"获取 {city} 天气失败: {e}")
        return f"无法获取 {city} 的天气信息：{str(e)}"


@mcp.tool()
async def get_weather_forecast(city: str, days: int = 3) -> str:
    """获取指定城市的天气预报

    Args:
        city: 城市名称（支持中文）
        days: 预报天数（1-3）
    """
    try:
        import httpx

        url = f"{WEATHER_API_BASE}/{city}"
        params = {
            "format": "j1",  # JSON 格式
            "lang": "zh",    # 中文
            "m": "",         # 公制单位
        }

        headers = {"User-Agent": USER_AGENT}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()

        # 解析位置信息
        area = data.get('nearest_area', [{}])[0]
        location_name = area.get('areaName', [{}])[0].get('value', city)

        # 解析天气预报数据
        weather_list = data.get("weather", [])

        result = f"\n{location_name}未来{min(days, 3)}天天气预报：\n\n"

        for i, day_data in enumerate(weather_list[:days]):
            date = day_data.get("date", "未知日期")
            avg_temp = day_data.get("avgtempC", "N/A")
            max_temp = day_data.get("maxtempC", "N/A")
            min_temp = day_data.get("mintempC", "N/A")

            # 每日天气状况
            hourly = day_data.get("hourly", [])
            if hourly:
                # 取中午12点的天气作为代表
                midday = hourly[12] if len(hourly) > 12 else hourly[0]
                condition = midday.get("lang_zh", [{}])[0].get('value', midday.get("weatherDesc", [{}])[0].get("value", "未知"))
                chance_of_rain = midday.get("chanceofrain", "0")
                humidity = midday.get("humidity", "N/A")
                uv_index = midday.get("uvIndex", "N/A")
            else:
                condition = "未知"
                chance_of_rain = "0"
                humidity = "N/A"
                uv_index = "N/A"

            result += f"📅 {date}\n"
            result += f"  天气：{condition}\n"
            result += f"  温度：{min_temp}°C ~ {max_temp}°C（平均 {avg_temp}°C）\n"
            result += f"  湿度：{humidity}%\n"
            result += f"  降水概率：{chance_of_rain}%\n"
            result += f"  紫外线指数：{uv_index}\n\n"

        return result

    except Exception as e:
        logger.error(f"获取 {city} 天气预报失败: {e}")
        return f"无法获取 {city} 的天气预报：{str(e)}"


def main():
    """主函数：运行MCP服务器"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("启动Weather MCP服务器（使用FastMCP）")
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()
