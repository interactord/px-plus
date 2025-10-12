"""
용어 추출 서비스 모듈

용어 추출의 핵심 오케스트레이션 로직을 담당합니다.
병렬 처리와 배치 처리를 관리합니다.
"""

import asyncio
import time
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor

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
from ....domain.term_extraction.value_objects.chunk_text import ChunkText, ChunkTextBatch
from ....domain.term_extraction.value_objects.extraction_context import ExtractionContext
from ....domain.term_extraction.entities.extraction_result import (
    ExtractionResult,
    ExtractionBatchResult
)
from ....domain.term_extraction.ports.term_extraction_port import TermExtractionPort

# DTO import
from ..dto.extraction_request_dto import ExtractionRequestDTO
from ..dto.extraction_response_dto import ExtractionResponseDTO


class TermExtractionService:
    """
    용어 추출 서비스
    
    병렬 처리를 통한 배치 용어 추출을 오케스트레이션합니다.
    """
    
    def __init__(
        self,
        extractor: TermExtractionPort,
        max_workers: int = 3
    ):
        """
        서비스 초기화
        
        Args:
            extractor: 실제 추출을 수행할 Port 구현체
            max_workers: 병렬 처리 워커 수 (기본값: 3)
        """
        self._extractor = extractor
        self._max_workers = max_workers
    
    async def extract_from_documents(
        self,
        request: ExtractionRequestDTO
    ) -> Result[ExtractionResponseDTO, str]:
        """
        문서들로부터 용어를 추출합니다.
        
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
        
        # 2. 병렬 처리
        if request.parallel_workers > 1 and len(chunks) > 1:
            results = await self._process_chunks_parallel(
                chunks,
                context,
                request.parallel_workers
            )
        else:
            # 단일 워커 처리
            results = await self._process_chunks_sequential(chunks, context)
        
        # 3. 결과 집계
        total_time = time.time() - start_time
        batch_result = ExtractionBatchResult(
            results=tuple(results),
            total_processing_time=total_time
        )
        
        # 4. DTO로 변환
        response = ExtractionResponseDTO.from_domain(batch_result)
        
        return Success(response)
    
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
            result = await self._extractor.extract(chunk, context)
            
            if result.is_success():
                results.append(result.value)
            else:
                # 실패한 청크는 실패 결과로 저장
                failed_result = ExtractionResult.failure(
                    chunk=chunk,
                    error=result.error
                )
                results.append(failed_result)
        
        return results
    
    async def _process_chunks_parallel(
        self,
        chunks: List[ChunkText],
        context: ExtractionContext,
        num_workers: int
    ) -> List[ExtractionResult]:
        """
        청크를 병렬로 처리합니다.
        
        Args:
            chunks: 처리할 청크 목록
            context: 추출 컨텍스트
            num_workers: 워커 수
            
        Returns:
            List[ExtractionResult]: 처리 결과 목록
        """
        # 1. 청크 분배
        batch = ChunkTextBatch(chunks=tuple(chunks))
        worker_batches = batch.split_for_parallel(num_workers)
        
        # 2. 워커별 처리 태스크 생성
        tasks = [
            self._process_worker_batch(worker_chunks, context)
            for worker_chunks in worker_batches
        ]
        
        # 3. 병렬 실행
        worker_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 4. 결과 병합 (원본 순서 유지)
        all_results: List[ExtractionResult] = []
        for worker_result in worker_results:
            if isinstance(worker_result, Exception):
                # 워커 전체가 실패한 경우 (예외 발생)
                # 이 경우는 거의 발생하지 않지만 안전성을 위해 처리
                continue
            all_results.extend(worker_result)
        
        # 5. chunk_index 기준으로 정렬 (원본 순서 복원)
        all_results.sort(key=lambda r: r.chunk.chunk_index)
        
        return all_results
    
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
        results: List[ExtractionResult] = []
        
        for chunk in chunks:
            start_time = time.time()
            
            result = await self._extractor.extract(chunk, context)
            
            processing_time = time.time() - start_time
            
            if result.is_success():
                # 처리 시간 업데이트
                success_result = result.value
                updated_result = ExtractionResult(
                    chunk=success_result.chunk,
                    entities=success_result.entities,
                    cached=success_result.cached,
                    processing_time=processing_time,
                    error=success_result.error
                )
                results.append(updated_result)
            else:
                # 실패한 청크
                failed_result = ExtractionResult.failure(
                    chunk=chunk,
                    error=result.error,
                    processing_time=processing_time
                )
                results.append(failed_result)
        
        return results
