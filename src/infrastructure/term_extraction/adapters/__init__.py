"""
용어 추출 Adapters

외부 시스템과의 통합을 위한 구체적인 구현을 제공합니다.
"""

from .openai_term_extractor import OpenAITermExtractor
from .memory_cache_adapter import MemoryCacheAdapter

__all__ = [
    "OpenAITermExtractor",
    "MemoryCacheAdapter",
]
