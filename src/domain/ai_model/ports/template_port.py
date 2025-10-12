"""
TemplatePort Interface

템플릿 렌더링 포트 인터페이스
"""

from abc import ABC, abstractmethod

try:
    from rfs.core.result import Result
except ImportError:
    # 폴백: 기본 Result 구현
    from dataclasses import dataclass
    from typing import Generic, TypeVar, Union

    T = TypeVar("T")
    E = TypeVar("E")

    @dataclass
    class Success(Generic[T]):
        """성공 결과"""
        value: T

        def is_success(self) -> bool:
            return True

        def unwrap(self) -> T:
            return self.value

    @dataclass
    class Failure(Generic[E]):
        """실패 결과"""
        error: E

        def is_success(self) -> bool:
            return False

        def unwrap_error(self) -> E:
            return self.error

    Result = Union[Success[T], Failure[E]]

from ..value_objects.template_context import TemplateContext


class TemplatePort(ABC):
    """
    템플릿 렌더링 포트 인터페이스

    Infrastructure Layer에서 구현해야 하는 추상 인터페이스입니다.
    """

    @abstractmethod
    def render(
        self,
        template_name: str,
        context: TemplateContext
    ) -> Result[str, str]:
        """
        템플릿 렌더링

        Args:
            template_name: 템플릿 파일명
            context: 템플릿 컨텍스트

        Returns:
            Result[str, str]: 성공 시 렌더링된 문자열, 실패 시 에러 메시지
        """
        pass
