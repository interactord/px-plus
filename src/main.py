"""
FastAPI + RFS Framework 메인 애플리케이션

헥사고날 아키텍처 기반의 FastAPI 애플리케이션
Result 패턴을 활용한 안전한 에러 처리
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .infrastructure.web.routes import router
from .shared.logging import setup_logging, get_logger, LogLevel

# 로깅 시스템 초기화
log_level_str = os.getenv("LOG_LEVEL", "INFO")
log_level = LogLevel(log_level_str)
enable_json = os.getenv("ENVIRONMENT", "development") == "production"

setup_logging(level=log_level, enable_json=enable_json)
logger = get_logger(__name__)

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="PX-Plus: FastAPI + RFS Framework",
    description="""
    ## 아키텍처

    **헥사고날 아키텍처** (Ports & Adapters)를 기반으로 구현된 FastAPI 애플리케이션입니다.

    ### 레이어 구조
    - **Domain Layer**: 비즈니스 로직 (Result 패턴 사용)
    - **Application Layer**: 유즈케이스 및 DTO
    - **Infrastructure Layer**: FastAPI, 외부 어댑터

    ### 핵심 패턴
    - **Result Pattern**: 예외 대신 Result<T, E> 사용
    - **Dependency Injection**: RFS Registry 기반 DI
    - **Immutability**: 불변 엔티티 및 데이터 구조
    - **Functional Programming**: 순수 함수 및 HOF 활용

    ## 기능

    - 문서 텍스트 추출 (PDF, PPTX, DOCX, XLSX)
    - 문서 청킹 (SpaCy 기반 문장 분할)
    - 헬스 체크
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(router, tags=["greetings"])

# 데모 페이지 라우팅
@app.get("/demo/document-extractor", tags=["demo"])
async def serve_demo_page():
    """
    문서 텍스트 추출 데모 페이지

    파일 업로드 및 텍스트 추출 기능을 테스트할 수 있는 웹 데모 페이지를 제공합니다.
    """
    static_dir = Path(__file__).parent.parent / "static"
    demo_file = static_dir / "demo-upload.html"

    if not demo_file.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Demo page not found")

    return FileResponse(demo_file)


# 애플리케이션 시작 이벤트
@app.on_event("startup")
async def startup_event() -> None:
    """
    애플리케이션 시작 시 실행되는 이벤트 핸들러

    레지스트리 초기화 및 리소스 준비
    """
    from .infrastructure.registry import get_registry

    logger.info("애플리케이션 시작 중", 
                app_title=app.title, 
                app_version=app.version,
                environment=os.getenv("ENVIRONMENT", "development"))

    # 레지스트리 초기화 (싱글톤 서비스 생성)
    registry = get_registry()
    
    logger.info("의존성 레지스트리 초기화 완료")
    logger.info("애플리케이션 시작 완료", 
                app_title=app.title, 
                app_version=app.version)


# 애플리케이션 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    애플리케이션 종료 시 실행되는 이벤트 핸들러

    리소스 정리 및 연결 종료
    """
    logger.info("애플리케이션 종료 중")


# 개발 서버 실행 (직접 실행 시)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 개발 모드: 코드 변경 시 자동 재시작
        log_level="info",
    )
