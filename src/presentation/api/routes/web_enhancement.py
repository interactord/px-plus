"""
웹 강화 API 라우터

POST /api/v1/web-enhancement/enhance
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
import os

from ....application.web_enhancement.dto.enhancement_request_dto import EnhancementRequestDTO
from ....application.web_enhancement.dto.enhancement_response_dto import EnhancementResponseDTO
from ....application.web_enhancement.services.batch_enhancement_service import BatchEnhancementService
from ....application.web_enhancement.services.cached_enhancement_service import CachedEnhancementService
from ....infrastructure.web_enhancement.factories.enhancement_service_factory import EnhancementServiceFactory


# Pydantic 모델 정의
class TermInput(BaseModel):
    """용어 입력 모델"""
    term: str = Field(..., description="용어", example="Partido Popular")
    type: str = Field(..., description="용어 타입", example="company")
    primary_domain: str = Field(..., description="주요 도메인", example="politics")
    context: str = Field(default="", description="맥락", example="Major Spanish political party")
    tags: List[str] = Field(default_factory=list, description="태그", example=["#PP", "#Spain"])


class EnhanceRequest(BaseModel):
    """웹 강화 요청 모델"""
    terms: List[TermInput] = Field(..., description="강화할 용어 목록")
    target_languages: Optional[List[str]] = Field(
        default=None,
        description="번역 대상 언어 (None이면 10개 모두)",
        example=["ko", "en", "ja"]
    )
    use_cache: bool = Field(default=True, description="캐시 사용 여부")
    batch_size: int = Field(default=5, ge=1, le=10, description="배치 크기")
    concurrent_batches: int = Field(default=3, ge=1, le=5, description="동시 배치 수")


class EnhanceResponse(BaseModel):
    """웹 강화 응답 모델"""
    enhanced_terms: List[dict]
    summary: dict
    errors: Optional[List[str]] = None


# 라우터 생성
router = APIRouter(
    prefix="/api/v1/web-enhancement",
    tags=["web-enhancement"]
)


# 의존성 주입 함수
def get_cached_enhancement_service() -> CachedEnhancementService:
    """
    CachedEnhancementService 의존성 주입
    
    환경 변수:
    - OPENAI_API_KEY: OpenAI API 키 (필수)
    - GOOGLE_API_KEY: Google API 키 (필수)
    - REDIS_URL: Redis 연결 URL (기본: redis://localhost:6379)
    - CACHE_TTL: 캐시 TTL 초 (기본: 86400)
    
    Returns:
        CachedEnhancementService: 캐시 강화 서비스
    """
    # 1. 웹 강화 도메인 서비스 생성
    service_result = EnhancementServiceFactory.create_service()
    
    if not service_result.is_success():
        raise HTTPException(
            status_code=500,
            detail=f"서비스 생성 실패: {service_result.unwrap_error()}"
        )
    
    web_enhancement_service = service_result.unwrap()
    
    # 2. 배치 서비스 생성
    batch_service = BatchEnhancementService(web_enhancement_service)
    
    # 3. 캐시 서비스 생성
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    cache_ttl = int(os.getenv("CACHE_TTL", "86400"))
    
    cached_service = CachedEnhancementService(
        batch_service=batch_service,
        redis_url=redis_url,
        ttl=cache_ttl
    )
    
    return cached_service


@router.post(
    "/enhance",
    response_model=EnhanceResponse,
    summary="웹 강화 API",
    description="""
    추출된 고유명사를 웹 검색 기반으로 강화합니다.
    
    - 웹 검색으로 공식 번역 확인
    - 10개 언어 동시 번역 (Single-shot)
    - 배치 처리 + Redis 캐싱
    - GPT-4o 우선, Gemini 자동 폴백
    
    지원 언어 (10개):
    - ko (한국어), zh-CN (중국어 간체), zh-TW (중국어 번체)
    - en (English), ja (日本語), fr (Français)
    - ru (Русский), it (Italiano), vi (Tiếng Việt)
    - ar (العربية), es (Español)
    
    처리 방식:
    - 배치 크기: 5개 용어 (Single-shot 최적)
    - 동시 배치: 3개 (라운드 로빈)
    - 캐시 TTL: 24시간
    """
)
async def enhance_terms(
    request: EnhanceRequest,
    service: CachedEnhancementService = Depends(get_cached_enhancement_service)
):
    """
    용어 웹 강화 API
    
    Args:
        request: 웹 강화 요청
        service: 캐시 강화 서비스 (의존성 주입)
    
    Returns:
        EnhanceResponse: 강화된 용어 및 요약
    
    Raises:
        HTTPException: 처리 실패 시
    """
    try:
        # 1. DTO 생성
        request_dto_result = EnhancementRequestDTO.create(
            terms=[term.model_dump() for term in request.terms],
            target_languages=request.target_languages,
            use_cache=request.use_cache,
            batch_size=request.batch_size,
            concurrent_batches=request.concurrent_batches
        )
        
        if not request_dto_result.is_success():
            raise HTTPException(
                status_code=400,
                detail=f"요청 검증 실패: {request_dto_result.unwrap_error()}"
            )
        
        request_dto = request_dto_result.unwrap()
        
        # 2. TermInfo 변환
        term_infos_result = request_dto.to_term_infos()
        
        if not term_infos_result.is_success():
            raise HTTPException(
                status_code=400,
                detail=f"용어 변환 실패: {term_infos_result.unwrap_error()}"
            )
        
        term_infos = term_infos_result.unwrap()
        
        # 3. 웹 강화 실행 (캐싱 + 배치)
        enhanced_terms, cache_hits, fallback_count, processing_time = await service.enhance_terms_with_cache(
            term_infos=term_infos,
            target_languages=request_dto.get_target_languages(),
            batch_size=request_dto.batch_size,
            concurrent_batches=request_dto.concurrent_batches,
            use_cache=request_dto.use_cache
        )
        
        # 4. 응답 DTO 생성
        total_batches = request_dto.get_total_batches()
        
        response_dto = EnhancementResponseDTO.create(
            enhanced_terms=enhanced_terms,
            total_terms=len(term_infos),
            cache_hits=cache_hits,
            total_batches=total_batches,
            fallback_count=fallback_count,
            processing_time=processing_time
        )
        
        # 5. JSON 응답 반환
        return response_dto.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"내부 서버 오류: {str(e)}"
        )


@router.get(
    "/cache/stats",
    summary="캐시 통계",
    description="Redis 캐시 통계 조회"
)
async def get_cache_stats(
    service: CachedEnhancementService = Depends(get_cached_enhancement_service)
):
    """
    캐시 통계 조회
    
    Args:
        service: 캐시 강화 서비스 (의존성 주입)
    
    Returns:
        dict: 캐시 통계
    """
    stats_result = service.get_cache_stats()
    
    if not stats_result.is_success():
        raise HTTPException(
            status_code=500,
            detail=f"통계 조회 실패: {stats_result.unwrap_error()}"
        )
    
    return stats_result.unwrap()


@router.delete(
    "/cache/clear",
    summary="캐시 삭제",
    description="웹 강화 캐시 전체 삭제"
)
async def clear_cache(
    service: CachedEnhancementService = Depends(get_cached_enhancement_service)
):
    """
    캐시 삭제
    
    Args:
        service: 캐시 강화 서비스 (의존성 주입)
    
    Returns:
        dict: 삭제 결과
    """
    clear_result = service.clear_cache()
    
    if not clear_result.is_success():
        raise HTTPException(
            status_code=500,
            detail=f"캐시 삭제 실패: {clear_result.unwrap_error()}"
        )
    
    deleted_count = clear_result.unwrap()
    
    return {
        "message": "캐시가 삭제되었습니다",
        "deleted_keys": deleted_count
    }


@router.get(
    "/health",
    summary="헬스 체크",
    description="API 및 Redis 연결 상태 확인"
)
async def health_check(
    service: CachedEnhancementService = Depends(get_cached_enhancement_service)
):
    """
    헬스 체크
    
    Args:
        service: 캐시 강화 서비스 (의존성 주입)
    
    Returns:
        dict: 헬스 체크 결과
    """
    # Redis 연결 확인
    redis_result = service.check_connection()
    
    return {
        "status": "healthy" if redis_result.is_success() else "degraded",
        "api": "ok",
        "redis": "connected" if redis_result.is_success() else "disconnected",
        "redis_error": None if redis_result.is_success() else redis_result.unwrap_error()
    }
