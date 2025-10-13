"""
CachedEnhancementService

Redis 캐싱을 지원하는 웹 강화 서비스
"""

import json
import hashlib
from typing import List, Tuple, Optional
import redis

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
from .batch_enhancement_service import BatchEnhancementService


class CachedEnhancementService:
    """
    Redis 캐싱을 지원하는 웹 강화 서비스
    
    캐싱 전략:
    - 키 형식: web_enhancement:{term}:{lang_hash}
    - TTL: 24시간 (86400초)
    - 환경별 Redis:
      - 개발: redis://localhost:6379 (Docker)
      - 프로덕션: Google Cloud Memorystore
    
    Attributes:
        batch_service: 배치 강화 서비스
        redis_client: Redis 클라이언트
        ttl: 캐시 TTL (초)
    """
    
    def __init__(
        self,
        batch_service: BatchEnhancementService,
        redis_url: str = "redis://localhost:6379",
        ttl: int = 86400
    ):
        """
        캐시 강화 서비스 초기화
        
        Args:
            batch_service: 배치 강화 서비스
            redis_url: Redis 연결 URL
            ttl: 캐시 TTL (초, 기본: 24시간)
        """
        self._batch_service = batch_service
        self._redis_client = redis.from_url(redis_url, decode_responses=True)
        self._ttl = ttl
    
    async def enhance_terms_with_cache(
        self,
        term_infos: List[TermInfo],
        target_languages: List[str],
        batch_size: int = 5,
        concurrent_batches: int = 3,
        use_cache: bool = True
    ) -> Tuple[List[EnhancedTerm], int, int, float]:
        """
        캐시를 활용한 용어 강화
        
        Args:
            term_infos: 강화할 용어 정보
            target_languages: 번역 대상 언어
            batch_size: 배치 크기
            concurrent_batches: 동시 배치 수
            use_cache: 캐시 사용 여부
        
        Returns:
            Tuple[List[EnhancedTerm], int, int, float]:
                - 강화된 용어 리스트
                - 캐시 히트 수
                - Fallback 사용 횟수
                - 처리 시간 (초)
        """
        # 1. 캐시 조회 (활성화된 경우)
        cached_terms = []
        cache_hits = 0
        terms_to_process = []
        
        if use_cache:
            for term_info in term_infos:
                cached_result = self._get_from_cache(term_info, target_languages)
                
                if cached_result.is_success():
                    cached_terms.append(cached_result.unwrap())
                    cache_hits += 1
                else:
                    terms_to_process.append(term_info)
        else:
            terms_to_process = term_infos
        
        # 2. 캐시 미스 용어만 배치 처리
        if terms_to_process:
            enhanced_terms, fallback_count, processing_time = await self._batch_service.enhance_terms_batch(
                terms_to_process,
                target_languages,
                batch_size,
                concurrent_batches
            )
            
            # 3. 새로 강화된 용어를 캐시에 저장 (웹 강화된 것만)
            if use_cache:
                for term in enhanced_terms:
                    # 일반 번역(gemini_simple, gpt4o_mini)은 캐시 안 함
                    if term.source not in ["gemini_simple", "gpt4o_mini"]:
                        self._save_to_cache(term, target_languages)
        else:
            # 모두 캐시 히트
            enhanced_terms = []
            fallback_count = 0
            processing_time = 0.0
        
        # 4. 캐시 결과 + 새 결과 병합
        all_terms = cached_terms + enhanced_terms
        
        return all_terms, cache_hits, fallback_count, processing_time
    
    def _get_from_cache(
        self,
        term_info: TermInfo,
        target_languages: List[str]
    ) -> Result[EnhancedTerm, str]:
        """
        Redis에서 캐시 조회
        
        Args:
            term_info: 용어 정보
            target_languages: 번역 대상 언어
        
        Returns:
            Result[EnhancedTerm, str]: 캐시된 용어 또는 에러
        """
        try:
            cache_key = self._generate_cache_key(term_info.term, target_languages)
            cached_data = self._redis_client.get(cache_key)
            
            if cached_data is None:
                return Failure("캐시 미스")
            
            # JSON 파싱
            data = json.loads(cached_data)
            
            # EnhancedTerm 복원
            term_result = EnhancedTerm.create(
                original_term=data["original_term"],
                term_type=data["term_type"],
                primary_domain=data["primary_domain"],
                context=data["context"],
                tags=data["tags"],
                translations=data["translations"],
                web_sources=data["web_sources"],
                source=data["source"],
                confidence_score=data["confidence_score"]
            )
            
            if not term_result.is_success():
                return Failure(f"캐시 데이터 복원 실패: {term_result.unwrap_error()}")
            
            return term_result
            
        except redis.RedisError as e:
            return Failure(f"Redis 에러: {str(e)}")
        except json.JSONDecodeError as e:
            return Failure(f"JSON 파싱 실패: {str(e)}")
        except Exception as e:
            return Failure(f"캐시 조회 실패: {str(e)}")
    
    def _save_to_cache(
        self,
        term: EnhancedTerm,
        target_languages: List[str]
    ) -> Result[None, str]:
        """
        Redis에 캐시 저장
        
        Args:
            term: 강화된 용어
            target_languages: 번역 대상 언어
        
        Returns:
            Result[None, str]: 성공 시 None, 실패 시 에러
        """
        try:
            cache_key = self._generate_cache_key(term.original_term, target_languages)
            
            # 딕셔너리로 변환
            data = term.to_dict()
            
            # JSON 직렬화
            cached_data = json.dumps(data, ensure_ascii=False)
            
            # Redis 저장 (TTL 설정)
            self._redis_client.setex(cache_key, self._ttl, cached_data)
            
            return Success(None)
            
        except redis.RedisError as e:
            return Failure(f"Redis 에러: {str(e)}")
        except Exception as e:
            return Failure(f"캐시 저장 실패: {str(e)}")
    
    def _generate_cache_key(
        self,
        term: str,
        target_languages: List[str]
    ) -> str:
        """
        캐시 키 생성
        
        형식: web_enhancement:{term}:{lang_hash}
        
        Args:
            term: 용어
            target_languages: 번역 대상 언어
        
        Returns:
            str: 캐시 키
        """
        # 언어 목록 해시 (순서 무관)
        sorted_languages = sorted(target_languages)
        lang_string = ",".join(sorted_languages)
        lang_hash = hashlib.md5(lang_string.encode()).hexdigest()[:8]
        
        # 용어 정규화 (소문자, 공백 제거)
        normalized_term = term.strip().lower().replace(" ", "_")
        
        return f"web_enhancement:{normalized_term}:{lang_hash}"
    
    def clear_cache(self, pattern: str = "web_enhancement:*") -> Result[int, str]:
        """
        캐시 삭제
        
        Args:
            pattern: 삭제할 키 패턴 (기본: 모든 웹 강화 캐시)
        
        Returns:
            Result[int, str]: 삭제된 키 수 또는 에러
        """
        try:
            keys = self._redis_client.keys(pattern)
            
            if not keys:
                return Success(0)
            
            deleted = self._redis_client.delete(*keys)
            return Success(deleted)
            
        except redis.RedisError as e:
            return Failure(f"Redis 에러: {str(e)}")
        except Exception as e:
            return Failure(f"캐시 삭제 실패: {str(e)}")
    
    def get_cache_stats(self) -> Result[dict, str]:
        """
        캐시 통계 조회
        
        Returns:
            Result[dict, str]: 캐시 통계 또는 에러
        """
        try:
            pattern = "web_enhancement:*"
            keys = self._redis_client.keys(pattern)
            
            stats = {
                "total_cached_terms": len(keys),
                "pattern": pattern
            }
            
            return Success(stats)
            
        except redis.RedisError as e:
            return Failure(f"Redis 에러: {str(e)}")
        except Exception as e:
            return Failure(f"통계 조회 실패: {str(e)}")
    
    def check_connection(self) -> Result[bool, str]:
        """
        Redis 연결 확인
        
        Returns:
            Result[bool, str]: 연결 여부 또는 에러
        """
        try:
            self._redis_client.ping()
            return Success(True)
        except redis.RedisError as e:
            return Failure(f"Redis 연결 실패: {str(e)}")
        except Exception as e:
            return Failure(f"연결 확인 실패: {str(e)}")
