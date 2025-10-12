"""
ModelConfig Entity

모델 설정 엔티티
"""

from dataclasses import dataclass
from typing import Optional

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
class ModelConfig:
    """
    모델 실행 설정 엔티티 (불변)

    Attributes:
        temperature: 응답 다양성 (0.0 ~ 2.0)
        max_tokens: 최대 토큰 수
        top_p: 누적 확률 임계값 (0.0 ~ 1.0)
        frequency_penalty: 빈도 패널티 (-2.0 ~ 2.0)
        presence_penalty: 존재 패널티 (-2.0 ~ 2.0)
    """

    temperature: float = 1.0
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

    @classmethod
    def create(
        cls,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0
    ) -> Result["ModelConfig", str]:
        """
        ModelConfig 생성 (검증 포함)

        Returns:
            Result[ModelConfig, str]: 성공 시 설정 객체, 실패 시 에러 메시지
        """
        # temperature 검증
        if not (0.0 <= temperature <= 2.0):
            return Failure(
                f"temperature는 0.0 ~ 2.0 사이여야 합니다: {temperature}"
            )

        # max_tokens 검증
        if max_tokens is not None and max_tokens <= 0:
            return Failure(
                f"max_tokens는 양수여야 합니다: {max_tokens}"
            )

        # top_p 검증
        if not (0.0 <= top_p <= 1.0):
            return Failure(
                f"top_p는 0.0 ~ 1.0 사이여야 합니다: {top_p}"
            )

        # frequency_penalty 검증
        if not (-2.0 <= frequency_penalty <= 2.0):
            return Failure(
                f"frequency_penalty는 -2.0 ~ 2.0 사이여야 합니다: {frequency_penalty}"
            )

        # presence_penalty 검증
        if not (-2.0 <= presence_penalty <= 2.0):
            return Failure(
                f"presence_penalty는 -2.0 ~ 2.0 사이여야 합니다: {presence_penalty}"
            )

        return Success(cls(
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty
        ))

    @classmethod
    def default(cls) -> "ModelConfig":
        """기본 설정 생성"""
        return cls()

    def to_dict(self) -> dict:
        """딕셔너리로 변환 (OpenAI API 포맷)"""
        config_dict = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty
        }

        if self.max_tokens is not None:
            config_dict["max_tokens"] = self.max_tokens

        return config_dict
