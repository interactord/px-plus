"""
추출 컨텍스트 Value Object

추출 작업의 컨텍스트 정보를 담고 있습니다.
"""

from dataclasses import dataclass
from typing import Optional

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
class ExtractionContext:
    """
    추출 작업 컨텍스트
    
    Attributes:
        template_name: 사용할 템플릿 이름 (고정: extract_terms.j2)
        max_entities: 최대 추출 개수 (None이면 무제한)
        include_context: 컨텍스트 설명 포함 여부
    """
    template_name: str = "extract_terms.j2"
    max_entities: Optional[int] = None
    include_context: bool = True
    
    @classmethod
    def default(cls) -> "ExtractionContext":
        """기본 컨텍스트 생성"""
        return cls()
    
    @classmethod
    def create(
        cls,
        template_name: str = "extract_terms.j2",
        max_entities: Optional[int] = None,
        include_context: bool = True
    ) -> Result["ExtractionContext", str]:
        """
        컨텍스트 생성
        
        Args:
            template_name: 템플릿 이름 (고정: extract_terms.j2)
            max_entities: 최대 엔티티 개수 (None이면 무제한)
            include_context: 컨텍스트 포함 여부
            
        Returns:
            Result[ExtractionContext, str]: 성공 시 컨텍스트, 실패 시 에러
        """
        # max_entities 검증: 음수는 불가, 0과 None은 무제한으로 허용
        if max_entities is not None and max_entities < 0:
            return Failure("최대 엔티티 개수는 0 이상이어야 합니다 (0=무제한)")
        
        return Success(cls(
            template_name=template_name,
            max_entities=max_entities,
            include_context=include_context
        ))
