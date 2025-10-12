"""
엔티티 타입 Value Object

추출 가능한 엔티티 타입을 정의하는 열거형입니다.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional

try:
    from rfs.core.result import Result, Success, Failure
except ImportError:
    # RFS Framework Fallback (동일한 Fallback 코드)
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
            Result[EntityType, str]: 성공 시 EntityType, 실패 시 에러 메시지
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
        """모든 엔티티 타입 문자열 리스트 반환"""
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
            
        Returns:
            Result[EntityTypeFilter, str]: 성공 시 필터, 실패 시 에러
        """
        # include 타입 변환
        include_types = None
        if include:
            types = []
            for type_str in include:
                result = EntityType.from_string(type_str)
                if result.is_failure():
                    return Failure(result.unwrap_failure())
                types.append(result.unwrap())
            include_types = tuple(types)
        
        # exclude 타입 변환
        exclude_types = []
        if exclude:
            for type_str in exclude:
                result = EntityType.from_string(type_str)
                if result.is_failure():
                    return Failure(result.unwrap_failure())
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
