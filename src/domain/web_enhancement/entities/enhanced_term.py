"""
EnhancedTerm

웹 검색으로 강화된 용어 엔티티
다국어 번역과 웹 출처를 포함한 고유명사 정보
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

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


@dataclass
class EnhancedTerm:
    """
    웹 검색으로 강화된 용어 엔티티
    
    추출된 고유명사에 웹 검색 기반 다국어 번역을 추가한 도메인 엔티티
    
    Attributes:
        original_term: 원본 용어 (예: "Partido Popular")
        term_type: 용어 타입 (person, company, location, etc.)
        primary_domain: 주요 도메인 (politics, media, sports, etc.)
        context: 용어의 맥락 정보
        tags: 태그 리스트 (예: ["#PP", "#Spain"])
        translations: 언어별 번역 딕셔너리 (언어 코드 → 번역)
        web_sources: 웹 검색 출처 URL 리스트
        source: 사용된 LLM 소스 ("gpt4o_web" or "gemini_web")
        confidence_score: 번역 신뢰도 (0.0-1.0)
        search_timestamp: 웹 검색 수행 시각
    
    지원 언어 (10개):
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
    """
    
    # 원본 용어 정보
    original_term: str
    term_type: str
    primary_domain: str
    context: str
    tags: List[str] = field(default_factory=list)
    
    # 웹 강화 정보
    translations: Dict[str, str] = field(default_factory=dict)
    web_sources: List[str] = field(default_factory=list)
    source: str = "unknown"
    confidence_score: float = 0.0
    search_timestamp: Optional[datetime] = None
    
    @classmethod
    def create(
        cls,
        original_term: str,
        term_type: str,
        primary_domain: str,
        context: str,
        tags: Optional[List[str]] = None,
        translations: Optional[Dict[str, str]] = None,
        web_sources: Optional[List[str]] = None,
        source: str = "unknown",
        confidence_score: float = 0.0,
        search_timestamp: Optional[datetime] = None
    ) -> Result["EnhancedTerm", str]:
        """
        EnhancedTerm 엔티티 생성
        
        팩토리 메서드로 유효성 검증 후 엔티티 생성
        
        Args:
            original_term: 원본 용어
            term_type: 용어 타입
            primary_domain: 주요 도메인
            context: 맥락 정보
            tags: 태그 리스트
            translations: 언어별 번역
            web_sources: 웹 출처 URL
            source: LLM 소스
            confidence_score: 신뢰도
            search_timestamp: 검색 시각
        
        Returns:
            Result[EnhancedTerm, str]: 성공 시 엔티티, 실패 시 에러 메시지
        """
        # 필수 필드 검증
        if not original_term or not original_term.strip():
            return Failure("원본 용어가 비어있습니다")
        
        if not term_type or not term_type.strip():
            return Failure("용어 타입이 비어있습니다")
        
        if not primary_domain or not primary_domain.strip():
            return Failure("주요 도메인이 비어있습니다")
        
        # 신뢰도 범위 검증
        if not 0.0 <= confidence_score <= 1.0:
            return Failure(f"신뢰도는 0.0-1.0 사이여야 합니다: {confidence_score}")
        
        # LLM 소스 검증
        valid_sources = {"gpt4o_web", "gemini_web", "unknown"}
        if source not in valid_sources:
            return Failure(
                f"유효하지 않은 소스입니다: {source}. "
                f"허용된 값: {', '.join(valid_sources)}"
            )
        
        # 번역 검증 (있는 경우)
        if translations:
            valid_language_codes = {
                "ko", "zh-CN", "zh-TW", "en", "ja",
                "fr", "ru", "it", "vi", "ar", "es"
            }
            
            invalid_codes = set(translations.keys()) - valid_language_codes
            if invalid_codes:
                return Failure(
                    f"유효하지 않은 언어 코드: {', '.join(invalid_codes)}"
                )
        
        # 엔티티 생성
        enhanced_term = cls(
            original_term=original_term.strip(),
            term_type=term_type.strip(),
            primary_domain=primary_domain.strip(),
            context=context,
            tags=tags or [],
            translations=translations or {},
            web_sources=web_sources or [],
            source=source,
            confidence_score=confidence_score,
            search_timestamp=search_timestamp or datetime.utcnow()
        )
        
        return Success(enhanced_term)
    
    def add_translation(self, language_code: str, translation: str) -> Result[None, str]:
        """
        번역 추가
        
        Args:
            language_code: 언어 코드 (예: "ko", "en")
            translation: 번역된 텍스트
        
        Returns:
            Result[None, str]: 성공 시 None, 실패 시 에러 메시지
        """
        valid_language_codes = {
            "ko", "zh-CN", "zh-TW", "en", "ja",
            "fr", "ru", "it", "vi", "ar", "es"
        }
        
        if language_code not in valid_language_codes:
            return Failure(
                f"유효하지 않은 언어 코드: {language_code}. "
                f"허용된 값: {', '.join(valid_language_codes)}"
            )
        
        if not translation or not translation.strip():
            return Failure("번역이 비어있습니다")
        
        self.translations[language_code] = translation.strip()
        return Success(None)
    
    def add_web_source(self, url: str) -> Result[None, str]:
        """
        웹 출처 URL 추가
        
        Args:
            url: 출처 URL
        
        Returns:
            Result[None, str]: 성공 시 None, 실패 시 에러 메시지
        """
        if not url or not url.strip():
            return Failure("URL이 비어있습니다")
        
        # URL 중복 방지
        if url not in self.web_sources:
            self.web_sources.append(url.strip())
        
        return Success(None)
    
    def get_translation(self, language_code: str) -> Optional[str]:
        """
        특정 언어의 번역 조회
        
        Args:
            language_code: 언어 코드
        
        Returns:
            Optional[str]: 번역 (없으면 None)
        """
        return self.translations.get(language_code)
    
    def has_translation(self, language_code: str) -> bool:
        """
        특정 언어의 번역 존재 여부
        
        Args:
            language_code: 언어 코드
        
        Returns:
            bool: 번역 존재 여부
        """
        return language_code in self.translations
    
    def is_complete(self) -> bool:
        """
        번역 완성 여부 (10개 언어 모두 번역)
        
        Returns:
            bool: 10개 언어 모두 번역되었는지 여부
        """
        required_languages = {
            "ko", "zh-CN", "zh-TW", "en", "ja",
            "fr", "ru", "it", "vi", "ar", "es"
        }
        return required_languages.issubset(set(self.translations.keys()))
    
    def get_completion_rate(self) -> float:
        """
        번역 완성도 (0.0-1.0)
        
        Returns:
            float: 번역된 언어 수 / 10
        """
        return len(self.translations) / 10.0
    
    @classmethod
    def from_dict(cls, data: Dict) -> "EnhancedTerm":
        """
        딕셔너리로부터 EnhancedTerm 생성
        
        Args:
            data: 엔티티 정보 딕셔너리
        
        Returns:
            EnhancedTerm: 생성된 엔티티
        """
        # search_timestamp 처리
        timestamp = data.get("search_timestamp")
        if timestamp and isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        return cls(
            original_term=data["original_term"],
            term_type=data["term_type"],
            primary_domain=data["primary_domain"],
            context=data["context"],
            tags=data.get("tags", []),
            translations=data.get("translations", {}),
            web_sources=data.get("web_sources", []),
            source=data.get("source", "unknown"),
            confidence_score=data.get("confidence_score", 0.0),
            search_timestamp=timestamp
        )
    
    def to_dict(self) -> Dict:
        """
        딕셔너리로 변환
        
        Returns:
            Dict: 엔티티 정보 딕셔너리
        """
        return {
            "original_term": self.original_term,
            "term_type": self.term_type,
            "primary_domain": self.primary_domain,
            "context": self.context,
            "tags": self.tags,
            "translations": self.translations,
            "web_sources": self.web_sources,
            "source": self.source,
            "confidence_score": self.confidence_score,
            "search_timestamp": (
                self.search_timestamp.isoformat()
                if self.search_timestamp else None
            ),
            "completion_rate": self.get_completion_rate(),
            "is_complete": self.is_complete()
        }
