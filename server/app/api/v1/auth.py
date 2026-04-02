"""
用户认证API
"""
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse
from app.core.database import Database
import secrets


router = APIRouter(prefix="/auth", tags=["用户认证"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """用户登录"""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"🔐 登录尝试: username={request.username}")

    user = Database.get_user_by_username(request.username)

    if not user:
        logger.warning(f"❌ 用户不存在: {request.username}")
        return LoginResponse(
            success=False,
            message="用户名或密码错误"
        )

    logger.info(f"✅ 用户存在: id={user['id']}")

    # 验证密码
    is_valid = Database.verify_password(request.password, user["password_hash"])
    logger.info(f"🔑 密码验证结果: {is_valid}")

    if not is_valid:
        logger.warning(f"❌ 密码错误: {request.username}")
        return LoginResponse(
            success=False,
            message="用户名或密码错误"
        )

    # 更新最后登录时间
    Database.update_last_login(user["id"])

    # 生成简单的token（生产环境应使用JWT）
    token = secrets.token_hex(32)

    logger.info(f"✅ 登录成功: {request.username}, user_id={user['id']}")

    return LoginResponse(
        success=True,
        message="登录成功",
        user_id=user["id"],
        username=user["username"],
        token=token
    )


@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    """用户注册"""
    # 验证用户名长度
    if len(request.username) < 3:
        return RegisterResponse(
            success=False,
            message="用户名至少需要3个字符"
        )

    # 验证密码长度
    if len(request.password) < 6:
        return RegisterResponse(
            success=False,
            message="密码至少需要6个字符"
        )

    # 创建用户
    user_id = Database.create_user(request.username, request.password)

    if user_id is None:
        return RegisterResponse(
            success=False,
            message="用户名已存在"
        )

    return RegisterResponse(
        success=True,
        message="注册成功",
        user_id=user_id
    )
