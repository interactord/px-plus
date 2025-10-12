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
    """
    html_content = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>데모 페이지 - PX-Plus</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #F3F4F6;
            color: #1F2937;
            line-height: 1.6;
            padding: 2rem;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        
        header {
            background: white;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
            margin-bottom: 2rem;
            text-align: center;
        }
        
        h1 {
            font-size: 2rem;
            margin-bottom: 0.5rem;
            color: #3B82F6;
        }
        
        .subtitle {
            color: #6B7280;
        }
        
        .demo-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
        }
        
        .demo-card {
            background: white;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .demo-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        
        .demo-card h2 {
            font-size: 1.5rem;
            margin-bottom: 1rem;
            color: #1F2937;
        }
        
        .demo-card p {
            color: #6B7280;
            margin-bottom: 1.5rem;
        }
        
        .demo-link {
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background: #3B82F6;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            transition: background 0.2s;
        }
        
        .demo-link:hover {
            background: #2563EB;
        }
        
        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            background: #DBEAFE;
            color: #1E40AF;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-top: 0.5rem;
        }
        
        footer {
            text-align: center;
            margin-top: 3rem;
            color: #6B7280;
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 PX-Plus 데모 페이지</h1>
            <p class="subtitle">FastAPI + RFS Framework + GPT-4o</p>
        </header>
        
        <div class="demo-grid">
            <div class="demo-card">
                <h2>🔍 용어 추출</h2>
                <p>
                    GPT-4o를 사용하여 텍스트에서 고유명사와 주요 도메인을 자동으로 추출합니다.
                    인물, 기업, 제품, 기술 용어 등을 식별합니다.
                </p>
                <a href="/demo/term-extraction" class="demo-link">데모 실행 →</a>
                <div>
                    <span class="badge">GPT-4o</span>
                    <span class="badge">캐싱</span>
                    <span class="badge">병렬 처리</span>
                </div>
            </div>
            
            <div class="demo-card">
                <h2>📄 문서 텍스트 추출</h2>
                <p>
                    다양한 형식의 문서에서 텍스트를 추출하고 청크 단위로 분할합니다.
                    PDF, DOCX, XLSX 등을 지원합니다.
                </p>
                <a href="/static/demo-upload.html" class="demo-link">데모 실행 →</a>
                <div>
                    <span class="badge">파일 업로드</span>
                    <span class="badge">청크 분할</span>
                </div>
            </div>
        </div>
        
        <footer>
            <p>&copy; 2024 PX-Plus - Hyper-Personalization AI Platform</p>
        </footer>
    </div>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content, status_code=200)
