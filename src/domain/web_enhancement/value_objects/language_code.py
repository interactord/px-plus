"""
LanguageCode

지원하는 언어 코드 값 객체
불변 객체로 언어 코드 유효성 보장
"""

from dataclasses import dataclass
from typing import Set, List

try:
    from rfs.core.result import Result, Success, Failure
except ImportError:
    from dataclasses import dataclass as _dataclass
    from typing import Generic, TypeVar, Union
    T, E = TypeVar("T"), TypeVar("E")

    @_dataclass
    class Success(Generic[T]):
        value: T
        def is_success(self) -> bool: return True
        def unwrap(self) -> T: return self.value

    @_dataclass
    class Failure(Generic[E]):
        error: E
        def is_success(self) -> bool: return False
        def unwrap_error(self) -> E: return self.error

    Result = Union[Success[T], Failure[E]]


@dataclass(frozen=True)
class LanguageCode:
    """
    언어 코드 값 객체 (불변)
    
    지원하는 10개 언어:
    - ko: 한국어
    - zh-CN: 중국어(간체)
    - zh-TW: 中文(繁體)
    - en: English
    - ja: 日本語
    - fr: Français
    - ru: Русский
    - it: Italiano
    - vi: Tiếng Việt
    - ar: العربية
    - es: Español
    
    Attributes:
        code: ISO 언어 코드 (예: "ko", "en", "zh-CN")
    """
    
    code: str
    
    # 지원하는 언어 코드 (클래스 변수)
    SUPPORTED_LANGUAGES: Set[str] = frozenset({
        "ko", "zh-CN", "zh-TW", "en", "ja",
        "fr", "ru", "it", "vi", "ar", "es"
    })
    
    # 언어별 이름 (표시용)
    LANGUAGE_NAMES = {
        "ko": "한국어",
        "zh-CN": "中文(简体)",
        "zh-TW": "中文(繁體)",
        "en": "English",
        "ja": "日本語",
        "fr": "Français",
        "ru": "Русский",
        "it": "Italiano",
        "vi": "Tiếng Việt",
        "ar": "العربية",
        "es": "Español"
    }
    
    @classmethod
    def create(cls, code: str) -> Result["LanguageCode", str]:
        """
        LanguageCode 값 객체 생성
        
        Args:
            code: 언어 코드 (예: "ko", "en")
        
        Returns:
            Result[LanguageCode, str]: 성공 시 값 객체, 실패 시 에러 메시지
        """
        if not code or not code.strip():
            return Failure("언어 코드가 비어있습니다")
        
        code = code.strip()
        
        if code not in cls.SUPPORTED_LANGUAGES:
            return Failure(
                f"지원하지 않는 언어 코드입니다: {code}. "
                f"지원 언어: {', '.join(sorted(cls.SUPPORTED_LANGUAGES))}"
            )
        
        return Success(cls(code=code))
    
    @classmethod
    def all_supported(cls) -> List["LanguageCode"]:
        """
        지원하는 모든 언어 코드 목록
        
        Returns:
            List[LanguageCode]: 지원하는 모든 언어 코드
        """
        return [cls(code=code) for code in sorted(cls.SUPPORTED_LANGUAGES)]
    
    @classmethod
    def is_valid(cls, code: str) -> bool:
        """
        유효한 언어 코드인지 검증
        
        Args:
            code: 언어 코드
        
        Returns:
            bool: 유효성 여부
        """
        return code in cls.SUPPORTED_LANGUAGES
    
    def get_name(self) -> str:
        """
        언어 이름 조회 (표시용)
        
        Returns:
            str: 언어 이름 (예: "한국어", "English")
        """
        return self.LANGUAGE_NAMES.get(self.code, self.code)
    
    def __str__(self) -> str:
        """문자열 표현"""
        return self.code
    
    def __repr__(self) -> str:
        """디버깅용 표현"""
        return f"LanguageCode(code='{self.code}', name='{self.get_name()}')"


# 편의 상수
KOREAN = LanguageCode(code="ko")
CHINESE_SIMPLIFIED = LanguageCode(code="zh-CN")
CHINESE_TRADITIONAL = LanguageCode(code="zh-TW")
ENGLISH = LanguageCode(code="en")
JAPANESE = LanguageCode(code="ja")
FRENCH = LanguageCode(code="fr")
RUSSIAN = LanguageCode(code="ru")
ITALIAN = LanguageCode(code="it")
VIETNAMESE = LanguageCode(code="vi")
ARABIC = LanguageCode(code="ar")
SPANISH = LanguageCode(code="es")
