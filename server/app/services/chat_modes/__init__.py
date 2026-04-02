"""
聊天模式服务
支持三种聊天模式：快速、思考、专家
"""
from app.services.chat_modes.base_mode import BaseChatMode
from app.services.chat_modes.fast_mode import FastMode
from app.services.chat_modes.thinking_mode import ThinkingMode
from app.services.chat_modes.expert_mode import ExpertMode

__all__ = ['BaseChatMode', 'FastMode', 'ThinkingMode', 'ExpertMode']
