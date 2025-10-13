"""
GeminiChatAdapter

Google Gemini Chat 모델 전용 어댑터
OpenAI ChatAdapter와 동일한 패턴 적용
"""

from typing import Dict, Any, List

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
from .base_gemini_adapter import BaseGeminiAdapter


class GeminiChatAdapter(BaseGeminiAdapter):
    """
    Google Gemini Chat 모델 전용 어댑터

    지원 모델:
    - gemini-2.0-flash-exp (최신, 추천)
    - gemini-1.5-pro
    - gemini-1.5-flash

    Note: OpenAI ChatAdapter와 유사한 구조
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash-exp",
        base_url: str = "https://generativelanguage.googleapis.com",
        timeout: int = 60
    ):
        """
        Chat 어댑터 초기화

        Args:
            api_key: Google API 키
            model_name: Gemini 모델명 (기본: gemini-2.0-flash-exp)
            base_url: API 기본 URL
            timeout: 타임아웃 (초)
        """
        super().__init__(api_key, base_url, timeout)
        self._model_name = model_name

    def execute(self, request: ModelRequest) -> Result[ModelResponse, str]:
        """
        Gemini Chat 모델 실행

        Args:
            request: 모델 요청

        Returns:
            Result[ModelResponse, str]: 성공 시 응답, 실패 시 에러
        """
        payload = self._build_payload(request)

        # Gemini API 엔드포인트: /v1beta/models/{model}:generateContent
        endpoint = f"/v1beta/models/{self._model_name}:generateContent"

        response_result = self._make_request(endpoint, payload)

        if not response_result.is_success():
            return response_result

        response_data = response_result.unwrap()
        return self._parse_response(response_data)

    def _build_payload(self, request: ModelRequest) -> Dict[str, Any]:
        """
        Gemini Chat 모델용 페이로드 구성

        OpenAI 형식:
        {
          "messages": [{"role": "user", "content": "..."}]
        }

        Gemini 형식:
        {
          "contents": [{
            "role": "user",
            "parts": [{"text": "..."}]
          }],
          "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1000
          }
        }

        Args:
            request: 모델 요청

        Returns:
            Dict[str, Any]: Gemini API 페이로드
        """
        # 1. Messages를 Gemini contents 형식으로 변환
        contents = self._convert_messages_to_contents(request.messages)

        # 2. 기본 페이로드
        payload = {
            "contents": contents
        }

        # 3. Generation Config 추가
        generation_config = self._build_generation_config(request.config)
        if generation_config:
            payload["generationConfig"] = generation_config

        return payload

    def _convert_messages_to_contents(self, messages: List[Any]) -> List[Dict[str, Any]]:
        """
        OpenAI 메시지 형식을 Gemini contents 형식으로 변환

        OpenAI: {"role": "user", "content": "text"}
        Gemini: {"role": "user", "parts": [{"text": "text"}]}

        Note:
        - OpenAI "system" role → Gemini "user" role로 통합
        - OpenAI "assistant" role → Gemini "model" role

        Args:
            messages: OpenAI 형식 메시지 리스트

        Returns:
            List[Dict[str, Any]]: Gemini contents 리스트
        """
        contents = []

        for msg in messages:
            role = msg.role if hasattr(msg, 'role') else msg.get("role", "user")
            content = msg.content if hasattr(msg, 'content') else msg.get("content", "")

            # OpenAI role을 Gemini role로 매핑
            gemini_role = self._map_role(role)

            contents.append({
                "role": gemini_role,
                "parts": [{"text": content}]
            })

        return contents

    def _map_role(self, openai_role: str) -> str:
        """
        OpenAI role을 Gemini role로 매핑

        OpenAI:
        - system: 시스템 지시
        - user: 사용자 입력
        - assistant: AI 응답

        Gemini:
        - user: 사용자/시스템 입력
        - model: AI 응답

        Args:
            openai_role: OpenAI role

        Returns:
            str: Gemini role
        """
        role_mapping = {
            "system": "user",      # system을 user로 통합
            "user": "user",
            "assistant": "model"   # assistant를 model로 변환
        }

        return role_mapping.get(openai_role.lower(), "user")

    def _build_generation_config(self, config: Any) -> Dict[str, Any]:
        """
        ModelConfig를 Gemini generationConfig로 변환

        OpenAI 설정:
        - temperature: 0.0-2.0
        - max_tokens: 최대 토큰 수
        - top_p: 핵 샘플링

        Gemini 설정:
        - temperature: 0.0-2.0
        - maxOutputTokens: 최대 출력 토큰
        - topP: 핵 샘플링

        Args:
            config: ModelConfig 객체

        Returns:
            Dict[str, Any]: Gemini generationConfig
        """
        generation_config = {}

        if hasattr(config, 'temperature') and config.temperature is not None:
            generation_config["temperature"] = config.temperature

        if hasattr(config, 'max_tokens') and config.max_tokens is not None:
            generation_config["maxOutputTokens"] = config.max_tokens

        if hasattr(config, 'top_p') and config.top_p is not None:
            generation_config["topP"] = config.top_p

        return generation_config
