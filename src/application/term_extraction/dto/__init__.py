"""
용어 추출 Data Transfer Objects (DTOs)

외부와의 데이터 교환을 위한 Pydantic 모델을 정의합니다.
"""

from .extraction_request_dto import ProcessedFileModel, ExtractionRequestDTO
from .extraction_response_dto import ChunkResultDTO, SummaryDTO, ExtractionResponseDTO

__all__ = [
    "ProcessedFileModel",
    "ExtractionRequestDTO",
    "ChunkResultDTO",
    "SummaryDTO",
    "ExtractionResponseDTO",
]
