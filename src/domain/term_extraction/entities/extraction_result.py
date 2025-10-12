"""
추출 결과 Entity

청크 단위 및 배치 단위 추출 결과를 표현합니다.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from ..value_objects.chunk_text import ChunkText
from ..value_objects.entity_type import EntityTypeFilter
from .extracted_entity import ExtractedEntity

try:
    from rfs.core.result import Result, Success, Failure
except ImportError:
    # RFS Framework Fallback
    from typing import Generic, TypeVar
    T = TypeVar('T')
    E = TypeVar('E')
    
    class Result(Generic[T, E]):
        def is_success(self) -> bool: ...
        def is_failure(self) -> bool: ...
        def unwrap(self) -> T: ...
        def unwrap_failure(self) -> E: ...
    
    class Success(Result[T, E]):
        def __init__(self, value: T): self._value = value
        def is_success(self) -> bool: return True
        def is_failure(self) -> bool: return False
        def unwrap(self) -> T: return self._value
        def unwrap_failure(self) -> E: raise ValueError("Success has no error")
    
    class Failure(Result[T, E]):
        def __init__(self, error: E): self._error = error
        def is_success(self) -> bool: return False
        def is_failure(self) -> bool: return True
        def unwrap(self) -> T: raise ValueError(f"Failure: {self._error}")
        def unwrap_failure(self) -> E: return self._error


@dataclass(frozen=True)
class ExtractionResult:
    """
    청크 단위 추출 결과
    
    Attributes:
        chunk: 원본 청크
        entities: 추출된 엔티티 튜플 (불변)
        cached: 캐시에서 가져왔는지 여부
        processing_time: 처리 시간 (초)
        error: 에러 메시지 (실패 시)
    """
    chunk: ChunkText
    entities: tuple[ExtractedEntity, ...] = field(default_factory=tuple)
    cached: bool = False
    processing_time: float = 0.0
    error: Optional[str] = None
    
    @classmethod
    def success(
        cls,
        chunk: ChunkText,
        entities: List[ExtractedEntity],
        cached: bool = False,
        processing_time: float = 0.0
    ) -> "ExtractionResult":
        """
        성공 결과 생성
        
        Args:
            chunk: 원본 청크
            entities: 추출된 엔티티 리스트
            cached: 캐시 여부
            processing_time: 처리 시간
            
        Returns:
            성공 결과
        """
        return cls(
            chunk=chunk,
            entities=tuple(entities),
            cached=cached,
            processing_time=processing_time,
            error=None
        )
    
    @classmethod
    def failure(
        cls,
        chunk: ChunkText,
        error: str,
        processing_time: float = 0.0
    ) -> "ExtractionResult":
        """
        실패 결과 생성
        
        Args:
            chunk: 원본 청크
            error: 에러 메시지
            processing_time: 처리 시간
            
        Returns:
            실패 결과
        """
        return cls(
            chunk=chunk,
            entities=(),
            cached=False,
            processing_time=processing_time,
            error=error
        )
    
    def is_success(self) -> bool:
        """성공 여부"""
        return self.error is None
    
    def is_failure(self) -> bool:
        """실패 여부"""
        return self.error is not None
    
    def entity_count(self) -> int:
        """추출된 엔티티 개수"""
        return len(self.entities)
    
    def filter_entities(
        self,
        type_filter: Optional[EntityTypeFilter]
    ) -> "ExtractionResult":
        """
        엔티티 필터링
        
        Args:
            type_filter: 타입 필터
            
        Returns:
            필터링된 새 결과 (불변성 유지)
        """
        if type_filter is None:
            return self
        
        filtered = [e for e in self.entities if e.matches_filter(type_filter)]
        
        return ExtractionResult(
            chunk=self.chunk,
            entities=tuple(filtered),
            cached=self.cached,
            processing_time=self.processing_time,
            error=self.error
        )
    
    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            "filename": self.chunk.source_filename,
            "chunk_index": self.chunk.chunk_index,
            "entities": [e.to_dict() for e in self.entities],
            "cached": self.cached,
            "processing_time": self.processing_time,
            "error": self.error,
            "success": self.is_success()
        }


@dataclass(frozen=True)
class ExtractionBatchResult:
    """
    배치 추출 결과
    
    Attributes:
        results: 개별 추출 결과 튜플 (불변)
        total_processing_time: 전체 처리 시간
    """
    results: tuple[ExtractionResult, ...] = field(default_factory=tuple)
    total_processing_time: float = 0.0
    
    @classmethod
    def create(
        cls,
        results: List[ExtractionResult],
        total_processing_time: float = 0.0
    ) -> "ExtractionBatchResult":
        """
        배치 결과 생성
        
        Args:
            results: 개별 결과 리스트
            total_processing_time: 전체 처리 시간
            
        Returns:
            배치 결과
        """
        return cls(
            results=tuple(results),
            total_processing_time=total_processing_time
        )
    
    def success_count(self) -> int:
        """성공 개수"""
        return sum(1 for r in self.results if r.is_success())
    
    def failure_count(self) -> int:
        """실패 개수"""
        return sum(1 for r in self.results if r.is_failure())
    
    def total_entities(self) -> int:
        """전체 엔티티 개수"""
        return sum(r.entity_count() for r in self.results)
    
    def cache_hit_count(self) -> int:
        """캐시 히트 개수"""
        return sum(1 for r in self.results if r.cached)
    
    def cache_hit_rate(self) -> float:
        """
        캐시 히트율 (0.0 ~ 1.0)
        
        Returns:
            캐시 히트율
        """
        total = len(self.results)
        if total == 0:
            return 0.0
        return self.cache_hit_count() / total
    
    def summary(self) -> dict:
        """
        요약 통계
        
        Returns:
            요약 딕셔너리
        """
        return {
            "total_chunks": len(self.results),
            "processed": self.success_count(),
            "failed": self.failure_count(),
            "total_entities": self.total_entities(),
            "cache_hits": self.cache_hit_count(),
            "cache_hit_rate": round(self.cache_hit_rate(), 2),
            "processing_time_seconds": round(self.total_processing_time, 2)
        }
