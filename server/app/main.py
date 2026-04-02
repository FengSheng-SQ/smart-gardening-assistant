from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import api_router
from app.core.config import settings
from pathlib import Path
import logging


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# 设置 uvicorn 和 fastapi 的日志级别
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logging.getLogger("fastapi").setLevel(logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI(
        title="智能种植助手API",
        description="本地服务器API",
        version="0.1.0"
    )

    # CORS配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 路由
    app.include_router(api_router)

    # 静态文件服务 - 图片和音频
    data_dir = Path("data")
    if data_dir.exists():
        app.mount("/data", StaticFiles(directory="data"), name="data")
        logging.info(f"✅ 静态文件服务已启用: /data -> {data_dir.absolute()}")
    else:
        data_dir.mkdir(parents=True, exist_ok=True)
        app.mount("/data", StaticFiles(directory="data"), name="data")
        logging.info(f"✅ 静态文件服务已创建: {data_dir.absolute()}")

    return app


app = create_app()


@app.on_event("startup")
async def startup_event():
    """启动时初始化服务"""
    # 初始化数据库
    from app.core.database import init_db
    print("🗄️  正在初始化数据库...")
    init_db()

    # 初始化ASR服务
    from app.services import asr_service
    await asr_service.initialize()

    # 初始化MCP服务器（如果启用）
    if settings.WEATHER_USE_MCP:
        try:
            from app.services.mcp import initialize_mcp_servers
            print("🔧 正在初始化MCP服务器...")
            success = await initialize_mcp_servers({
                "weather": settings.WEATHER_MCP_COMMAND
            })
            if success:
                print("✅ MCP服务器初始化成功")
            else:
                print("⚠️ MCP服务器初始化失败，天气服务将使用API方式")
        except Exception as e:
            print(f"❌ MCP服务器初始化失败: {e}")
            print("   将使用API方式获取天气信息")
    else:
        print("ℹ️  MCP未启用，天气服务将使用API方式")

    # 初始化Coqui TTS（如果启用）
    if settings.USE_COQUI_TTS:
        try:
            from app.services.coqui_tts_service import getCoquiTts
            print("🔧 正在初始化Coqui TTS...")
            print("   首次运行会自动下载模型，请耐心等待...")
            tts = getCoquiTts()
            if tts and tts.is_available:
                print("✅ Coqui TTS初始化成功")
            else:
                print("⚠️ Coqui TTS初始化失败")
        except ImportError:
            print("⚠️ TTS未安装，将不使用语音合成")
            print("   安装方法: pip install TTS")
        except Exception as e:
            print(f"❌ Coqui TTS初始化失败: {e}")
            print("   将不使用语音合成")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理资源"""
    # 关闭MCP服务器（如果启用）
    if settings.WEATHER_USE_MCP:
        try:
            from app.services.mcp import shutdown_mcp_servers
            print("🛑 正在关闭MCP服务器...")
            await shutdown_mcp_servers()
            print("✅ MCP服务器已关闭")
        except Exception as e:
            print(f"❌ 关闭MCP服务器时出错: {e}")

    # 关闭LLM服务
    from app.services import llm_service
    await llm_service.close()
