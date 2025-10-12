"""
용어 추출 Port

Infrastructure Layer에서 구현할 추상 인터페이스입니다.
"""

from abc import ABC, abstractmethod
from typing import List

from ..value_objects.chunk_text import ChunkText
from ..value_objects.extraction_context import ExtractionContext
from ..entities.extraction_result import ExtractionResult

try:
    from rfs.core.result import Result
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


class TermExtractionPort(ABC):
    """
    용어 추출 포트
    
    Infrastructure Layer에서 이 인터페이스를 구현합니다.
    (예: OpenAITermExtractor)
    """
    
    @abstractmethod
    async def extract(
        self,
        chunk: ChunkText,
        context: ExtractionContext = None
    ) -> Result[ExtractionResult, str]:
        """
        단일 청크에서 용어 추출
        
        Args:
            chunk: 추출할 청크
            context: 추출 컨텍스트 (None이면 기본값 사용)
            
        Returns:
            Result[ExtractionResult, str]: 성공 시 추출 결과, 실패 시 에러 메시지
        """
        pass
    
    @abstractmethod
    async def extract_batch(
        self,
        chunks: List[ChunkText],
        context: ExtractionContext = None
    ) -> List[Result[ExtractionResult, str]]:
        """
        여러 청크에서 용어 추출 (병렬 처리 가능)
        
        Args:
            chunks: 추출할 청크 리스트
            context: 추출 컨텍스트 (None이면 기본값 사용)
            
        Returns:
            각 청크별 Result 리스트
        """
        pass
