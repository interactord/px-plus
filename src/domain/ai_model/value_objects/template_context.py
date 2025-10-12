"""
TemplateContext Value Object

템플릿 컨텍스트 값 객체
"""

from dataclasses import dataclass, field
from typing import Any, Dict

try:
    from rfs.core.result import Result, Success, Failure
except ImportError:
    # 폴백: 기본 Result 구현
    from dataclasses import dataclass as _dataclass
    from typing import Generic, TypeVar, Union

    T = TypeVar("T")
    E = TypeVar("E")

    @_dataclass
    class Success(Generic[T]):
        """성공 결과"""
        value: T

        def is_success(self) -> bool:
            return True

        def unwrap(self) -> T:
            return self.value

    @_dataclass
    class Failure(Generic[E]):
        """실패 결과"""
        error: E

        def is_success(self) -> bool:
            return False

        def unwrap_error(self) -> E:
            return self.error

    Result = Union[Success[T], Failure[E]]


@dataclass(frozen=True)
class TemplateContext:
    """
    템플릿 렌더링 컨텍스트 값 객체 (불변)

    Attributes:
        variables: 템플릿 변수 딕셔너리
    """

    variables: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, variables: Dict[str, Any]) -> Result["TemplateContext", str]:
        """
        TemplateContext 생성 (검증 포함)

        Args:
            variables: 템플릿 변수 딕셔너리

        Returns:
            Result[TemplateContext, str]: 성공 시 컨텍스트 객체, 실패 시 에러 메시지
        """
        if variables is None:
            return Failure("템플릿 변수 딕셔너리는 None일 수 없습니다")

        # 불변 딕셔너리로 복사 (얕은 복사)
        immutable_vars = dict(variables)

        return Success(cls(variables=immutable_vars))

    @classmethod
    def empty(cls) -> "TemplateContext":
        """빈 컨텍스트 생성"""
        return cls(variables={})

    def get(self, key: str, default: Any = None) -> Any:
        """변수 값 가져오기"""
        return self.variables.get(key, default)

    def has(self, key: str) -> bool:
        """변수 존재 여부 확인"""
        return key in self.variables

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return dict(self.variables)

    def merge(self, other: "TemplateContext") -> "TemplateContext":
        """
        다른 컨텍스트와 병합 (불변 연산)

        Args:
            other: 병합할 컨텍스트

        Returns:
            TemplateContext: 병합된 새 컨텍스트
        """
        merged_vars = {**self.variables, **other.variables}
        return TemplateContext(variables=merged_vars)
