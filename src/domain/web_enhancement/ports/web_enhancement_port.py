"""
WebEnhancementPort

웹 강화 기능의 포트 인터페이스
LLM 어댑터가 구현해야 할 인터페이스 정의
"""

from abc import ABC, abstractmethod
from typing import List

try:
    from rfs.core.result import Result
except ImportError:
    from dataclasses import dataclass
    from typing import Generic, TypeVar, Union
    T, E = TypeVar("T"), TypeVar("E")

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


class WebEnhancementPort(ABC):
    """
    웹 강화 포트 인터페이스
    
    LLM 어댑터(GPT-4o, Gemini)가 구현해야 할 인터페이스
    웹 검색 + 다국어 번역을 Single-Shot으로 처리
    
    구현체:
    - GPT4oWebEnhancementAdapter: GPT-4o + 웹서치
    - GeminiWebEnhancementAdapter: Gemini + Google Search Grounding
    """
    
    @abstractmethod
    def enhance_terms(
        self,
        term_infos: List[TermInfo],
        target_languages: List[str]
    ) -> Result[List[EnhancedTerm], str]:
        """
        용어 목록을 웹 검색 기반으로 강화
        
        Single-Shot 프롬프트로:
        1. 각 용어에 대해 웹 검색 수행
        2. 10개 언어로 동시 번역
        3. 웹 출처 URL 수집
        
        Args:
            term_infos: 강화할 용어 정보 리스트 (최대 5개 권장)
            target_languages: 번역 대상 언어 코드 (예: ["ko", "en", "ja"])
        
        Returns:
            Result[List[EnhancedTerm], str]: 성공 시 강화된 용어 리스트, 실패 시 에러 메시지
        
        Note:
            - 배치 크기는 5개가 최적 (Single-Shot 프롬프트 성능)
            - 10개 언어 동시 번역: ko, zh-CN, zh-TW, en, ja, fr, ru, it, vi, ar, es
        """
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """
        LLM 소스 이름 반환
        
        Returns:
            str: "gpt4o_web" or "gemini_web"
        """
        pass
