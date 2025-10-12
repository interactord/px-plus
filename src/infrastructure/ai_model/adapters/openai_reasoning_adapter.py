"""
OpenAIReasoningAdapter

OpenAI Reasoning 모델 전용 어댑터
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

from ...domain.ai_model.entities.model_request import ModelRequest
from ...domain.ai_model.entities.model_response import ModelResponse
from .base_openai_adapter import BaseOpenAIAdapter


class OpenAIReasoningAdapter(BaseOpenAIAdapter):
    """
    OpenAI Reasoning 모델 전용 어댑터

    Note: Reasoning 모델은 temperature, top_p 등 일부 파라미터를 지원하지 않음
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "o1-preview",
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 120
    ):
        """Reasoning 어댑터 초기화 (타임아웃 120초)"""
        super().__init__(api_key, base_url, timeout)
        self._model_name = model_name

    def execute(self, request: ModelRequest) -> Result[ModelResponse, str]:
        """Reasoning 모델 실행"""
        payload = self._build_payload(request)
        response_result = self._make_request("/chat/completions", payload)

        if not response_result.is_success():
            return response_result

        response_data = response_result.unwrap()
        return self._parse_response(response_data)

    def _build_payload(self, request: ModelRequest) -> Dict[str, Any]:
        """Reasoning 모델용 페이로드 구성 (max_tokens만 지원)"""
        payload = {
            "model": self._model_name,
            "messages": [msg.to_dict() for msg in request.messages]
        }

        if request.config.max_tokens:
            payload["max_tokens"] = request.config.max_tokens

        return payload
