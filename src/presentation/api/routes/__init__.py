"""
API Routes

FastAPI 라우터들을 정의합니다.
"""

from .term_extraction import router as term_extraction_router
from .demo import router as demo_router

__all__ = [
    "term_extraction_router",
    "demo_router",
]
