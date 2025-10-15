"""
마크다운 생성 API 라우터

JSON 용어 데이터를 마크다운 테이블로 변환하는 API를 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated

from src.application.markdown.dto.markdown_request_dto import MarkdownGenerationRequest
from src.application.markdown.dto.markdown_response_dto import MarkdownGenerationResponse
from src.application.markdown.services.markdown_generation_service import MarkdownGenerationService
from src.infrastructure.web.dependencies import get_markdown_service

# 라우터 생성
router = APIRouter(
    prefix="/api/v1/markdown",
    tags=["markdown"]
)


@router.post(
    "/generate",
    response_model=MarkdownGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="마크다운 테이블 생성",
    description="""
    JSON 용어 데이터를 마크다운 테이블 형식으로 변환합니다.

    **입력 데이터 구조:**
    - terms_data: enhanced_terms 배열을 포함하는 JSON 객체
    - selected_languages: 선택된 언어 코드 배열 (1-11개)

    **마크다운 테이블 형식:**
    - 컬럼: term | term_type | tags | [선택된 언어별 번역]
    - 타이트한 스페이싱으로 컴팩트하게 생성
    - tags는 공백으로 구분된 문자열 (#tag1 #tag2)

    **지원 언어 코드:**
    - ko, en, zh-CN, zh-TW, ja, fr, ru, it, vi, ar, es
    """,
    responses={
        200: {
            "description": "마크다운 테이블 생성 성공",
            "content": {
                "application/json": {
                    "example": {
                        "markdown_table": "| term | term_type | tags | ko | en |\n|------|----------|------|----|----|",
                        "term_count": 50,
                        "column_count": 5
                    }
                }
            }
        },
        400: {
            "description": "잘못된 입력 데이터",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "terms_data에 enhanced_terms 배열이 없습니다"
                    }
                }
            }
        },
        422: {
            "description": "유효성 검증 실패",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "선택된 언어가 최대 11개를 초과했습니다"
                    }
                }
            }
        }
    }
)
async def generate_markdown_table(
    request: MarkdownGenerationRequest,
    service: Annotated[MarkdownGenerationService, Depends(get_markdown_service)]
) -> MarkdownGenerationResponse:
    """
    JSON 용어 데이터를 마크다운 테이블로 변환합니다.

    Args:
        request: 마크다운 생성 요청 DTO
        service: 마크다운 생성 서비스 (DI)

    Returns:
        MarkdownGenerationResponse: 생성된 마크다운 테이블 및 메타데이터

    Raises:
        HTTPException: 입력 데이터 검증 실패 또는 서버 오류
    """
    try:
        # 서비스 호출하여 마크다운 생성
        response = await service.generate_markdown_table(request)
        return response

    except ValueError as e:
        # 입력 데이터 검증 실패
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # 예상치 못한 오류
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"마크다운 생성 중 오류 발생: {str(e)}"
        )
