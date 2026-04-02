import asyncio
import sys
import uvicorn
from app.core.config import settings


if __name__ == "__main__":
    # Windows 上设置 ProactorEventLoopPolicy 以支持子进程
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # 禁用 reload 模式（Windows上MCP不支持）
    # 如需代码热重载，请使用 start_server.py 或依赖前端热重载
    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=False,  # 必须禁用 reload
        log_level="info"
    )
