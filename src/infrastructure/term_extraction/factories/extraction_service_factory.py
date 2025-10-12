"""
용어 추출 서비스 팩토리 모듈

의존성을 조립하여 서비스 인스턴스를 생성합니다.
"""

from typing import Optional

# Application Layer
from ....application.term_extraction.services.term_extraction_service import (
    TermExtractionService
)
from ....application.term_extraction.services.cached_extraction_service import (
    CachedTermExtractionService
)

# Infrastructure Layer
from ..adapters.openai_term_extractor import OpenAITermExtractor
from ..adapters.memory_cache_adapter import MemoryCacheAdapter

# AI Model Ports (기존 시스템)
from ....domain.ai_model.ports.model_port import ModelPort
from ....domain.ai_model.ports.template_port import TemplatePort


class ExtractionServiceFactory:
    """
    용어 추출 서비스 팩토리
    
    의존성을 주입하여 완전히 구성된 서비스를 생성합니다.
    """
    
    def __init__(
        self,
        model_port: ModelPort,
        template_port: TemplatePort
    ):
        """
        팩토리 초기화
        
        Args:
            model_port: AI 모델 실행 포트
            template_port: 템플릿 렌더링 포트
        """
        self._model_port = model_port
        self._template_port = template_port
        
        # 싱글톤 캐시 인스턴스
        self._cache_adapter: Optional[MemoryCacheAdapter] = None
    
    def create_basic_service(self, max_workers: int = 3) -> TermExtractionService:
        """
        캐시 없는 기본 서비스를 생성합니다.
        
        Args:
            max_workers: 병렬 처리 워커 수 (기본값: 3)
            
        Returns:
            TermExtractionService: 구성된 서비스 인스턴스
        """
        # Extractor 생성
        extractor = OpenAITermExtractor(
            model_port=self._model_port,
            template_port=self._template_port
        )
        
        # 서비스 생성
        service = TermExtractionService(
            extractor=extractor,
            max_workers=max_workers
        )
        
        return service
    
    def create_cached_service(
        self,
        max_workers: int = 3,
        use_shared_cache: bool = True
    ) -> CachedTermExtractionService:
        """
        캐시를 지원하는 서비스를 생성합니다.
        
        Args:
            max_workers: 병렬 처리 워커 수 (기본값: 3)
            use_shared_cache: 공유 캐시 사용 여부 (기본값: True)
                              True면 싱글톤 캐시, False면 새 캐시 인스턴스
            
        Returns:
            CachedTermExtractionService: 구성된 서비스 인스턴스
        """
        # Extractor 생성
        extractor = OpenAITermExtractor(
            model_port=self._model_port,
            template_port=self._template_port
        )
        
        # Cache 생성
        if use_shared_cache:
            # 싱글톤 캐시 사용
            if self._cache_adapter is None:
                self._cache_adapter = MemoryCacheAdapter()
            cache = self._cache_adapter
        else:
            # 새 캐시 인스턴스 생성
            cache = MemoryCacheAdapter()
        
        # 서비스 생성
        service = CachedTermExtractionService(
            extractor=extractor,
            cache=cache,
            max_workers=max_workers
        )
        
        return service
    
    def get_cache_stats(self) -> dict:
        """
        캐시 통계를 반환합니다.
        
        Returns:
            dict: 캐시 통계 정보 (싱글톤 캐시가 없으면 빈 딕셔너리)
        """
        if self._cache_adapter is None:
            return {
                "cache_enabled": False,
                "message": "캐시가 아직 초기화되지 않았습니다"
            }
        
        return {
            "cache_enabled": True,
            "cached_items": self._cache_adapter.size()
        }
