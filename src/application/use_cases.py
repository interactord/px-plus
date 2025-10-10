"""
Use Cases

애플리케이션의 유즈케이스를 구현합니다.
도메인 서비스를 조율하여 비즈니스 플로우를 완성합니다.
RFS HOF를 활용한 함수형 접근을 적용합니다.
"""

import time
from dataclasses import dataclass
from typing import List, Sequence, Tuple

# RFS Framework Result 패턴 임포트
try:
    from rfs.core.result import Failure, Result, Success
    from rfs.hof.core import pipe
    from rfs.hof.collections import compact_map, partition
except ImportError:
    from dataclasses import dataclass
    from typing import Generic, TypeVar, Union

    T = TypeVar("T")
    E = TypeVar("E")

    @dataclass
    class Success(Generic[T]):
        value: T

        def is_success(self) -> bool:
            return True

        def unwrap(self) -> T:
            return self.value

        def bind(self, func):
            return func(self.value)

    @dataclass
    class Failure(Generic[E]):
        error: E

        def is_success(self) -> bool:
            return False

        def unwrap_error(self) -> E:
            return self.error

        def bind(self, func):
            return self

    Result = Union[Success[T], Failure[E]]
    
    def pipe(*funcs):
        """함수 합성"""
        def _pipe(value):
            result = value
            for func in funcs:
                result = func(result)
            return result
        return _pipe
    
    def compact_map(func, items):
        """변환 후 None 제거"""
        return [result for item in items if (result := func(item)) is not None]
    
    def partition(predicate, items):
        """조건으로 분할"""
        true_items, false_items = [], []
        for item in items:
            (true_items if predicate(item) else false_items).append(item)
        return true_items, false_items

from ..domain.entities import DocumentChunk, ProcessedDocument as DomainProcessedDocument
from ..domain.services import (
    DocumentChunkingService,
    FileTextExtractionService,
)
from ..shared.logging import get_logger

# 로거 초기화
logger = get_logger(__name__)


@dataclass
class ProcessedDocumentDTO:
    """처리된 문서 DTO (Application Layer)"""
    filename: str
    chunks: List[str]
    total_characters: int


@dataclass
class SkippedDocumentDTO:
    """처리에서 제외된 문서 DTO"""
    filename: str
    reason: str


@dataclass
class DocumentExtractionResult:
    """문서 추출 유즈케이스 결과"""
    processed: List[ProcessedDocumentDTO]
    skipped: List[SkippedDocumentDTO]


class ExtractDocumentChunksUseCase:
    """
    업로드된 문서에서 텍스트를 추출하고 청크로 분할하는 유즈케이스
    
    HOF 패턴: pipe, compact_map을 활용한 함수형 구현
    """

    def __init__(
        self,
        text_extraction_service: FileTextExtractionService,
        chunking_service: DocumentChunkingService,
    ) -> None:
        """
        유즈케이스 초기화
        
        Args:
            text_extraction_service: 텍스트 추출 서비스
            chunking_service: 청킹 서비스
        """
        self._text_extraction_service = text_extraction_service
        self._chunking_service = chunking_service

    def execute(
        self, documents: Sequence[Tuple[str, bytes]]
    ) -> Result[DocumentExtractionResult, str]:
        """
        문서 텍스트 추출 및 청크 분할 실행 (HOF 패턴 적용)
        
        Args:
            documents: (파일명, 바이너리) 튜플 리스트
            
        Returns:
            Result[DocumentExtractionResult, str]: 처리 결과 또는 에러
        """
        start_time = time.time()
        
        logger.log_operation("document_extraction", "started",
                           document_count=len(documents))
        
        processed: List[ProcessedDocumentDTO] = []
        skipped: List[SkippedDocumentDTO] = []

        # 각 문서 처리 (함수형 접근)
        for filename, file_bytes in documents:
            # 지원 여부 확인
            if not self._text_extraction_service.is_supported(filename):
                logger.debug("파일 형식 미지원", filename=filename)
                skipped.append(SkippedDocumentDTO(
                    filename=filename,
                    reason="지원하지 않는 파일 형식입니다."
                ))
                continue

            # pipe 패턴: 텍스트 추출 → 청킹
            result = self._process_document(filename, file_bytes)
            
            if result.is_success():
                processed.append(result.unwrap())
                logger.debug("문서 처리 성공", filename=filename)
            else:
                skipped.append(SkippedDocumentDTO(
                    filename=filename,
                    reason=result.unwrap_error()
                ))
                logger.warning("문서 처리 실패", 
                             filename=filename,
                             reason=result.unwrap_error())

        # 결과 검증
        if not processed:
            logger.error("처리 가능한 문서 없음",
                       total_documents=len(documents),
                       skipped_count=len(skipped))
            return Failure("처리 가능한 문서가 없습니다. 지원되는 파일 형식을 업로드해주세요.")

        duration_ms = (time.time() - start_time) * 1000
        logger.log_performance("document_extraction",
                             duration_ms=duration_ms,
                             total_documents=len(documents),
                             processed_count=len(processed),
                             skipped_count=len(skipped))
        
        logger.log_operation("document_extraction", "completed",
                           processed_count=len(processed),
                           skipped_count=len(skipped))

        return Success(DocumentExtractionResult(
            processed=processed,
            skipped=skipped
        ))

    def _process_document(
        self, filename: str, file_bytes: bytes
    ) -> Result[ProcessedDocumentDTO, str]:
        """
        단일 문서 처리 (pipe 패턴)
        
        Args:
            filename: 파일명
            file_bytes: 파일 바이너리
            
        Returns:
            Result[ProcessedDocumentDTO, str]: 처리된 문서 또는 에러
        """
        # 텍스트 추출
        text_result = self._text_extraction_service.extract_text(file_bytes, filename)
        if not text_result.is_success():
            return Failure(text_result.unwrap_error())
        
        # 청킹
        chunk_result = self._chunking_service.chunk_text(text_result.unwrap())
        if not chunk_result.is_success():
            return Failure(chunk_result.unwrap_error())
        
        # DTO 생성
        chunks = chunk_result.unwrap()
        return Success(ProcessedDocumentDTO(
            filename=filename,
            chunks=chunks,
            total_characters=sum(len(chunk) for chunk in chunks)
        ))
