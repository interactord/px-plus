"""
FastAPI Dependencies

FastAPI의 의존성 주입을 위한 의존성 함수들
RFS Registry와 FastAPI DI를 연결합니다.
"""

from typing import Annotated
from functools import lru_cache

from fastapi import Depends

from ...application.use_cases import ExtractDocumentChunksUseCase
from ...application.markdown.services.markdown_generation_service import MarkdownGenerationService
from ...domain.markdown.services.markdown_table_formatter import MarkdownTableFormatter
from ..registry import get_registry


def get_extract_document_chunks_use_case() -> ExtractDocumentChunksUseCase:
    """
    ExtractDocumentChunksUseCase 의존성 주입
    """
    registry = get_registry()
    return registry.resolve("extract_document_chunks_use_case")


@lru_cache()
def get_markdown_table_formatter() -> MarkdownTableFormatter:
    """
    마크다운 테이블 포매터 싱글톤 인스턴스 반환

    Returns:
        MarkdownTableFormatter: 포매터 인스턴스
    """
    return MarkdownTableFormatter()


@lru_cache()
def get_markdown_service() -> MarkdownGenerationService:
    """
    마크다운 생성 서비스 싱글톤 인스턴스 반환

    Returns:
        MarkdownGenerationService: 서비스 인스턴스
    """
    formatter = get_markdown_table_formatter()
    return MarkdownGenerationService(formatter=formatter)


ExtractDocumentChunksUseCaseDep = Annotated[
    ExtractDocumentChunksUseCase, Depends(get_extract_document_chunks_use_case)
]
