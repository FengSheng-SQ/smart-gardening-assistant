"""
自定义Uvicorn启动脚本
解决Windows上MCP子进程问题
"""
import asyncio
import sys
import multiprocessing
import uvicorn
from app.core.config import settings


def run_server():
    """在子进程中运行服务器"""
    # Windows 上设置事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=False,  # 使用自定义reloader
        log_level="info"
    )


if __name__ == "__main__":
    # Windows 上需要的启动方式
    if sys.platform == "win32":
        # 直接运行，不使用多进程
        run_server()
    else:
        # Unix系统可以使用多进程
        multiprocessing.set_start_method("spawn")
        run_server()
