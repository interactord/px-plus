"""
ModelType Value Object

모델 타입 열거형
"""

from enum import Enum
from typing import Literal


class ModelType(str, Enum):
    """
    OpenAI 모델 타입 열거형

    지원 타입:
        - REASONING: 추론 전용 모델 (o1, o3 등)
        - CHAT: 일반 대화 모델 (gpt-4, gpt-3.5-turbo 등)
    """

    REASONING = "reasoning"
    CHAT = "chat"

    @classmethod
    def from_string(cls, value: str) -> "ModelType":
        """
        문자열로부터 ModelType 생성

        Args:
            value: 모델 타입 문자열

        Returns:
            ModelType: 열거형 값

        Raises:
            ValueError: 지원하지 않는 타입인 경우
        """
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(
                f"지원하지 않는 모델 타입: {value}. "
                f"가능한 값: {', '.join([t.value for t in cls])}"
            )

    def is_reasoning(self) -> bool:
        """추론 모델 여부 확인"""
        return self == ModelType.REASONING

    def is_chat(self) -> bool:
        """대화 모델 여부 확인"""
        return self == ModelType.CHAT


# 타입 힌트용 리터럴
ModelTypeLiteral = Literal["reasoning", "chat"]
