"""
Data Transfer Objects (DTO)

API 요청/응답을 위한 Pydantic 모델을 정의합니다.
입력 검증은 Pydantic이 처리하고, 비즈니스 로직 검증은 도메인 레이어가 처리합니다.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """
    에러 응답 DTO
    
    Result 패턴의 Failure를 HTTP 응답으로 변환할 때 사용
    """
    error: str = Field(..., description="에러 메시지")
    code: str = Field(default="BUSINESS_ERROR", description="에러 코드")
    details: Optional[dict] = Field(None, description="추가 에러 상세 정보")


class HealthResponse(BaseModel):
    """
    헬스 체크 응답 DTO

    서비스 상태를 확인하는 엔드포인트의 응답
    """

    status: str = Field(..., description="서비스 상태")
    service: str = Field(..., description="서비스 이름")
    version: str = Field(..., description="서비스 버전")
    timestamp: str = Field(..., description="응답 시각")


class ProcessedDocumentResponse(BaseModel):
    """
    처리된 문서 응답 DTO
    """

    filename: str = Field(..., description="처리된 파일 이름")
    total_characters: int = Field(..., description="문서에 포함된 총 문자 수")
    total_chunks: int = Field(..., description="생성된 청크 수")
    chunks: List[str] = Field(..., description="문서에서 추출된 텍스트 청크 목록")


class SkippedDocumentResponse(BaseModel):
    """
    처리에서 제외된 문서 응답 DTO
    """

    filename: str = Field(..., description="제외된 파일 이름")
    reason: str = Field(..., description="제외 사유")


class DocumentExtractionSummaryResponse(BaseModel):
    """
    문서 추출 API 응답 DTO
    """

    processed: List[ProcessedDocumentResponse] = Field(
        ..., description="처리된 문서 목록"
    )
    skipped: List[SkippedDocumentResponse] = Field(
        ..., description="처리에서 제외된 문서 목록"
    )
