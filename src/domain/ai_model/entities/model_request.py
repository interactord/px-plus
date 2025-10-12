"""
ModelRequest Entity

모델 요청 엔티티
"""

from dataclasses import dataclass, field
from typing import List, Optional

try:
    from rfs.core.result import Result, Success, Failure
except ImportError:
    # 폴백: 기본 Result 구현
    from dataclasses import dataclass as _dataclass
    from typing import Generic, TypeVar, Union

    T = TypeVar("T")
    E = TypeVar("E")

    @_dataclass
    class Success(Generic[T]):
        """성공 결과"""
        value: T

        def is_success(self) -> bool:
            return True

        def unwrap(self) -> T:
            return self.value

    @_dataclass
    class Failure(Generic[E]):
        """실패 결과"""
        error: E

        def is_success(self) -> bool:
            return False

        def unwrap_error(self) -> E:
            return self.error

    Result = Union[Success[T], Failure[E]]

from ..value_objects.model_type import ModelType
from ..value_objects.message import Message
from ..value_objects.template_context import TemplateContext
from .model_config import ModelConfig


@dataclass(frozen=True)
class ModelRequest:
    """
    모델 실행 요청 엔티티 (불변)

    Attributes:
        model_type: 모델 타입 (REASONING or CHAT)
        messages: 대화 메시지 리스트
        config: 모델 설정
        template_name: 사용할 템플릿 이름 (선택)
        template_context: 템플릿 컨텍스트 (선택)
    """

    model_type: ModelType
    messages: List[Message]
    config: ModelConfig = field(default_factory=ModelConfig.default)
    template_name: Optional[str] = None
    template_context: Optional[TemplateContext] = None

    @classmethod
    def create(
        cls,
        model_type: ModelType,
        messages: List[Message],
        config: Optional[ModelConfig] = None,
        template_name: Optional[str] = None,
        template_context: Optional[TemplateContext] = None
    ) -> Result["ModelRequest", str]:
        """
        ModelRequest 생성 (검증 포함)

        Args:
            model_type: 모델 타입
            messages: 대화 메시지 리스트
            config: 모델 설정 (선택)
            template_name: 템플릿 이름 (선택)
            template_context: 템플릿 컨텍스트 (선택)

        Returns:
            Result[ModelRequest, str]: 성공 시 요청 객체, 실패 시 에러 메시지
        """
        # messages 검증
        if not messages:
            return Failure("메시지는 최소 1개 이상이어야 합니다")

        # 템플릿 검증
        if template_name and not template_context:
            return Failure("템플릿 이름이 제공되면 템플릿 컨텍스트도 필요합니다")

        # config 기본값 설정
        final_config = config if config is not None else ModelConfig.default()

        return Success(cls(
            model_type=model_type,
            messages=messages,
            config=final_config,
            template_name=template_name,
            template_context=template_context
        ))

    def has_template(self) -> bool:
        """템플릿 사용 여부 확인"""
        return self.template_name is not None

    def message_count(self) -> int:
        """메시지 개수 반환"""
        return len(self.messages)

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "model_type": self.model_type.value,
            "messages": [msg.to_dict() for msg in self.messages],
            "config": self.config.to_dict(),
            "template_name": self.template_name,
            "template_context": (
                self.template_context.to_dict()
                if self.template_context
                else None
            )
        }
