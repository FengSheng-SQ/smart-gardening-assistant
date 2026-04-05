from pydantic import BaseModel, validator, model_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class ChatMode(str, Enum):
    fast = "fast"
    thinking = "thinking"
    expert = "expert"


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class LocationInfo(BaseModel):
    city: str
    latitude: float
    longitude: float
    source: str  # 'gps', 'ip', 'manual'


class WeatherInfo(BaseModel):
    city: str
    temperature: float
    description: str
    humidity: Optional[int] = None
    wind_speed: Optional[float] = None
    timezone: Optional[str] = None


class TimeInfo(BaseModel):
    current_time: str
    date: str
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    weekday: int
    season: str
    timezone: str


class ChatMessage(BaseModel):
    # 主字段（用于API通信）
    id: Union[int, str]  # 兼容数据库的int和API的str
    user_id: Optional[Union[int, str]] = None  # ⚠️ 改为可选！数据库查询不返回此字段
    role: Optional[MessageRole] = None  # 可选，从is_user转换
    content: Optional[str] = None  # 可选，使用message_text
    image_path: Optional[str] = None
    audio_url: Optional[str] = None
    chat_mode: ChatMode = ChatMode.fast  # 默认fast
    location: Optional[LocationInfo] = None
    created_at: Optional[datetime] = None
    error: Optional[str] = None

    # 数据库字段兼容（用于直接从数据库加载）
    message_text: Optional[str] = None
    is_user: Optional[bool] = None
    audio_filename: Optional[str] = None
    image_filename: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def convert_database_format(cls, data: Any) -> Any:
        """转换数据库格式到API格式"""
        if not isinstance(data, dict):
            return data

        # 如果是数据库格式（有message_text字段），转换为API格式
        if 'message_text' in data:
            data = dict(data)  # 创建副本避免修改原数据
            if 'content' not in data and data['message_text']:
                data['content'] = data['message_text']

        # 从is_user推导role
        if 'is_user' in data and 'role' not in data:
            data = dict(data)
            if data['is_user'] is True:
                data['role'] = MessageRole.user
            elif data['is_user'] is False:
                data['role'] = MessageRole.assistant

        # 映射image_filename到image_path
        if 'image_filename' in data and 'image_path' not in data:
            data = dict(data)
            data['image_path'] = data['image_filename']

        # 映射audio_filename到audio_url
        if 'audio_filename' in data and 'audio_url' not in data:
            data = dict(data)
            data['audio_url'] = data['audio_filename']

        # 确保chat_mode有默认值（使用枚举而不是字符串）
        if 'chat_mode' not in data:
            data = dict(data)
            data['chat_mode'] = ChatMode.fast
        elif isinstance(data.get('chat_mode'), str):
            # 如果是字符串，转换为枚举
            data = dict(data)
            try:
                data['chat_mode'] = ChatMode(data['chat_mode'])
            except ValueError:
                data['chat_mode'] = ChatMode.fast

        # 转换int ID为str
        if 'id' in data and isinstance(data['id'], int):
            data = dict(data)
            data['id'] = str(data['id'])

        if 'user_id' in data and isinstance(data['user_id'], int):
            data = dict(data)
            data['user_id'] = str(data['user_id'])

        return data

    class Config:
        from_attributes = True


class ChatHistory(BaseModel):
    user_id: str
    messages: List[ChatMessage]
    total_count: int


class ChatRequest(BaseModel):
    text: Optional[str] = None
    image: Optional[str] = None
    question: Optional[str] = None
    chat_mode: ChatMode = ChatMode.fast
    location: Optional[LocationInfo] = None


class ChatResponse(BaseModel):
    type: str  # 'text', 'audio', 'status', 'error'
    text: Optional[str] = None
    audio_url: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    chat_mode: Optional[ChatMode] = None


class WebSocketConnect(BaseModel):
    client_id: str
    user_id: Optional[str] = None
    token: str


class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


# 别名，用于兼容
RegisterRequest = UserRegister
LoginRequest = UserLogin


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    token: Optional[str] = None


class RegisterResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[int] = None


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AgentContext(BaseModel):
    location: Optional[LocationInfo] = None
    weather: Optional[WeatherInfo] = None
    time_info: Optional[TimeInfo] = None
    chat_history: List[ChatMessage] = []
    current_question: str


class PlantingAdvice(BaseModel):
    question: str
    advice: str
    context: Dict[str, Any]
    confidence: float = 0.8


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime = datetime.now()


# API响应模型
class ChatHistoryResponse(BaseModel):
    success: bool
    messages: List[ChatMessage]
    message: Optional[str] = None


class ClearChatResponse(BaseModel):
    success: bool
    message: str
