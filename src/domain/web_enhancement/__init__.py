"""
웹 강화 도메인 계층

추출된 고유명사에 웹 검색 기반 다국어 번역을 추가하는 도메인
"""

from .entities import EnhancedTerm
from .value_objects import LanguageCode, TermInfo
from .ports import WebEnhancementPort
from .services import WebEnhancementService

__all__ = [
    "EnhancedTerm",
    "LanguageCode",
    "TermInfo",
    "WebEnhancementPort",
    "WebEnhancementService"
]
