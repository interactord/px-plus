"""
용어 추출 API 라우터

청크 텍스트로부터 용어를 추출하는 RESTful API 엔드포인트를 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated

# RFS Framework - Result 패턴
try:
    from rfs.core.result import Result, Success, Failure
except ImportError:
    from dataclasses import dataclass
    from typing import Generic, TypeVar, Union
    
    T = TypeVar('T')
    E = TypeVar('E')
    
    @dataclass(frozen=True)
    class Success(Generic[T]):
        value: T
        def is_success(self) -> bool: return True
        def is_failure(self) -> bool: return False
    
    @dataclass(frozen=True)
    class Failure(Generic[E]):
        error: E
        def is_success(self) -> bool: return False
        def is_failure(self) -> bool: return True
    
    Result = Union[Success[T], Failure[E]]

# Application Layer
from ....application.term_extraction.dto.extraction_request_dto import ExtractionRequestDTO
from ....application.term_extraction.dto.extraction_response_dto import ExtractionResponseDTO
from ....application.term_extraction.services.cached_extraction_service import (
    CachedTermExtractionService
)

# Infrastructure Layer
from ....infrastructure.term_extraction.factories.extraction_service_factory import (
    ExtractionServiceFactory
)

# 기존 AI Model 시스템 (Domain Layer에 위치)
from ....domain.ai_model.ports.model_port import ModelPort
from ....domain.ai_model.ports.template_port import TemplatePort


# 라우터 생성
router = APIRouter(
    prefix="/api/v1/extract-terms",
    tags=["term-extraction"]
)


# 의존성 주입 함수들
async def get_model_port() -> ModelPort:
    """
    AI 모델 포트를 반환합니다.
    
    환경 변수에서 OPENAI_API_KEY를 읽어 OpenAIChatAdapter를 생성합니다.
    
    Returns:
        ModelPort: OpenAI Chat 어댑터 인스턴스
        
    Raises:
        HTTPException: API 키가 설정되지 않은 경우
    """
    import os
    from fastapi import HTTPException, status
    from ....infrastructure.ai_model.adapters.openai_chat_adapter import OpenAIChatAdapter
    
    # 환경 변수에서 API 키 읽기
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key or api_key == "your-openai-api-key-here":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPENAI_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요."
        )
    
    # OpenAI Chat 어댑터 생성
    return OpenAIChatAdapter(
        api_key=api_key,
        model_name="gpt-4o",
        base_url="https://api.openai.com/v1",
        timeout=60
    )


async def get_template_port() -> TemplatePort:
    """
    템플릿 포트를 반환합니다.
    
    프로젝트의 템플릿 디렉토리를 사용하여 Jinja2TemplateAdapter를 생성합니다.
    
    Returns:
        TemplatePort: Jinja2 템플릿 어댑터 인스턴스
        
    Raises:
        HTTPException: 템플릿 디렉토리를 찾을 수 없는 경우
    """
    from pathlib import Path
    from fastapi import HTTPException, status
    from ....infrastructure.ai_model.adapters.jinja2_template_adapter import Jinja2TemplateAdapter
    
    # 템플릿 디렉토리 경로 설정
    # src/presentation/api/routes → src/infrastructure/term_extraction/templates
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    template_dir = project_root / "infrastructure" / "term_extraction" / "templates"
    
    if not template_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"템플릿 디렉토리를 찾을 수 없습니다: {template_dir}"
        )
    
    # Jinja2 템플릿 어댑터 생성
    return Jinja2TemplateAdapter(template_dir=str(template_dir))


async def get_extraction_service(
    model_port: Annotated[ModelPort, Depends(get_model_port)],
    template_port: Annotated[TemplatePort, Depends(get_template_port)]
) -> CachedTermExtractionService:
    """
    용어 추출 서비스를 생성합니다.
    
    Args:
        model_port: AI 모델 포트
        template_port: 템플릿 포트
        
    Returns:
        CachedTermExtractionService: 구성된 서비스 인스턴스
    """
    factory = ExtractionServiceFactory(
        model_port=model_port,
        template_port=template_port
    )
    
    # 캐시 지원 서비스 생성 (싱글톤 캐시 사용)
    service = factory.create_cached_service(
        max_workers=3,
        use_shared_cache=True
    )
    
    return service


# API 엔드포인트
@router.post(
    "/process-documents",
    response_model=ExtractionResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="문서에서 용어 추출",
    description="""
    청크로 분할된 문서들로부터 고유명사와 주요 도메인을 추출합니다.
    
    **주요 기능:**
    - GPT-4o를 사용한 고정밀 용어 추출
    - LLM 응답 캐싱으로 빠른 재추출
    - 3-워커 병렬 처리로 높은 처리량
    - 엔티티 타입 필터링 지원
    - 청크당 최대 엔티티 수 제한
    
    **처리 흐름:**
    1. 청크별 캐시 확인
    2. 캐시 미스 청크만 LLM 추출
    3. 병렬 처리로 빠른 응답
    4. 결과 통계 포함하여 반환
    """,
    responses={
        200: {
            "description": "용어 추출 성공",
            "content": {
                "application/json": {
                    "example": {
                        "results": [
                            {
                                "chunk_index": 0,
                                "source_filename": "document.txt",
                                "entities": [
                                    {
                                        "term": "#홍길동",
                                        "type": "person",
                                        "primary_domain": "#역사",
                                        "tags": ["#조선시대"],
                                        "context": "홍길동은 조선시대의 의적이다."
                                    }
                                ],
                                "cached": False,
                                "processing_time": 1.234,
                                "error": None
                            }
                        ],
                        "summary": {
                            "total_chunks": 10,
                            "processed_chunks": 10,
                            "failed_chunks": 0,
                            "cache_hits": 3,
                            "cache_hit_rate": 0.3,
                            "total_entities": 45,
                            "total_processing_time": 12.345,
                            "average_processing_time": 1.235
                        }
                    }
                }
            }
        },
        400: {
            "description": "잘못된 요청 (유효성 검증 실패)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "청크 배열은 비어있을 수 없습니다"
                    }
                }
            }
        },
        500: {
            "description": "서버 내부 오류",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "용어 추출 중 오류가 발생했습니다"
                    }
                }
            }
        }
    }
)
async def process_documents(
    request: ExtractionRequestDTO,
    service: Annotated[CachedTermExtractionService, Depends(get_extraction_service)]
) -> ExtractionResponseDTO:
    """
    문서들로부터 용어를 추출합니다.
    
    Args:
        request: 추출 요청 데이터
        service: 용어 추출 서비스 (의존성 주입)
        
    Returns:
        ExtractionResponseDTO: 추출 결과
        
    Raises:
        HTTPException: 처리 실패 시
    """
    # 서비스 실행
    result = await service.extract_from_documents(request)
    
    # Result 패턴 처리
    if result.is_failure():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"용어 추출 실패: {result.error}"
        )
    
    return result.value


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="헬스 체크",
    description="용어 추출 API의 상태를 확인합니다."
)
async def health_check() -> dict:
    """
    API 헬스 체크 엔드포인트
    
    Returns:
        dict: 상태 정보
    """
    return {
        "status": "healthy",
        "service": "term-extraction",
        "version": "1.0.0"
    }


@router.get(
    "/cache-stats",
    status_code=status.HTTP_200_OK,
    summary="캐시 통계",
    description="현재 캐시의 통계 정보를 반환합니다."
)
async def get_cache_statistics(
    model_port: Annotated[ModelPort, Depends(get_model_port)],
    template_port: Annotated[TemplatePort, Depends(get_template_port)]
) -> dict:
    """
    캐시 통계를 반환합니다.
    
    Args:
        model_port: AI 모델 포트
        template_port: 템플릿 포트
        
    Returns:
        dict: 캐시 통계 정보
    """
    factory = ExtractionServiceFactory(
        model_port=model_port,
        template_port=template_port
    )
    
    stats = factory.get_cache_stats()
    
    return stats
