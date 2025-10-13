"""
BatchEnhancementService

배치 기반 웹 강화 서비스
라운드 로빈 방식의 비동기 배치 처리
"""

import asyncio
import time
import logging
from typing import List, Tuple
import math

logger = logging.getLogger(__name__)

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
from ....domain.web_enhancement.services.web_enhancement_service import WebEnhancementService


class BatchEnhancementService:
    """
    배치 기반 웹 강화 서비스
    
    라운드 로빈 방식 비동기 배치 처리:
    - 배치 크기: 5개 용어 (Single-shot 최적)
    - 동시 배치: 3개 (기본값, 조정 가능)
    - 처리 방식: 라운드 로빈
    
    예시 (33개 용어, 5개 배치, 3 동시):
    Round 1: Batch A(1-5), B(6-10), C(11-15)  ← 3개 동시
    Round 2: Batch D(16-20), E(21-25), F(26-30)
    Round 3: Batch G(31-33)
    
    Attributes:
        enhancement_service: 도메인 웹 강화 서비스
    """
    
    def __init__(self, enhancement_service: WebEnhancementService):
        """
        배치 강화 서비스 초기화
        
        Args:
            enhancement_service: 도메인 웹 강화 서비스
        """
        self._enhancement_service = enhancement_service
    
    async def enhance_terms_batch(
        self,
        term_infos: List[TermInfo],
        target_languages: List[str],
        batch_size: int = 5,
        concurrent_batches: int = 3
    ) -> Tuple[List[EnhancedTerm], int, float]:
        """
        배치 방식 용어 강화
        
        Args:
            term_infos: 강화할 용어 정보
            target_languages: 번역 대상 언어
            batch_size: 배치 크기 (기본: 5)
            concurrent_batches: 동시 배치 수 (기본: 3)
        
        Returns:
            Tuple[List[EnhancedTerm], int, float]:
                - 강화된 용어 리스트
                - Fallback 사용 횟수
                - 처리 시간 (초)
        """
        start_time = time.time()
        
        # 1. 배치 생성
        batches = self._create_batches(term_infos, batch_size)
        total_batches = len(batches)
        
        # 2. 라운드 로빈 처리
        enhanced_terms = []
        fallback_count = 0
        
        # 동시 처리할 배치들을 라운드로 묶음
        rounds = self._create_rounds(batches, concurrent_batches)
        
        for round_idx, round_batches in enumerate(rounds):
            # 라운드 내 배치들을 동시 처리
            round_results = await self._process_round(
                round_batches,
                target_languages
            )
            
            # 결과 수집
            for batch_result, batch_fallback_count in round_results:
                enhanced_terms.extend(batch_result)
                fallback_count += batch_fallback_count
        
        processing_time = time.time() - start_time
        
        return enhanced_terms, fallback_count, processing_time
    
    def _create_batches(
        self,
        term_infos: List[TermInfo],
        batch_size: int
    ) -> List[List[TermInfo]]:
        """
        용어 리스트를 배치로 분할
        
        Args:
            term_infos: 용어 정보 리스트
            batch_size: 배치 크기
        
        Returns:
            List[List[TermInfo]]: 배치 리스트
        """
        batches = []
        
        for i in range(0, len(term_infos), batch_size):
            batch = term_infos[i:i + batch_size]
            batches.append(batch)
        
        return batches
    
    def _create_rounds(
        self,
        batches: List[List[TermInfo]],
        concurrent_batches: int
    ) -> List[List[List[TermInfo]]]:
        """
        배치들을 라운드로 그룹화
        
        Args:
            batches: 전체 배치 리스트
            concurrent_batches: 동시 처리할 배치 수
        
        Returns:
            List[List[List[TermInfo]]]: 라운드 리스트
        """
        rounds = []
        
        for i in range(0, len(batches), concurrent_batches):
            round_batches = batches[i:i + concurrent_batches]
            rounds.append(round_batches)
        
        return rounds
    
    async def _process_round(
        self,
        round_batches: List[List[TermInfo]],
        target_languages: List[str]
    ) -> List[Tuple[List[EnhancedTerm], int]]:
        """
        라운드 내 배치들을 동시 처리
        
        Args:
            round_batches: 라운드 내 배치들
            target_languages: 번역 대상 언어
        
        Returns:
            List[Tuple[List[EnhancedTerm], int]]:
                각 배치의 (강화된 용어, Fallback 횟수)
        """
        # 모든 배치를 동시에 처리
        tasks = [
            self._process_batch(batch, target_languages)
            for batch in round_batches
        ]
        
        results = await asyncio.gather(*tasks)
        return results
    
    async def _process_batch(
        self,
        batch: List[TermInfo],
        target_languages: List[str]
    ) -> Tuple[List[EnhancedTerm], int]:
        """
        단일 배치 처리 (비동기)
        
        Args:
            batch: 배치 (용어 정보 리스트)
            target_languages: 번역 대상 언어
        
        Returns:
            Tuple[List[EnhancedTerm], int]:
                - 강화된 용어
                - Fallback 사용 여부 (0 or 1)
        """
        # 동기 서비스를 비동기로 실행
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._enhancement_service.enhance_terms,
            batch,
            target_languages
        )
        
        if result.is_success():
            enhanced_terms = result.unwrap()
            
            # Fallback 사용 여부 확인 (Gemini, Gemini Simple, GPT-4o-mini 모두 포함)
            primary_source = self._enhancement_service.get_primary_source()
            fallback_used = any(
                term.source != primary_source
                for term in enhanced_terms
            )
            
            fallback_count = 1 if fallback_used else 0
            return enhanced_terms, fallback_count
        else:
            # 실패 시 빈 리스트 반환
            error_msg = result.unwrap_error()
            logger.error(f"💥 배치 처리 실패 ({len(batch)}개 용어): {error_msg}")
            return [], 0
    
    def calculate_batch_count(
        self,
        total_terms: int,
        batch_size: int
    ) -> int:
        """
        전체 배치 수 계산
        
        Args:
            total_terms: 전체 용어 수
            batch_size: 배치 크기
        
        Returns:
            int: 전체 배치 수
        """
        return math.ceil(total_terms / batch_size)
    
    def calculate_round_count(
        self,
        total_batches: int,
        concurrent_batches: int
    ) -> int:
        """
        전체 라운드 수 계산
        
        Args:
            total_batches: 전체 배치 수
            concurrent_batches: 동시 배치 수
        
        Returns:
            int: 전체 라운드 수
        """
        return math.ceil(total_batches / concurrent_batches)
    
    def estimate_processing_time(
        self,
        total_terms: int,
        batch_size: int,
        concurrent_batches: int,
        avg_batch_time: float = 6.0
    ) -> float:
        """
        예상 처리 시간 계산
        
        Args:
            total_terms: 전체 용어 수
            batch_size: 배치 크기
            concurrent_batches: 동시 배치 수
            avg_batch_time: 배치당 평균 시간 (초, 기본: 6초)
        
        Returns:
            float: 예상 처리 시간 (초)
        """
        total_batches = self.calculate_batch_count(total_terms, batch_size)
        total_rounds = self.calculate_round_count(total_batches, concurrent_batches)
        
        return total_rounds * avg_batch_time
