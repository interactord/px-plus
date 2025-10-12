"""
ModelAdapterFactory

모델 어댑터 생성 팩토리
"""

from typing import Dict, Callable

try:
    from rfs.core.registry import Registry
    from rfs.core.result import Result, Success, Failure
except ImportError:
    # 폴백 구현
    from dataclasses import dataclass
    from typing import Generic, TypeVar, Union, Any
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

    class Registry:
        def __init__(self):
            self._registry = {}

        def register(self, key: Any, value: Any):
            self._registry[key] = value

        def get(self, key: Any) -> Any:
            return self._registry[key]

from ...domain.ai_model.value_objects.model_type import ModelType
from ...domain.ai_model.ports.model_port import ModelPort

from ..adapters.openai_reasoning_adapter import OpenAIReasoningAdapter
from ..adapters.openai_chat_adapter import OpenAIChatAdapter


class AdapterConfig:
    """어댑터 설정"""

    def __init__(
        self,
        api_key: str,
        model_name: str = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self.timeout = timeout


class ModelAdapterFactory:
    """
    모델 어댑터 생성 팩토리

    RFS Registry 패턴을 사용하여 어댑터 등록 및 조회
    """

    def __init__(self):
        """팩토리 초기화 및 어댑터 등록"""
        self._registry = Registry()
        self._register_adapters()

    def _register_adapters(self):
        """어댑터 팩토리 함수 등록"""
        self._registry.register(
            ModelType.REASONING,
            self._create_reasoning_adapter
        )
        self._registry.register(
            ModelType.CHAT,
            self._create_chat_adapter
        )

    @staticmethod
    def _create_reasoning_adapter(config: AdapterConfig) -> ModelPort:
        """Reasoning 어댑터 생성"""
        return OpenAIReasoningAdapter(
            api_key=config.api_key,
            model_name=config.model_name or "o1-preview",
            base_url=config.base_url,
            timeout=config.timeout if config.timeout else 120
        )

    @staticmethod
    def _create_chat_adapter(config: AdapterConfig) -> ModelPort:
        """Chat 어댑터 생성"""
        return OpenAIChatAdapter(
            api_key=config.api_key,
            model_name=config.model_name or "gpt-4o",
            base_url=config.base_url,
            timeout=config.timeout
        )

    def create(
        self,
        model_type: ModelType,
        config: AdapterConfig
    ) -> Result[ModelPort, str]:
        """
        모델 타입에 맞는 어댑터 생성

        Args:
            model_type: 모델 타입
            config: 어댑터 설정

        Returns:
            Result[ModelPort, str]: 성공 시 어댑터 인스턴스, 실패 시 에러 메시지
        """
        if not isinstance(model_type, ModelType):
            return Failure(f"잘못된 모델 타입: {type(model_type)}")

        if not config.api_key or not config.api_key.strip():
            return Failure("API 키가 필요합니다")

        try:
            factory_fn = self._registry.get(model_type)
            adapter = factory_fn(config)
            return Success(adapter)

        except KeyError:
            return Failure(f"지원하지 않는 모델 타입: {model_type.value}")
        except Exception as e:
            return Failure(f"어댑터 생성 실패: {str(e)}")

    def supported_types(self) -> list:
        """지원하는 모델 타입 목록 반환"""
        return list(ModelType)
