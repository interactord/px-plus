"""
AsyncCachedEnhancementService

비동기 Redis 캐싱을 지원하는 웹 강화 서비스
"""

import json
import hashlib
from typing import List, Tuple, Optional
import redis.asyncio as aioredis

try:
    from rfs.core.result import Result, Success, Failure
except ImportError:
    from dataclasses import dataclass
    from typing import Generic, TypeVar, Union
    T, E = TypeVar("T"), TypeVar("E")

    @dataclass
    class Success(Generic[T]):
        value: T
        def is_success(self) -> bool: return True
        def unwrap(self) -> T: return self.value

    @dataclass
    class Failure(Generic[E]):
        error: E
        def is_success(self) -> bool: return False
        def unwrap_error(self) -> E: return self.error

    Result = Union[Success[T], Failure[E]]

from ....domain.web_enhancement.entities.enhanced_term import EnhancedTerm
from ....domain.web_enhancement.value_objects.term_info import TermInfo
from .async_batch_enhancement_service import AsyncBatchEnhancementService


class AsyncCachedEnhancementService:
    """
    비동기 Redis 캐싱을 지원하는 웹 강화 서비스

    캐싱 전략:
    - 키 형식: web_enhancement:{term}:{lang_hash}
    - TTL: 24시간 (86400초)
    - 비동기 Redis 클라이언트 사용 (redis.asyncio)

    성능 개선:
    - 비동기 Redis 작업으로 블로킹 제거
    - 캐시 조회/저장 시 다른 작업 병렬 처리

    Attributes:
        async_batch_service: 비동기 배치 강화 서비스
        redis_client: 비동기 Redis 클라이언트
        ttl: 캐시 TTL (초)
    """

    def __init__(
        self,
        async_batch_service: AsyncBatchEnhancementService,
        redis_url: str = "redis://localhost:6379",
        ttl: int = 86400
    ):
        """
        비동기 캐시 강화 서비스 초기화

        Args:
            async_batch_service: 비동기 배치 강화 서비스
            redis_url: Redis 연결 URL
            ttl: 캐시 TTL (초, 기본: 24시간)
        """
        self._async_batch_service = async_batch_service
        self._redis_client = aioredis.from_url(redis_url, decode_responses=True)
        self._ttl = ttl

    async def enhance_terms_with_cache(
        self,
        term_infos: List[TermInfo],
        target_languages: List[str],
        batch_size: int = 5,
        concurrent_batches: int = 10,
        use_cache: bool = True
    ) -> Tuple[List[EnhancedTerm], int, int, float]:
        """
        비동기 캐시를 활용한 용어 강화

        Args:
            term_infos: 강화할 용어 정보
            target_languages: 번역 대상 언어
            batch_size: 배치 크기 (기본: 5)
            concurrent_batches: 동시 배치 수 (기본: 10)
            use_cache: 캐시 사용 여부

        Returns:
            Tuple[List[EnhancedTerm], int, int, float]:
                - 강화된 용어 리스트
                - 캐시 히트 수
                - Fallback 사용 횟수
                - 처리 시간 (초)
        """
        import time
        start_time = time.time()

        # 1. 캐시 조회 (비동기)
        cached_terms = []
        uncached_infos = []
        cache_hits = 0

        if use_cache:
            for term_info in term_infos:
                cache_key = self._generate_cache_key(term_info.term, target_languages)
                cached_data = await self._redis_client.get(cache_key)

                if cached_data:
                    # 캐시 히트
                    try:
                        term_dict = json.loads(cached_data)
                        term_result = EnhancedTerm.from_dict(term_dict)
                        if term_result.is_success():
                            cached_terms.append(term_result.unwrap())
                            cache_hits += 1
                            continue
                    except Exception:
                        pass

                # 캐시 미스
                uncached_infos.append(term_info)
        else:
            uncached_infos = term_infos

        # 2. 캐시되지 않은 용어 처리 (비동기 배치)
        if uncached_infos:
            enhanced_terms, fallback_count, _ = await self._async_batch_service.enhance_terms_batch(
                term_infos=uncached_infos,
                target_languages=target_languages,
                batch_size=batch_size,
                concurrent_batches=concurrent_batches
            )

            # 3. 캐시 저장 (비동기 - 병렬 처리)
            if use_cache and enhanced_terms:
                await self._save_to_cache_batch(enhanced_terms, target_languages)

            # 4. 결과 결합
            all_terms = cached_terms + enhanced_terms
        else:
            all_terms = cached_terms
            fallback_count = 0

        processing_time = time.time() - start_time

        return all_terms, cache_hits, fallback_count, processing_time

    def _generate_cache_key(self, term: str, target_languages: List[str]) -> str:
        """
        캐시 키 생성

        Args:
            term: 용어
            target_languages: 대상 언어

        Returns:
            str: 캐시 키
        """
        # 용어 정규화
        normalized_term = term.strip().lower()

        # 언어 해시 생성
        lang_str = ",".join(sorted(target_languages))
        lang_hash = hashlib.md5(lang_str.encode()).hexdigest()[:8]

        return f"web_enhancement:{normalized_term}:{lang_hash}"

    async def _save_to_cache_batch(
        self,
        enhanced_terms: List[EnhancedTerm],
        target_languages: List[str]
    ):
        """
        배치 캐시 저장 (비동기 병렬)

        Args:
            enhanced_terms: 강화된 용어 리스트
            target_languages: 대상 언어
        """
        import asyncio

        # 모든 캐시 저장 작업을 병렬로 실행
        save_tasks = [
            self._save_to_cache(term, target_languages)
            for term in enhanced_terms
        ]

        await asyncio.gather(*save_tasks, return_exceptions=True)

    async def _save_to_cache(
        self,
        enhanced_term: EnhancedTerm,
        target_languages: List[str]
    ):
        """
        단일 용어 캐시 저장 (비동기)

        Args:
            enhanced_term: 강화된 용어
            target_languages: 대상 언어
        """
        try:
            cache_key = self._generate_cache_key(
                enhanced_term.original_term,
                target_languages
            )

            # EnhancedTerm을 JSON으로 직렬화
            term_dict = enhanced_term.to_dict()
            cache_data = json.dumps(term_dict, ensure_ascii=False)

            # Redis에 비동기 저장
            await self._redis_client.setex(
                cache_key,
                self._ttl,
                cache_data
            )

        except Exception as e:
            # 캐시 저장 실패는 무시 (로깅만)
            import logging
            logging.error(f"캐시 저장 실패: {str(e)}")

    async def get_cache_stats(self) -> Result[dict, str]:
        """
        비동기 캐시 통계 조회

        Returns:
            Result[dict, str]: 캐시 통계 또는 에러
        """
        try:
            info = await self._redis_client.info("stats")
            keyspace = await self._redis_client.info("keyspace")

            stats = {
                "total_keys": keyspace.get("keys", 0),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                )
            }

            return Success(stats)

        except Exception as e:
            return Failure(f"캐시 통계 조회 실패: {str(e)}")

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """
        캐시 히트율 계산

        Args:
            hits: 히트 수
            misses: 미스 수

        Returns:
            float: 히트율 (0.0 ~ 1.0)
        """
        total = hits + misses
        if total == 0:
            return 0.0

        return hits / total

    async def clear_cache(self, pattern: str = "web_enhancement:*") -> Result[int, str]:
        """
        비동기 캐시 삭제

        Args:
            pattern: 삭제할 키 패턴

        Returns:
            Result[int, str]: 삭제된 키 수 또는 에러
        """
        try:
            # 패턴에 맞는 키 검색 (비동기)
            keys = []
            async for key in self._redis_client.scan_iter(match=pattern):
                keys.append(key)

            # 키 삭제 (비동기)
            if keys:
                deleted = await self._redis_client.delete(*keys)
                return Success(deleted)
            else:
                return Success(0)

        except Exception as e:
            return Failure(f"캐시 삭제 실패: {str(e)}")

    async def check_connection(self) -> Result[None, str]:
        """
        비동기 Redis 연결 확인

        Returns:
            Result[None, str]: 성공 또는 에러
        """
        try:
            await self._redis_client.ping()
            return Success(None)
        except Exception as e:
            return Failure(f"Redis 연결 실패: {str(e)}")

    async def close(self):
        """
        비동기 Redis 클라이언트 종료
        """
        await self._redis_client.close()
