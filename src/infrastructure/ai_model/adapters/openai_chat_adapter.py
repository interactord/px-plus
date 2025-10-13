"""
OpenAIChatAdapter

OpenAI Chat Completion 모델 전용 어댑터
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
from .base_openai_adapter import BaseOpenAIAdapter


class OpenAIChatAdapter(BaseOpenAIAdapter):
    """
    OpenAI Chat Completion 모델 전용 어댑터

    Note: Chat 모델은 모든 설정 파라미터 지원
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60
    ):
        """Chat 어댑터 초기화"""
        super().__init__(api_key, base_url, timeout)
        self._model_name = model_name

    def execute(self, request: ModelRequest) -> Result[ModelResponse, str]:
        """Chat 모델 실행"""
        payload = self._build_payload(request)
        response_result = self._make_request("/chat/completions", payload)

        if not response_result.is_success():
            return response_result

        response_data = response_result.unwrap()
        return self._parse_response(response_data)

    def _build_payload(self, request: ModelRequest) -> Dict[str, Any]:
        """Chat 모델용 페이로드 구성 (모든 파라미터 지원)"""
        payload = {
            "model": self._model_name,
            "messages": [msg.to_dict() for msg in request.messages]
        }

        # config를 페이로드에 병합
        config_dict = request.config.to_dict()
        payload.update(config_dict)

        return payload
