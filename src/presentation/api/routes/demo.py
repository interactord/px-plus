"""
데모 페이지 라우터

데모 페이지를 서빙하는 FastAPI 엔드포인트를 제공합니다.
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse

# 라우터 생성
router = APIRouter(
    prefix="/demo",
    tags=["demo"]
)


@router.get(
    "/term-extraction",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    summary="용어 추출 데모 페이지",
    description="""
    용어 추출 API를 테스트할 수 있는 인터랙티브 데모 페이지를 제공합니다.
    
    **주요 기능:**
    - 텍스트 입력 및 샘플 데이터 제공
    - GPT-4o 기반 용어 추출 실시간 테스트
    - JSON 응답 표시 및 통계 확인
    - 캐시 및 병렬 처리 옵션 설정
    
    **사용 방법:**
    1. 브라우저에서 /demo/term-extraction 접속
    2. 샘플 텍스트 선택 또는 직접 입력
    3. "용어 추출 시작" 버튼 클릭
    4. JSON 응답 및 통계 확인
    """,
    responses={
        200: {
            "description": "데모 페이지 HTML 반환",
            "content": {
                "text/html": {
                    "example": "<!DOCTYPE html>..."
                }
            }
        },
        404: {
            "description": "데모 페이지 파일을 찾을 수 없음",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "데모 페이지 파일을 찾을 수 없습니다"
                    }
                }
            }
        }
    }
)
async def term_extraction_demo() -> HTMLResponse:
    """
    용어 추출 데모 페이지를 반환합니다.
    
    Returns:
        HTMLResponse: HTML 페이지 콘텐츠
        
    Raises:
        HTTPException: 파일을 찾을 수 없는 경우
    """
    # HTML 파일 경로
    html_file = Path("static/term-extraction-demo.html")
    
    # 파일 존재 확인
    if not html_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"데모 페이지 파일을 찾을 수 없습니다: {html_file}"
        )
    
    # HTML 파일 읽기
    try:
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데모 페이지 로드 실패: {str(e)}"
        )
    
    return HTMLResponse(content=html_content, status_code=200)


@router.get(
    "/",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    summary="데모 페이지 목록",
    description="사용 가능한 데모 페이지 목록을 표시합니다."
)
async def demo_index() -> HTMLResponse:
    """
    데모 페이지 목록을 반환합니다.

    Returns:
        HTMLResponse: 데모 페이지 목록 HTML

    Raises:
        HTTPException: 파일을 찾을 수 없는 경우
    """
    # HTML 파일 경로
    html_file = Path("static/demo-index.html")

    # 파일 존재 확인
    if not html_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"데모 인덱스 페이지 파일을 찾을 수 없습니다: {html_file}"
        )

    # HTML 파일 읽기
    try:
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데모 인덱스 페이지 로드 실패: {str(e)}"
        )

    return HTMLResponse(content=html_content, status_code=200)
