"""
思考模式实现
结合历史聊天记录，AI可以理解上下文
适合连续性咨询
"""
from app.services.chat_modes.base_mode import BaseChatMode
from app.services import llm_service
from app.core.database import Database
from app.core.config import settings


class ThinkingMode(BaseChatMode):
    """思考模式 - 使用历史记录，理解上下文"""

    async def process(self, message: str, user_id: int, image_base64: str = None) -> str:
        """
        处理用户消息（思考模式）

        Args:
            message: 用户消息文本
            user_id: 用户ID
            image_base64: 图片的base64编码（可选）

        Returns:
            AI回复文本
        """
        self._log_process_start(message, user_id)

        try:
            # 1. 从数据库获取历史记录
            history_limit = settings.CHAT_HISTORY_LIMIT
            self.logger.info(f"📚 加载最近 {history_limit} 条历史记录")

            history = Database.get_chat_history(user_id, limit=history_limit)
            self.logger.info(f"✅ 从数据库获取到 {len(history)} 条历史记录")

            # 2. 转换为LLM格式的历史对话
            conversation_history = self._build_conversation_history(history)
            self.logger.info(f"🔄 转换了 {len(conversation_history)} 条对话历史")

            # 3. 如果有图片，使用视觉模型
            if image_base64:
                self.logger.info("📸 使用视觉模型 + 历史记录")
                response = await llm_service.chat_with_image(
                    message=message,
                    image_base64=image_base64,
                    conversation_history=conversation_history
                )
            else:
                # 纯文本模式，使用历史记录
                self.logger.info(f"🧠 思考模式：使用 {len(conversation_history)} 条历史记录")
                response = await llm_service.chat(
                    message=message,
                    conversation_history=conversation_history
                )

            self._log_process_end(response)
            return response

        except Exception as e:
            self.logger.error(f"❌ 思考模式处理失败: {e}", exc_info=True)
            raise

    def _build_conversation_history(self, history: list) -> list:
        """
        将数据库历史记录转换为LLM格式的对话历史

        Args:
            history: 数据库返回的历史记录列表

        Returns:
            LLM格式的对话历史列表
        """
        conversation = []

        for msg in history:
            # 跳过没有实际内容的消息
            if not msg.get("message_text"):
                continue

            role = "user" if msg["is_user"] else "assistant"

            # 清理消息文本（移除前缀）
            message_text = msg["message_text"]
            message_text = message_text.replace("你: ", "").replace("AI: ", "")
            message_text = message_text.replace("[语音] ", "").replace("[图片] ", "")

            conversation.append({
                "role": role,
                "content": message_text
            })

        self.logger.debug(f"对话历史: {conversation}")
        return conversation
