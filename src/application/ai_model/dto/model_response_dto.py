"""
ModelResponseDTO

모델 응답 데이터 전송 객체
"""

from dataclasses import dataclass
from typing import Dict, Any

from ...domain.ai_model.entities.model_response import ModelResponse


@dataclass
class ModelResponseDTO:
    """
    모델 응답 DTO

    Domain Entity를 외부 응답으로 변환합니다.
    """

    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    metadata: Dict[str, Any]

    @classmethod
    def from_domain(cls, response: ModelResponse) -> "ModelResponseDTO":
        """Domain Entity로부터 DTO 생성"""
        return cls(
            content=response.content,
            model=response.model,
            usage=dict(response.usage),
            finish_reason=response.finish_reason,
            metadata=dict(response.metadata) if response.metadata else {}
        )

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
            "metadata": self.metadata
        }
