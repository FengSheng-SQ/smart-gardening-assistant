"""
地点提取工具
从用户消息中提取城市名称
"""
import logging
import re
from typing import Optional


logger = logging.getLogger(__name__)


class LocationExtractor:
    """地点提取器"""

    # 中国主要城市列表（用于匹配）
    CITIES = {
        # 直辖市
        "北京", "上海", "天津", "重庆",

        # 省会城市
        "广州", "深圳", "成都", "杭州", "武汉", "西安", "南京",
        "郑州", "长沙", "沈阳", "哈尔滨", "济南", "青岛", "大连",
        "厦门", "福州", "苏州", "宁波", "合肥", "南昌", "昆明",
        "贵阳", "南宁", "海口", "三亚", "兰州", "西宁", "银川",
        "呼和浩特", "太原", "石家庄", "唐山", "长春", "吉林",
        "牡丹江", "齐齐哈尔", "徐州", "常州", "扬州", "镇江",
        "南通", "连云港", "淮安", "盐城", "温州", "嘉兴", "湖州",
        "绍兴", "金华", "衢州", "台州", "丽水", "蚌埠", "芜湖",
        "马鞍山", "铜陵", "安庆", "黄山", "滁州", "阜阳", "宿州",
        "六安", "亳州", "池州", "宣城", "莆田", "三明", "泉州",
        "漳州", "南平", "龙岩", "赣州", "吉安", "宜春", "抚州",
        "上饶", "九江", "萍乡", "新余", "景德镇", "烟台", "威海",
        "潍坊", "临沂", "枣庄", "东营", "淄博", "泰安", "日照",
        "莱芜", "临沂", "德州", "聊城", "滨州", "菏泽", "洛阳",
        "开封", "安阳", "鹤壁", "新乡", "焦作", "濮阳", "许昌", "漯河",
        "三门峡", "南阳", "商丘", "信阳", "周口", "驻马店", "平顶山",
        "宜昌", "襄阳", "鄂州", "荆州", "黄冈", "黄石", "咸宁",
        "十堰", "随州", "恩施", "孝感", "荆门", "株洲", "湘潭",
        "衡阳", "邵阳", "岳阳", "常德", "张家界", "益阳", "郴州",
        "永州", "怀化", "娄底", "韶关", "珠海", "汕头", "佛山",
        "江门", "湛江", "茂名", "肇庆", "惠州", "梅州", "汕尾",
        "河源", "阳江", "清远", "东莞", "中山", "潮州", "揭阳",
        "云浮", "柳州", "桂林", "梧州", "北海", "防城港", "钦州",
        "贵港", "玉林", "百色", "贺州", "河池", "来宾", "崇左",
        "绵阳", "自贡", "攀枝花", "泸州", "德阳", "广元", "遂宁",
        "内江", "乐山", "南充", "眉山", "宜宾", "广安", "达州",
        "雅安", "巴中", "资阳", "拉萨", "日喀则", "昌都", "林芝",
        "山南", "那曲", "银川", "石嘴山", "吴忠", "固原", "中卫",
        "西宁", "海东", "海北", "黄南", "海南", "果洛", "玉树",
        "海西", "乌鲁木齐", "克拉玛依", "吐鲁番", "哈密", "昌吉",
        "博尔塔拉", "巴音郭楞", "阿克苏", "克孜勒苏", "喀什",
        "和田", "伊犁", "塔城", "阿勒泰", "石河子", "阿拉尔",
        "图木舒克", "五家渠", "北屯", "铁门关", "阿拉尔", "图木舒克"
    }

    # 常见地点模式
    LOCATION_PATTERNS = [
        r'(.{2,4})市',
        r'(.{2,4})的天气',
        r'(.{2,4})现在',
        r'(.{2,4})怎么样',
        r'(.{2,4})天气',
        r'查询(.{2,4})',
        r'(.{2,4})地区',
    ]

    @classmethod
    def extract_city(cls, message: str) -> Optional[str]:
        """
        从用户消息中提取城市名称

        Args:
            message: 用户消息

        Returns:
            提取到的城市名称，如果没有找到返回None
        """
        if not message:
            return None

        message = message.strip()

        # 方法1: 直接匹配城市列表
        for city in cls.CITIES:
            if city in message:
                logger.info(f"🎯 从消息中提取到城市: {city}")
                return city

        # 方法2: 使用正则表达式匹配模式
        for pattern in cls.LOCATION_PATTERNS:
            match = re.search(pattern, message)
            if match:
                city = match.group(1)
                if city in cls.CITIES or len(city) >= 2:
                    logger.info(f"🎯 从消息中提取到城市: {city}")
                    return city

        # 方法3: 查找"天气"前面的词语
        weather_index = message.find('天气')
        if weather_index > 0:
            # 获取"天气"前的10个字符
            before_text = message[max(0, weather_index - 10):weather_index]
            # 提取可能的地点词
            words = before_text.split()
            if words:
                last_word = words[-1].rstrip('，。、！？')
                if len(last_word) >= 2 and last_word in cls.CITIES:
                    logger.info(f"🎯 从消息中提取到城市: {last_word}")
                    return last_word

        return None

    @classmethod
    def should_override_location(cls, message: str, gps_location: dict) -> bool:
        """
        判断是否应该使用提取的地点覆盖GPS位置

        Args:
            message: 用户消息
            gps_location: GPS位置信息

        Returns:
            True表示应该使用提取的地点
        """
        # 从消息中提取地点
        extracted_city = cls.extract_city(message)

        if not extracted_city:
            # 没有提取到地点，使用GPS
            return False

        # 提取到地点了
        gps_city = gps_location.get('city', '')

        # 如果GPS城市与提取的城市不同，使用提取的
        if extracted_city != gps_city and gps_city not in extracted_city:
            logger.info(f"📍 地点覆盖: GPS={gps_city} → 提取={extracted_city}")
            return True

        return False

    @classmethod
    def get_location_for_query(cls, message: str, gps_location: dict) -> dict:
        """
        获取用于查询的地点信息

        Args:
            message: 用户消息
            gps_location: GPS位置信息

        Returns:
            地点信息字典
        """
        # 尝试从消息中提取地点
        extracted_city = cls.extract_city(message)

        if extracted_city:
            # 使用提取的城市
            return {
                "city": extracted_city,
                "source": "nlp_extracted"
            }
        else:
            # 没有提取到地点，使用GPS
            logger.info(f"📍 未提取到地点，使用GPS: {gps_location.get('city')}")
            return {
                **gps_location,
                "source": "gps"
            }


# 导出单例
_location_extractor = LocationExtractor()

def get_location_extractor() -> LocationExtractor:
    """获取地点提取器实例"""
    return _location_extractor
