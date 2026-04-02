"""
聊天记录API
"""
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import ChatHistoryResponse, ClearChatResponse, ChatMessage
from app.core.database import Database
from typing import Optional


router = APIRouter(prefix="/chat", tags=["聊天记录"])


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    user_id: int = Query(..., description="用户ID"),
    limit: int = Query(100, description="返回消息数量限制", ge=1, le=500)
):
    """获取用户聊天历史"""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"📜 获取聊天历史: user_id={user_id}, limit={limit}")

    try:
        messages = Database.get_chat_history(user_id, limit)
        logger.info(f"📜 从数据库获取到 {len(messages)} 条消息")

        # 转换为响应模型
        message_models = [
            ChatMessage(
                id=msg["id"],
                message_text=msg["message_text"],
                is_user=bool(msg["is_user"]),
                audio_filename=msg["audio_filename"],
                image_filename=msg["image_filename"],
                created_at=msg["created_at"]
            )
            for msg in messages
        ]

        logger.info(f"✅ 返回 {len(message_models)} 条消息")

        return ChatHistoryResponse(
            success=True,
            messages=message_models
        )
    except Exception as e:
        logger.error(f"❌ 获取聊天历史失败: {e}")
        return ChatHistoryResponse(
            success=False,
            messages=[]
        )


@router.delete("/clear", response_model=ClearChatResponse)
async def clear_chat_history(
    user_id: int = Query(..., description="用户ID")
):
    """清空用户聊天历史"""
    try:
        count = Database.clear_chat_history(user_id)
        return ClearChatResponse(
            success=True,
            message=f"已清空 {count} 条聊天记录"
        )
    except Exception as e:
        return ClearChatResponse(
            success=False,
            message=f"清空失败: {str(e)}"
        )


@router.post("/save")
async def save_chat_message(
    user_id: int,
    message_text: str,
    is_user: bool,
    audio_filename: Optional[str] = None,
    image_filename: Optional[str] = None
):
    """保存聊天消息（内部API，供WebSocket调用）"""
    try:
        message_id = Database.save_chat_message(
            user_id=user_id,
            message_text=message_text,
            is_user=is_user,
            audio_filename=audio_filename,
            image_filename=image_filename
        )
        return {"success": True, "message_id": message_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/message/{message_id}")
async def delete_chat_message(
    message_id: int,
    user_id: int = Query(..., description="用户ID")
):
    """删除单条聊天消息"""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"🗑️  请求删除消息: message_id={message_id}, user_id={user_id}")

    try:
        success = Database.delete_chat_message(message_id, user_id)
        if success:
            return {
                "success": True,
                "message": "消息已删除"
            }
        else:
            return {
                "success": False,
                "message": "消息不存在或无权删除"
            }
    except Exception as e:
        logger.error(f"❌ 删除消息API错误: {e}")
        return {
            "success": False,
            "message": f"删除失败: {str(e)}"
        }


@router.delete("/messages")
async def delete_chat_messages(
    message_ids: str = Query(..., description="消息ID列表，逗号分隔"),
    user_id: int = Query(..., description="用户ID")
):
    """批量删除聊天消息"""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"🗑️  请求批量删除消息: user_id={user_id}")

    try:
        # 解析消息ID列表
        id_list = [int(id.strip()) for id in message_ids.split(',') if id.strip()]
        logger.info(f"📋 解析到的消息ID列表: {id_list}")

        deleted_count = Database.delete_chat_messages(id_list, user_id)
        return {
            "success": True,
            "message": f"已删除 {deleted_count} 条消息",
            "deleted_count": deleted_count
        }
    except ValueError as e:
        logger.error(f"❌ 消息ID格式错误: {e}")
        return {
            "success": False,
            "message": "消息ID格式错误"
        }
    except Exception as e:
        logger.error(f"❌ 批量删除消息API错误: {e}")
        return {
            "success": False,
            "message": f"删除失败: {str(e)}"
        }
