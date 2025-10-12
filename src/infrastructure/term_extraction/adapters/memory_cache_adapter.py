"""
메모리 기반 캐시 Adapter 모듈

간단한 인메모리 캐시 구현을 제공합니다.
프로덕션에서는 Redis 등으로 교체 가능합니다.
"""

import time
from typing import Optional, Dict
from dataclasses import dataclass

# 도메인 객체 import
from ....domain.term_extraction.entities.extraction_result import ExtractionResult
from ....domain.term_extraction.ports.cache_port import CachePort


@dataclass
class CacheEntry:
    """
    캐시 항목
    
    값과 만료 시간을 함께 저장합니다.
    """
    value: ExtractionResult
    expires_at: float  # Unix timestamp


class MemoryCacheAdapter(CachePort):
    """
    메모리 기반 캐시 구현체
    
    단순한 딕셔너리를 사용한 인메모리 캐시입니다.
    TTL(Time To Live)을 지원합니다.
    
    주의: 프로세스 재시작 시 모든 데이터가 소실됩니다.
    프로덕션에서는 Redis 등의 영구 캐시 사용을 권장합니다.
    """
    
    def __init__(self):
        """캐시 초기화"""
        self._cache: Dict[str, CacheEntry] = {}
    
    async def get(self, key: str) -> Optional[ExtractionResult]:
        """
        캐시에서 값을 가져옵니다.
        
        Args:
            key: 캐시 키
            
        Returns:
            Optional[ExtractionResult]: 캐시 히트 시 결과, 미스 시 None
        """
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # TTL 확인
        if time.time() > entry.expires_at:
            # 만료된 항목 삭제
            del self._cache[key]
            return None
        
        return entry.value
    
    async def set(
        self,
        key: str,
        value: ExtractionResult,
        ttl: int = 86400
    ) -> None:
        """
        캐시에 값을 저장합니다.
        
        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: Time To Live (초 단위, 기본값: 86400 = 24시간)
        """
        expires_at = time.time() + ttl
        
        entry = CacheEntry(
            value=value,
            expires_at=expires_at
        )
        
        self._cache[key] = entry
    
    async def delete(self, key: str) -> None:
        """
        캐시에서 값을 삭제합니다.
        
        Args:
            key: 삭제할 키
        """
        if key in self._cache:
            del self._cache[key]
    
    async def clear(self) -> None:
        """캐시의 모든 항목을 삭제합니다."""
        self._cache.clear()
    
    async def exists(self, key: str) -> bool:
        """
        캐시에 키가 존재하는지 확인합니다.
        
        Args:
            key: 확인할 키
            
        Returns:
            bool: 존재하고 유효하면 True, 아니면 False
        """
        if key not in self._cache:
            return False
        
        entry = self._cache[key]
        
        # TTL 확인
        if time.time() > entry.expires_at:
            # 만료된 항목 삭제
            del self._cache[key]
            return False
        
        return True
    
    def size(self) -> int:
        """
        현재 캐시에 저장된 항목 수를 반환합니다.
        
        Returns:
            int: 캐시 항목 수
        """
        # 만료된 항목 정리
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time > entry.expires_at
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(self._cache)
