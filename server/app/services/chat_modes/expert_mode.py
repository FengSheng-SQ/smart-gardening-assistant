"""
专家模式实现
多Agent协作，获取位置、天气、时间等信息，提供专业建议
"""
from app.services.chat_modes.base_mode import BaseChatMode
from app.services.agents.coordinator import ExpertCoordinator
from app.services.utils import get_location_extractor


class ExpertMode(BaseChatMode):
    """专家模式 - 多Agent协作"""

    def __init__(self):
        super().__init__()
        self.coordinator = ExpertCoordinator()
        self.location_extractor = get_location_extractor()

    async def process(self, message: str, user_id: int, image_base64: str = None, location: dict = None) -> str:
        """
        处理用户消息（专家模式）

        Args:
            message: 用户消息文本
            user_id: 用户ID
            image_base64: 图片的base64编码（可选）
            location: 位置信息字典（可选）

        Returns:
            AI回复文本
        """
        self._log_process_start(message, user_id)
        if location:
            self.logger.info(f"📍 收到前端位置信息: {location}")

        try:
            # 智能地点提取：从用户消息中提取地点，如果有明确提到则使用提取的地点
            final_location = location
            if location:
                final_location = self.location_extractor.get_location_for_query(message, location)
                if final_location.get('source') == 'nlp_extracted':
                    self.logger.info(f"🎯 使用NLP提取的地点: {final_location['city']}（覆盖GPS: {location.get('city')}）")

            # 如果有图片，暂时不支持（后续可以扩展）
            if image_base64:
                self.logger.warning("⚠️ 专家模式暂不支持图片，使用降级处理")
                # 降级到简单处理
                from app.services import llm_service
                response = await llm_service.chat_with_image(
                    message=message,
                    image_base64=image_base64,
                    conversation_history=[]
                )
            else:
                # 使用协调器处理
                self.logger.info("👨‍🔬 启动专家模式Agent团队")
                result = await self.coordinator.process(message, user_id, location=final_location)

                # 提取回复文本
                response = result.get("text", "抱歉，专家模式暂时无法处理您的问题。")

                # 记录元数据
                metadata = result.get("metadata", {})
                if metadata:
                    self.logger.info(f"📊 专家模式元数据: {metadata}")

            self._log_process_end(response)
            return response

        except Exception as e:
            self.logger.error(f"❌ 专家模式处理失败: {e}", exc_info=True)
            raise
