"""
마크다운 테이블 포매터

마크다운 테이블 생성 및 포맷팅 로직을 담당합니다.
"""

from typing import List, Dict, Any


class MarkdownTableFormatter:
    """
    마크다운 테이블 포매터

    용어 데이터를 컴팩트한 마크다운 테이블로 변환합니다.
    """

    def format_table(
        self,
        terms: List[Dict[str, Any]],
        languages: List[str]
    ) -> str:
        """
        용어 데이터를 마크다운 테이블로 포맷팅합니다.

        Args:
            terms: 용어 데이터 리스트
            languages: 선택된 언어 코드 리스트

        Returns:
            포맷팅된 마크다운 테이블 문자열 (컴팩트 스페이싱)
        """
        # 테이블 헤더 생성
        header = self._format_header(languages)

        # 구분선 생성
        separator = self._format_separator(len(languages))

        # 데이터 행 생성
        rows = [
            self._format_row(term, languages)
            for term in terms
        ]

        # 테이블 조립 (타이트한 스페이싱 - 공백 없음)
        table_lines = [header, separator] + rows
        return "\n".join(table_lines)

    def _format_header(self, languages: List[str]) -> str:
        """
        테이블 헤더 생성

        Args:
            languages: 언어 코드 리스트

        Returns:
            헤더 문자열 (예: "| term | term_type | tags | ko | en |")
        """
        # 기본 컬럼: term, term_type, tags
        columns = ["term", "term_type", "tags"] + languages

        # 컴팩트 포맷: 파이프 사이에 공백 1개씩
        return "| " + " | ".join(columns) + " |"

    def _format_separator(self, language_count: int) -> str:
        """
        테이블 구분선 생성

        Args:
            language_count: 언어 개수

        Returns:
            구분선 문자열 (예: "|------|----------|------|----|----|")
        """
        # 기본 컬럼 구분선 (컬럼명 길이에 맞춤)
        base_separators = ["------", "----------", "------"]  # term, term_type, tags

        # 언어 컬럼 구분선 (최소 4개 대시)
        lang_separators = ["-----"] * language_count

        # 조립 (공백 포함)
        return "| " + " | ".join(base_separators + lang_separators) + " |"

    def _format_row(
        self,
        term: Dict[str, Any],
        languages: List[str]
    ) -> str:
        """
        데이터 행 포맷팅

        Args:
            term: 용어 데이터
            languages: 언어 코드 리스트

        Returns:
            데이터 행 문자열
        """
        # 기본 필드
        original_term = term.get("original_term", "")
        term_type = term.get("term_type", "")

        # Tags 포맷팅 (배열 → 공백 구분 문자열)
        tags = self._format_tags(term.get("tags", []))

        # 번역 데이터
        translations = term.get("translations", {})
        translated_values = [
            translations.get(lang, "")
            for lang in languages
        ]

        # 행 조립
        cells = [original_term, term_type, tags] + translated_values

        # 이스케이프 처리 (파이프 문자)
        escaped_cells = [
            self._escape_pipe(cell) if isinstance(cell, str) else str(cell)
            for cell in cells
        ]

        # 공백 포함 포맷
        return "| " + " | ".join(escaped_cells) + " |"

    def _format_tags(self, tags: List[str]) -> str:
        """
        태그 배열을 공백 구분 문자열로 변환

        Args:
            tags: 태그 배열 (예: ["#tag1", "#tag2"])

        Returns:
            공백 구분 문자열 (예: "#tag1 #tag2")
        """
        if not tags:
            return ""

        return " ".join(tags)

    def _escape_pipe(self, text: str) -> str:
        """
        마크다운 테이블의 파이프 문자 이스케이프

        Args:
            text: 원본 텍스트

        Returns:
            파이프 문자가 이스케이프된 텍스트
        """
        return text.replace("|", "\\|")
