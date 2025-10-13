"""
캐시 지원 용어 추출 서비스 모듈

캐시 레이어를 추가하여 LLM 호출을 최소화합니다.
"""

import time
from typing import List, Dict, Optional

# RFS Framework - Result 패턴
try:
    from rfs.core.result import Result, Success, Failure
except ImportError:
    from dataclasses import dataclass
    from typing import Generic, TypeVar, Union
    
    T = TypeVar('T')
    E = TypeVar('E')
    
    @dataclass(frozen=True)
    class Success(Generic[T]):
        value: T
        def is_success(self) -> bool: return True
        def is_failure(self) -> bool: return False
    
    @dataclass(frozen=True)
    class Failure(Generic[E]):
        error: E
        def is_success(self) -> bool: return False
        def is_failure(self) -> bool: return True
    
    Result = Union[Success[T], Failure[E]]

# 도메인 객체 import
from ....domain.term_extraction.value_objects.chunk_text import ChunkText
from ....domain.term_extraction.value_objects.extraction_context import ExtractionContext
from ....domain.term_extraction.entities.extraction_result import (
    ExtractionResult,
    ExtractionBatchResult
)
from ....domain.term_extraction.ports.term_extraction_port import TermExtractionPort
from ....domain.term_extraction.ports.cache_port import CachePort

# DTO import
from ..dto.extraction_request_dto import ExtractionRequestDTO
from ..dto.extraction_response_dto import ExtractionResponseDTO


class CachedTermExtractionService:
    """
    캐시 지원 용어 추출 서비스
    
    캐시를 활용하여 동일한 청크에 대한 반복 추출을 최적화합니다.
    """
    
    def __init__(
        self,
        extractor: TermExtractionPort,
        cache: CachePort,
        max_workers: int = 3
    ):
        """
        서비스 초기화
        
        Args:
            extractor: 실제 추출을 수행할 Port 구현체
            cache: 캐시 Port 구현체
            max_workers: 병렬 처리 워커 수 (기본값: 3)
        """
        self._extractor = extractor
        self._cache = cache
        self._max_workers = max_workers
    
    async def extract_from_documents(
        self,
        request: ExtractionRequestDTO
    ) -> Result[ExtractionResponseDTO, str]:
        """
        문서들로부터 용어를 추출합니다 (캐시 활용).
        
        Args:
            request: 추출 요청 DTO
            
        Returns:
            Result[ExtractionResponseDTO, str]: 성공 시 응답 DTO, 실패 시 에러 메시지
        """
        start_time = time.time()
        
        # 1. DTO를 도메인 객체로 변환
        chunks_result = request.to_chunks()
        if chunks_result.is_failure():
            return Failure(f"청크 변환 실패: {chunks_result.error}")
        
        context_result = request.to_extraction_context()
        if context_result.is_failure():
            return Failure(f"컨텍스트 생성 실패: {context_result.error}")
        
        chunks = chunks_result.value
        context = context_result.value
        
        # 2. 캐시 사용 여부에 따른 처리
        if request.use_cache:
            results = await self._extract_with_cache(chunks, context, request.parallel_workers)
        else:
            results = await self._extract_without_cache(chunks, context, request.parallel_workers)
        
        # 3. 결과 집계
        total_time = time.time() - start_time
        batch_result = ExtractionBatchResult(
            results=tuple(results),
            total_processing_time=total_time
        )
        
        # 4. DTO로 변환
        response = ExtractionResponseDTO.from_domain(batch_result)
        
        return Success(response)
    
    async def _extract_with_cache(
        self,
        chunks: List[ChunkText],
        context: ExtractionContext,
        num_workers: Optional[int]
    ) -> List[ExtractionResult]:
        """
        캐시를 활용하여 청크를 처리합니다.
        
        Args:
            chunks: 처리할 청크 목록
            context: 추출 컨텍스트
            num_workers: 워커 수
            
        Returns:
            List[ExtractionResult]: 처리 결과 목록
        """
        # 1. 캐시 확인
        cache_results: Dict[int, ExtractionResult] = {}
        chunks_to_process: List[ChunkText] = []
        
        for chunk in chunks:
            cache_key = chunk.cache_key(context.template_name)
            cached_result = await self._cache.get(cache_key)
            
            if cached_result is not None:
                # 캐시 히트
                cache_results[chunk.chunk_index] = cached_result
            else:
                # 캐시 미스 - 처리 필요
                chunks_to_process.append(chunk)
        
        # 2. 캐시 미스 청크 처리
        new_results: Dict[int, ExtractionResult] = {}
        if chunks_to_process:
            processed = await self._extract_without_cache(
                chunks_to_process,
                context,
                num_workers
            )
            
            # 새 결과를 캐시에 저장
            for result in processed:
                if result.error is None:  # 성공한 경우만 캐시
                    cache_key = result.chunk.cache_key(context.template_name)
                    await self._cache.set(cache_key, result)
                
                new_results[result.chunk.chunk_index] = result
        
        # 3. 결과 병합 (원본 순서 유지)
        all_results: List[ExtractionResult] = []
        for chunk in chunks:
            idx = chunk.chunk_index
            
            if idx in cache_results:
                all_results.append(cache_results[idx])
            elif idx in new_results:
                all_results.append(new_results[idx])
            else:
                # 이론적으로는 도달할 수 없는 경로
                failed_result = ExtractionResult.failure(
                    chunk=chunk,
                    error="알 수 없는 처리 오류"
                )
                all_results.append(failed_result)
        
        return all_results
    
    async def _extract_without_cache(
        self,
        chunks: List[ChunkText],
        context: ExtractionContext,
        num_workers: Optional[int]
    ) -> List[ExtractionResult]:
        """
        캐시 없이 청크를 처리합니다.
        
        Args:
            chunks: 처리할 청크 목록
            context: 추출 컨텍스트
            num_workers: 워커 수
            
        Returns:
            List[ExtractionResult]: 처리 결과 목록
        """
        # parallel_workers가 None이면 1로 처리 (순차 실행)
        workers = num_workers if num_workers is not None else 1
        
        if workers > 1 and len(chunks) > 1:
            # 병렬 처리
            from ....domain.term_extraction.value_objects.chunk_text import ChunkTextBatch
            import asyncio
            
            batch = ChunkTextBatch(chunks=tuple(chunks))
            worker_batches = batch.split_for_parallel(workers)
            
            tasks = [
                self._process_worker_batch(worker_chunks, context)
                for worker_chunks in worker_batches
            ]
            
            worker_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            all_results: List[ExtractionResult] = []
            for worker_result in worker_results:
                if isinstance(worker_result, Exception):
                    continue
                all_results.extend(worker_result)
            
            all_results.sort(key=lambda r: r.chunk.chunk_index)
            return all_results
        else:
            # 순차 처리
            return await self._process_chunks_sequential(chunks, context)
    
    async def _process_chunks_sequential(
        self,
        chunks: List[ChunkText],
        context: ExtractionContext
    ) -> List[ExtractionResult]:
        """
        청크를 순차적으로 처리합니다.
        
        Args:
            chunks: 처리할 청크 목록
            context: 추출 컨텍스트
            
        Returns:
            List[ExtractionResult]: 처리 결과 목록
        """
        results: List[ExtractionResult] = []
        
        for chunk in chunks:
            start_time = time.time()
            
            result = await self._extractor.extract(chunk, context)
            
            processing_time = time.time() - start_time
            
            if result.is_success():
                success_result = result.value
                updated_result = ExtractionResult(
                    chunk=success_result.chunk,
                    entities=success_result.entities,
                    cached=False,
                    processing_time=processing_time,
                    error=success_result.error
                )
                results.append(updated_result)
            else:
                failed_result = ExtractionResult.failure(
                    chunk=chunk,
                    error=result.error,
                    processing_time=processing_time
                )
                results.append(failed_result)
        
        return results
    
    async def _process_worker_batch(
        self,
        chunks: List[ChunkText],
        context: ExtractionContext
    ) -> List[ExtractionResult]:
        """
        단일 워커가 할당받은 청크 배치를 처리합니다.
        
        Args:
            chunks: 워커에 할당된 청크 목록
            context: 추출 컨텍스트
            
        Returns:
            List[ExtractionResult]: 처리 결과 목록
        """
        return await self._process_chunks_sequential(chunks, context)
