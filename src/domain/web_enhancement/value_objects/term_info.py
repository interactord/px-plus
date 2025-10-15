"""
TermInfo

용어 기본 정보 값 객체
원본 추출 정보를 불변 객체로 관리
"""

from dataclasses import dataclass, field
from typing import List

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
class TermInfo:
    """
    용어 기본 정보 값 객체 (불변)
    
    추출된 고유명사의 원본 정보
    
    Attributes:
        term: 용어 (예: "Partido Popular")
        type: 용어 타입 (person, company, location, etc.)
        primary_domain: 주요 도메인 (politics, media, sports, etc.)
        context: 용어의 맥락 정보
        tags: 태그 리스트 (예: ["#PP", "#Spain"])
    """
    
    term: str
    type: str
    primary_domain: str
    context: str = ""
    tags: List[str] = field(default_factory=list)
    
    @classmethod
    def create(
        cls,
        term: str,
        type: str,
        primary_domain: str,
        context: str = "",
        tags: List[str] = None
    ) -> Result["TermInfo", str]:
        """
        TermInfo 값 객체 생성
        
        Args:
            term: 용어
            type: 용어 타입
            primary_domain: 주요 도메인
            context: 맥락 정보
            tags: 태그 리스트
        
        Returns:
            Result[TermInfo, str]: 성공 시 값 객체, 실패 시 에러 메시지
        """
        # 필수 필드 검증
        if not term or not term.strip():
            return Failure("용어가 비어있습니다")
        
        if not type or not type.strip():
            return Failure("용어 타입이 비어있습니다")
        
        if not primary_domain or not primary_domain.strip():
            return Failure("주요 도메인이 비어있습니다")
        
        # 타입 정규화 (검증 없이 소문자로 변환만)
        normalized_type = type.strip().lower()
        
        # 도메인 기본 검증 (길이와 형식만)
        normalized_domain = primary_domain.strip().lower()
        
        # 최소한의 검증: 비어있지 않고, 합리적인 길이
        if len(normalized_domain) > 100:
            return Failure(f"도메인이 너무 깁니다 (최대 100자): {primary_domain}")
        
        return Success(cls(
            term=term.strip(),
            type=normalized_type,
            primary_domain=normalized_domain,
            context=context.strip() if context else "",
            tags=tags or []
        ))
    
    @classmethod
    def from_dict(cls, data: dict) -> Result["TermInfo", str]:
        """
        딕셔너리에서 TermInfo 생성
        
        sample_term.json 형식과 호환
        
        Args:
            data: 용어 정보 딕셔너리
        
        Returns:
            Result[TermInfo, str]: 성공 시 값 객체, 실패 시 에러 메시지
        """
        try:
            return cls.create(
                term=data.get("term", ""),
                type=data.get("type", ""),
                primary_domain=data.get("primary_domain", ""),
                context=data.get("context", ""),
                tags=data.get("tags", [])
            )
        except Exception as e:
            return Failure(f"딕셔너리 파싱 실패: {str(e)}")
    
    def to_dict(self) -> dict:
        """
        딕셔너리로 변환
        
        Returns:
            dict: 용어 정보 딕셔너리
        """
        return {
            "term": self.term,
            "type": self.type,
            "primary_domain": self.primary_domain,
            "context": self.context,
            "tags": self.tags
        }
    
    def __str__(self) -> str:
        """문자열 표현"""
        return f"{self.term} ({self.type}, {self.primary_domain})"
    
    def __repr__(self) -> str:
        """디버깅용 표현"""
        return (
            f"TermInfo(term='{self.term}', type='{self.type}', "
            f"primary_domain='{self.primary_domain}')"
        )
