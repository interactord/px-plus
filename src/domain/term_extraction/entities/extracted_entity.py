"""
추출된 엔티티 Entity

LLM이 추출한 단일 엔티티를 표현합니다.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List

from ..value_objects.entity_type import EntityType, EntityTypeFilter

try:
    from rfs.core.result import Result, Success, Failure
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
class ExtractedEntity:
    """
    추출된 엔티티
    
    Attributes:
        term: 용어/명사
        type: 엔티티 타입
        primary_domain: 주요 도메인
        tags: 태그 튜플 (불변)
        context: 간단한 설명 (최대 200자)
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
        
        Args:
            term: 용어
            type_value: 타입 문자열
            primary_domain: 주요 도메인
            tags: 태그 리스트 (선택)
            context: 컨텍스트 (선택)
            multilingual_expressions: 다국어 표현 (선택)
            
        Returns:
            Result[ExtractedEntity, str]: 성공 시 엔티티, 실패 시 에러
        """
        # 검증: term
        if not term or not term.strip():
            return Failure("용어는 비어있을 수 없습니다")
        
        if len(term) > 100:
            return Failure("용어는 100자를 초과할 수 없습니다")
        
        # 검증: type
        type_result = EntityType.from_string(type_value)
        if type_result.is_failure():
            return Failure(type_result.unwrap_failure())
        entity_type = type_result.unwrap()
        
        # 검증: primary_domain
        if not primary_domain or not primary_domain.strip():
            return Failure("주요 도메인은 비어있을 수 없습니다")
        
        if len(primary_domain) > 50:
            return Failure("주요 도메인은 50자를 초과할 수 없습니다")
        
        # 검증: tags
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
        
        # 검증: context
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
        """
        딕셔너리로부터 엔티티 생성
        
        Args:
            data: 엔티티 데이터 딕셔너리
            
        Returns:
            Result[ExtractedEntity, str]: 성공 시 엔티티, 실패 시 에러
        """
        return cls.create(
            term=data.get("term", ""),
            type_value=data.get("type", ""),
            primary_domain=data.get("primary_domain", ""),
            tags=data.get("tags"),
            context=data.get("context", ""),
            multilingual_expressions=data.get("multilingual_expressions")
        )
    
    def matches_filter(self, filter: Optional[EntityTypeFilter]) -> bool:
        """
        필터 조건 확인
        
        Args:
            filter: 타입 필터 (None이면 항상 True)
            
        Returns:
            필터 통과 여부
        """
        if filter is None:
            return True
        return filter.matches(self.type)
