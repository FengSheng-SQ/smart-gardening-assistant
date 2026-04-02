from fastapi import APIRouter, WebSocket, Query, status, WebSocketDisconnect
from typing import Optional
import logging
import json
from app.services import asr_service, tts_service, llm_service
from app.core.config import settings
from app.core.database import Database
from app.api.v1.websocket import VoiceChatManager

logger = logging.getLogger(__name__)

router = APIRouter()
manager = VoiceChatManager()

# 导入子路由
from app.api.v1 import auth, chat

# 包含认证和聊天记录路由
router.include_router(auth.router)
router.include_router(chat.router)


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    token: str = Query(None, description="访问令牌"),
    user_id: Optional[int] = Query(None, description="用户ID（登录用户必填）")
):
    """WebSocket端点 - 带Token验证"""

    # 验证Token
    if not token:
        logger.warning(f"连接被拒绝: 缺少token (client_id={client_id})")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return

    if token != settings.WS_TOKEN:
        logger.warning(f"连接被拒绝: 无效token (client_id={client_id})")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    logger.info(f"新连接: client_id={client_id}, user_id={user_id}")

    await manager.connect(websocket, client_id, user_id)
    await websocket.send_json({"type": "connected", "message": "WebSocket连接成功"})

    try:
        while True:
            # 接收消息
            message = await websocket.receive()

            # 处理音频数据
            if "bytes" in message:
                logger.info(f"收到音频数据: {len(message['bytes'])} bytes")
                await manager.handle_audio(client_id, message["bytes"])

            # 处理文本消息（用于调试和纯文本对话）
            elif "text" in message:
                logger.info(f"收到文本消息: {message['text']}")
                try:
                    data = json.loads(message["text"])
                    logger.info(f"解析后的JSON: {data}")

                    if data.get("type") == "text":
                        # 文本对话
                        text = data.get("text", "")
                        chat_mode = data.get("chat_mode", "fast")  # 获取聊天模式，默认fast
                        location = data.get("location")  # 获取位置信息
                        logger.info(f"处理文本对话: {text}, 模式: {chat_mode}, 位置: {location}")
                        await manager.handle_text(client_id, text, chat_mode, location)

                    elif data.get("type") == "image":
                        # 图片分析
                        image_base64 = data.get("image", "")
                        question = data.get("question", None)
                        chat_mode = data.get("chat_mode", "fast")  # 获取聊天模式，默认fast
                        location = data.get("location")  # 获取位置信息
                        logger.info(f"处理图片分析: question={question}, 模式: {chat_mode}, 位置: {location}")
                        await manager.handle_image(client_id, image_base64, question, chat_mode, location)

                    elif data.get("type") == "prepare_image_with_audio":
                        # 准备图片+语音模式（先保存图片，等待音频）
                        image_base64 = data.get("image", "")
                        logger.info(f"📸 准备图片+语音模式，保存图片数据，等待音频...")
                        manager.pending_images[client_id] = image_base64
                        await websocket.send_json({
                            "type": "status",
                            "message": "图片已准备，请发送语音..."
                        })

                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e} - 原始消息: {message['text']}")
                    await websocket.send_json({
                        "type": "error",
                        "message": f"JSON解析失败: {str(e)}"
                    })
                except Exception as e:
                    logger.error(f"处理文本消息错误: {e}", exc_info=True)
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"处理失败: {str(e)}"
                        })
                    except Exception:
                        pass  # 连接已关闭，忽略发送错误

    except WebSocketDisconnect:
        logger.info(f"客户端正常断开: client_id={client_id}")
        manager.disconnect(client_id)
    except Exception as e:
        # 检查是否是客户端正常断开
        error_msg = str(e)
        if "disconnect" in error_msg.lower() or "closed" in error_msg.lower():
            logger.info(f"客户端正常断开: client_id={client_id}")
        else:
            logger.error(f"连接错误: {e}", exc_info=True)
        manager.disconnect(client_id)


