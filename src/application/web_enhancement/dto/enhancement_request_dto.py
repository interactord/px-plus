"""
EnhancementRequestDTO

웹 강화 요청 DTO
"""

from dataclasses import dataclass, field
from typing import List, Optional

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

from ....domain.web_enhancement.value_objects.term_info import TermInfo
from ....domain.web_enhancement.value_objects.language_code import LanguageCode


@dataclass
class EnhancementRequestDTO:
    """
    웹 강화 요청 DTO
    
    API 요청 → Domain 엔티티 변환
    
    Attributes:
        terms: 강화할 용어 목록
        target_languages: 번역 대상 언어 (None이면 10개 모두)
        use_cache: 캐시 사용 여부 (기본: True)
        batch_size: 배치 크기 (기본: 5)
        concurrent_batches: 동시 배치 수 (기본: 3)
    """
    
    terms: List[dict]
    target_languages: Optional[List[str]] = None
    use_cache: bool = True
    batch_size: int = 5
    concurrent_batches: int = 3
    
    @classmethod
    def create(
        cls,
        terms: List[dict],
        target_languages: Optional[List[str]] = None,
        use_cache: bool = True,
        batch_size: int = 5,
        concurrent_batches: int = 3
    ) -> Result["EnhancementRequestDTO", str]:
        """
        EnhancementRequestDTO 생성
        
        Args:
            terms: 강화할 용어 목록 (딕셔너리)
            target_languages: 번역 대상 언어
            use_cache: 캐시 사용 여부
            batch_size: 배치 크기
            concurrent_batches: 동시 배치 수
        
        Returns:
            Result[EnhancementRequestDTO, str]: 생성된 DTO 또는 에러
        """
        # 입력 검증
        if not terms:
            return Failure("용어 목록이 비어있습니다")
        
        if batch_size < 1:
            return Failure(f"배치 크기는 1 이상이어야 합니다: {batch_size}")
        
        if batch_size > 10:
            return Failure(f"배치 크기는 10 이하를 권장합니다: {batch_size}")
        
        if concurrent_batches < 1:
            return Failure(f"동시 배치 수는 1 이상이어야 합니다: {concurrent_batches}")
        
        if concurrent_batches > 15:
            return Failure(f"동시 배치 수는 15 이하를 권장합니다: {concurrent_batches}")
        
        # 언어 코드 검증
        if target_languages is not None:
            for lang in target_languages:
                if not LanguageCode.is_valid(lang):
                    return Failure(
                        f"유효하지 않은 언어 코드: {lang}. "
                        f"지원 언어: {', '.join(sorted(LanguageCode.SUPPORTED_LANGUAGES))}"
                    )
        
        return Success(cls(
            terms=terms,
            target_languages=target_languages,
            use_cache=use_cache,
            batch_size=batch_size,
            concurrent_batches=concurrent_batches
        ))
    
    def to_term_infos(self) -> Result[List[TermInfo], str]:
        """
        TermInfo 리스트로 변환
        
        Returns:
            Result[List[TermInfo], str]: 변환된 TermInfo 또는 에러
        """
        term_infos = []
        
        for idx, term_dict in enumerate(self.terms):
            result = TermInfo.from_dict(term_dict)
            
            if not result.is_success():
                return Failure(
                    f"용어 {idx+1} 변환 실패: {result.unwrap_error()}"
                )
            
            term_infos.append(result.unwrap())
        
        return Success(term_infos)
    
    def get_target_languages(self) -> List[str]:
        """
        번역 대상 언어 목록
        
        Returns:
            List[str]: 언어 코드 (None이면 10개 모두)
        """
        if self.target_languages is None:
            return [
                "ko", "zh-CN", "zh-TW", "en", "ja",
                "fr", "ru", "it", "vi", "ar", "es"
            ]
        return self.target_languages
    
    def get_total_batches(self) -> int:
        """
        전체 배치 수 계산
        
        Returns:
            int: 전체 배치 수
        """
        import math
        return math.ceil(len(self.terms) / self.batch_size)
