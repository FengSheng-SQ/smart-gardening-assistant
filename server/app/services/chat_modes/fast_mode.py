"""
快速模式实现
仅根据当前输入内容进行回复，不使用历史记录
适合快速问答
"""
from app.services.chat_modes.base_mode import BaseChatMode
from app.services import llm_service


class FastMode(BaseChatMode):
    """快速模式 - 无历史记录，响应最快"""

    async def process(self, message: str, user_id: int, image_base64: str = None) -> str:
        """
        处理用户消息（快速模式）

        Args:
            message: 用户消息文本
            user_id: 用户ID
            image_base64: 图片的base64编码（可选）

        Returns:
            AI回复文本
        """
        self._log_process_start(message, user_id)

        try:
            # 如果有图片，使用视觉模型
            if image_base64:
                self.logger.info("📸 使用视觉模型处理图片")
                response = await llm_service.chat_with_image(
                    message=message,
                    image_base64=image_base64,
                    conversation_history=[]
                )
            else:
                # 纯文本模式，不传递历史记录
                self.logger.info("⚡ 快速模式：不使用历史记录")
                response = await llm_service.chat(
                    message=message,
                    conversation_history=[]
                )

            self._log_process_end(response)
            return response

        except Exception as e:
            self.logger.error(f"❌ 快速模式处理失败: {e}", exc_info=True)
            raise
