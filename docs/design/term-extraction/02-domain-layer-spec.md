# Domain Layer 명세서

## 1. 개요

Term Extraction 시스템의 Domain Layer는 핵심 비즈니스 로직과 엔티티를 정의합니다. 외부 의존성 없이 순수한 비즈니스 규칙만을 포함합니다.

## 2. 디렉토리 구조

```
src/domain/term_extraction/
├── __init__.py
├── value_objects/
│   ├── __init__.py
│   ├── chunk_text.py
│   ├── entity_type.py
│   └── extraction_context.py
├── entities/
│   ├── __init__.py
│   ├── extracted_entity.py
│   └── extraction_result.py
└── ports/
    ├── __init__.py
    ├── term_extraction_port.py
    └── cache_port.py
```

## 3. Value Objects

### 3.1 ChunkText

**목적**: 청크로 분할된 텍스트를 표현하는 불변 객체

**파일**: `src/domain/term_extraction/value_objects/chunk_text.py`

```python
from dataclasses import dataclass
from typing import Optional
import hashlib
from rfs.core.result import Result, Success, Failure

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
        """
        # 검증
        if not content or not content.strip():
            return Failure("청크 내용은 비어있을 수 없습니다")
        
        if len(content) > 10000:
            return Failure("청크 크기는 10,000자를 초과할 수 없습니다")
        
        if chunk_index < 0:
            return Failure("청크 인덱스는 0 이상이어야 합니다")
        
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
        chunks: ChunkText 리스트
        total_chunks: 전체 청크 개수
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
        
        Args:
            num_workers: 워커 개수
            
        Returns:
            워커별 청크 리스트
        """
        result = [[] for _ in range(num_workers)]
        for idx, chunk in enumerate(self.chunks):
            worker_id = idx % num_workers
            result[worker_id].append(chunk)
        return result
```

### 3.2 EntityType

**목적**: 추출 가능한 엔티티 타입을 정의하는 열거형

**파일**: `src/domain/term_extraction/value_objects/entity_type.py`

```python
from enum import Enum
from typing import Optional
from rfs.core.result import Result, Success, Failure


class EntityType(str, Enum):
    """
    추출 가능한 엔티티 타입
    
    Values:
        PERSON: 개인 이름, 전문가, 팀 멤버
        COMPANY: 조직, 기업, 기관, 스타트업
        PRODUCT: 제품, 서비스, 브랜드, 애플리케이션, 플랫폼
        TECHNICAL_TERM: 기술 용어, 프레임워크, 도구, 방법론, 프로그래밍 언어
    """
    PERSON = "person"
    COMPANY = "company"
    PRODUCT = "product"
    TECHNICAL_TERM = "technical_term"
    
    @classmethod
    def from_string(cls, value: str) -> Result["EntityType", str]:
        """
        문자열로부터 EntityType 생성
        
        Args:
            value: 엔티티 타입 문자열
            
        Returns:
            Success(EntityType) 또는 Failure(에러 메시지)
        """
        try:
            return Success(cls(value.lower()))
        except ValueError:
            valid_types = ", ".join([t.value for t in cls])
            return Failure(
                f"지원하지 않는 엔티티 타입: {value}. "
                f"사용 가능한 타입: {valid_types}"
            )
    
    @classmethod
    def all_types(cls) -> list[str]:
        """모든 엔티티 타입 반환"""
        return [t.value for t in cls]
    
    def description(self) -> str:
        """엔티티 타입 설명"""
        descriptions = {
            EntityType.PERSON: "개인 이름, 전문가, 팀 멤버",
            EntityType.COMPANY: "조직, 기업, 기관, 스타트업",
            EntityType.PRODUCT: "제품, 서비스, 브랜드, 애플리케이션",
            EntityType.TECHNICAL_TERM: "기술 용어, 프레임워크, 도구, 방법론"
        }
        return descriptions.get(self, "알 수 없는 타입")


@dataclass(frozen=True)
class EntityTypeFilter:
    """
    엔티티 타입 필터
    
    Attributes:
        include_types: 포함할 타입 (None이면 전체)
        exclude_types: 제외할 타입
    """
    include_types: Optional[tuple[EntityType, ...]] = None
    exclude_types: tuple[EntityType, ...] = ()
    
    @classmethod
    def create(
        cls,
        include: Optional[list[str]] = None,
        exclude: Optional[list[str]] = None
    ) -> Result["EntityTypeFilter", str]:
        """
        필터 생성
        
        Args:
            include: 포함할 타입 문자열 리스트
            exclude: 제외할 타입 문자열 리스트
        """
        include_types = None
        if include:
            types = []
            for type_str in include:
                result = EntityType.from_string(type_str)
                if result.is_failure():
                    return result.map(lambda _: None)
                types.append(result.unwrap())
            include_types = tuple(types)
        
        exclude_types = []
        if exclude:
            for type_str in exclude:
                result = EntityType.from_string(type_str)
                if result.is_failure():
                    return result.map(lambda _: None)
                exclude_types.append(result.unwrap())
        
        return Success(cls(
            include_types=include_types,
            exclude_types=tuple(exclude_types)
        ))
    
    def matches(self, entity_type: EntityType) -> bool:
        """
        엔티티 타입이 필터 조건에 맞는지 확인
        
        Args:
            entity_type: 확인할 엔티티 타입
            
        Returns:
            필터 통과 여부
        """
        # 제외 목록에 있으면 False
        if entity_type in self.exclude_types:
            return False
        
        # 포함 목록이 None이면 전체 허용
        if self.include_types is None:
            return True
        
        # 포함 목록에 있으면 True
        return entity_type in self.include_types
```

### 3.3 ExtractionContext

**목적**: 추출 작업의 컨텍스트 정보

**파일**: `src/domain/term_extraction/value_objects/extraction_context.py`

```python
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ExtractionContext:
    """
    추출 작업 컨텍스트
    
    Attributes:
        template_name: 사용할 템플릿 이름
        type_filter: 엔티티 타입 필터
        max_entities: 최대 추출 개수 (None이면 무제한)
        include_context: 컨텍스트 설명 포함 여부
    """
    template_name: str = "extract_terms.j2"
    type_filter: Optional[EntityTypeFilter] = None
    max_entities: Optional[int] = None
    include_context: bool = True
    
    @classmethod
    def default(cls) -> "ExtractionContext":
        """기본 컨텍스트"""
        return cls()
    
    @classmethod
    def create(
        cls,
        template_name: str = "extract_terms.j2",
        include_types: Optional[list[str]] = None,
        exclude_types: Optional[list[str]] = None,
        max_entities: Optional[int] = None,
        include_context: bool = True
    ) -> Result["ExtractionContext", str]:
        """
        컨텍스트 생성
        
        Args:
            template_name: 템플릿 이름
            include_types: 포함할 타입
            exclude_types: 제외할 타입
            max_entities: 최대 엔티티 개수
            include_context: 컨텍스트 포함 여부
        """
        # 타입 필터 생성
        type_filter = None
        if include_types or exclude_types:
            filter_result = EntityTypeFilter.create(include_types, exclude_types)
            if filter_result.is_failure():
                return filter_result.map(lambda _: None)
            type_filter = filter_result.unwrap()
        
        # max_entities 검증
        if max_entities is not None and max_entities <= 0:
            return Failure("최대 엔티티 개수는 1 이상이어야 합니다")
        
        return Success(cls(
            template_name=template_name,
            type_filter=type_filter,
            max_entities=max_entities,
            include_context=include_context
        ))
```

## 4. Entities

### 4.1 ExtractedEntity

**목적**: 추출된 단일 엔티티

**파일**: `src/domain/term_extraction/entities/extracted_entity.py`

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from ..value_objects.entity_type import EntityType
from rfs.core.result import Result, Success, Failure


@dataclass(frozen=True)
class ExtractedEntity:
    """
    추출된 엔티티
    
    Attributes:
        term: 용어/명사
        type: 엔티티 타입
        primary_domain: 주요 도메인
        tags: 태그 리스트
        context: 간단한 설명 (최대 100자)
        multilingual_expressions: 다국어 표현 (예: {"ko": "안드로이드", "en": "Android"})
    """
    term: str
    type: EntityType
    primary_domain: str
    tags: tuple[str, ...] = field(default_factory=tuple)
    context: str = ""
    multilingual_expressions: Optional[Dict[str, str]] = None
    
    @classmethod
    def create(
        cls,
        term: str,
        type_value: str,
        primary_domain: str,
        tags: Optional[List[str]] = None,
        context: str = "",
        multilingual_expressions: Optional[Dict[str, str]] = None
    ) -> Result["ExtractedEntity", str]:
        """
        엔티티 생성 팩토리 메소드
        
        검증 규칙:
        - term은 비어있지 않고 100자 이하
        - type은 유효한 EntityType
        - primary_domain은 비어있지 않고 50자 이하
        - tags는 최대 5개
        - context는 최대 200자
        """
        # term 검증
        if not term or not term.strip():
            return Failure("용어는 비어있을 수 없습니다")
        
        if len(term) > 100:
            return Failure("용어는 100자를 초과할 수 없습니다")
        
        # type 검증
        type_result = EntityType.from_string(type_value)
        if type_result.is_failure():
            return type_result.map(lambda _: None)
        entity_type = type_result.unwrap()
        
        # primary_domain 검증
        if not primary_domain or not primary_domain.strip():
            return Failure("주요 도메인은 비어있을 수 없습니다")
        
        if len(primary_domain) > 50:
            return Failure("주요 도메인은 50자를 초과할 수 없습니다")
        
        # tags 검증
        validated_tags = []
        if tags:
            if len(tags) > 5:
                return Failure("태그는 최대 5개까지 허용됩니다")
            
            for tag in tags:
                clean_tag = tag.strip()
                if clean_tag:
                    # # 접두사 추가 (없으면)
                    if not clean_tag.startswith("#"):
                        clean_tag = f"#{clean_tag}"
                    validated_tags.append(clean_tag)
        
        # context 검증
        clean_context = context.strip()
        if len(clean_context) > 200:
            return Failure("컨텍스트는 200자를 초과할 수 없습니다")
        
        return Success(cls(
            term=term.strip(),
            type=entity_type,
            primary_domain=primary_domain.strip(),
            tags=tuple(validated_tags),
            context=clean_context,
            multilingual_expressions=multilingual_expressions
        ))
    
    def to_dict(self) -> Dict[str, any]:
        """딕셔너리 변환"""
        return {
            "term": self.term,
            "type": self.type.value,
            "primary_domain": self.primary_domain,
            "tags": list(self.tags),
            "context": self.context,
            "multilingual_expressions": self.multilingual_expressions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> Result["ExtractedEntity", str]:
        """딕셔너리로부터 생성"""
        return cls.create(
            term=data.get("term", ""),
            type_value=data.get("type", ""),
            primary_domain=data.get("primary_domain", ""),
            tags=data.get("tags"),
            context=data.get("context", ""),
            multilingual_expressions=data.get("multilingual_expressions")
        )
    
    def matches_filter(self, filter: Optional[EntityTypeFilter]) -> bool:
        """필터 조건 확인"""
        if filter is None:
            return True
        return filter.matches(self.type)
```

### 4.2 ExtractionResult

**목적**: 청크 단위 추출 결과

**파일**: `src/domain/term_extraction/entities/extraction_result.py`

```python
from dataclasses import dataclass, field
from typing import List, Optional
from ..value_objects.chunk_text import ChunkText
from .extracted_entity import ExtractedEntity
from rfs.core.result import Result, Success, Failure
import time


@dataclass(frozen=True)
class ExtractionResult:
    """
    청크 단위 추출 결과
    
    Attributes:
        chunk: 원본 청크
        entities: 추출된 엔티티 리스트
        cached: 캐시에서 가져왔는지 여부
        processing_time: 처리 시간 (초)
        error: 에러 메시지 (실패 시)
    """
    chunk: ChunkText
    entities: tuple[ExtractedEntity, ...] = field(default_factory=tuple)
    cached: bool = False
    processing_time: float = 0.0
    error: Optional[str] = None
    
    @classmethod
    def success(
        cls,
        chunk: ChunkText,
        entities: List[ExtractedEntity],
        cached: bool = False,
        processing_time: float = 0.0
    ) -> "ExtractionResult":
        """성공 결과 생성"""
        return cls(
            chunk=chunk,
            entities=tuple(entities),
            cached=cached,
            processing_time=processing_time,
            error=None
        )
    
    @classmethod
    def failure(
        cls,
        chunk: ChunkText,
        error: str,
        processing_time: float = 0.0
    ) -> "ExtractionResult":
        """실패 결과 생성"""
        return cls(
            chunk=chunk,
            entities=(),
            cached=False,
            processing_time=processing_time,
            error=error
        )
    
    def is_success(self) -> bool:
        """성공 여부"""
        return self.error is None
    
    def is_failure(self) -> bool:
        """실패 여부"""
        return self.error is not None
    
    def entity_count(self) -> int:
        """추출된 엔티티 개수"""
        return len(self.entities)
    
    def filter_entities(
        self,
        type_filter: Optional[EntityTypeFilter]
    ) -> "ExtractionResult":
        """
        엔티티 필터링
        
        Args:
            type_filter: 타입 필터
            
        Returns:
            필터링된 새 결과
        """
        if type_filter is None:
            return self
        
        filtered = [e for e in self.entities if e.matches_filter(type_filter)]
        return ExtractionResult(
            chunk=self.chunk,
            entities=tuple(filtered),
            cached=self.cached,
            processing_time=self.processing_time,
            error=self.error
        )
    
    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            "filename": self.chunk.source_filename,
            "chunk_index": self.chunk.chunk_index,
            "entities": [e.to_dict() for e in self.entities],
            "cached": self.cached,
            "processing_time": self.processing_time,
            "error": self.error,
            "success": self.is_success()
        }


@dataclass(frozen=True)
class ExtractionBatchResult:
    """
    배치 추출 결과
    
    Attributes:
        results: 개별 추출 결과 리스트
        total_processing_time: 전체 처리 시간
    """
    results: tuple[ExtractionResult, ...] = field(default_factory=tuple)
    total_processing_time: float = 0.0
    
    @classmethod
    def create(
        cls,
        results: List[ExtractionResult],
        total_processing_time: float = 0.0
    ) -> "ExtractionBatchResult":
        """배치 결과 생성"""
        return cls(
            results=tuple(results),
            total_processing_time=total_processing_time
        )
    
    def success_count(self) -> int:
        """성공 개수"""
        return sum(1 for r in self.results if r.is_success())
    
    def failure_count(self) -> int:
        """실패 개수"""
        return sum(1 for r in self.results if r.is_failure())
    
    def total_entities(self) -> int:
        """전체 엔티티 개수"""
        return sum(r.entity_count() for r in self.results)
    
    def cache_hit_count(self) -> int:
        """캐시 히트 개수"""
        return sum(1 for r in self.results if r.cached)
    
    def cache_hit_rate(self) -> float:
        """캐시 히트율 (0.0 ~ 1.0)"""
        total = len(self.results)
        if total == 0:
            return 0.0
        return self.cache_hit_count() / total
    
    def summary(self) -> dict:
        """요약 통계"""
        return {
            "total_chunks": len(self.results),
            "processed": self.success_count(),
            "failed": self.failure_count(),
            "total_entities": self.total_entities(),
            "cache_hits": self.cache_hit_count(),
            "cache_hit_rate": round(self.cache_hit_rate(), 2),
            "processing_time_seconds": round(self.total_processing_time, 2)
        }
```

## 5. Ports

### 5.1 TermExtractionPort

**목적**: 용어 추출 인터페이스

**파일**: `src/domain/term_extraction/ports/term_extraction_port.py`

```python
from abc import ABC, abstractmethod
from ..value_objects.chunk_text import ChunkText
from ..value_objects.extraction_context import ExtractionContext
from ..entities.extraction_result import ExtractionResult
from rfs.core.result import Result


class TermExtractionPort(ABC):
    """
    용어 추출 포트
    
    Infrastructure Layer에서 구현됨
    """
    
    @abstractmethod
    async def extract(
        self,
        chunk: ChunkText,
        context: ExtractionContext = ExtractionContext.default()
    ) -> Result[ExtractionResult, str]:
        """
        청크에서 용어 추출
        
        Args:
            chunk: 추출할 청크
            context: 추출 컨텍스트
            
        Returns:
            Success(ExtractionResult) 또는 Failure(에러 메시지)
        """
        pass
    
    @abstractmethod
    async def extract_batch(
        self,
        chunks: List[ChunkText],
        context: ExtractionContext = ExtractionContext.default()
    ) -> List[Result[ExtractionResult, str]]:
        """
        여러 청크에서 용어 추출 (병렬 처리)
        
        Args:
            chunks: 추출할 청크 리스트
            context: 추출 컨텍스트
            
        Returns:
            각 청크별 Result 리스트
        """
        pass
```

### 5.2 CachePort

**목적**: 캐시 인터페이스

**파일**: `src/domain/term_extraction/ports/cache_port.py`

```python
from abc import ABC, abstractmethod
from typing import Optional
from ..entities.extraction_result import ExtractionResult


class CachePort(ABC):
    """
    캐시 포트
    
    Infrastructure Layer에서 구현됨
    """
    
    @abstractmethod
    async def get(self, key: str) -> Optional[ExtractionResult]:
        """
        캐시에서 결과 조회
        
        Args:
            key: 캐시 키
            
        Returns:
            ExtractionResult 또는 None (캐시 미스)
        """
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: ExtractionResult,
        ttl: int = 86400
    ) -> None:
        """
        캐시에 결과 저장
        
        Args:
            key: 캐시 키
            value: 저장할 결과
            ttl: Time-To-Live (초, 기본 24시간)
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        캐시에서 삭제
        
        Args:
            key: 캐시 키
        """
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """전체 캐시 삭제"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        캐시 존재 여부 확인
        
        Args:
            key: 캐시 키
            
        Returns:
            존재 여부
        """
        pass
```

## 6. 의존성 흐름

```
Domain Layer (Pure Business Logic)
    ↑
    │ (Ports - Interfaces)
    │
Infrastructure Layer (Concrete Implementations)
```

**중요**: Domain Layer는 외부 의존성이 없습니다. Infrastructure Layer가 Domain의 Port를 구현합니다.

## 7. Result 패턴 활용

모든 생성 메소드와 검증 로직은 Result 패턴을 사용합니다:

```python
# Success case
result = ChunkText.create("content", 0, "file.md")
if result.is_success():
    chunk = result.unwrap()

# Failure case
result = ChunkText.create("", 0, "file.md")
if result.is_failure():
    error = result.unwrap_failure()

# Chaining
result = (
    ChunkText.create(text, 0, "file.md")
    .bind(lambda chunk: extract_entities(chunk))
    .map(lambda entities: filter_entities(entities))
)
```

## 8. 불변성 (Immutability)

모든 Value Objects와 Entities는 `frozen=True`로 불변입니다:

- 생성 후 수정 불가
- 스레드 안전성 보장
- 캐싱 안전성 보장

## 9. 다음 단계

Domain Layer 구현 완료 후:
- Application Layer 명세 작성
- Infrastructure Layer 명세 작성
- 실제 구현 시작
