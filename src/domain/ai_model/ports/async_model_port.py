"""
AsyncModelPort

비동기 AI 모델 인터페이스 (포트)
"""

from abc import ABC, abstractmethod

try:
    from rfs.core.result import Result
except ImportError:
    from typing import Union, TypeVar, Generic
    from dataclasses import dataclass

    T = TypeVar("T")
    E = TypeVar("E")

    @dataclass
    class Success(Generic[T]):
        value: T
        def is_success(self) -> bool: return True
        def unwrap(self) -> T: return self.value

    @dataclass
    class Failure(Generic[E]):
        error: E
        def is_success(self) -> bool: return False
        def unwrap_error(self) -> E: return self.error

    Result = Union[Success[T], Failure[E]]

from ..entities.model_request import ModelRequest
from ..entities.model_response import ModelResponse


class AsyncModelPort(ABC):
    """
    비동기 AI 모델 포트 인터페이스

    모든 비동기 AI 모델 어댑터가 구현해야 하는 인터페이스
    헥사고날 아키텍처의 포트 역할

    구현체:
    - AsyncOpenAIChatAdapter: OpenAI AsyncClient 기반
    - AsyncGeminiChatAdapter: Google Gen AI 비동기 클라이언트 기반
    """

    @abstractmethod
    async def execute(self, request: ModelRequest) -> Result[ModelResponse, str]:
        """
        비동기 AI 모델 실행

        Args:
            request: 모델 요청

        Returns:
            Result[ModelResponse, str]: 성공 시 응답, 실패 시 에러 메시지
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        AI 모델 사용 가능 여부

        Returns:
            bool: 사용 가능 여부
        """
        pass
