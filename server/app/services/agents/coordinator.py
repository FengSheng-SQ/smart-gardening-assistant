"""
Agent协调器
协调多个Agent协作，处理专家模式请求
"""
import logging
from typing import Dict, List
from app.services.agents.location_agent import LocationAgent
from app.services.agents.weather_agent import WeatherAgent
from app.services.agents.time_agent import TimeAgent
from app.services.agents.planting_agent import PlantingAgent
from app.core.database import Database
from app.core.config import settings


logger = logging.getLogger(__name__)


class ExpertCoordinator:
    """专家模式协调器"""

    def __init__(self):
        self.location_agent = LocationAgent()
        self.weather_agent = WeatherAgent()
        self.time_agent = TimeAgent()
        self.planting_agent = PlantingAgent()
        self.logger = logger

    async def process(self, message: str, user_id: int, image_base64: str = None, location: dict = None) -> dict:
        """
        处理专家模式请求

        Args:
            message: 用户消息
            user_id: 用户ID
            image_base64: 图片base64（可选）
            location: 前端提供的位置信息（可选）

        Returns:
            处理结果字典
        """
        self.logger.info("=" * 80)
        self.logger.info("🚀 ExpertCoordinator 开始处理专家模式请求")
        self.logger.info(f"   用户消息: {message[:50]}...")
        self.logger.info(f"   用户ID: {user_id}")
        if location:
            self.logger.info(f"   前端位置: {location}")
        else:
            self.logger.info("   无前端位置，将由Agent获取")
        self.logger.info("=" * 80)

        try:
            # 1. 获取历史记录
            history_limit = settings.CHAT_HISTORY_LIMIT
            self.logger.info(f"📚 加载最近 {history_limit} 条历史记录")
            history = Database.get_chat_history(user_id, limit=history_limit)
            conversation_history = self._build_conversation_history(history)
            self.logger.info(f"✅ 转换了 {len(conversation_history)} 条对话历史")

            # 2. 并行调用各Agent获取信息
            self.logger.info("🤖 启动Agent团队...")

            # 检查是否有前端提供的位置
            if location and location.get("source"):
                self.logger.info(f"✅ 使用前端提供的位置: {location}")
                # 使用前端位置，跳过LocationAgent
                agent_results = {
                    "location": {
                        "success": True,
                        "data": location
                    }
                }
                # 仍然需要获取时间和天气
                import asyncio
                results = await asyncio.gather(
                    self.time_agent.execute({"user_message": message}),
                    return_exceptions=True
                )

                for result in results:
                    if isinstance(result, Exception):
                        self.logger.error(f"Agent执行异常: {result}")
                        continue
                    agent_name = result.get("agent", "unknown")
                    agent_results[agent_name.replace("Agent", "").lower()] = result

                # 获取天气（依赖位置）
                if "location" in agent_results and agent_results["location"].get("success"):
                    location_data = agent_results["location"]["data"]
                    weather_result = await self.weather_agent.execute({
                        "user_message": message,
                        "location": location_data
                    })
                    agent_results["weather"] = weather_result
            else:
                # 没有前端位置，让Agent自行获取
                agent_results = await self._execute_agents(message)

            # 3. 构建完整上下文
            context = {
                "user_message": message,
                "conversation_history": conversation_history,
                "location": agent_results.get("location", {}).get("data", {}),
                "weather": agent_results.get("weather", {}).get("data", {}),
                "time": agent_results.get("time", {}).get("data", {})
            }

            # 4. 调用种植Agent生成最终建议
            self.logger.info("🌱 调用PlantingAgent生成最终建议...")
            planting_result = await self.planting_agent.execute(context)

            if planting_result.get("success"):
                response = planting_result["data"]["response"]
                metadata = planting_result["data"].get("context_used", {})

                self.logger.info("✅ 专家模式处理完成")
                self.logger.info(f"   使用了: {metadata}")

                return {
                    "text": response,
                    "chat_mode": "expert",
                    "metadata": {
                        "mode": "expert",
                        "agents_used": ["location", "weather", "time", "planting"],
                        "location": metadata.get("location", "未知"),
                        "weather": metadata.get("weather", "未知"),
                        "season": metadata.get("season", "未知"),
                        "history_count": len(conversation_history)
                    }
                }
            else:
                # 如果种植Agent失败，降级到简单回复
                self.logger.error("❌ PlantingAgent失败，使用降级处理")
                return await self._fallback_processing(message, conversation_history)

        except Exception as e:
            self.logger.error(f"❌ 专家模式处理失败: {e}", exc_info=True)
            # 降级处理
            history = Database.get_chat_history(user_id, limit=settings.CHAT_HISTORY_LIMIT)
            conversation_history = self._build_conversation_history(history)
            return await self._fallback_processing(message, conversation_history)

    async def _execute_agents(self, message: str) -> Dict[str, dict]:
        """
        并行执行各个Agent

        Args:
            message: 用户消息

        Returns:
            各Agent的执行结果
        """
        import asyncio

        # 构建基础上下文
        base_context = {"user_message": message}

        # 并行执行Agent
        results = await asyncio.gather(
            self.location_agent.execute(base_context),
            self.time_agent.execute(base_context),
            return_exceptions=True
        )

        # 处理结果
        agent_results = {}

        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Agent执行异常: {result}")
                continue

            agent_name = result.get("agent", "unknown")
            agent_results[agent_name.replace("Agent", "").lower()] = result

        # 依赖位置Agent的结果执行天气Agent
        if "location" in agent_results and agent_results["location"].get("success"):
            location_data = agent_results["location"]["data"]
            weather_result = await self.weather_agent.execute({
                "user_message": message,
                "location": location_data
            })
            agent_results["weather"] = weather_result

        return agent_results

    def _build_conversation_history(self, history: list) -> list:
        """转换历史记录为LLM格式"""
        conversation = []

        for msg in history:
            if not msg.get("message_text"):
                continue

            role = "user" if msg["is_user"] else "assistant"
            message_text = msg["message_text"]
            message_text = message_text.replace("你: ", "").replace("AI: ", "")
            message_text = message_text.replace("[语音] ", "").replace("[图片] ", "")

            conversation.append({
                "role": role,
                "content": message_text
            })

        return conversation

    async def _fallback_processing(self, message: str, conversation_history: list) -> dict:
        """降级处理：当专家模式失败时使用"""
        from app.services import llm_service

        self.logger.info("⚠️ 使用降级处理")

        # 使用历史记录调用LLM
        response = await llm_service.chat(
            message=message,
            conversation_history=conversation_history
        )

        return {
            "text": response,
            "chat_mode": "expert",
            "metadata": {
                "mode": "expert",
                "fallback": True,
                "agents_used": ["glm_fallback"],
                "history_count": len(conversation_history)
            }
        }
