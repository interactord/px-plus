"""
OpenAIChatAdapter

OpenAI SDK 기반 Chat Completion 어댑터
공식 openai 라이브러리를 사용하여 안정적이고 간결한 구현 제공
"""

from typing import Dict, Any

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

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
from ....domain.ai_model.ports.model_port import ModelPort


class OpenAIChatAdapter(ModelPort):
    """
    OpenAI SDK 기반 Chat Completion 어댑터
    
    특징:
    - 공식 openai SDK 사용
    - 자동 재시도 및 에러 처리
    - 스트리밍 지원 (향후)
    
    지원 모델:
    - gpt-4o (최신, 추천)
    - gpt-4o-mini
    - gpt-4-turbo
    - gpt-3.5-turbo
    
    사용 예:
    ```python
    adapter = OpenAIChatAdapter(
        api_key="your-api-key",
        model_name="gpt-4o"
    )
    
    response = adapter.execute(request)
    ```
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        timeout: int = 60
    ):
        """
        OpenAI Chat 어댑터 초기화
        
        Args:
            api_key: OpenAI API 키 (None이면 OPENAI_API_KEY 환경 변수 사용)
            model_name: 모델명 (기본: gpt-4o)
            temperature: 온도 (0.0-2.0)
            max_tokens: 최대 토큰 수
            timeout: 타임아웃 (초)
        
        Raises:
            ImportError: openai 패키지가 설치되지 않은 경우
            ValueError: API 키가 없는 경우
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai 패키지가 설치되지 않았습니다. "
                "다음 명령어로 설치하세요: pip install openai"
            )
        
        # API 키 설정
        import os
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "OpenAI API 키가 필요합니다. "
                "api_key 인자로 전달하거나 OPENAI_API_KEY 환경 변수를 설정하세요."
            )
        
        self._model_name = model_name
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout
        
        # OpenAI 클라이언트 생성
        from openai import OpenAI
        self._client = OpenAI(
            api_key=self._api_key,
            timeout=timeout
        )

    def execute(self, request: ModelRequest) -> Result[ModelResponse, str]:
        """
        OpenAI Chat 모델 실행
        
        Args:
            request: 모델 요청
        
        Returns:
            Result[ModelResponse, str]: 성공 시 응답, 실패 시 에러 메시지
        """
        try:
            # 메시지 변환
            messages = self._convert_messages(request.messages)
            
            # 설정 구성
            kwargs = self._build_kwargs(request.config)
            
            # OpenAI API 호출
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=messages,
                **kwargs
            )
            
            # 응답 파싱
            return self._parse_response(response)
        
        except Exception as e:
            return Failure(f"OpenAI SDK 호출 실패: {str(e)}")

    def _convert_messages(self, messages):
        """
        ModelRequest 메시지를 OpenAI 형식으로 변환
        
        Args:
            messages: Message 객체 리스트
        
        Returns:
            list: OpenAI API 형식 메시지
        """
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]

    def _build_kwargs(self, model_config):
        """
        OpenAI API kwargs 구성
        
        Args:
            model_config: ModelConfig 객체
        
        Returns:
            dict: OpenAI API kwargs
        """
        kwargs = {
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        
        # ModelConfig에서 설정 오버라이드
        if model_config:
            if hasattr(model_config, 'temperature') and model_config.temperature is not None:
                kwargs["temperature"] = model_config.temperature
            if hasattr(model_config, 'max_tokens') and model_config.max_tokens is not None:
                kwargs["max_tokens"] = model_config.max_tokens
            if hasattr(model_config, 'top_p') and model_config.top_p is not None:
                kwargs["top_p"] = model_config.top_p
            if hasattr(model_config, 'frequency_penalty') and model_config.frequency_penalty is not None:
                kwargs["frequency_penalty"] = model_config.frequency_penalty
            if hasattr(model_config, 'presence_penalty') and model_config.presence_penalty is not None:
                kwargs["presence_penalty"] = model_config.presence_penalty
        
        return kwargs

    def _parse_response(self, response) -> Result[ModelResponse, str]:
        """
        OpenAI SDK 응답을 ModelResponse로 변환
        
        Args:
            response: OpenAI API 응답
        
        Returns:
            Result[ModelResponse, str]: 파싱된 응답 또는 에러
        """
        try:
            # 첫 번째 choice 사용
            choice = response.choices[0]
            content = choice.message.content
            
            # Usage 정보 추출
            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            
            # 메타데이터
            metadata = {
                "id": response.id,
                "created": response.created,
                "system_fingerprint": getattr(response, 'system_fingerprint', None)
            }
            
            # ModelResponse 생성
            model_response = ModelResponse.create(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=choice.finish_reason,
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
        OpenAI SDK 사용 가능 여부
        
        Returns:
            bool: openai 패키지 설치 여부
        """
        return OPENAI_AVAILABLE

    @classmethod
    def check_requirements(cls) -> Result[None, str]:
        """
        필수 요구사항 확인
        
        Returns:
            Result[None, str]: 성공 또는 에러 메시지
        """
        if not OPENAI_AVAILABLE:
            return Failure(
                "openai 패키지가 설치되지 않았습니다. "
                "설치 명령어: pip install openai"
            )
        
        import os
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return Failure(
                "OPENAI_API_KEY 환경 변수가 설정되지 않았습니다. "
                ".env 파일을 확인하세요."
            )
        
        return Success(None)
