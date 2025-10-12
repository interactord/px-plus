"""
ModelRequestDTO

모델 요청 데이터 전송 객체
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

try:
    from rfs.core.result import Result, Success, Failure
except ImportError:
    from dataclasses import dataclass as _dc
    from typing import Generic, TypeVar, Union
    T, E = TypeVar("T"), TypeVar("E")

    @_dc
    class Success(Generic[T]):
        value: T
        def is_success(self) -> bool: return True
        def unwrap(self) -> T: return self.value

    @_dc
    class Failure(Generic[E]):
        error: E
        def is_success(self) -> bool: return False
        def unwrap_error(self) -> E: return self.error

    Result = Union[Success[T], Failure[E]]

from ...domain.ai_model.entities.model_request import ModelRequest
from ...domain.ai_model.entities.model_config import ModelConfig
from ...domain.ai_model.value_objects.model_type import ModelType
from ...domain.ai_model.value_objects.message import Message
from ...domain.ai_model.value_objects.template_context import TemplateContext


@dataclass
class ModelRequestDTO:
    """
    모델 요청 DTO

    외부 입력을 Domain Entity로 변환합니다.
    """

    model_type: str
    messages: List[Dict[str, str]]
    config: Optional[Dict[str, Any]] = None
    template_name: Optional[str] = None
    template_context: Optional[Dict[str, Any]] = None

    def to_domain(self) -> Result[ModelRequest, str]:
        """DTO를 Domain Entity로 변환"""
        # 1. ModelType 변환
        try:
            domain_model_type = ModelType.from_string(self.model_type)
        except ValueError as e:
            return Failure(str(e))

        # 2. Messages 변환
        message_results = [
            Message.create(
                role=msg.get("role", ""),
                content=msg.get("content", "")
            )
            for msg in self.messages
        ]

        failed_messages = [
            result.unwrap_error()
            for result in message_results
            if not result.is_success()
        ]

        if failed_messages:
            return Failure(f"메시지 변환 실패: {', '.join(failed_messages)}")

        domain_messages = [
            result.unwrap()
            for result in message_results
            if result.is_success()
        ]

        # 3. ModelConfig 변환
        if self.config:
            config_result = ModelConfig.create(
                temperature=self.config.get("temperature", 1.0),
                max_tokens=self.config.get("max_tokens"),
                top_p=self.config.get("top_p", 1.0),
                frequency_penalty=self.config.get("frequency_penalty", 0.0),
                presence_penalty=self.config.get("presence_penalty", 0.0)
            )

            if not config_result.is_success():
                return Failure(config_result.unwrap_error())

            domain_config = config_result.unwrap()
        else:
            domain_config = ModelConfig.default()

        # 4. TemplateContext 변환
        domain_template_context = None
        if self.template_context:
            context_result = TemplateContext.create(self.template_context)
            if not context_result.is_success():
                return Failure(context_result.unwrap_error())
            domain_template_context = context_result.unwrap()

        # 5. ModelRequest 생성
        return ModelRequest.create(
            model_type=domain_model_type,
            messages=domain_messages,
            config=domain_config,
            template_name=self.template_name,
            template_context=domain_template_context
        )
