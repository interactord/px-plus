"""
EnhancementResponseDTO

웹 강화 응답 DTO
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

from ....domain.web_enhancement.entities.enhanced_term import EnhancedTerm


@dataclass
class EnhancedTermDTO:
    """
    강화된 용어 DTO
    
    Domain → API 응답 변환
    
    Attributes:
        original_term: 원본 용어
        term_type: 용어 타입
        primary_domain: 주요 도메인
        context: 맥락
        tags: 태그
        translations: 언어별 번역
        web_sources: 웹 출처 URL
        source: LLM 소스
        confidence_score: 신뢰도
        search_timestamp: 검색 시각
    """
    
    original_term: str
    term_type: str
    primary_domain: str
    context: str
    tags: List[str]
    translations: Dict[str, str]
    web_sources: List[str]
    source: str
    confidence_score: float
    search_timestamp: str
    
    @classmethod
    def from_entity(cls, entity: EnhancedTerm) -> "EnhancedTermDTO":
        """
        EnhancedTerm 엔티티에서 DTO 생성
        
        Args:
            entity: EnhancedTerm 엔티티
        
        Returns:
            EnhancedTermDTO: 변환된 DTO
        """
        return cls(
            original_term=entity.original_term,
            term_type=entity.term_type,
            primary_domain=entity.primary_domain,
            context=entity.context,
            tags=entity.tags,
            translations=entity.translations,
            web_sources=entity.web_sources,
            source=entity.source,
            confidence_score=entity.confidence_score,
            search_timestamp=(
                entity.search_timestamp.isoformat()
                if entity.search_timestamp else ""
            )
        )
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "original_term": self.original_term,
            "term_type": self.term_type,
            "primary_domain": self.primary_domain,
            "context": self.context,
            "tags": self.tags,
            "translations": self.translations,
            "web_sources": self.web_sources,
            "source": self.source,
            "confidence_score": self.confidence_score,
            "search_timestamp": self.search_timestamp
        }


@dataclass
class SummaryDTO:
    """
    처리 요약 DTO
    
    Attributes:
        total_terms: 전체 용어 수
        enhanced_terms: 강화 성공 용어 수
        failed_terms: 강화 실패 용어 수
        cache_hits: 캐시 히트 수
        cache_hit_rate: 캐시 히트율 (0.0-1.0)
        total_batches: 전체 배치 수
        fallback_count: Fallback 사용 횟수
        processing_time: 처리 시간 (초)
    """
    
    total_terms: int
    enhanced_terms: int
    failed_terms: int = 0
    cache_hits: int = 0
    cache_hit_rate: float = 0.0
    total_batches: int = 0
    fallback_count: int = 0
    processing_time: float = 0.0
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "total_terms": self.total_terms,
            "enhanced_terms": self.enhanced_terms,
            "failed_terms": self.failed_terms,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": round(self.cache_hit_rate, 2),
            "total_batches": self.total_batches,
            "fallback_count": self.fallback_count,
            "processing_time": round(self.processing_time, 2)
        }


@dataclass
class EnhancementResponseDTO:
    """
    웹 강화 응답 DTO
    
    API 응답 전체 구조
    
    Attributes:
        enhanced_terms: 강화된 용어 리스트
        summary: 처리 요약
        errors: 에러 목록 (선택)
    """
    
    enhanced_terms: List[EnhancedTermDTO]
    summary: SummaryDTO
    errors: List[str] = field(default_factory=list)
    
    @classmethod
    def create(
        cls,
        enhanced_terms: List[EnhancedTerm],
        total_terms: int,
        cache_hits: int = 0,
        total_batches: int = 0,
        fallback_count: int = 0,
        processing_time: float = 0.0,
        errors: List[str] = None
    ) -> "EnhancementResponseDTO":
        """
        EnhancementResponseDTO 생성
        
        Args:
            enhanced_terms: 강화된 용어 엔티티 리스트
            total_terms: 전체 용어 수
            cache_hits: 캐시 히트 수
            total_batches: 전체 배치 수
            fallback_count: Fallback 사용 횟수
            processing_time: 처리 시간 (초)
            errors: 에러 목록
        
        Returns:
            EnhancementResponseDTO: 생성된 DTO
        """
        # DTO 변환
        term_dtos = [
            EnhancedTermDTO.from_entity(term)
            for term in enhanced_terms
        ]
        
        # 요약 생성
        enhanced_count = len(enhanced_terms)
        failed_count = total_terms - enhanced_count
        cache_hit_rate = cache_hits / total_terms if total_terms > 0 else 0.0
        
        summary = SummaryDTO(
            total_terms=total_terms,
            enhanced_terms=enhanced_count,
            failed_terms=failed_count,
            cache_hits=cache_hits,
            cache_hit_rate=cache_hit_rate,
            total_batches=total_batches,
            fallback_count=fallback_count,
            processing_time=processing_time
        )
        
        return cls(
            enhanced_terms=term_dtos,
            summary=summary,
            errors=errors or []
        )
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        result = {
            "enhanced_terms": [term.to_dict() for term in self.enhanced_terms],
            "summary": self.summary.to_dict()
        }
        
        if self.errors:
            result["errors"] = self.errors
        
        return result
