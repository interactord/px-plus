# Application Layer 명세서

## 1. 개요

Application Layer는 비즈니스 유스케이스를 오케스트레이션하고, Domain과 Infrastructure를 연결합니다.

## 2. 디렉토리 구조

```
src/application/term_extraction/
├── __init__.py
├── dto/
│   ├── __init__.py
│   ├── extraction_request_dto.py
│   └── extraction_response_dto.py
└── services/
    ├── __init__.py
    ├── term_extraction_service.py
    └── cached_extraction_service.py
```

## 3. DTOs (Data Transfer Objects)

### 3.1 ExtractionRequestDTO

**목적**: API 요청을 Domain 객체로 변환

**파일**: `src/application/term_extraction/dto/extraction_request_dto.py`

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from ...domain.term_extraction.value_objects.chunk_text import ChunkText, ChunkTextBatch
from ...domain.term_extraction.value_objects.extraction_context import ExtractionContext
from rfs.core.result import Result, Success, Failure


class ProcessedFileModel(BaseModel):
    """
    처리할 파일 정보 (Pydantic V2)
    
    Attributes:
        filename: 파일명
        chunks: 청크 텍스트 배열
    """
    filename: str = Field(..., description="원본 파일명", min_length=1, max_length=255)
    chunks: List[str] = Field(..., description="청크 배열", min_length=1, max_length=1000)
    
    @field_validator('chunks')
    @classmethod
    def validate_chunks(cls, v: List[str]) -> List[str]:
        """청크 유효성 검증"""
        if not v:
            raise ValueError("청크는 최소 1개 이상이어야 합니다")
        
        for idx, chunk in enumerate(v):
            if not chunk or not chunk.strip():
                raise ValueError(f"청크 {idx}는 비어있을 수 없습니다")
            
            if len(chunk) > 10000:
                raise ValueError(f"청크 {idx}는 10,000자를 초과할 수 없습니다")
        
        return v


class ExtractionRequestDTO(BaseModel):
    """
    용어 추출 요청 DTO (Pydantic V2)
    
    Attributes:
        processed: 처리할 파일 리스트
        use_cache: 캐시 사용 여부
        parallel_workers: 병렬 워커 개수
        template_name: 사용할 템플릿 이름
        include_types: 포함할 엔티티 타입
        exclude_types: 제외할 엔티티 타입
        max_entities_per_chunk: 청크당 최대 엔티티 개수
    """
    processed: List[ProcessedFileModel] = Field(
        ..., 
        description="처리할 파일 리스트",
        min_length=1,
        max_length=100
    )
    use_cache: bool = Field(
        default=True,
        description="캐시 사용 여부"
    )
    parallel_workers: int = Field(
        default=3,
        ge=1,
        le=10,
        description="병렬 워커 개수 (1-10)"
    )
    template_name: str = Field(
        default="extract_terms.j2",
        description="템플릿 이름"
    )
    include_types: Optional[List[str]] = Field(
        default=None,
        description="포함할 엔티티 타입"
    )
    exclude_types: Optional[List[str]] = Field(
        default=None,
        description="제외할 엔티티 타입"
    )
    max_entities_per_chunk: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="청크당 최대 엔티티 개수"
    )
    
    def to_chunks(self) -> Result[List[ChunkText], str]:
        """
        DTO를 ChunkText 리스트로 변환
        
        Returns:
            Result[List[ChunkText], str]: 성공 시 청크 리스트, 실패 시 에러
        """
        all_chunks = []
        
        for file_model in self.processed:
            for chunk_index, chunk_content in enumerate(file_model.chunks):
                chunk_result = ChunkText.create(
                    content=chunk_content,
                    chunk_index=chunk_index,
                    source_filename=file_model.filename
                )
                
                if chunk_result.is_failure():
                    return Failure(
                        f"{file_model.filename}의 청크 {chunk_index} 생성 실패: "
                        f"{chunk_result.unwrap_failure()}"
                    )
                
                all_chunks.append(chunk_result.unwrap())
        
        return Success(all_chunks)
    
    def to_extraction_context(self) -> Result[ExtractionContext, str]:
        """
        추출 컨텍스트 생성
        
        Returns:
            Result[ExtractionContext, str]: 성공 시 컨텍스트, 실패 시 에러
        """
        return ExtractionContext.create(
            template_name=self.template_name,
            include_types=self.include_types,
            exclude_types=self.exclude_types,
            max_entities=self.max_entities_per_chunk,
            include_context=True
        )
    
    def total_chunks(self) -> int:
        """전체 청크 개수"""
        return sum(len(f.chunks) for f in self.processed)
    
    class Config:
        """Pydantic 설정"""
        json_schema_extra = {
            "example": {
                "processed": [
                    {
                        "filename": "document1.md",
                        "chunks": [
                            "Android 보안 체크리스트...",
                            "FastAPI는 현대적인 웹 프레임워크..."
                        ]
                    }
                ],
                "use_cache": True,
                "parallel_workers": 3,
                "template_name": "extract_terms.j2"
            }
        }
```

### 3.2 ExtractionResponseDTO

**목적**: Domain 결과를 API 응답으로 변환

**파일**: `src/application/term_extraction/dto/extraction_response_dto.py`

```python
from dataclasses import dataclass
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from ...domain.term_extraction.entities.extraction_result import (
    ExtractionResult,
    ExtractionBatchResult
)


class ExtractedEntityDTO(BaseModel):
    """
    추출된 엔티티 DTO
    
    Attributes:
        term: 용어
        type: 엔티티 타입
        primary_domain: 주요 도메인
        tags: 태그 리스트
        context: 컨텍스트 설명
        multilingual_expressions: 다국어 표현
    """
    term: str = Field(..., description="추출된 용어")
    type: str = Field(..., description="엔티티 타입")
    primary_domain: str = Field(..., description="주요 도메인")
    tags: List[str] = Field(default_factory=list, description="태그")
    context: str = Field(default="", description="컨텍스트")
    multilingual_expressions: Dict[str, str] | None = Field(
        default=None,
        description="다국어 표현"
    )


class ChunkResultDTO(BaseModel):
    """
    청크 단위 추출 결과
    
    Attributes:
        filename: 원본 파일명
        chunk_index: 청크 인덱스
        entities: 추출된 엔티티 리스트
        cached: 캐시 히트 여부
        processing_time: 처리 시간 (초)
        success: 성공 여부
        error: 에러 메시지 (실패 시)
    """
    filename: str = Field(..., description="원본 파일명")
    chunk_index: int = Field(..., description="청크 인덱스")
    entities: List[ExtractedEntityDTO] = Field(
        default_factory=list,
        description="추출된 엔티티"
    )
    cached: bool = Field(default=False, description="캐시 히트 여부")
    processing_time: float = Field(..., description="처리 시간 (초)")
    success: bool = Field(..., description="성공 여부")
    error: str | None = Field(default=None, description="에러 메시지")
    
    @classmethod
    def from_domain(cls, result: ExtractionResult) -> "ChunkResultDTO":
        """Domain ExtractionResult로부터 DTO 생성"""
        entities_dto = [
            ExtractedEntityDTO(
                term=e.term,
                type=e.type.value,
                primary_domain=e.primary_domain,
                tags=list(e.tags),
                context=e.context,
                multilingual_expressions=e.multilingual_expressions
            )
            for e in result.entities
        ]
        
        return cls(
            filename=result.chunk.source_filename,
            chunk_index=result.chunk.chunk_index,
            entities=entities_dto,
            cached=result.cached,
            processing_time=result.processing_time,
            success=result.is_success(),
            error=result.error
        )


class SummaryDTO(BaseModel):
    """
    추출 요약 통계
    
    Attributes:
        total_chunks: 전체 청크 개수
        processed: 성공 처리 개수
        failed: 실패 개수
        total_entities: 전체 엔티티 개수
        cache_hits: 캐시 히트 개수
        cache_hit_rate: 캐시 히트율
        processing_time_seconds: 전체 처리 시간
    """
    total_chunks: int = Field(..., description="전체 청크 개수")
    processed: int = Field(..., description="성공 처리 개수")
    failed: int = Field(..., description="실패 개수")
    total_entities: int = Field(..., description="전체 엔티티 개수")
    cache_hits: int = Field(..., description="캐시 히트 개수")
    cache_hit_rate: float = Field(..., description="캐시 히트율 (0.0-1.0)")
    processing_time_seconds: float = Field(..., description="전체 처리 시간")


class ExtractionResponseDTO(BaseModel):
    """
    용어 추출 응답 DTO
    
    Attributes:
        results: 청크별 추출 결과
        summary: 요약 통계
    """
    results: List[ChunkResultDTO] = Field(
        ...,
        description="청크별 추출 결과"
    )
    summary: SummaryDTO = Field(..., description="요약 통계")
    
    @classmethod
    def from_domain(cls, batch_result: ExtractionBatchResult) -> "ExtractionResponseDTO":
        """Domain ExtractionBatchResult로부터 DTO 생성"""
        results_dto = [
            ChunkResultDTO.from_domain(r)
            for r in batch_result.results
        ]
        
        summary = batch_result.summary()
        summary_dto = SummaryDTO(
            total_chunks=summary["total_chunks"],
            processed=summary["processed"],
            failed=summary["failed"],
            total_entities=summary["total_entities"],
            cache_hits=summary["cache_hits"],
            cache_hit_rate=summary["cache_hit_rate"],
            processing_time_seconds=summary["processing_time_seconds"]
        )
        
        return cls(
            results=results_dto,
            summary=summary_dto
        )
    
    class Config:
        """Pydantic 설정"""
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "filename": "document1.md",
                        "chunk_index": 0,
                        "entities": [
                            {
                                "term": "FastAPI",
                                "type": "technical_term",
                                "primary_domain": "web_framework",
                                "tags": ["#python", "#web", "#api"],
                                "context": "Modern Python web framework",
                                "multilingual_expressions": None
                            }
                        ],
                        "cached": False,
                        "processing_time": 2.5,
                        "success": True,
                        "error": None
                    }
                ],
                "summary": {
                    "total_chunks": 10,
                    "processed": 10,
                    "failed": 0,
                    "total_entities": 45,
                    "cache_hits": 3,
                    "cache_hit_rate": 0.3,
                    "processing_time_seconds": 15.2
                }
            }
        }
```

## 4. Services

### 4.1 TermExtractionService

**목적**: 용어 추출 비즈니스 로직 오케스트레이션

**파일**: `src/application/term_extraction/services/term_extraction_service.py`

```python
import asyncio
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor
from ...domain.term_extraction.value_objects.chunk_text import ChunkText
from ...domain.term_extraction.value_objects.extraction_context import ExtractionContext
from ...domain.term_extraction.entities.extraction_result import (
    ExtractionResult,
    ExtractionBatchResult
)
from ...domain.term_extraction.ports.term_extraction_port import TermExtractionPort
from ..dto.extraction_request_dto import ExtractionRequestDTO
from ..dto.extraction_response_dto import ExtractionResponseDTO
from rfs.core.result import Result, Success, Failure
import logging

logger = logging.getLogger(__name__)


class TermExtractionService:
    """
    용어 추출 서비스
    
    단일책임: 용어 추출 유스케이스 오케스트레이션
    """
    
    def __init__(
        self,
        extractor: TermExtractionPort,
        executor: ThreadPoolExecutor | None = None
    ):
        """
        서비스 초기화
        
        Args:
            extractor: 용어 추출 포트 구현
            executor: 스레드 풀 (None이면 기본 3 워커)
        """
        self._extractor = extractor
        self._executor = executor or ThreadPoolExecutor(max_workers=3)
    
    async def extract_from_documents(
        self,
        request: ExtractionRequestDTO
    ) -> Result[ExtractionResponseDTO, str]:
        """
        문서들에서 용어 추출 (병렬 처리)
        
        Args:
            request: 추출 요청 DTO
            
        Returns:
            Result[ExtractionResponseDTO, str]: 성공 시 응답 DTO, 실패 시 에러
        """
        start_time = time.time()
        
        # 1. 청크 생성
        chunks_result = request.to_chunks()
        if chunks_result.is_failure():
            return Failure(chunks_result.unwrap_failure())
        
        chunks = chunks_result.unwrap()
        logger.info(f"총 {len(chunks)}개 청크 생성 완료")
        
        # 2. 추출 컨텍스트 생성
        context_result = request.to_extraction_context()
        if context_result.is_failure():
            return Failure(context_result.unwrap_failure())
        
        context = context_result.unwrap()
        
        # 3. 병렬 처리
        results = await self._process_chunks_parallel(
            chunks=chunks,
            context=context,
            num_workers=request.parallel_workers
        )
        
        # 4. 배치 결과 생성
        total_time = time.time() - start_time
        batch_result = ExtractionBatchResult.create(
            results=results,
            total_processing_time=total_time
        )
        
        # 5. DTO 변환
        response_dto = ExtractionResponseDTO.from_domain(batch_result)
        
        logger.info(
            f"추출 완료: {batch_result.success_count()}/{len(chunks)} 성공, "
            f"총 {batch_result.total_entities()}개 엔티티, "
            f"캐시 히트율: {batch_result.cache_hit_rate():.2%}, "
            f"처리 시간: {total_time:.2f}초"
        )
        
        return Success(response_dto)
    
    async def _process_chunks_parallel(
        self,
        chunks: List[ChunkText],
        context: ExtractionContext,
        num_workers: int
    ) -> List[ExtractionResult]:
        """
        청크들을 병렬로 처리
        
        Args:
            chunks: 처리할 청크 리스트
            context: 추출 컨텍스트
            num_workers: 워커 개수
            
        Returns:
            추출 결과 리스트
        """
        # 워커별로 청크 분배
        worker_chunks = self._distribute_chunks(chunks, num_workers)
        
        # 각 워커에 대해 비동기 작업 생성
        tasks = [
            self._process_chunk_batch(batch, context)
            for batch in worker_chunks
        ]
        
        # 모든 작업 병렬 실행
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 평탄화
        all_results = []
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                logger.error(f"워커 실행 중 예외 발생: {batch_result}")
                continue
            all_results.extend(batch_result)
        
        return all_results
    
    async def _process_chunk_batch(
        self,
        chunks: List[ChunkText],
        context: ExtractionContext
    ) -> List[ExtractionResult]:
        """
        청크 배치 처리 (단일 워커)
        
        Args:
            chunks: 처리할 청크 리스트
            context: 추출 컨텍스트
            
        Returns:
            추출 결과 리스트
        """
        results = []
        
        for chunk in chunks:
            try:
                result = await self._extractor.extract(chunk, context)
                
                if result.is_success():
                    results.append(result.unwrap())
                else:
                    # 실패 시에도 결과 기록
                    error = result.unwrap_failure()
                    failure_result = ExtractionResult.failure(
                        chunk=chunk,
                        error=error
                    )
                    results.append(failure_result)
                    logger.warning(
                        f"{chunk.source_filename}:{chunk.chunk_index} 추출 실패: {error}"
                    )
            
            except Exception as e:
                # 예외 발생 시에도 결과 기록
                error_msg = f"예외 발생: {str(e)}"
                failure_result = ExtractionResult.failure(
                    chunk=chunk,
                    error=error_msg
                )
                results.append(failure_result)
                logger.exception(
                    f"{chunk.source_filename}:{chunk.chunk_index} 처리 중 예외"
                )
        
        return results
    
    def _distribute_chunks(
        self,
        chunks: List[ChunkText],
        num_workers: int
    ) -> List[List[ChunkText]]:
        """
        청크를 워커들에게 균등 분배
        
        Args:
            chunks: 전체 청크 리스트
            num_workers: 워커 개수
            
        Returns:
            워커별 청크 리스트
        """
        worker_chunks = [[] for _ in range(num_workers)]
        
        for idx, chunk in enumerate(chunks):
            worker_id = idx % num_workers
            worker_chunks[worker_id].append(chunk)
        
        return worker_chunks
    
    def __del__(self):
        """소멸자: 스레드 풀 정리"""
        if hasattr(self, '_executor') and self._executor:
            self._executor.shutdown(wait=True)
```

### 4.2 CachedTermExtractionService

**목적**: 캐싱 레이어 추가

**파일**: `src/application/term_extraction/services/cached_extraction_service.py`

```python
import time
from typing import List
from ...domain.term_extraction.value_objects.chunk_text import ChunkText
from ...domain.term_extraction.value_objects.extraction_context import ExtractionContext
from ...domain.term_extraction.entities.extraction_result import ExtractionResult
from ...domain.term_extraction.ports.cache_port import CachePort
from .term_extraction_service import TermExtractionService
from ..dto.extraction_request_dto import ExtractionRequestDTO
from ..dto.extraction_response_dto import ExtractionResponseDTO
from rfs.core.result import Result, Success, Failure
import logging

logger = logging.getLogger(__name__)


class CachedTermExtractionService:
    """
    캐싱이 적용된 용어 추출 서비스
    
    단일책임: 캐시 레이어 관리 및 위임
    """
    
    def __init__(
        self,
        service: TermExtractionService,
        cache: CachePort
    ):
        """
        서비스 초기화
        
        Args:
            service: 기본 추출 서비스
            cache: 캐시 포트 구현
        """
        self._service = service
        self._cache = cache
    
    async def extract_with_cache(
        self,
        request: ExtractionRequestDTO
    ) -> Result[ExtractionResponseDTO, str]:
        """
        캐시를 활용한 용어 추출
        
        Args:
            request: 추출 요청 DTO
            
        Returns:
            Result[ExtractionResponseDTO, str]: 성공 시 응답 DTO, 실패 시 에러
        """
        # 캐시 비활성화 시 직접 실행
        if not request.use_cache:
            logger.info("캐시 비활성화 - 직접 추출 실행")
            return await self._service.extract_from_documents(request)
        
        # 1. 청크 생성
        chunks_result = request.to_chunks()
        if chunks_result.is_failure():
            return Failure(chunks_result.unwrap_failure())
        
        chunks = chunks_result.unwrap()
        
        # 2. 컨텍스트 생성
        context_result = request.to_extraction_context()
        if context_result.is_failure():
            return Failure(context_result.unwrap_failure())
        
        context = context_result.unwrap()
        
        # 3. 캐시 확인 및 필터링
        cache_hits, cache_misses = await self._check_cache(chunks, context)
        
        logger.info(
            f"캐시 확인: {len(cache_hits)}개 히트, {len(cache_misses)}개 미스"
        )
        
        # 4. 캐시 미스만 추출
        if cache_misses:
            # 새 요청 생성 (캐시 미스만)
            miss_request = self._create_request_for_misses(
                request, cache_misses
            )
            
            # 추출 실행
            result = await self._service.extract_from_documents(miss_request)
            
            if result.is_failure():
                return result
            
            response = result.unwrap()
            
            # 5. 새 결과를 캐시에 저장
            await self._save_to_cache(response, context)
            
            # 6. 캐시 히트와 병합
            merged_response = self._merge_results(cache_hits, response)
            
            return Success(merged_response)
        
        else:
            # 모두 캐시 히트
            logger.info("모든 청크가 캐시에서 조회됨")
            return Success(self._create_response_from_cache(cache_hits))
    
    async def _check_cache(
        self,
        chunks: List[ChunkText],
        context: ExtractionContext
    ) -> tuple[List[ExtractionResult], List[ChunkText]]:
        """
        캐시 확인
        
        Args:
            chunks: 확인할 청크 리스트
            context: 추출 컨텍스트
            
        Returns:
            (캐시 히트 결과, 캐시 미스 청크)
        """
        cache_hits = []
        cache_misses = []
        
        for chunk in chunks:
            cache_key = chunk.cache_key(context.template_name)
            cached_result = await self._cache.get(cache_key)
            
            if cached_result:
                cache_hits.append(cached_result)
            else:
                cache_misses.append(chunk)
        
        return cache_hits, cache_misses
    
    async def _save_to_cache(
        self,
        response: ExtractionResponseDTO,
        context: ExtractionContext
    ) -> None:
        """
        결과를 캐시에 저장
        
        Args:
            response: 저장할 응답
            context: 추출 컨텍스트
        """
        for result_dto in response.results:
            # DTO를 다시 Domain으로 변환 (캐시 저장용)
            # 실제로는 원본 ExtractionResult를 유지하는 것이 더 효율적
            # 여기서는 간단히 캐시 키만 생성
            cache_key = f"{result_dto.filename}:{result_dto.chunk_index}:{context.template_name}"
            # 실제 구현에서는 ExtractionResult 객체를 저장
            logger.debug(f"캐시 저장: {cache_key}")
    
    def _create_request_for_misses(
        self,
        original_request: ExtractionRequestDTO,
        miss_chunks: List[ChunkText]
    ) -> ExtractionRequestDTO:
        """
        캐시 미스 청크만으로 새 요청 생성
        
        Args:
            original_request: 원본 요청
            miss_chunks: 캐시 미스 청크
            
        Returns:
            새 요청 DTO
        """
        # 청크를 파일별로 그룹화
        from collections import defaultdict
        files_dict = defaultdict(list)
        
        for chunk in miss_chunks:
            files_dict[chunk.source_filename].append(chunk.content)
        
        # ProcessedFileModel 생성
        from ..dto.extraction_request_dto import ProcessedFileModel
        processed_files = [
            ProcessedFileModel(filename=fname, chunks=chunks)
            for fname, chunks in files_dict.items()
        ]
        
        # 새 요청 생성
        return ExtractionRequestDTO(
            processed=processed_files,
            use_cache=False,  # 이미 필터링했으므로 캐시 비활성화
            parallel_workers=original_request.parallel_workers,
            template_name=original_request.template_name,
            include_types=original_request.include_types,
            exclude_types=original_request.exclude_types,
            max_entities_per_chunk=original_request.max_entities_per_chunk
        )
    
    def _merge_results(
        self,
        cache_hits: List[ExtractionResult],
        new_response: ExtractionResponseDTO
    ) -> ExtractionResponseDTO:
        """
        캐시 히트와 새 결과 병합
        
        Args:
            cache_hits: 캐시 히트 결과
            new_response: 새로 추출한 결과
            
        Returns:
            병합된 응답
        """
        # 캐시 히트를 DTO로 변환
        from ..dto.extraction_response_dto import ChunkResultDTO
        cache_dtos = [ChunkResultDTO.from_domain(r) for r in cache_hits]
        
        # 모든 결과 합치기
        all_results = cache_dtos + new_response.results
        
        # 요약 재계산
        total_chunks = len(all_results)
        processed = sum(1 for r in all_results if r.success)
        failed = sum(1 for r in all_results if not r.success)
        total_entities = sum(len(r.entities) for r in all_results)
        cache_hits_count = sum(1 for r in all_results if r.cached)
        cache_hit_rate = cache_hits_count / total_chunks if total_chunks > 0 else 0.0
        processing_time = new_response.summary.processing_time_seconds
        
        from ..dto.extraction_response_dto import SummaryDTO
        summary = SummaryDTO(
            total_chunks=total_chunks,
            processed=processed,
            failed=failed,
            total_entities=total_entities,
            cache_hits=cache_hits_count,
            cache_hit_rate=cache_hit_rate,
            processing_time_seconds=processing_time
        )
        
        return ExtractionResponseDTO(results=all_results, summary=summary)
    
    def _create_response_from_cache(
        self,
        cache_hits: List[ExtractionResult]
    ) -> ExtractionResponseDTO:
        """
        캐시 히트만으로 응답 생성
        
        Args:
            cache_hits: 캐시 히트 결과
            
        Returns:
            응답 DTO
        """
        from ..dto.extraction_response_dto import ChunkResultDTO, SummaryDTO
        
        results = [ChunkResultDTO.from_domain(r) for r in cache_hits]
        
        summary = SummaryDTO(
            total_chunks=len(results),
            processed=len(results),
            failed=0,
            total_entities=sum(len(r.entities) for r in results),
            cache_hits=len(results),
            cache_hit_rate=1.0,
            processing_time_seconds=0.0
        )
        
        return ExtractionResponseDTO(results=results, summary=summary)
```

## 5. 의존성 흐름

```
API Layer
    ↓
CachedTermExtractionService
    ├─> CachePort (check/save)
    └─> TermExtractionService
            └─> TermExtractionPort
```

## 6. FastAPI 통합 패턴

### 6.1 의존성 주입

```python
from fastapi import Depends

# 서비스 팩토리
def get_extraction_service() -> TermExtractionService:
    # Infrastructure 레이어에서 실제 구현 제공
    extractor = get_openai_extractor()
    return TermExtractionService(extractor=extractor)

def get_cached_service(
    service: TermExtractionService = Depends(get_extraction_service)
) -> CachedTermExtractionService:
    cache = get_cache_adapter()
    return CachedTermExtractionService(service=service, cache=cache)

# 라우터에서 사용
@router.post("/extract-terms")
async def extract_terms(
    request: ExtractionRequestDTO,
    service: CachedTermExtractionService = Depends(get_cached_service)
):
    result = await service.extract_with_cache(request)
    # ...
```

### 6.2 비동기 처리

- `async/await` 전면 사용
- `asyncio.gather()로 병렬 실행
- ThreadPoolExecutor로 CPU 집약 작업 분리

### 6.3 에러 처리

```python
try:
    result = await service.extract_with_cache(request)
    if result.is_success():
        return result.unwrap()
    else:
        raise HTTPException(
            status_code=400,
            detail=result.unwrap_failure()
        )
except Exception as e:
    logger.exception("용어 추출 중 예외 발생")
    raise HTTPException(
        status_code=500,
        detail=f"서버 에러: {str(e)}"
    )
```

## 7. 성능 최적화

### 7.1 병렬 처리

- 3개 워커로 청크 분산
- Round-robin 방식 균등 분배
- `asyncio.gather()` 활용

### 7.2 캐싱 전략

- 청크 단위 캐싱
- SHA256 기반 캐시 키
- 선택적 캐시 활성화

### 7.3 메모리 관리

- 스트리밍 없음 (배치 처리)
- 청크 크기 제한 (10K 자)
- 배치 크기 제한 (100 파일)

## 8. 로깅 및 모니터링

```python
logger.info(
    "추출 완료",
    extra={
        "total_chunks": len(chunks),
        "success_count": success_count,
        "cache_hit_rate": cache_hit_rate,
        "processing_time": processing_time
    }
)
```

## 9. 다음 단계

- Infrastructure Layer 명세 작성
- API 엔드포인트 명세 작성
- 실제 구현 시작
