"""
种植Agent
主Agent，负责生成种植建议
"""
from app.services.agents.base_agent import BaseAgent
from app.services import llm_service


class PlantingAgent(BaseAgent):
    """种植Agent - 生成种植建议"""

    def __init__(self):
        super().__init__("PlantingAgent")

    async def execute(self, context: dict) -> dict:
        """
        生成种植建议

        Args:
            context: 包含用户消息、位置、天气、时间、历史记录等

        Returns:
            种植建议字典
        """
        self.logger.info("🌱 PlantingAgent 执行中...")

        try:
            # 提取上下文信息
            user_message = context.get("user_message", "")
            location = context.get("location", {})
            weather = context.get("weather", {})
            time_info = context.get("time", {})
            conversation_history = context.get("conversation_history", [])

            # 构建上下文提示词
            context_prompt = self._build_context_prompt(
                location, weather, time_info
            )

            # 构建完整提示词
            full_prompt = self._build_full_prompt(
                user_message, context_prompt, conversation_history
            )

            # 调用LLM生成建议
            self.logger.info("🤖 调用LLM生成种植建议...")
            self.logger.info(f"📚 使用 {len(conversation_history)} 条历史记录")
            response = await llm_service.chat(
                message=full_prompt,
                conversation_history=conversation_history  # ← 修复：传递历史记录
            )

            self.logger.info("✅ PlantingAgent 完成")

            return {
                "agent": self.name,
                "success": True,
                "data": {
                    "response": response,
                    "context_used": {
                        "location": location.get("city", "未知"),
                        "weather": f"{weather.get('condition', '未知')}, {weather.get('temperature', 'N/A')}°C",
                        "season": time_info.get("season", "未知"),
                        "history_count": len(conversation_history)
                    }
                }
            }

        except Exception as e:
            self.logger.error(f"❌ PlantingAgent 失败: {e}")
            return {
                "agent": self.name,
                "success": False,
                "error": str(e)
            }

    def _build_context_prompt(self, location: dict, weather: dict, time_info: dict) -> str:
        """构建上下文提示词"""
        parts = []

        # 位置信息
        if location:
            city = location.get("city", "未知")
            parts.append(f"位置：{city}")

        # 天气信息
        if weather:
            condition = weather.get("condition", "未知")
            temp = weather.get("temperature", "N/A")
            parts.append(f"天气：{condition}，{temp}°C")

        # 时间信息
        if time_info:
            season = time_info.get("season", "未知")
            date = time_info.get("date", "未知")
            parts.append(f"时间：{date}，{season}")

        if parts:
            return "当前环境信息：\n" + "、".join(parts)
        return ""

    def _build_full_prompt(self, user_message: str, context_prompt: str, conversation_history: list) -> str:
        """构建完整提示词"""
        parts = []

        # 系统角色
        parts.append("你是一个专业的种植顾问助手。请根据用户的问题和环境信息，提供详细的种植建议。")

        # 上下文信息
        if context_prompt:
            parts.append(f"\n{context_prompt}")

        # 历史对话提示
        if conversation_history:
            parts.append(f"\n注意：用户之前有{len(conversation_history)}条对话历史，请考虑上下文关系。")

        # 用户问题
        parts.append(f"\n用户问题：{user_message}")

        return "\n".join(parts)
