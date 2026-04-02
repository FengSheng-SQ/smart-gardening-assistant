import json
import os
import uuid
import logging
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect, Query, status
from app.services import asr_service, llm_service
from app.core.config import settings
from app.core.database import Database
from app.services.chat_modes import FastMode, ThinkingMode, ExpertMode

# 尝试导入Coqui TTS
try:
    from app.services.coqui_tts_service import getCoquiTts
    COQUI_TTS_AVAILABLE = True
except ImportError:
    COQUI_TTS_AVAILABLE = False
    getCoquiTts = None

logger = logging.getLogger(__name__)


class VoiceChatManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.user_connections: dict[str, Optional[int]] = {}  # client_id -> user_id
        self.pending_images: dict[str, str] = {}  # client_id -> image_base64 (等待音频的图片)

    async def connect(self, websocket: WebSocket, client_id: str, user_id: Optional[int] = None):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.user_connections[client_id] = user_id
        logger.info(f"✅ 客户端已连接: client_id={client_id}, user_id={user_id}")
        logger.info(f"📊 当前活跃连接数: {len(self.active_connections)}")
        logger.info(f"📊 已保存的user_ids: {list(self.user_connections.values())}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.user_connections:
            del self.user_connections[client_id]
        if client_id in self.pending_images:
            del self.pending_images[client_id]

    async def handle_audio(self, client_id: str, audio_data: bytes):
        """处理音频数据"""
        websocket = self.active_connections.get(client_id)
        user_id = self.user_connections.get(client_id)

        # 检查是否有待处理的图片
        image_base64 = self.pending_images.get(client_id)
        is_image_with_voice = image_base64 is not None

        # 清除待处理的图片
        if client_id in self.pending_images:
            del self.pending_images[client_id]

        if not websocket:
            return

        # 保存音频文件
        audio_filename = f"{uuid.uuid4()}.wav"
        audio_path = f"data/audio/{audio_filename}"
        os.makedirs("data/audio", exist_ok=True)

        with open(audio_path, "wb") as f:
            f.write(audio_data)

        try:
            if is_image_with_voice:
                # 图片+语音模式
                # 1. 语音识别
                await websocket.send_json({"type": "status", "message": "正在识别..."})
                text = await asr_service.transcribe(audio_path)
                await websocket.send_json({"type": "transcription", "text": text})

                # 保存用户消息到数据库
                if user_id:
                    Database.save_chat_message(
                        user_id=user_id,
                        message_text=f"[语音] {text}",
                        is_user=True,
                        audio_filename=audio_filename
                    )

                # 2. 调用LLM视觉模型
                await websocket.send_json({"type": "status", "message": "正在分析图片..."})
                response = await llm_service.chat_with_image(text, image_base64)

                # 保存AI回复到数据库
                if user_id:
                    Database.save_chat_message(
                        user_id=user_id,
                        message_text=response,
                        is_user=False
                    )

                # 发送响应
                await websocket.send_json({
                    "type": "response",
                    "text": response
                })
            else:
                # 纯语音模式
                # 1. 语音识别
                await websocket.send_json({"type": "status", "message": "正在识别..."})
                text = await asr_service.transcribe(audio_path)
                await websocket.send_json({"type": "transcription", "text": text})

                # 保存用户消息到数据库
                if user_id:
                    Database.save_chat_message(
                        user_id=user_id,
                        message_text=f"[语音] {text}",
                        is_user=True,
                        audio_filename=audio_filename
                    )

                # 2. 调用LLM
                await websocket.send_json({"type": "status", "message": "正在思考..."})
                response = await llm_service.chat(text)

                # 3. 语音合成
                await websocket.send_json({"type": "status", "message": "正在合成语音..."})
                tts_filename = f"{uuid.uuid4()}.wav"
                tts_path = f"data/audio/{tts_filename}"

                # 使用Coqui TTS（如果配置了且可用）
                if settings.USE_COQUI_TTS and COQUI_TTS_AVAILABLE:
                    try:
                        coqui_tts = getCoquiTts()
                        if coqui_tts and coqui_tts.is_available:
                            logger.info("使用Coqui TTS合成语音")
                            coqui_tts.synthesize(response, tts_path)

                            # 读取音频文件并发送
                            with open(tts_path, "rb") as f:
                                audio_bytes = f.read()

                            # 发送响应
                            await websocket.send_json({
                                "type": "response",
                                "text": response,
                                "audio_filename": tts_filename
                            })
                            await websocket.send_bytes(audio_bytes)

                            # 保存AI回复到数据库
                            if user_id:
                                Database.save_chat_message(
                                    user_id=user_id,
                                    message_text=response,
                                    is_user=False,
                                    audio_filename=tts_filename
                                )
                        else:
                            logger.warning("Coqui TTS不可用，仅发送文本回复")
                            # 仅发送文本响应
                            await websocket.send_json({
                                "type": "response",
                                "text": response
                            })
                            # 保存AI回复到数据库
                            if user_id:
                                Database.save_chat_message(
                                    user_id=user_id,
                                    message_text=response,
                                    is_user=False
                                )
                    except Exception as e:
                        logger.error(f"Coqui TTS合成失败: {e}，仅发送文本回复")
                        # 仅发送文本响应
                        await websocket.send_json({
                            "type": "response",
                            "text": response
                        })
                        # 保存AI回复到数据库
                        if user_id:
                            Database.save_chat_message(
                                user_id=user_id,
                                message_text=response,
                                is_user=False
                            )
                else:
                    # 不使用TTS，仅发送文本响应
                    await websocket.send_json({
                        "type": "response",
                        "text": response
                    })
                    # 保存AI回复到数据库
                    if user_id:
                        Database.save_chat_message(
                            user_id=user_id,
                            message_text=response,
                            is_user=False
                        )

        except Exception as e:
            logger.error(f"处理音频时出错: {e}")
            if websocket:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

                # 2. 调用LLM
                await websocket.send_json({"type": "status", "message": "正在思考..."})
                response = await llm_service.chat(text)

                # 3. 语音合成
                await websocket.send_json({"type": "status", "message": "正在合成语音..."})
                tts_filename = f"{uuid.uuid4()}.wav"
                tts_path = f"data/audio/{tts_filename}"

                # 使用Coqui TTS（如果配置了且可用）
                if settings.USE_COQUI_TTS and COQUI_TTS_AVAILABLE:
                    try:
                        coqui_tts = getCoquiTts()
                        if coqui_tts and coqui_tts.is_available:
                            logger.info("使用Coqui TTS合成语音")
                            coqui_tts.synthesize(response, tts_path)

                            # 读取音频文件并发送
                            with open(tts_path, "rb") as f:
                                audio_bytes = f.read()

                            # 发送响应
                            await websocket.send_json({
                                "type": "response",
                                "text": response,
                                "audio_filename": tts_filename
                            })
                            await websocket.send_bytes(audio_bytes)

                            # 保存AI回复到数据库
                            if user_id:
                                Database.save_chat_message(
                                    user_id=user_id,
                                    message_text=response,
                                    is_user=False,
                                    audio_filename=tts_filename
                                )
                        else:
                            logger.warning("Coqui TTS不可用，仅发送文本回复")
                            # 仅发送文本响应
                            await websocket.send_json({
                                "type": "response",
                                "text": response
                            })
                            # 保存AI回复到数据库
                            if user_id:
                                Database.save_chat_message(
                                    user_id=user_id,
                                    message_text=response,
                                    is_user=False
                                )
                    except Exception as e:
                        logger.error(f"Coqui TTS合成失败: {e}，仅发送文本回复")
                        # 仅发送文本响应
                        await websocket.send_json({
                            "type": "response",
                            "text": response
                        })
                        # 保存AI回复到数据库
                        if user_id:
                            Database.save_chat_message(
                                user_id=user_id,
                                message_text=response,
                                is_user=False
                            )
                else:
                    # 不使用TTS，仅发送文本响应
                    await websocket.send_json({
                        "type": "response",
                        "text": response
                    })
                    # 保存AI回复到数据库
                    if user_id:
                        Database.save_chat_message(
                            user_id=user_id,
                            message_text=response,
                            is_user=False
                        )

    async def handle_text(self, client_id: str, text: str, chat_mode: str = "fast", location: dict = None):
        """处理文本消息"""
        websocket = self.active_connections.get(client_id)
        user_id = self.user_connections.get(client_id)

        logger.info(f"📝 收到文本消息: client_id={client_id}, user_id={user_id}, chat_mode={chat_mode}")
        logger.info(f"📝 消息内容: {text[:50]}...")
        if location:
            logger.info(f"📍 收到位置信息: {location}")

        if not websocket:
            logger.warning("❌ WebSocket连接不存在")
            return

        try:
            # 保存用户消息到数据库
            if user_id:
                logger.info(f"💾 准备保存用户消息到数据库: user_id={user_id}, chat_mode={chat_mode}")
                msg_id = Database.save_chat_message(
                    user_id=user_id,
                    message_text=text,
                    is_user=True,
                    image_filename=None,
                    chat_mode=chat_mode
                )
                logger.info(f"✅ 用户消息已保存: message_id={msg_id}")
            else:
                logger.warning("⚠️  user_id为空，跳过保存")

            # 发送状态消息
            await websocket.send_json({
                "type": "status",
                "message": "正在思考..."
            })

            # 根据聊天模式调用相应的处理逻辑
            if chat_mode == "fast":
                # 快速模式：不使用历史记录
                logger.info("⚡ 使用快速模式处理")
                fast_mode = FastMode()
                response = await fast_mode.process(text, user_id or 0)
            elif chat_mode == "thinking":
                # 思考模式：使用历史记录
                logger.info("🧠 使用思考模式处理")
                thinking_mode = ThinkingMode()
                response = await thinking_mode.process(text, user_id or 0)
            elif chat_mode == "expert":
                # 专家模式：多Agent协作
                logger.info("👨‍🔬 使用专家模式处理")
                expert_mode = ExpertMode()
                response = await expert_mode.process(text, user_id or 0, location=location)
            else:
                # 其他模式暂时使用默认LLM服务
                logger.info(f"ℹ️ 暂未实现的模式: {chat_mode}，使用默认处理")
                response = await llm_service.chat(text)

            logger.info(f"💬 AI回复: {response[:100]}...")

            # 保存AI回复到数据库
            if user_id:
                logger.info(f"💾 准备保存AI回复到数据库: user_id={user_id}, chat_mode={chat_mode}")
                msg_id = Database.save_chat_message(
                    user_id=user_id,
                    message_text=response,
                    is_user=False,
                    image_filename=None,
                    chat_mode=chat_mode
                )
                logger.info(f"✅ AI回复已保存: message_id={msg_id}")
            else:
                logger.warning("⚠️  user_id为空，跳过保存AI回复")

            # 发送响应
            await websocket.send_json({
                "type": "response",
                "text": response,
                "chat_mode": chat_mode
            })
            logger.info("✅ 响应已发送")

        except Exception as e:
            logger.error(f"❌ 处理文本消息错误: {e}", exc_info=True)
            await websocket.send_json({
                "type": "error",
                "message": f"处理失败: {str(e)}"
            })

    async def handle_image(self, client_id: str, image_base64: str, question: str = None, chat_mode: str = "fast", location: dict = None):
        """处理图片消息"""
        websocket = self.active_connections.get(client_id)
        user_id = self.user_connections.get(client_id)

        logger.info(f"📸 收到图片消息: client_id={client_id}, user_id={user_id}, chat_mode={chat_mode}")
        logger.info(f"📸 图片数据长度: {len(image_base64)} 字符")
        logger.info(f"📸 问题: {question}")
        if location:
            logger.info(f"📍 收到位置信息: {location}")

        if not websocket:
            logger.warning("❌ WebSocket连接不存在")
            return

        try:
            # 设置默认问题
            if question is None or question.strip() == "":
                question = "这是什么植物？生长状况如何？需要注意什么？"
                logger.info(f"📸 使用默认问题: {question}")

            # 保存图片文件
            import base64
            image_filename = None
            try:
                image_filename = f"{uuid.uuid4()}.jpg"
                image_path = f"data/images/{image_filename}"
                os.makedirs("data/images", exist_ok=True)

                # 解码base64并保存图片
                image_data = base64.b64decode(image_base64)
                with open(image_path, "wb") as f:
                    f.write(image_data)

                logger.info(f"✅ 图片已保存: {image_path}")
            except Exception as img_err:
                logger.error(f"❌ 保存图片失败: {img_err}")
                image_filename = None

            # 保存用户消息到数据库
            if user_id:
                logger.info(f"💾 准备保存图片消息到数据库: user_id={user_id}, chat_mode={chat_mode}")
                msg_id = Database.save_chat_message(
                    user_id=user_id,
                    message_text=f"[图片] {question}",
                    is_user=True,
                    image_filename=image_filename,
                    chat_mode=chat_mode
                )
                logger.info(f"✅ 图片消息已保存: message_id={msg_id}")
            else:
                logger.warning("⚠️  user_id为空，跳过保存图片消息")

            # 发送状态消息
            logger.info("📤 发送状态消息: 正在分析图片...")
            await websocket.send_json({
                "type": "status",
                "message": "正在分析图片..."
            })

            # 调用LLM视觉模型
            logger.info("=" * 60)
            logger.info("🔍 开始调用LLM视觉模型...")
            logger.info(f"🔍 模型: {getattr(llm_service, 'model', 'unknown')}")
            logger.info(f"🔍 问题: {question}")
            logger.info(f"🔍 图片前100字符: {image_base64[:100]}...")

            try:
                response = await llm_service.chat_with_image(question, image_base64)
                logger.info(f"✅ LLM视觉模型响应成功")
                logger.info(f"📝 响应长度: {len(response)} 字符")
                logger.info(f"📝 响应前200字符: {response[:200]}...")
            except Exception as glm_error:
                logger.error(f"❌ LLM视觉模型调用失败: {glm_error}", exc_info=True)
                raise glm_error

            logger.info("=" * 60)

            # 保存AI回复到数据库
            if user_id:
                logger.info(f"💾 准备保存AI回复到数据库: user_id={user_id}, chat_mode={chat_mode}")
                msg_id = Database.save_chat_message(
                    user_id=user_id,
                    message_text=response,
                    is_user=False,
                    image_filename=None,
                    chat_mode=chat_mode
                )
                logger.info(f"✅ AI回复已保存: message_id={msg_id}")
            else:
                logger.warning("⚠️  user_id为空，跳过保存AI回复")

            # 发送响应
            logger.info("📤 发送最终响应给客户端...")
            await websocket.send_json({
                "type": "response",
                "text": response,
                "chat_mode": chat_mode
            })
            logger.info("✅ 图片分析响应已发送")

        except Exception as e:
            logger.error(f"❌ 处理图片消息错误: {e}", exc_info=True)
            logger.error(f"❌ 错误类型: {type(e).__name__}")
            logger.error(f"❌ 错误详情: {str(e)}")
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": f"图片分析失败: {str(e)}"
                })
            except Exception as send_error:
                logger.error(f"❌ 发送错误消息失败: {send_error}")


manager = VoiceChatManager()
