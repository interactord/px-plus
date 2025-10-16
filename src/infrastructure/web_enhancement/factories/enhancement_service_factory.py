"""
EnhancementServiceFactory

웹 강화 서비스 팩토리
환경 변수 기반 어댑터 및 서비스 생성
"""

import os
from typing import Optional

try:
    from rfs.core.result import Result, Success, Failure
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

from ....domain.web_enhancement.services.web_enhancement_service import WebEnhancementService
from ....domain.web_enhancement.services.async_web_enhancement_service import AsyncWebEnhancementService
from ..adapters.gpt4o_web_enhancement_adapter import GPT4oWebEnhancementAdapter
from ..adapters.gemini_web_enhancement_adapter import GeminiWebEnhancementAdapter
from ..adapters.gemini_simple_translation_adapter import GeminiSimpleTranslationAdapter
from ..adapters.gpt4o_mini_translation_adapter import GPT4oMiniTranslationAdapter
from ..adapters.async_gpt4o_web_enhancement_adapter import AsyncGPT4oWebEnhancementAdapter
from ..adapters.async_gemini_web_enhancement_adapter import AsyncGeminiWebEnhancementAdapter


class EnhancementServiceFactory:
    """
    웹 강화 서비스 팩토리
    
    환경 변수 기반으로 적절한 어댑터와 서비스를 생성
    
    환경 변수:
    - OPENAI_API_KEY: OpenAI API 키 (필수)
    - GOOGLE_API_KEY: Google API 키 (필수)
    - WEB_ENHANCEMENT_PRIMARY: Primary 어댑터 (기본: "gpt4o")
    - WEB_ENHANCEMENT_FALLBACK: Fallback 어댑터 (기본: "gemini")
    """
    
    @classmethod
    def create_service(
        cls,
        openai_api_key: Optional[str] = None,
        google_api_key: Optional[str] = None,
        primary: str = "gpt4o",
        fallback: str = "gemini"
    ) -> Result[WebEnhancementService, str]:
        """
        웹 강화 서비스 생성
        
        Args:
            openai_api_key: OpenAI API 키 (None이면 환경 변수)
            google_api_key: Google API 키 (None이면 환경 변수)
            primary: Primary 어댑터 타입 ("gpt4o" or "gemini")
            fallback: Fallback 어댑터 타입 ("gpt4o" or "gemini")
        
        Returns:
            Result[WebEnhancementService, str]: 생성된 서비스 또는 에러
        """
        # API 키 가져오기
        openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        google_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        
        if not openai_key:
            return Failure("OPENAI_API_KEY가 설정되지 않았습니다")
        
        if not google_key:
            return Failure("GOOGLE_API_KEY가 설정되지 않았습니다")
        
        # Gemini + 웹검색 어댑터만 생성 (다른 폴백 비활성화)
        gemini_adapter = GeminiWebEnhancementAdapter(
            api_key=google_key,
            model_name="gemini-2.0-flash-exp",
            temperature=0.3,
            max_tokens=4000,
            dynamic_threshold=0.7
        )

        # 서비스 생성 (Gemini + 웹검색만 활성화, 폴백 없음)
        service = WebEnhancementService(
            primary_adapter=gemini_adapter,
            fallback_adapter=None,  # 폴백 비활성화
            simple_translation_adapter=None,  # 폴백 비활성화
            final_fallback_adapter=None,  # 폴백 비활성화
            fallback_delay=2.0
        )
        
        return Success(service)

    
    @classmethod
    def create_async_service(
        cls,
        openai_api_key: Optional[str] = None,
        google_api_key: Optional[str] = None,
        primary: str = "gpt4o",
        fallback: str = "gemini"
    ) -> Result[AsyncWebEnhancementService, str]:
        """
        비동기 웹 강화 서비스 생성
        
        Args:
            openai_api_key: OpenAI API 키 (None이면 환경 변수)
            google_api_key: Google API 키 (None이면 환경 변수)
            primary: Primary 어댑터 타입 ("gpt4o" or "gemini")
            fallback: Fallback 어댑터 타입 ("gpt4o" or "gemini")
        
        Returns:
            Result[AsyncWebEnhancementService, str]: 생성된 비동기 서비스 또는 에러
        """
        # API 키 가져오기
        openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        google_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        
        if not openai_key:
            return Failure("OPENAI_API_KEY가 설정되지 않았습니다")
        
        if not google_key:
            return Failure("GOOGLE_API_KEY가 설정되지 않았습니다")
        
        # Primary 어댑터 생성 (AsyncGPT-4o + 웹검색)
        primary_adapter = AsyncGPT4oWebEnhancementAdapter(
            api_key=openai_key,
            model_name="gpt-4o",
            temperature=0.3,
            max_tokens=4000
        )
        
        # Fallback 어댑터 생성 (AsyncGemini + 웹검색)
        fallback_adapter = AsyncGeminiWebEnhancementAdapter(
            api_key=google_key,
            model_name="gemini-2.0-flash-exp",
            temperature=0.3,
            max_tokens=4000
        )
        
        # 비동기 서비스 생성
        service = AsyncWebEnhancementService(
            primary_adapter=primary_adapter,
            fallback_adapter=fallback_adapter,
            simple_translation_adapter=None,  # 선택사항
            final_fallback_adapter=None,  # 선택사항
            fallback_delay=0.0  # 비동기에서는 지연 불필요
        )
        
        return Success(service)
    
    @classmethod
    def _create_adapter(
        cls,
        adapter_type: str,
        openai_key: str,
        google_key: str
    ):
        """
        어댑터 생성
        
        Args:
            adapter_type: 어댑터 타입 ("gpt4o" or "gemini")
            openai_key: OpenAI API 키
            google_key: Google API 키
        
        Returns:
            Result: 생성된 어댑터 또는 에러
        """
        if adapter_type == "gpt4o":
            return Success(GPT4oWebEnhancementAdapter(
                api_key=openai_key,
                model_name="gpt-4o",
                temperature=0.3,
                max_tokens=4000
            ))
        elif adapter_type == "gemini":
            return Success(GeminiWebEnhancementAdapter(
                api_key=google_key,
                model_name="gemini-2.0-flash-exp",
                temperature=0.3,
                max_tokens=4000,
                dynamic_threshold=0.7
            ))
        else:
            return Failure(
                f"알 수 없는 어댑터 타입: {adapter_type}. "
                f"허용된 값: gpt4o, gemini"
            )
    
    @classmethod
    def create_gpt4o_adapter(
        cls,
        api_key: Optional[str] = None
    ) -> Result[GPT4oWebEnhancementAdapter, str]:
        """
        GPT-4o 어댑터만 생성
        
        Args:
            api_key: OpenAI API 키 (None이면 환경 변수)
        
        Returns:
            Result[GPT4oWebEnhancementAdapter, str]: 어댑터 또는 에러
        """
        key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not key:
            return Failure("OPENAI_API_KEY가 설정되지 않았습니다")
        
        return Success(GPT4oWebEnhancementAdapter(
            api_key=key,
            model_name="gpt-4o",
            temperature=0.3,
            max_tokens=4000
        ))
    
    @classmethod
    def create_gemini_adapter(
        cls,
        api_key: Optional[str] = None
    ) -> Result[GeminiWebEnhancementAdapter, str]:
        """
        Gemini 어댑터만 생성
        
        Args:
            api_key: Google API 키 (None이면 환경 변수)
        
        Returns:
            Result[GeminiWebEnhancementAdapter, str]: 어댑터 또는 에러
        """
        key = api_key or os.getenv("GOOGLE_API_KEY")
        
        if not key:
            return Failure("GOOGLE_API_KEY가 설정되지 않았습니다")
        
        return Success(GeminiWebEnhancementAdapter(
            api_key=key,
            model_name="gemini-2.0-flash-exp",
            temperature=0.3,
            max_tokens=4000,
            dynamic_threshold=0.7
        ))
