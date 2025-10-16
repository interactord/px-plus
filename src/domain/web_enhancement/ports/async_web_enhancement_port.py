"""
AsyncWebEnhancementPort

비동기 웹 강화 포트 인터페이스
"""

from abc import ABC, abstractmethod
from typing import List

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

from ..entities.enhanced_term import EnhancedTerm
from ..value_objects.term_info import TermInfo


class AsyncWebEnhancementPort(ABC):
    """
    비동기 웹 강화 포트 인터페이스

    고유명사를 웹 검색으로 강화하고 다국어 번역을 제공하는 비동기 인터페이스
    헥사고날 아키텍처의 포트 역할

    구현체:
    - AsyncGPT4oWebEnhancementAdapter: GPT-4o + 웹검색
    - AsyncGeminiWebEnhancementAdapter: Gemini + 웹검색
    """

    @abstractmethod
    async def enhance_terms(
        self,
        term_infos: List[TermInfo],
        target_languages: List[str]
    ) -> Result[List[EnhancedTerm], str]:
        """
        비동기 용어 웹 강화

        Args:
            term_infos: 강화할 용어 정보
            target_languages: 번역 대상 언어

        Returns:
            Result[List[EnhancedTerm], str]: 강화된 용어 리스트 또는 에러
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """
        소스 이름 반환

        Returns:
            str: 소스 식별자
        """
        pass
