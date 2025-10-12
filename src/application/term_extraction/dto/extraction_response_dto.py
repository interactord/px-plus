"""
용어 추출 응답 DTO 모듈

도메인 객체를 FastAPI 응답 데이터로 변환합니다.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# 도메인 객체 import
from ....domain.term_extraction.entities.extracted_entity import ExtractedEntity
from ....domain.term_extraction.entities.extraction_result import (
    ExtractionResult,
    ExtractionBatchResult
)


class ExtractedEntityDTO(BaseModel):
    """
    추출된 엔티티 DTO
    
    단일 엔티티의 정보를 표현합니다.
    """
    
    term: str = Field(
        ...,
        description="추출된 용어 (# 접두사 포함)"
    )
    
    type: str = Field(
        ...,
        description="엔티티 타입 (person, company, product, technical_term)"
    )
    
    primary_domain: str = Field(
        ...,
        description="주요 도메인 (# 접두사 포함)"
    )
    
    tags: List[str] = Field(
        default_factory=list,
        description="관련 태그 목록 (# 접두사 포함)"
    )
    
    context: Optional[str] = Field(
        default=None,
        description="엔티티가 사용된 문맥"
    )
    
    multilingual_expressions: Optional[Dict[str, str]] = Field(
        default=None,
        description="다국어 표현 (언어 코드: 용어)"
    )
    
    @classmethod
    def from_domain(cls, entity: ExtractedEntity) -> "ExtractedEntityDTO":
        """
        도메인 ExtractedEntity 객체를 DTO로 변환합니다.
        
        Args:
            entity: 도메인 ExtractedEntity 객체
            
        Returns:
            ExtractedEntityDTO: 변환된 DTO
        """
        return cls(
            term=entity.term,
            type=entity.type.value,
            primary_domain=entity.primary_domain,
            tags=list(entity.tags),
            context=entity.context if entity.context else None,
            multilingual_expressions=entity.multilingual_expressions
        )


class ChunkResultDTO(BaseModel):
    """
    청크 처리 결과 DTO
    
    단일 청크의 처리 결과를 표현합니다.
    """
    
    chunk_index: int = Field(
        ...,
        description="청크 인덱스"
    )
    
    source_filename: str = Field(
        ...,
        description="원본 파일명"
    )
    
    entities: List[ExtractedEntityDTO] = Field(
        default_factory=list,
        description="추출된 엔티티 목록"
    )
    
    cached: bool = Field(
        default=False,
        description="캐시에서 가져온 결과인지 여부"
    )
    
    processing_time: float = Field(
        default=0.0,
        description="처리 시간 (초)",
        ge=0.0
    )
    
    error: Optional[str] = Field(
        default=None,
        description="처리 중 발생한 에러 메시지"
    )
    
    @classmethod
    def from_domain(cls, result: ExtractionResult) -> "ChunkResultDTO":
        """
        도메인 ExtractionResult 객체를 DTO로 변환합니다.
        
        Args:
            result: 도메인 ExtractionResult 객체
            
        Returns:
            ChunkResultDTO: 변환된 DTO
        """
        entities_dto = [
            ExtractedEntityDTO.from_domain(entity)
            for entity in result.entities
        ]
        
        return cls(
            chunk_index=result.chunk.chunk_index,
            source_filename=result.chunk.source_filename,
            entities=entities_dto,
            cached=result.cached,
            processing_time=result.processing_time,
            error=result.error
        )


class SummaryDTO(BaseModel):
    """
    처리 결과 요약 DTO
    
    전체 처리 결과의 통계 정보를 표현합니다.
    """
    
    total_chunks: int = Field(
        ...,
        description="전체 청크 수",
        ge=0
    )
    
    processed_chunks: int = Field(
        ...,
        description="성공적으로 처리된 청크 수",
        ge=0
    )
    
    failed_chunks: int = Field(
        ...,
        description="처리 실패한 청크 수",
        ge=0
    )
    
    cache_hits: int = Field(
        ...,
        description="캐시 히트 수",
        ge=0
    )
    
    cache_hit_rate: float = Field(
        ...,
        description="캐시 히트율 (0.0 ~ 1.0)",
        ge=0.0,
        le=1.0
    )
    
    total_entities: int = Field(
        ...,
        description="총 추출된 엔티티 수",
        ge=0
    )
    
    total_processing_time: float = Field(
        ...,
        description="전체 처리 시간 (초)",
        ge=0.0
    )
    
    average_processing_time: float = Field(
        ...,
        description="청크당 평균 처리 시간 (초)",
        ge=0.0
    )
    
    @classmethod
    def from_domain(cls, batch_result: ExtractionBatchResult) -> "SummaryDTO":
        """
        도메인 ExtractionBatchResult 객체를 요약 DTO로 변환합니다.
        
        Args:
            batch_result: 도메인 ExtractionBatchResult 객체
            
        Returns:
            SummaryDTO: 변환된 요약 DTO
        """
        summary = batch_result.summary()
        
        return cls(
            total_chunks=summary["total_chunks"],
            processed_chunks=summary["processed"],
            failed_chunks=summary["failed"],
            cache_hits=summary["cache_hits"],
            cache_hit_rate=summary["cache_hit_rate"],
            total_entities=summary["total_entities"],
            total_processing_time=summary["total_processing_time"],
            average_processing_time=summary["avg_processing_time"]
        )


class ExtractionResponseDTO(BaseModel):
    """
    용어 추출 응답 DTO
    
    FastAPI 엔드포인트의 전체 응답 데이터를 표현합니다.
    """
    
    results: List[ChunkResultDTO] = Field(
        default_factory=list,
        description="청크별 처리 결과 목록"
    )
    
    summary: SummaryDTO = Field(
        ...,
        description="처리 결과 요약 통계"
    )
    
    @classmethod
    def from_domain(cls, batch_result: ExtractionBatchResult) -> "ExtractionResponseDTO":
        """
        도메인 ExtractionBatchResult 객체를 응답 DTO로 변환합니다.
        
        Args:
            batch_result: 도메인 ExtractionBatchResult 객체
            
        Returns:
            ExtractionResponseDTO: 변환된 응답 DTO
        """
        chunk_results_dto = [
            ChunkResultDTO.from_domain(result)
            for result in batch_result.results
        ]
        
        summary_dto = SummaryDTO.from_domain(batch_result)
        
        return cls(
            results=chunk_results_dto,
            summary=summary_dto
        )
    
    class Config:
        """Pydantic 설정"""
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "chunk_index": 0,
                        "source_filename": "document.txt",
                        "entities": [
                            {
                                "term": "#홍길동",
                                "type": "person",
                                "primary_domain": "#역사",
                                "tags": ["#조선시대", "#의적"],
                                "context": "홍길동은 조선시대의 전설적인 의적이다.",
                                "multilingual_expressions": {
                                    "en": "Hong Gildong",
                                    "ja": "ホン・ギルドン"
                                }
                            }
                        ],
                        "cached": False,
                        "processing_time": 1.234,
                        "error": None
                    }
                ],
                "summary": {
                    "total_chunks": 10,
                    "processed_chunks": 9,
                    "failed_chunks": 1,
                    "cache_hits": 3,
                    "cache_hit_rate": 0.3,
                    "total_entities": 45,
                    "total_processing_time": 12.345,
                    "average_processing_time": 1.235
                }
            }
        }
