"""
웹 강화 DTO
"""

from .enhancement_request_dto import EnhancementRequestDTO
from .enhancement_response_dto import EnhancementResponseDTO, EnhancedTermDTO, SummaryDTO

__all__ = [
    "EnhancementRequestDTO",
    "EnhancementResponseDTO",
    "EnhancedTermDTO",
    "SummaryDTO"
]
