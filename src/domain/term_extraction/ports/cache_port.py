"""
캐시 Port

Infrastructure Layer에서 구현할 캐시 추상 인터페이스입니다.
"""

from abc import ABC, abstractmethod
from typing import Optional

from ..entities.extraction_result import ExtractionResult


class CachePort(ABC):
    """
    캐시 포트
    
    Infrastructure Layer에서 이 인터페이스를 구현합니다.
    (예: MemoryCacheAdapter, RedisCacheAdapter)
    """
    
    @abstractmethod
    async def get(self, key: str) -> Optional[ExtractionResult]:
        """
        캐시에서 결과 조회
        
        Args:
            key: 캐시 키
            
        Returns:
            ExtractionResult 또는 None (캐시 미스)
        """
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: ExtractionResult,
        ttl: int = 86400
    ) -> None:
        """
        캐시에 결과 저장
        
        Args:
            key: 캐시 키
            value: 저장할 결과
            ttl: Time-To-Live (초, 기본 24시간)
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        캐시에서 삭제
        
        Args:
            key: 캐시 키
        """
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """전체 캐시 삭제"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        캐시 존재 여부 확인
        
        Args:
            key: 캐시 키
            
        Returns:
            존재 여부
        """
        pass
