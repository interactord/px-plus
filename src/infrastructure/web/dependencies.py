"""
FastAPI Dependencies

FastAPI의 의존성 주입을 위한 의존성 함수들
RFS Registry와 FastAPI DI를 연결합니다.
"""

from typing import Annotated

from fastapi import Depends

from ...application.use_cases import ExtractDocumentChunksUseCase
from ..registry import get_registry


def get_extract_document_chunks_use_case() -> ExtractDocumentChunksUseCase:
    """
    ExtractDocumentChunksUseCase 의존성 주입
    """
    registry = get_registry()
    return registry.resolve("extract_document_chunks_use_case")


ExtractDocumentChunksUseCaseDep = Annotated[
    ExtractDocumentChunksUseCase, Depends(get_extract_document_chunks_use_case)
]
