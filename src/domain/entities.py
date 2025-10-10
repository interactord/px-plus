"""
Domain Entities

불변(immutable) 엔티티를 정의합니다.
문서 처리 도메인 엔티티만 포함합니다.
"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class DocumentChunk:
    """
    문서 청크 엔티티 (불변)
    
    Attributes:
        text: 청크 텍스트 내용
        index: 청크 순서 (0부터 시작)
        total_chars: 청크 문자 수
    """
    text: str
    index: int
    total_chars: int
    
    def __post_init__(self) -> None:
        """엔티티 검증"""
        if not self.text or not self.text.strip():
            raise ValueError("청크 텍스트는 비어있을 수 없습니다")
        if self.index < 0:
            raise ValueError("청크 인덱스는 0 이상이어야 합니다")
        if self.total_chars <= 0:
            raise ValueError("청크 문자 수는 0보다 커야 합니다")


@dataclass(frozen=True)
class ProcessedDocument:
    """
    처리된 문서 엔티티 (불변)
    
    Attributes:
        filename: 파일 이름
        chunks: 문서 청크 리스트
        total_characters: 전체 문자 수
    """
    filename: str
    chunks: List[DocumentChunk]
    total_characters: int
    
    def __post_init__(self) -> None:
        """엔티티 검증"""
        if not self.filename:
            raise ValueError("파일 이름은 필수입니다")
        if not self.chunks:
            raise ValueError("청크는 최소 1개 이상이어야 합니다")
        if self.total_characters <= 0:
            raise ValueError("전체 문자 수는 0보다 커야 합니다")
