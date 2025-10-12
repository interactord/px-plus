"""
ModelResponse Entity

모델 응답 엔티티
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any

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


@dataclass(frozen=True)
class ModelResponse:
    """
    모델 실행 응답 엔티티 (불변)

    Attributes:
        content: 생성된 텍스트
        model: 사용된 모델 이름
        usage: 토큰 사용량 정보
        finish_reason: 완료 이유 (stop, length, content_filter 등)
        metadata: 추가 메타데이터
    """

    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        content: str,
        model: str,
        usage: Dict[str, int],
        finish_reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Result["ModelResponse", str]:
        """
        ModelResponse 생성 (검증 포함)

        Args:
            content: 생성된 텍스트
            model: 사용된 모델 이름
            usage: 토큰 사용량 정보
            finish_reason: 완료 이유
            metadata: 추가 메타데이터 (선택)

        Returns:
            Result[ModelResponse, str]: 성공 시 응답 객체, 실패 시 에러 메시지
        """
        # content 검증
        if not content:
            return Failure("응답 내용이 비어있습니다")

        # model 검증
        if not model or not model.strip():
            return Failure("모델 이름이 필요합니다")

        # usage 검증
        if not usage:
            return Failure("토큰 사용량 정보가 필요합니다")

        return Success(cls(
            content=content.strip(),
            model=model.strip(),
            usage=dict(usage),  # 불변 복사
            finish_reason=finish_reason,
            metadata=dict(metadata) if metadata else {}
        ))

    def total_tokens(self) -> int:
        """전체 토큰 사용량 반환"""
        return self.usage.get("total_tokens", 0)

    def prompt_tokens(self) -> int:
        """프롬프트 토큰 사용량 반환"""
        return self.usage.get("prompt_tokens", 0)

    def completion_tokens(self) -> int:
        """완성 토큰 사용량 반환"""
        return self.usage.get("completion_tokens", 0)

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "content": self.content,
            "model": self.model,
            "usage": dict(self.usage),
            "finish_reason": self.finish_reason,
            "metadata": dict(self.metadata) if self.metadata else {}
        }
