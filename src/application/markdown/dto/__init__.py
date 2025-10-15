"""
마크다운 생성 DTO

API 요청/응답 데이터 구조를 정의합니다.
"""

from src.application.markdown.dto.markdown_request_dto import MarkdownGenerationRequest
from src.application.markdown.dto.markdown_response_dto import MarkdownGenerationResponse

__all__ = [
    "MarkdownGenerationRequest",
    "MarkdownGenerationResponse",
]
