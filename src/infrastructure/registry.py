"""
Dependency Injection Registry

RFS Framework의 Registry 패턴을 사용한 의존성 주입 설정
"""

from typing import Any, Dict

# RFS Framework Registry (폴백 포함)
try:
    from rfs.core.registry import Registry, ServiceScope
except ImportError:
    # 간단한 Registry 구현
    from enum import Enum

    class ServiceScope(Enum):
        """서비스 스코프"""

        SINGLETON = "singleton"
        PROTOTYPE = "prototype"

    class Registry:
        """간단한 의존성 주입 레지스트리"""

        def __init__(self) -> None:
            self._services: Dict[str, Any] = {}
            self._factories: Dict[str, Any] = {}

        def register(
            self, name: str, factory: Any, scope: ServiceScope = ServiceScope.SINGLETON
        ) -> None:
            """서비스 등록"""
            if scope == ServiceScope.SINGLETON:
                self._services[name] = factory()
            else:
                self._factories[name] = factory

        def resolve(self, name: str) -> Any:
            """서비스 조회"""
            if name in self._services:
                return self._services[name]
            if name in self._factories:
                return self._factories[name]()
            raise KeyError(f"Service not found: {name}")

from ..application.use_cases import ExtractDocumentChunksUseCase
from ..domain.services import (
    DocumentChunkingService,
    FileTextExtractionService,
)


def create_registry() -> Registry:
    """
    애플리케이션 의존성 레지스트리 생성
    
    Returns:
        Registry: 설정된 의존성 레지스트리
        
    Service Registration:
        - file_text_extraction_service: 싱글톤 FileTextExtractionService
        - document_chunking_service: 싱글톤 DocumentChunkingService
        - extract_document_chunks_use_case: 프로토타입 ExtractDocumentChunksUseCase
    """
    registry = Registry()

    # 도메인 서비스 등록 (싱글톤)
    registry.register(
        "file_text_extraction_service",
        lambda: FileTextExtractionService(),
        scope=ServiceScope.SINGLETON,
    )
    registry.register(
        "document_chunking_service",
        lambda: DocumentChunkingService(),
        scope=ServiceScope.SINGLETON,
    )

    # 유즈케이스 등록 (프로토타입 - 요청마다 새 인스턴스)
    registry.register(
        "extract_document_chunks_use_case",
        lambda: ExtractDocumentChunksUseCase(
            registry.resolve("file_text_extraction_service"),
            registry.resolve("document_chunking_service"),
        ),
        scope=ServiceScope.PROTOTYPE,
    )

    return registry


# 글로벌 레지스트리 인스턴스
_registry: Registry | None = None


def get_registry() -> Registry:
    """
    글로벌 레지스트리 인스턴스 반환

    Returns:
        Registry: 애플리케이션 레지스트리
    """
    global _registry
    if _registry is None:
        _registry = create_registry()
    return _registry
