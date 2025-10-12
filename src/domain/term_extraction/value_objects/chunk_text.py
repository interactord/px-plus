"""
청크 텍스트 Value Object

청크로 분할된 텍스트를 표현하는 불변 객체입니다.
"""

from dataclasses import dataclass
from typing import Optional
import hashlib

try:
    from rfs.core.result import Result, Success, Failure
except ImportError:
    # RFS Framework Fallback
    from typing import Generic, TypeVar, Union
    T = TypeVar('T')
    E = TypeVar('E')
    
    class Result(Generic[T, E]):
        def is_success(self) -> bool: ...
        def is_failure(self) -> bool: ...
        def unwrap(self) -> T: ...
        def unwrap_failure(self) -> E: ...
    
    class Success(Result[T, E]):
        def __init__(self, value: T): self._value = value
        def is_success(self) -> bool: return True
        def is_failure(self) -> bool: return False
        def unwrap(self) -> T: return self._value
        def unwrap_failure(self) -> E: raise ValueError("Success has no error")
    
    class Failure(Result[T, E]):
        def __init__(self, error: E): self._error = error
        def is_success(self) -> bool: return False
        def is_failure(self) -> bool: return True
        def unwrap(self) -> T: raise ValueError(f"Failure: {self._error}")
        def unwrap_failure(self) -> E: return self._error


@dataclass(frozen=True)
class ChunkText:
    """
    청크로 분할된 텍스트
    
    Attributes:
        content: 청크 텍스트 내용
        chunk_index: 파일 내에서의 청크 인덱스 (0부터 시작)
        source_filename: 원본 파일명
        metadata: 추가 메타데이터 (선택)
    """
    content: str
    chunk_index: int
    source_filename: str
    metadata: Optional[dict] = None
    
    @classmethod
    def create(
        cls,
        content: str,
        chunk_index: int,
        source_filename: str,
        metadata: Optional[dict] = None
    ) -> Result["ChunkText", str]:
        """
        ChunkText 생성 팩토리 메소드
        
        검증 규칙:
        - content는 비어있지 않아야 함
        - content 길이는 10,000자 이하
        - chunk_index는 0 이상
        - source_filename은 비어있지 않아야 함
        
        Args:
            content: 청크 내용
            chunk_index: 청크 인덱스
            source_filename: 원본 파일명
            metadata: 메타데이터 (선택)
            
        Returns:
            Result[ChunkText, str]: 성공 시 ChunkText, 실패 시 에러 메시지
        """
        # 검증: content
        if not content or not content.strip():
            return Failure("청크 내용은 비어있을 수 없습니다")
        
        if len(content) > 10000:
            return Failure("청크 크기는 10,000자를 초과할 수 없습니다")
        
        # 검증: chunk_index
        if chunk_index < 0:
            return Failure("청크 인덱스는 0 이상이어야 합니다")
        
        # 검증: source_filename
        if not source_filename or not source_filename.strip():
            return Failure("원본 파일명은 비어있을 수 없습니다")
        
        return Success(cls(
            content=content.strip(),
            chunk_index=chunk_index,
            source_filename=source_filename.strip(),
            metadata=metadata or {}
        ))
    
    def cache_key(self, template_name: str = "default") -> str:
        """
        캐시 키 생성
        
        Args:
            template_name: 템플릿 이름 (캐시 키에 포함)
            
        Returns:
            SHA256 해시 기반 캐시 키
        """
        key_content = f"{self.content}:{template_name}"
        return hashlib.sha256(key_content.encode()).hexdigest()
    
    def truncate_preview(self, max_length: int = 100) -> str:
        """
        로깅/디버깅용 미리보기 텍스트
        
        Args:
            max_length: 최대 길이
            
        Returns:
            잘린 미리보기 텍스트
        """
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."


@dataclass(frozen=True)
class ChunkTextBatch:
    """
    청크 배치
    
    Attributes:
        chunks: ChunkText 튜플 (불변)
    """
    chunks: tuple[ChunkText, ...]
    
    @classmethod
    def create(
        cls,
        chunks: list[ChunkText]
    ) -> Result["ChunkTextBatch", str]:
        """
        청크 배치 생성
        
        검증 규칙:
        - chunks는 비어있지 않아야 함
        - chunks는 최대 1000개 이하
        
        Args:
            chunks: ChunkText 리스트
            
        Returns:
            Result[ChunkTextBatch, str]: 성공 시 배치, 실패 시 에러
        """
        if not chunks:
            return Failure("청크 배치는 비어있을 수 없습니다")
        
        if len(chunks) > 1000:
            return Failure("청크 배치는 1000개를 초과할 수 없습니다")
        
        return Success(cls(chunks=tuple(chunks)))
    
    @property
    def total_chunks(self) -> int:
        """전체 청크 개수"""
        return len(self.chunks)
    
    def split_for_parallel(self, num_workers: int) -> list[list[ChunkText]]:
        """
        병렬 처리를 위한 청크 분할
        
        워커별로 Round-robin 방식으로 균등 분배합니다.
        
        Args:
            num_workers: 워커 개수
            
        Returns:
            워커별 청크 리스트
        """
        worker_chunks = [[] for _ in range(num_workers)]
        
        for idx, chunk in enumerate(self.chunks):
            worker_id = idx % num_workers
            worker_chunks[worker_id].append(chunk)
        
        return worker_chunks
