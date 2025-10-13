"""
GeminiWebSearchAdapter

Google Gemini 웹 검색 (Grounding) 전용 어댑터
Google Search와 연동하여 최신 정보를 활용한 응답 생성
"""

from typing import Dict, Any

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

from ....domain.ai_model.entities.model_request import ModelRequest
from ....domain.ai_model.entities.model_response import ModelResponse
from .gemini_chat_adapter import GeminiChatAdapter


class GeminiWebSearchAdapter(GeminiChatAdapter):
    """
    Google Gemini 웹 검색 (Grounding) 전용 어댑터

    특징:
    - Google Search Grounding 활성화
    - 최신 웹 정보를 기반으로 응답 생성
    - 출처 URL 제공

    사용 사례:
    - 최신 정보가 필요한 번역
    - 실시간 데이터 기반 응답
    - 웹 검증이 필요한 사실 확인

    Note: GeminiChatAdapter 확장 (웹 검색 기능 추가)
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash-exp",
        enable_grounding: bool = True,
        dynamic_threshold: float = 0.7,
        base_url: str = "https://generativelanguage.googleapis.com",
        timeout: int = 60
    ):
        """
        웹 검색 어댑터 초기화

        Args:
            api_key: Google API 키
            model_name: Gemini 모델명 (기본: gemini-2.0-flash-exp)
            enable_grounding: Google Search Grounding 활성화 여부
            dynamic_threshold: 동적 검색 임계값 (0.0-1.0, 높을수록 검색 빈도 증가)
            base_url: API 기본 URL
            timeout: 타임아웃 (초)
        """
        super().__init__(api_key, model_name, base_url, timeout)
        self._enable_grounding = enable_grounding
        self._dynamic_threshold = dynamic_threshold

    def _build_payload(self, request: ModelRequest) -> Dict[str, Any]:
        """
        Gemini 웹 검색용 페이로드 구성

        기본 페이로드에 Google Search Grounding 도구 추가

        Gemini Grounding 형식:
        {
          "contents": [...],
          "generationConfig": {...},
          "tools": [{
            "googleSearchRetrieval": {
              "dynamicRetrievalConfig": {
                "mode": "MODE_DYNAMIC",
                "dynamicThreshold": 0.7
              }
            }
          }]
        }

        Args:
            request: 모델 요청

        Returns:
            Dict[str, Any]: Gemini API 페이로드 (웹 검색 포함)
        """
        # 부모 클래스의 기본 페이로드 생성
        payload = super()._build_payload(request)

        # Google Search Grounding 추가
        if self._enable_grounding:
            payload["tools"] = [self._build_grounding_tool()]

        return payload

    def _build_grounding_tool(self) -> Dict[str, Any]:
        """
        Google Search Grounding 도구 구성

        Grounding 모드:
        - MODE_UNSPECIFIED: 기본 모드
        - MODE_DYNAMIC: 동적으로 필요 시 검색 (추천)

        동적 임계값 (dynamicThreshold):
        - 0.0-1.0 사이 값
        - 높을수록 검색 빈도 증가
        - 0.7 권장 (균형)

        Returns:
            Dict[str, Any]: Grounding 도구 설정
        """
        return {
            "googleSearch": {}
        }

    def execute(self, request: ModelRequest) -> Result[ModelResponse, str]:
        """
        Gemini 웹 검색 실행

        웹 검색이 활성화된 상태로 모델 실행
        응답에는 검색된 웹 정보와 출처가 포함됨

        Args:
            request: 모델 요청

        Returns:
            Result[ModelResponse, str]: 웹 검색 기반 응답 또는 에러
        """
        # GeminiChatAdapter의 execute 활용
        # (웹 검색은 _build_payload에서 자동 추가됨)
        return super().execute(request)
