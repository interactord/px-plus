"""
마크다운 생성 서비스

비즈니스 로직을 처리하고 도메인 레이어와 통신합니다.
"""

from typing import List, Dict, Any

from src.application.markdown.dto.markdown_request_dto import MarkdownGenerationRequest
from src.application.markdown.dto.markdown_response_dto import MarkdownGenerationResponse
from src.domain.markdown.services.markdown_table_formatter import MarkdownTableFormatter


class MarkdownGenerationService:
    """
    마크다운 생성 서비스

    용어 데이터를 마크다운 테이블로 변환하는 비즈니스 로직을 처리합니다.
    """

    def __init__(self, formatter: MarkdownTableFormatter):
        """
        서비스 초기화

        Args:
            formatter: 마크다운 테이블 포매터 (도메인 서비스)
        """
        self._formatter = formatter

    async def generate_markdown_table(
        self,
        request: MarkdownGenerationRequest
    ) -> MarkdownGenerationResponse:
        """
        JSON 용어 데이터를 마크다운 테이블로 변환합니다.

        Args:
            request: 마크다운 생성 요청 DTO

        Returns:
            MarkdownGenerationResponse: 생성된 마크다운 및 메타데이터

        Raises:
            ValueError: 데이터 검증 실패
        """
        # enhanced_terms 배열 추출
        enhanced_terms = request.terms_data.get("enhanced_terms", [])

        # 용어 데이터 검증
        self._validate_terms(enhanced_terms, request.selected_languages)

        # 마크다운 테이블 생성
        markdown_table = self._formatter.format_table(
            terms=enhanced_terms,
            languages=request.selected_languages
        )

        # 응답 생성
        return MarkdownGenerationResponse(
            markdown_table=markdown_table,
            term_count=len(enhanced_terms),
            column_count=3 + len(request.selected_languages)  # term + term_type + tags + languages
        )

    def _validate_terms(
        self,
        terms: List[Dict[str, Any]],
        languages: List[str]
    ) -> None:
        """
        용어 데이터 유효성 검증

        Args:
            terms: 용어 데이터 리스트
            languages: 선택된 언어 코드 리스트

        Raises:
            ValueError: 필수 필드 누락 또는 번역 데이터 부족
        """
        for idx, term in enumerate(terms):
            # 필수 필드 확인
            required_fields = ["original_term", "term_type", "tags", "translations"]
            missing = [f for f in required_fields if f not in term]

            if missing:
                raise ValueError(
                    f"용어 {idx}에 필수 필드 누락: {', '.join(missing)}"
                )

            # 번역 데이터 확인
            translations = term.get("translations", {})
            missing_langs = [lang for lang in languages if lang not in translations]

            if missing_langs:
                raise ValueError(
                    f"용어 '{term['original_term']}'에 번역 누락: {', '.join(missing_langs)}"
                )
