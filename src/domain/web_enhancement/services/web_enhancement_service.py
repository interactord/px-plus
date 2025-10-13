"""
WebEnhancementService

웹 강화 도메인 서비스
비즈니스 로직 및 폴백 전략 관리
"""

import time
import logging
from typing import List

logger = logging.getLogger(__name__)

try:
    from rfs.core.result import Result, Success, Failure
except ImportError:
    from dataclasses import dataclass
    from typing import Generic, TypeVar, Union
    T, E = TypeVar("T"), TypeVar("E")

    @dataclass
    class Success(Generic[T]):
        value: T
        def is_success(self) -> bool: return True
        def unwrap(self) -> T: return self.value

    @dataclass
    class Failure(Generic[E]):
        error: E
        def is_success(self) -> bool: return False
        def unwrap_error(self) -> E: return self.error

    Result = Union[Success[T], Failure[E]]

from ..entities.enhanced_term import EnhancedTerm
from ..value_objects.term_info import TermInfo
from ..value_objects.language_code import LanguageCode
from ..ports.web_enhancement_port import WebEnhancementPort


class WebEnhancementService:
    """
    웹 강화 도메인 서비스
    
    주요 책임:
    1. 4단계 폴백 전략 관리
    2. 폴백 전략 실행:
       - Primary: GPT-4o + 웹검색
       - Fallback 1: Gemini + 웹검색
       - Fallback 2: Gemini Flash (일반 번역)
       - Fallback 3: GPT-4o-mini (일반 번역)
    3. 결과 검증 및 품질 보장
    
    Attributes:
        primary_adapter: GPT-4o + 웹검색
        fallback_adapter: Gemini + 웹검색
        simple_translation_adapter: Gemini Flash (일반 번역)
        final_fallback_adapter: GPT-4o-mini (일반 번역)
        fallback_delay: 폴백 시 대기 시간 (초)
    """
    
    def __init__(
        self,
        primary_adapter: WebEnhancementPort,
        fallback_adapter: WebEnhancementPort,
        simple_translation_adapter: WebEnhancementPort = None,
        final_fallback_adapter: WebEnhancementPort = None,
        fallback_delay: float = 2.0
    ):
        """
        웹 강화 서비스 초기화
        
        Args:
            primary_adapter: 우선 어댑터 (GPT-4o + 웹검색)
            fallback_adapter: 폴백 어댑터 (Gemini + 웹검색)
            simple_translation_adapter: 일반 번역 어댑터 (Gemini Flash, 웹검색 없음)
            final_fallback_adapter: 최종 폴백 어댑터 (GPT-4o-mini, 웹검색 없음)
            fallback_delay: 폴백 시 대기 시간 (초, 기본: 2.0)
        """
        self._primary_adapter = primary_adapter
        self._fallback_adapter = fallback_adapter
        self._simple_translation_adapter = simple_translation_adapter
        self._final_fallback_adapter = final_fallback_adapter
        self._fallback_delay = fallback_delay
    
    def enhance_terms(
        self,
        term_infos: List[TermInfo],
        target_languages: List[str] = None
    ) -> Result[List[EnhancedTerm], str]:
        """
        용어 목록 웹 강화 (폴백 전략 포함)
        
        실행 순서:
        1. Primary 어댑터 시도 (GPT-4o)
        2. 실패 시 Fallback 어댑터 시도 (Gemini)
        3. 결과 검증
        
        Args:
            term_infos: 강화할 용어 정보 리스트
            target_languages: 번역 대상 언어 (None이면 10개 모두)
        
        Returns:
            Result[List[EnhancedTerm], str]: 성공 시 강화된 용어 리스트, 실패 시 에러 메시지
        """
        # 입력 검증
        if not term_infos:
            return Failure("용어 정보가 비어있습니다")
        
        # 언어 코드 검증
        if target_languages is None:
            # 기본: 10개 언어 모두
            target_languages = [
                "ko", "zh-CN", "zh-TW", "en", "ja",
                "fr", "ru", "it", "vi", "ar", "es"
            ]
        else:
            # 유효성 검증
            for lang in target_languages:
                if not LanguageCode.is_valid(lang):
                    return Failure(
                        f"유효하지 않은 언어 코드: {lang}. "
                        f"지원 언어: {', '.join(sorted(LanguageCode.SUPPORTED_LANGUAGES))}"
                    )
        
        # Primary 어댑터 시도
        result = self._primary_adapter.enhance_terms(term_infos, target_languages)
        
        if result.is_success():
            # 성공: 결과 검증
            enhanced_terms = result.unwrap()
            validation_result = self._validate_results(enhanced_terms, target_languages)
            
            if validation_result.is_success():
                return result
            else:
                # 검증 실패: Fallback 시도
                return self._try_fallback(
                    term_infos,
                    target_languages,
                    f"Primary 결과 검증 실패: {validation_result.unwrap_error()}"
                )
        else:
            # Primary 실패: Fallback 시도
            return self._try_fallback(
                term_infos,
                target_languages,
                f"Primary 어댑터 실패: {result.unwrap_error()}"
            )
    
    def _try_fallback(
        self,
        term_infos: List[TermInfo],
        target_languages: List[str],
        primary_error: str
    ) -> Result[List[EnhancedTerm], str]:
        """
        4단계 폴백 시도
        
        1. Gemini + 웹검색
        2. Gemini Flash (일반 번역)
        3. GPT-4o-mini (일반 번역)
        
        Args:
            term_infos: 강화할 용어 정보
            target_languages: 번역 대상 언어
            primary_error: Primary 실패 이유
        
        Returns:
            Result[List[EnhancedTerm], str]: 성공 시 강화된 용어, 실패 시 에러
        """
        errors = [f"Primary: {primary_error}"]
        
        # Fallback 1: Gemini + 웹검색
        logger.info(f"🔄 Fallback 1 시도: Gemini + 웹검색 ({len(term_infos)}개 용어)")
        if self._fallback_delay > 0:
            time.sleep(self._fallback_delay)
        
        fallback_result = self._fallback_adapter.enhance_terms(term_infos, target_languages)
        
        if fallback_result.is_success():
            enhanced_terms = fallback_result.unwrap()
            validation_result = self._validate_results(enhanced_terms, target_languages)
            
            if validation_result.is_success():
                logger.info(f"✅ Fallback 1 성공: Gemini + 웹검색")
                return fallback_result
            else:
                error_msg = f"Fallback 1 (Gemini+웹): 검증 실패 - {validation_result.unwrap_error()}"
                logger.warning(f"⚠️ {error_msg}")
                errors.append(error_msg)
        else:
            error_msg = f"Fallback 1 (Gemini+웹): {fallback_result.unwrap_error()}"
            logger.error(f"❌ {error_msg}")
            errors.append(error_msg)
        
        # Fallback 2: Gemini Flash (일반 번역) - 캐시 저장 안 함
        if self._simple_translation_adapter:
            logger.info(f"🔄 Fallback 2 시도: Gemini Flash 일반 번역 ({len(term_infos)}개 용어)")
            if self._fallback_delay > 0:
                time.sleep(self._fallback_delay)
            
            simple_result = self._simple_translation_adapter.enhance_terms(term_infos, target_languages)
            
            if simple_result.is_success():
                # 일반 번역은 검증 완화 (웹 출처 없어도 OK)
                logger.info(f"✅ Fallback 2 성공: Gemini Flash 일반 번역")
                return simple_result
            else:
                error_msg = f"Fallback 2 (Gemini 일반): {simple_result.unwrap_error()}"
                logger.error(f"❌ {error_msg}")
                errors.append(error_msg)
        
        # Fallback 3: GPT-4o-mini (일반 번역) - 캐시 저장 안 함
        if self._final_fallback_adapter:
            logger.info(f"🔄 Fallback 3 시도: GPT-4o-mini 일반 번역 ({len(term_infos)}개 용어)")
            if self._fallback_delay > 0:
                time.sleep(self._fallback_delay)
            
            final_result = self._final_fallback_adapter.enhance_terms(term_infos, target_languages)
            
            if final_result.is_success():
                # 일반 번역은 검증 완화
                logger.info(f"✅ Fallback 3 성공: GPT-4o-mini 일반 번역")
                return final_result
            else:
                error_msg = f"Fallback 3 (GPT-4o-mini 일반): {final_result.unwrap_error()}"
                logger.error(f"❌ {error_msg}")
                errors.append(error_msg)
        
        final_error = "모든 폴백 실패. " + " | ".join(errors)
        logger.error(f"💥 {final_error}")
        return Failure(final_error)
    
    def _validate_results(
        self,
        enhanced_terms: List[EnhancedTerm],
        target_languages: List[str]
    ) -> Result[None, str]:
        """
        강화 결과 검증
        
        검증 항목:
        1. 결과 개수 일치
        2. 필수 번역 존재
        3. 신뢰도 임계값
        
        Args:
            enhanced_terms: 강화된 용어 리스트
            target_languages: 요청한 언어 코드
        
        Returns:
            Result[None, str]: 성공 시 None, 실패 시 에러 메시지
        """
        if not enhanced_terms:
            return Failure("강화된 용어가 없습니다")
        
        # 각 용어 검증
        for term in enhanced_terms:
            # 번역 검증
            missing_languages = []
            for lang in target_languages:
                if not term.has_translation(lang):
                    missing_languages.append(lang)
            
            if missing_languages:
                return Failure(
                    f"용어 '{term.original_term}'에 누락된 번역: "
                    f"{', '.join(missing_languages)}"
                )
            
            # 신뢰도 검증 (최소 0.5)
            if term.confidence_score < 0.5:
                return Failure(
                    f"용어 '{term.original_term}'의 신뢰도가 낮습니다: "
                    f"{term.confidence_score:.2f}"
                )
            
            # 웹 출처 검증 (최소 1개)
            if not term.web_sources:
                return Failure(
                    f"용어 '{term.original_term}'에 웹 출처가 없습니다"
                )
        
        return Success(None)
    
    def get_primary_source(self) -> str:
        """Primary 어댑터 소스 이름"""
        return self._primary_adapter.get_source_name()
    
    def get_fallback_source(self) -> str:
        """Fallback 어댑터 소스 이름"""
        return self._fallback_adapter.get_source_name()
