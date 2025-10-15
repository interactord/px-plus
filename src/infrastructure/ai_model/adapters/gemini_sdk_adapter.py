"""
GeminiSDKAdapter

Google Gen AI SDK 기반 Gemini 어댑터
공식 google-genai 라이브러리를 사용하여 안정적이고 간결한 구현 제공
"""

import os
from typing import Dict, Any, List

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

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

from ....domain.ai_model.entities.model_request import ModelRequest
from ....domain.ai_model.entities.model_response import ModelResponse
from ....domain.ai_model.value_objects.message import Message
from ....domain.ai_model.entities.model_config import ModelConfig
from ....domain.ai_model.ports.model_port import ModelPort


class GeminiSDKAdapter(ModelPort):
    """
    Google Gen AI SDK 기반 Gemini 어댑터

    특징:
    - 공식 google-genai SDK 사용
    - SSL 인증서 문제 자동 해결
    - Google Search Grounding 지원
    - 간결한 코드와 우수한 안정성

    장점:
    - ✅ SSL 문제 없음 (SDK가 자동 처리)
    - ✅ 공식 지원 및 자동 업데이트
    - ✅ 에러 처리 개선
    - ✅ 코드 간결성

    사용 예:
    ```python
    adapter = GeminiSDKAdapter(
        api_key="your-api-key",
        model_name="gemini-2.0-flash-exp",
        enable_grounding=True
    )

    response = adapter.execute(request)
    ```
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = "gemini-2.0-flash-exp",
        enable_grounding: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        timeout: int = 60
    ):
        """
        Gemini SDK 어댑터 초기화

        Args:
            api_key: Google API 키 (None이면 GOOGLE_API_KEY 환경 변수 사용)
            model_name: Gemini 모델명 (기본: gemini-2.0-flash-exp)
            enable_grounding: Google Search Grounding 활성화 여부
            temperature: 온도 (0.0-1.0, 낮을수록 일관성)
            max_tokens: 최대 토큰 수
            timeout: 타임아웃 (초)

        Raises:
            ImportError: google-genai 패키지가 설치되지 않은 경우
            ValueError: API 키가 없는 경우
        """
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-genai 패키지가 설치되지 않았습니다. "
                "다음 명령어로 설치하세요: pip install google-genai"
            )

        # API 키 설정
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self._api_key:
            raise ValueError(
                "Google API 키가 필요합니다. "
                "api_key 인자로 전달하거나 GOOGLE_API_KEY 환경 변수를 설정하세요."
            )

        self._model_name = model_name
        self._enable_grounding = enable_grounding
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout

        # Google Gen AI 클라이언트 생성
        self._client = genai.Client(api_key=self._api_key)

    def execute(self, request: ModelRequest) -> Result[ModelResponse, str]:
        """
        Gemini 모델 실행

        Args:
            request: 모델 요청

        Returns:
            Result[ModelResponse, str]: 성공 시 응답, 실패 시 에러 메시지
        """
        try:
            # 메시지 내용 추출
            contents = self._extract_contents(request)

            # 설정 구성
            config = self._build_config(request.config)

            # Gemini API 호출
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=contents,
                config=config
            )

            # 응답 파싱
            return self._parse_response(response)

        except Exception as e:
            return Failure(f"Gemini SDK 호출 실패: {str(e)}")

    def _extract_contents(self, request: ModelRequest) -> str:
        """
        ModelRequest에서 콘텐츠 추출

        Args:
            request: 모델 요청

        Returns:
            str: 콘텐츠 문자열
        """
        if not request.messages:
            return ""

        # 마지막 사용자 메시지 사용
        for message in reversed(request.messages):
            if message.role == "user":
                return message.content

        return request.messages[-1].content if request.messages else ""

    def _build_config(self, model_config: ModelConfig = None):
        """
        GenerateContentConfig 구성

        Args:
            model_config: 모델 설정

        Returns:
            types.GenerateContentConfig: Gemini API 설정
        """
        # 기본 설정
        config_dict = {
            "temperature": self._temperature,
            "max_output_tokens": self._max_tokens,
        }

        # ModelConfig에서 설정 오버라이드
        if model_config:
            if model_config.temperature is not None:
                config_dict["temperature"] = model_config.temperature
            if model_config.max_tokens is not None:
                config_dict["max_output_tokens"] = model_config.max_tokens

        # Google Search Grounding 추가
        if self._enable_grounding:
            config_dict["tools"] = [{"google_search": {}}]

        return types.GenerateContentConfig(**config_dict)

    def _parse_response(self, response) -> Result[ModelResponse, str]:
        """
        Gemini SDK 응답을 ModelResponse로 변환

        Args:
            response: Gemini API 응답

        Returns:
            Result[ModelResponse, str]: 파싱된 응답 또는 에러
        """
        try:
            # 텍스트 추출
            text_content = response.text if hasattr(response, 'text') else ""

            # Grounding 메타데이터 추가 정보 (옵션)
            metadata = {}
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]

                # Grounding 정보 추출
                if hasattr(candidate, 'grounding_metadata'):
                    grounding = candidate.grounding_metadata
                    if hasattr(grounding, 'web_search_queries'):
                        metadata['web_search_queries'] = grounding.web_search_queries
                    if hasattr(grounding, 'grounding_chunks'):
                        metadata['grounding_sources'] = [
                            {
                                'title': chunk.web.title if hasattr(chunk, 'web') else None,
                                'uri': chunk.web.uri if hasattr(chunk, 'web') else None
                            }
                            for chunk in grounding.grounding_chunks
                        ]

            # Usage 정보 추출 (토큰 사용량)
            usage = {}
            if hasattr(response, 'usage_metadata'):
                usage_metadata = response.usage_metadata
                usage = {
                    "prompt_tokens": getattr(usage_metadata, 'prompt_token_count', 0),
                    "completion_tokens": getattr(usage_metadata, 'candidates_token_count', 0),
                    "total_tokens": getattr(usage_metadata, 'total_token_count', 0)
                }

            # ModelResponse 생성
            model_response = ModelResponse.create(
                content=text_content,
                model=self._model_name,
                usage=usage,
                finish_reason="STOP",
                metadata=metadata
            )

            if model_response.is_success():
                return Success(model_response.value)
            else:
                return Failure(f"ModelResponse 생성 실패: {model_response.error}")

        except Exception as e:
            return Failure(f"응답 파싱 실패: {str(e)}")

    def is_available(self) -> bool:
        """
        Gemini SDK 사용 가능 여부

        Returns:
            bool: google-genai 패키지 설치 여부
        """
        return GENAI_AVAILABLE

    @classmethod
    def check_requirements(cls) -> Result[None, str]:
        """
        필수 요구사항 확인

        Returns:
            Result[None, str]: 성공 또는 에러 메시지
        """
        if not GENAI_AVAILABLE:
            return Failure(
                "google-genai 패키지가 설치되지 않았습니다. "
                "설치 명령어: pip install google-genai"
            )

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return Failure(
                "GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다. "
                ".env 파일을 확인하세요."
            )

        return Success(None)
