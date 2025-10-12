"""
ModelPort Interface

모델 실행 포트 인터페이스
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

from ..entities.model_request import ModelRequest
from ..entities.model_response import ModelResponse


class ModelPort(ABC):
    """
    모델 실행 포트 인터페이스

    Infrastructure Layer에서 구현해야 하는 추상 인터페이스입니다.
    """

    @abstractmethod
    def execute(self, request: ModelRequest) -> Result[ModelResponse, str]:
        """
        모델 실행

        Args:
            request: 모델 요청 엔티티

        Returns:
            Result[ModelResponse, str]: 성공 시 응답 엔티티, 실패 시 에러 메시지
        """
        pass
