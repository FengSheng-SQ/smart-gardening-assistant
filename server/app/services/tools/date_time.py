"""
时间工具
获取当前时间、季节等信息
"""
from datetime import datetime
import pytz
from typing import Dict


class DateTimeTool:
    """时间工具类"""

    def __init__(self, default_timezone: str = "Asia/Shanghai"):
        self.default_timezone = default_timezone

    def get_current_time(self, timezone: str = None) -> Dict[str, any]:
        """
        获取当前时间信息

        Args:
            timezone: 时区，默认使用初始化时的时区

        Returns:
            时间信息字典
        """
        tz = pytz.timezone(timezone or self.default_timezone)
        now = datetime.now(tz)

        return {
            "datetime": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "weekday": now.strftime("%A"),
            "month": now.strftime("%B"),
            "year": now.year,
            "month_num": now.month,
            "day": now.day,
            "hour": now.hour,
            "timezone": str(tz)
        }

    def get_season(self, date: datetime = None) -> str:
        """
        获取季节

        Args:
            date: 日期对象，默认使用当前日期

        Returns:
            季节名称
        """
        if date is None:
            date = datetime.now()

        month = date.month
        if month in [12, 1, 2]:
            return "冬季"
        elif month in [3, 4, 5]:
            return "春季"
        elif month in [6, 7, 8]:
            return "夏季"
        else:
            return "秋季"

    def get_seasonal_info(self) -> Dict[str, str]:
        """获取季节相关信息"""
        time_info = self.get_current_time()
        now = datetime.now()

        return {
            "season": self.get_season(now),
            "month": time_info["month"],
            "date": time_info["date"],
            "time": time_info["time"],
            "timezone": time_info["timezone"]
        }


# 全局实例
datetime_tool = DateTimeTool()
