"""
용어 추출 요청 DTO 모듈

FastAPI 엔드포인트로부터 받은 요청 데이터를 도메인 객체로 변환합니다.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

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
from ....domain.term_extraction.value_objects.entity_type import EntityTypeFilter
from ....domain.term_extraction.value_objects.extraction_context import ExtractionContext


class ProcessedFileModel(BaseModel):
    """
    처리된 파일 데이터 모델
    
    단일 파일의 청크 데이터를 표현합니다.
    """
    
    filename: str = Field(
        ...,
        description="원본 파일명",
        min_length=1,
        max_length=255
    )
    
    chunks: List[str] = Field(
        ...,
        description="청크로 분할된 텍스트 배열",
        min_length=1
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="파일 메타데이터 (선택사항)"
    )
    
    @field_validator("chunks")
    @classmethod
    def validate_chunks_not_empty(cls, v: List[str]) -> List[str]:
        """
        청크 배열의 유효성을 검증합니다.
        
        - 배열이 비어있지 않은지
        - 각 청크가 비어있지 않은지
        
        Raises:
            ValueError: 검증 실패 시
        """
        if not v or len(v) == 0:
            raise ValueError("청크 배열은 비어있을 수 없습니다")
        
        for i, chunk in enumerate(v):
            if not chunk or not chunk.strip():
                raise ValueError(f"청크 인덱스 {i}는 비어있을 수 없습니다")
        
        return v
    
    def to_chunk_texts(self) -> Result[List[ChunkText], str]:
        """
        DTO를 도메인 ChunkText 객체 리스트로 변환합니다.
        
        Returns:
            Result[List[ChunkText], str]: 성공 시 ChunkText 리스트, 실패 시 에러 메시지
        """
        chunk_texts: List[ChunkText] = []
        
        for idx, content in enumerate(self.chunks):
            result = ChunkText.create(
                content=content,
                chunk_index=idx,
                source_filename=self.filename,
                metadata=self.metadata
            )
            
            if result.is_failure():
                return Failure(
                    f"청크 {idx} 생성 실패 (파일: {self.filename}): {result.error}"
                )
            
            chunk_texts.append(result.value)
        
        return Success(chunk_texts)


class ExtractionRequestDTO(BaseModel):
    """
    용어 추출 요청 DTO
    
    FastAPI 엔드포인트로부터 받은 전체 요청 데이터를 표현합니다.
    """
    
    processed_files: List[ProcessedFileModel] = Field(
        ...,
        description="처리할 파일 목록",
        min_length=1
    )
    
    use_cache: bool = Field(
        default=True,
        description="LLM 응답 캐싱 사용 여부"
    )
    
    parallel_workers: int = Field(
        default=3,
        description="병렬 처리 워커 수",
        ge=1,
        le=10
    )
    
    template_name: str = Field(
        default="extract_terms.j2",
        description="사용할 Jinja2 템플릿 파일명"
    )
    
    type_filter: Optional[List[str]] = Field(
        default=None,
        description="필터링할 엔티티 타입 (예: ['person', 'company'])"
    )
    
    max_entities_per_chunk: Optional[int] = Field(
        default=None,
        description="청크당 최대 추출 엔티티 수",
        ge=1,
        le=100
    )
    
    include_context: bool = Field(
        default=True,
        description="엔티티의 컨텍스트 정보 포함 여부"
    )
    
    @field_validator("template_name")
    @classmethod
    def validate_template_name(cls, v: str) -> str:
        """템플릿 파일명 검증"""
        if not v.endswith(".j2"):
            raise ValueError("템플릿 파일명은 .j2 확장자를 가져야 합니다")
        return v
    
    def to_chunks(self) -> Result[List[ChunkText], str]:
        """
        모든 파일의 청크를 도메인 ChunkText 객체 리스트로 변환합니다.
        
        Returns:
            Result[List[ChunkText], str]: 성공 시 모든 ChunkText 리스트, 실패 시 에러 메시지
        """
        all_chunks: List[ChunkText] = []
        
        for file_model in self.processed_files:
            result = file_model.to_chunk_texts()
            
            if result.is_failure():
                return result
            
            all_chunks.extend(result.value)
        
        return Success(all_chunks)
    
    def to_extraction_context(self) -> Result[ExtractionContext, str]:
        """
        DTO에서 도메인 ExtractionContext 객체를 생성합니다.
        
        Returns:
            Result[ExtractionContext, str]: 성공 시 ExtractionContext, 실패 시 에러 메시지
        """
        # type_filter 변환
        type_filter_obj = None
        if self.type_filter:
            result = EntityTypeFilter.create(self.type_filter)
            if result.is_failure():
                return Failure(f"타입 필터 생성 실패: {result.error}")
            type_filter_obj = result.value
        
        # ExtractionContext 생성
        result = ExtractionContext.create(
            template_name=self.template_name,
            type_filter=type_filter_obj,
            max_entities=self.max_entities_per_chunk,
            include_context=self.include_context
        )
        
        if result.is_failure():
            return Failure(f"추출 컨텍스트 생성 실패: {result.error}")
        
        return result
    
    class Config:
        """Pydantic 설정"""
        json_schema_extra = {
            "example": {
                "processed_files": [
                    {
                        "filename": "document.txt",
                        "chunks": [
                            "첫 번째 청크 내용...",
                            "두 번째 청크 내용..."
                        ],
                        "metadata": {
                            "author": "홍길동",
                            "date": "2024-01-15"
                        }
                    }
                ],
                "use_cache": True,
                "parallel_workers": 3,
                "template_name": "extract_terms.j2",
                "type_filter": ["person", "company"],
                "max_entities_per_chunk": 50,
                "include_context": True
            }
        }
