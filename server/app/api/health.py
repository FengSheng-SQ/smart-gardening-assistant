from fastapi import APIRouter
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    message: str


class TestLLMResponse(BaseModel):
    status: str
    response: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", message="服务运行正常")


@router.get("/test-llm", response_model=TestLLMResponse)
async def test_llm():
    """测试LLM服务"""
    try:
        from app.services.llm_service import llm_service

        logger.info("测试LLM服务...")
        response = await llm_service.chat("你好")
        logger.info(f"LLM响应: {response[:100]}")

        return TestLLMResponse(status="ok", response=response[:200])

    except Exception as e:
        logger.error(f"LLM测试失败: {e}", exc_info=True)
        return TestLLMResponse(status="error", response=str(e))
