import httpx
import base64
from typing import Optional, List
from app.core.config import settings


class LLMService:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=settings.LLM_API_URL,
            headers={
                "Authorization": f"Bearer {settings.LLM_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=httpx.Timeout(
                connect=10.0,
                read=120.0,  # 视觉模型需要更长时间处理图片
                write=10.0,
                pool=10.0
            )
        )

    async def chat(self, message: str, conversation_history: list = None) -> str:
        """
        使用LLM文本模型进行对话
        用于回答种植问题、提供咨询
        """
        if conversation_history is None:
            conversation_history = []

        messages = [
            {
                "role": "system",
                "content": "你是一个专业的种植顾问助手。请用简洁、友好的语言回答用户的种植问题。提供实用的种植建议，包括浇水、施肥、病虫害防治等。"
            }
        ]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})

        response = await self.client.post(
            settings.LLM_API_URL,
            json={
                "model": settings.LLM_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 3000  # 增加到3000，避免回复被截断
            }
        )

        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def analyze_plant_image(self, image_base64: str, question: str = None) -> str:
        """
        使用LLM视觉模型分析植株照片
        用于识别植株生长状况、病虫害等

        Args:
            image_base64: base64编码的图片数据
            question: 用户问题（可选）

        Returns:
            分析结果
        """
        if question is None:
            question = "这是什么植物？生长状况如何？需要注意什么？"

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"你是专业种植顾问。分析这张植物照片：{question}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]

        response = await self.client.post(
            settings.LLM_API_URL,
            json={
                "model": settings.LLM_VISION_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1500
            }
        )

        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def chat_with_image(self, message: str, image_base64: str, conversation_history: list = None) -> str:
        """
        结合图片和文本的对话
        用户可以发送照片并提问
        """
        if conversation_history is None:
            conversation_history = []

        messages = [
            {
                "role": "system",
                "content": "你是一个专业的种植顾问助手。你可以分析植物照片，回答用户的种植问题。请提供详细、实用的建议。"
            }
        ]

        # 添加历史对话（纯文本的历史）
        for msg in conversation_history:
            messages.append(msg)

        # 添加当前消息（包含图片）
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": message
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                }
            ]
        })

        response = await self.client.post(
            settings.LLM_API_URL,
            json={
                "model": settings.LLM_VISION_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1500
            }
        )

        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def close(self):
        await self.client.aclose()


llm_service = LLMService()
