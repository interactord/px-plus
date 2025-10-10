"""
API Routes

FastAPI 라우터를 정의합니다.
Result 패턴을 사용하는 유즈케이스를 HTTP 엔드포인트로 노출합니다.
"""

import time
from datetime import datetime
from typing import List, Tuple

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from ...application.dto import (
    DocumentExtractionSummaryResponse,
    ErrorResponse,
    HealthResponse,
    ProcessedDocumentResponse,
    SkippedDocumentResponse,
)
from ...shared.logging import get_logger
from .dependencies import ExtractDocumentChunksUseCaseDep
from .validators import get_file_validator

# 로거 초기화
logger = get_logger(__name__)

# API 라우터 생성
router = APIRouter()


@router.get(
    "/",
    response_model=HealthResponse,
    summary="헬스 체크 (루트)",
    description="서비스 상태를 확인합니다",
)
async def root() -> HealthResponse:
    """
    루트 엔드포인트 - 헬스 체크
    
    Returns:
        HealthResponse: 서비스 상태 정보
    """
    return HealthResponse(
        status="healthy",
        service="px-plus",
        version="0.1.0",
        timestamp=datetime.now().isoformat(),
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="헬스 체크",
    description="서비스 상태를 확인합니다",
)
async def health_check() -> HealthResponse:
    """
    헬스 체크 엔드포인트

    Returns:
        HealthResponse: 서비스 상태 정보
    """
    return HealthResponse(
        status="healthy",
        service="px-plus",
        version="0.1.0",
        timestamp=datetime.now().isoformat(),
    )


@router.post(
    "/v1/document-extractor",
    response_model=DocumentExtractionSummaryResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"description": "파일 크기 또는 개수 초과"},
    },
    summary="문서 텍스트 추출 및 청크 분할",
    description="""
    지원되는 문서에서 텍스트를 추출하고 약 2000자 단위로 청크를 생성합니다.
    
    **제한 사항**:
    - 단일 파일 최대 크기: 10MB (환경변수 MAX_FILE_SIZE)
    - 전체 파일 총합 최대 크기: 20MB (환경변수 MAX_TOTAL_FILE_SIZE)
    - 최대 파일 개수: 10개 (환경변수 MAX_FILES)
    - 허용 파일 형식: .txt, .md, .pdf, .docx, .xlsx, .csv, .json, .pptx, .ppt
    """,
)
async def extract_document_chunks(
    use_case: ExtractDocumentChunksUseCaseDep,
    files: List[UploadFile] = File(
        ...,
        description="처리할 파일 목록 (단일 파일 최대 10MB, 전체 최대 20MB, 최대 10개)",
    ),
) -> DocumentExtractionSummaryResponse:
    """
    문서 텍스트 추출 엔드포인트
    
    파일 크기 및 개수를 검증한 후 텍스트를 추출하고 청크로 분할합니다.
    """
    start_time = time.time()
    
    logger.log_operation(
        "api_request",
        "started",
        endpoint="/v1/document-extractor",
        file_count=len(files),
    )
    
    # 파일 검증 및 읽기 (크기, 개수, 확장자 검증 포함)
    validator = get_file_validator()
    documents = await validator.validate_files(files)
    
    # 검증 통과한 파일들 로깅
    for filename, file_bytes in documents:
        logger.debug(
            "파일 검증 통과",
            filename=filename,
            size_bytes=len(file_bytes),
        )

    # 유즈케이스 실행
    result = use_case.execute(documents)
    
    if not result.is_success():
        logger.error("문서 처리 실패",
                   endpoint="/v1/document-extractor",
                   error=result.unwrap_error())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=result.unwrap_error()
        )

    # 응답 생성
    summary = result.unwrap()
    processed_responses = [
        ProcessedDocumentResponse(
            filename=doc.filename,
            total_characters=doc.total_characters,
            total_chunks=len(doc.chunks),
            chunks=doc.chunks,
        )
        for doc in summary.processed
    ]
    skipped_responses = [
        SkippedDocumentResponse(filename=item.filename, reason=item.reason)
        for item in summary.skipped
    ]

    duration_ms = (time.time() - start_time) * 1000
    logger.log_performance("api_request",
                         duration_ms=duration_ms,
                         endpoint="/v1/document-extractor",
                         processed_count=len(processed_responses),
                         skipped_count=len(skipped_responses))
    
    logger.log_operation("api_request", "completed",
                       endpoint="/v1/document-extractor",
                       processed_count=len(processed_responses))

    return DocumentExtractionSummaryResponse(
        processed=processed_responses,
        skipped=skipped_responses,
    )
