# 마크다운 테이블 생성 데모 페이지 설계 명세서

## 📋 개요

### 목적
용어 추출 및 웹 강화 결과를 마크다운 테이블 형식으로 변환하여 표시하는 데모 페이지 설계

### 주요 기능
1. JSON 데이터 입력 (textarea 또는 파일 업로드)
2. 다국어 번역 컬럼 선택 (11개 언어 중 최대 11개 선택)
3. 서버 API를 통한 마크다운 테이블 생성
4. 생성된 마크다운 표시 및 다운로드

### 기술 스택
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Backend**: FastAPI, Python 3.11+
- **Data Format**: JSON (입력), Markdown (출력)

---

## 🏗️ 시스템 아키텍처

### 컴포넌트 구조

```
┌─────────────────────────────────────────────────┐
│              Frontend (HTML/JS)                 │
│  ┌──────────────────────────────────────────┐   │
│  │  Input Section                           │   │
│  │  - JSON textarea / File upload           │   │
│  │  - Sample data load button               │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  Language Options Section                │   │
│  │  - 11 language checkboxes (3 columns)    │   │
│  │  - All/None selection buttons            │   │
│  │  - Default: ko + en selected             │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  Output Section                          │   │
│  │  - Markdown table textarea (read-only)   │   │
│  │  - Copy to clipboard button              │   │
│  │  - Download .md file button              │   │
│  │  - Statistics (term count, column count) │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
                      ↓ POST /api/v1/markdown/generate
┌─────────────────────────────────────────────────┐
│       Backend API (FastAPI)                     │
│  ┌──────────────────────────────────────────┐   │
│  │  Presentation Layer                      │   │
│  │  - MarkdownRouter                        │   │
│  │  - Request validation                    │   │
│  │  - Response serialization                │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  Application Layer                       │   │
│  │  - MarkdownGenerationService             │   │
│  │  - DTO: Request/Response                 │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  Domain Layer                            │   │
│  │  - MarkdownTableFormatter                │   │
│  │  - Language validation logic             │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### 데이터 플로우

```
1. User Input
   ↓
2. Frontend validates JSON + selected languages
   ↓
3. POST /api/v1/markdown/generate
   {
     "terms_data": { enhanced_terms: [...] },
     "selected_languages": ["ko", "en", ...]
   }
   ↓
4. Backend processes request
   - Parse JSON
   - Validate languages
   - Generate markdown table
   ↓
5. Return response
   {
     "markdown_table": "| term | ... |",
     "term_count": 50,
     "column_count": 5
   }
   ↓
6. Frontend displays markdown in textarea
```

---

## 🎨 프론트엔드 설계

### 페이지 레이아웃

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <title>마크다운 테이블 생성 데모</title>
</head>
<body>
    <!-- Header Section -->
    <header>
        <h1>📊 마크다운 테이블 생성 데모</h1>
        <p>용어 추출 결과를 마크다운 테이블로 변환합니다</p>
    </header>

    <!-- Input Section -->
    <section id="input-section">
        <h2>1. JSON 데이터 입력</h2>
        <textarea id="json-input" rows="10"></textarea>
        <div class="buttons">
            <button id="load-sample">샘플 데이터 로드</button>
            <button id="upload-file">파일 업로드</button>
        </div>
    </section>

    <!-- Language Options Section -->
    <section id="language-options">
        <h2>2. 번역 언어 선택 (최대 11개)</h2>
        <div class="selection-buttons">
            <button id="select-all">전체 선택</button>
            <button id="select-none">선택 해제</button>
        </div>
        <div class="language-grid">
            <!-- 3 columns x 4 rows -->
            <label><input type="checkbox" value="ko" checked> 한국어 (ko)</label>
            <label><input type="checkbox" value="en" checked> English (en)</label>
            <label><input type="checkbox" value="zh-CN"> 简体中文 (zh-CN)</label>
            <label><input type="checkbox" value="zh-TW"> 繁體中文 (zh-TW)</label>
            <label><input type="checkbox" value="ja"> 日本語 (ja)</label>
            <label><input type="checkbox" value="fr"> Français (fr)</label>
            <label><input type="checkbox" value="ru"> Русский (ru)</label>
            <label><input type="checkbox" value="it"> Italiano (it)</label>
            <label><input type="checkbox" value="vi"> Tiếng Việt (vi)</label>
            <label><input type="checkbox" value="ar"> العربية (ar)</label>
            <label><input type="checkbox" value="es"> Español (es)</label>
        </div>
    </section>

    <!-- Submit Section -->
    <section id="submit-section">
        <button id="generate-btn" class="primary-btn">
            🚀 마크다운 테이블 생성
        </button>
    </section>

    <!-- Output Section -->
    <section id="output-section">
        <h2>3. 생성된 마크다운 테이블</h2>
        <textarea id="markdown-output" rows="20" readonly></textarea>
        <div class="output-buttons">
            <button id="copy-btn">📋 클립보드에 복사</button>
            <button id="download-btn">💾 .md 파일 다운로드</button>
        </div>
        <div class="statistics">
            <span>용어 개수: <strong id="term-count">0</strong></span>
            <span>컬럼 개수: <strong id="column-count">0</strong></span>
        </div>
    </section>
</body>
</html>
```

### CSS 스타일 가이드

```css
/* 주요 스타일 컴포넌트 */
:root {
    --primary-color: #4A90E2;
    --success-color: #28A745;
    --bg-light: #F8F9FA;
    --border-color: #DEE2E6;
    --text-dark: #212529;
}

/* 레이아웃 */
body {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

section {
    margin-bottom: 30px;
    padding: 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* 입력 필드 */
textarea {
    width: 100%;
    padding: 12px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 14px;
    resize: vertical;
}

/* 언어 선택 그리드 */
.language-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-top: 15px;
}

.language-grid label {
    padding: 8px 12px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
}

.language-grid label:hover {
    background: var(--bg-light);
    border-color: var(--primary-color);
}

/* 버튼 */
button {
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.2s;
}

.primary-btn {
    background: var(--primary-color);
    color: white;
    font-size: 16px;
    padding: 12px 30px;
}

.primary-btn:hover {
    background: #357ABD;
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}
```

### JavaScript 로직

```javascript
// 주요 이벤트 핸들러
document.addEventListener('DOMContentLoaded', () => {
    // 샘플 데이터 로드
    document.getElementById('load-sample').addEventListener('click', loadSampleData);

    // 전체 선택/해제
    document.getElementById('select-all').addEventListener('click', selectAllLanguages);
    document.getElementById('select-none').addEventListener('click', deselectAllLanguages);

    // 마크다운 생성
    document.getElementById('generate-btn').addEventListener('click', generateMarkdown);

    // 클립보드 복사
    document.getElementById('copy-btn').addEventListener('click', copyToClipboard);

    // 파일 다운로드
    document.getElementById('download-btn').addEventListener('click', downloadMarkdown);
});

// 마크다운 생성 API 호출
async function generateMarkdown() {
    try {
        // 입력 데이터 가져오기
        const jsonInput = document.getElementById('json-input').value;
        const termsData = JSON.parse(jsonInput);

        // 선택된 언어 가져오기
        const selectedLanguages = Array.from(
            document.querySelectorAll('.language-grid input:checked')
        ).map(cb => cb.value);

        // 유효성 검증
        if (selectedLanguages.length === 0) {
            alert('최소 1개 이상의 언어를 선택해주세요');
            return;
        }

        if (selectedLanguages.length > 11) {
            alert('최대 11개까지 선택 가능합니다');
            return;
        }

        // API 요청
        const response = await fetch('/api/v1/markdown/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                terms_data: termsData,
                selected_languages: selectedLanguages
            })
        });

        if (!response.ok) {
            throw new Error(`API 오류: ${response.status}`);
        }

        // 응답 처리
        const result = await response.json();

        // 마크다운 표시
        document.getElementById('markdown-output').value = result.markdown_table;

        // 통계 업데이트
        document.getElementById('term-count').textContent = result.term_count;
        document.getElementById('column-count').textContent = result.column_count;

        // 성공 메시지
        alert('✅ 마크다운 테이블 생성 완료!');

    } catch (error) {
        console.error('마크다운 생성 실패:', error);
        alert(`❌ 오류 발생: ${error.message}`);
    }
}

// 클립보드 복사
async function copyToClipboard() {
    const markdown = document.getElementById('markdown-output').value;
    if (!markdown) {
        alert('생성된 마크다운이 없습니다');
        return;
    }

    try {
        await navigator.clipboard.writeText(markdown);
        alert('✅ 클립보드에 복사되었습니다');
    } catch (error) {
        alert('❌ 복사 실패: ' + error.message);
    }
}

// 파일 다운로드
function downloadMarkdown() {
    const markdown = document.getElementById('markdown-output').value;
    if (!markdown) {
        alert('생성된 마크다운이 없습니다');
        return;
    }

    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `terms-table-${new Date().toISOString().slice(0,10)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
```

---

## 🔧 백엔드 API 설계

### 1. API 엔드포인트

#### POST /api/v1/markdown/generate

**설명**: JSON 용어 데이터를 마크다운 테이블로 변환

**Request Body**:
```json
{
    "terms_data": {
        "enhanced_terms": [
            {
                "original_term": "Naciones Unidas",
                "term_type": "company",
                "primary_domain": "international relations",
                "context": "International organization",
                "tags": ["#ONU", "#global", "#politics"],
                "translations": {
                    "ko": "유엔",
                    "en": "United Nations",
                    "zh-CN": "联合国",
                    "zh-TW": "聯合國",
                    "ja": "国際連合",
                    "fr": "Nations Unies",
                    "ru": "Организация Объединённых Наций",
                    "it": "Nazioni Unite",
                    "vi": "Liên Hợp Quốc",
                    "ar": "الأمم المتحدة",
                    "es": "Naciones Unidas"
                },
                "web_sources": ["https://www.un.org/"],
                "source": "gpt4o_web",
                "confidence_score": 0.98,
                "search_timestamp": "2025-10-13T13:21:05.504783"
            }
        ]
    },
    "selected_languages": ["ko", "en", "ja"]
}
```

**Response**:
```json
{
    "markdown_table": "| term | term_type | tags | ko | en | ja |\n|------|----------|------|----|----|----|\n| Naciones Unidas | company | #ONU #global #politics | 유엔 | United Nations | 国際連合 |",
    "term_count": 1,
    "column_count": 6
}
```

**Status Codes**:
- `200 OK`: 성공적으로 마크다운 생성
- `400 Bad Request`: 잘못된 입력 데이터
- `422 Unprocessable Entity`: 유효성 검증 실패
- `500 Internal Server Error`: 서버 오류

### 2. 라우터 구현

**파일**: `src/presentation/api/routes/markdown.py`

```python
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
```

### 3. DTO 클래스

#### MarkdownGenerationRequest

**파일**: `src/application/markdown/dto/markdown_request_dto.py`

```python
"""
마크다운 생성 요청 DTO

API 요청 데이터를 검증하고 변환합니다.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Any


class MarkdownGenerationRequest(BaseModel):
    """
    마크다운 테이블 생성 요청 DTO

    Attributes:
        terms_data: enhanced_terms 배열을 포함하는 JSON 데이터
        selected_languages: 선택된 언어 코드 리스트 (1-11개)
    """

    terms_data: Dict[str, Any] = Field(
        ...,
        description="용어 데이터 JSON (enhanced_terms 배열 포함)",
        example={
            "enhanced_terms": [
                {
                    "original_term": "Naciones Unidas",
                    "term_type": "company",
                    "tags": ["#ONU", "#global"],
                    "translations": {
                        "ko": "유엔",
                        "en": "United Nations"
                    }
                }
            ]
        }
    )

    selected_languages: List[str] = Field(
        ...,
        min_length=1,
        max_length=11,
        description="선택된 언어 코드 리스트",
        example=["ko", "en", "ja"]
    )

    @field_validator("terms_data")
    @classmethod
    def validate_terms_data(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """
        terms_data 유효성 검증

        Args:
            v: terms_data 딕셔너리

        Returns:
            검증된 terms_data

        Raises:
            ValueError: enhanced_terms 배열이 없거나 비어있는 경우
        """
        if "enhanced_terms" not in v:
            raise ValueError("terms_data에 enhanced_terms 배열이 없습니다")

        if not isinstance(v["enhanced_terms"], list):
            raise ValueError("enhanced_terms는 배열이어야 합니다")

        if len(v["enhanced_terms"]) == 0:
            raise ValueError("enhanced_terms 배열이 비어있습니다")

        return v

    @field_validator("selected_languages")
    @classmethod
    def validate_languages(cls, v: List[str]) -> List[str]:
        """
        선택된 언어 코드 유효성 검증

        Args:
            v: 언어 코드 리스트

        Returns:
            검증된 언어 코드 리스트

        Raises:
            ValueError: 유효하지 않은 언어 코드 포함 시
        """
        VALID_LANGUAGES = {
            "ko", "en", "zh-CN", "zh-TW", "ja",
            "fr", "ru", "it", "vi", "ar", "es"
        }

        # 중복 제거
        unique_languages = list(dict.fromkeys(v))

        # 유효성 검증
        invalid = set(unique_languages) - VALID_LANGUAGES
        if invalid:
            raise ValueError(
                f"유효하지 않은 언어 코드: {', '.join(invalid)}"
            )

        return unique_languages

    class Config:
        json_schema_extra = {
            "example": {
                "terms_data": {
                    "enhanced_terms": [
                        {
                            "original_term": "Naciones Unidas",
                            "term_type": "company",
                            "tags": ["#ONU", "#global", "#politics"],
                            "translations": {
                                "ko": "유엔",
                                "en": "United Nations",
                                "ja": "国際連合"
                            }
                        }
                    ]
                },
                "selected_languages": ["ko", "en", "ja"]
            }
        }
```

#### MarkdownGenerationResponse

**파일**: `src/application/markdown/dto/markdown_response_dto.py`

```python
"""
마크다운 생성 응답 DTO

API 응답 데이터 구조를 정의합니다.
"""

from pydantic import BaseModel, Field


class MarkdownGenerationResponse(BaseModel):
    """
    마크다운 테이블 생성 응답 DTO

    Attributes:
        markdown_table: 생성된 마크다운 테이블 문자열
        term_count: 용어 개수
        column_count: 컬럼 개수 (term, term_type, tags + 선택된 언어 수)
    """

    markdown_table: str = Field(
        ...,
        description="생성된 마크다운 테이블 문자열",
        example="| term | term_type | tags | ko | en |\n|------|----------|------|----|----|"
    )

    term_count: int = Field(
        ...,
        ge=0,
        description="용어 개수",
        example=50
    )

    column_count: int = Field(
        ...,
        ge=4,  # 최소: term, term_type, tags + 1개 언어
        le=14,  # 최대: term, term_type, tags + 11개 언어
        description="컬럼 개수",
        example=5
    )

    class Config:
        json_schema_extra = {
            "example": {
                "markdown_table": "| term | term_type | tags | ko | en |\n|------|----------|------|----|----|----|\n| Naciones Unidas | company | #ONU #global | 유엔 | United Nations |",
                "term_count": 1,
                "column_count": 5
            }
        }
```

### 4. 서비스 레이어

#### MarkdownGenerationService

**파일**: `src/application/markdown/services/markdown_generation_service.py`

```python
"""
마크다운 생성 서비스

비즈니스 로직을 처리하고 도메인 레이어와 통신합니다.
"""

from typing import List, Dict, Any

from src.application.markdown.dto.markdown_request_dto import MarkdownGenerationRequest
from src.application.markdown.dto.markdown_response_dto import MarkdownGenerationResponse
from src.domain.markdown.services.markdown_table_formatter import MarkdownTableFormatter


class MarkdownGenerationService:
    """
    마크다운 생성 서비스

    용어 데이터를 마크다운 테이블로 변환하는 비즈니스 로직을 처리합니다.
    """

    def __init__(self, formatter: MarkdownTableFormatter):
        """
        서비스 초기화

        Args:
            formatter: 마크다운 테이블 포매터 (도메인 서비스)
        """
        self._formatter = formatter

    async def generate_markdown_table(
        self,
        request: MarkdownGenerationRequest
    ) -> MarkdownGenerationResponse:
        """
        JSON 용어 데이터를 마크다운 테이블로 변환합니다.

        Args:
            request: 마크다운 생성 요청 DTO

        Returns:
            MarkdownGenerationResponse: 생성된 마크다운 및 메타데이터

        Raises:
            ValueError: 데이터 검증 실패
        """
        # enhanced_terms 배열 추출
        enhanced_terms = request.terms_data.get("enhanced_terms", [])

        # 용어 데이터 검증
        self._validate_terms(enhanced_terms, request.selected_languages)

        # 마크다운 테이블 생성
        markdown_table = self._formatter.format_table(
            terms=enhanced_terms,
            languages=request.selected_languages
        )

        # 응답 생성
        return MarkdownGenerationResponse(
            markdown_table=markdown_table,
            term_count=len(enhanced_terms),
            column_count=3 + len(request.selected_languages)  # term + term_type + tags + languages
        )

    def _validate_terms(
        self,
        terms: List[Dict[str, Any]],
        languages: List[str]
    ) -> None:
        """
        용어 데이터 유효성 검증

        Args:
            terms: 용어 데이터 리스트
            languages: 선택된 언어 코드 리스트

        Raises:
            ValueError: 필수 필드 누락 또는 번역 데이터 부족
        """
        for idx, term in enumerate(terms):
            # 필수 필드 확인
            required_fields = ["original_term", "term_type", "tags", "translations"]
            missing = [f for f in required_fields if f not in term]

            if missing:
                raise ValueError(
                    f"용어 {idx}에 필수 필드 누락: {', '.join(missing)}"
                )

            # 번역 데이터 확인
            translations = term.get("translations", {})
            missing_langs = [lang for lang in languages if lang not in translations]

            if missing_langs:
                raise ValueError(
                    f"용어 '{term['original_term']}'에 번역 누락: {', '.join(missing_langs)}"
                )
```

### 5. 도메인 서비스

#### MarkdownTableFormatter

**파일**: `src/domain/markdown/services/markdown_table_formatter.py`

```python
"""
마크다운 테이블 포매터

마크다운 테이블 생성 및 포맷팅 로직을 담당합니다.
"""

from typing import List, Dict, Any


class MarkdownTableFormatter:
    """
    마크다운 테이블 포매터

    용어 데이터를 컴팩트한 마크다운 테이블로 변환합니다.
    """

    def format_table(
        self,
        terms: List[Dict[str, Any]],
        languages: List[str]
    ) -> str:
        """
        용어 데이터를 마크다운 테이블로 포맷팅합니다.

        Args:
            terms: 용어 데이터 리스트
            languages: 선택된 언어 코드 리스트

        Returns:
            포맷팅된 마크다운 테이블 문자열
        """
        # 테이블 헤더 생성
        header = self._format_header(languages)

        # 구분선 생성
        separator = self._format_separator(len(languages))

        # 데이터 행 생성
        rows = [
            self._format_row(term, languages)
            for term in terms
        ]

        # 테이블 조립 (타이트한 스페이싱)
        table_lines = [header, separator] + rows
        return "\n".join(table_lines)

    def _format_header(self, languages: List[str]) -> str:
        """
        테이블 헤더 생성

        Args:
            languages: 언어 코드 리스트

        Returns:
            헤더 문자열 (예: "| term | term_type | tags | ko | en |")
        """
        # 기본 컬럼: term, term_type, tags
        columns = ["term", "term_type", "tags"] + languages

        # 컴팩트 포맷: 공백 최소화
        return "|" + "|".join(columns) + "|"

    def _format_separator(self, language_count: int) -> str:
        """
        테이블 구분선 생성

        Args:
            language_count: 언어 개수

        Returns:
            구분선 문자열 (예: "|------|----------|------|----|----|")
        """
        # 기본 컬럼 구분선
        base_separators = ["------", "----------", "------"]  # term, term_type, tags

        # 언어 컬럼 구분선
        lang_separators = ["-----"] * language_count

        # 조립
        return "|" + "|".join(base_separators + lang_separators) + "|"

    def _format_row(
        self,
        term: Dict[str, Any],
        languages: List[str]
    ) -> str:
        """
        데이터 행 포맷팅

        Args:
            term: 용어 데이터
            languages: 언어 코드 리스트

        Returns:
            데이터 행 문자열
        """
        # 기본 필드
        original_term = term.get("original_term", "")
        term_type = term.get("term_type", "")

        # Tags 포맷팅 (배열 → 공백 구분 문자열)
        tags = self._format_tags(term.get("tags", []))

        # 번역 데이터
        translations = term.get("translations", {})
        translated_values = [
            translations.get(lang, "")
            for lang in languages
        ]

        # 행 조립
        cells = [original_term, term_type, tags] + translated_values

        # 이스케이프 처리 (파이프 문자)
        escaped_cells = [
            cell.replace("|", "\\|") if isinstance(cell, str) else str(cell)
            for cell in cells
        ]

        return "|" + "|".join(escaped_cells) + "|"

    def _format_tags(self, tags: List[str]) -> str:
        """
        태그 배열을 공백 구분 문자열로 변환

        Args:
            tags: 태그 배열 (예: ["#tag1", "#tag2"])

        Returns:
            공백 구분 문자열 (예: "#tag1 #tag2")
        """
        if not tags:
            return ""

        return " ".join(tags)
```

---

## 📂 파일 구조

```
px-plus/
├── src/
│   ├── presentation/
│   │   └── api/
│   │       └── routes/
│   │           ├── demo.py (기존)
│   │           └── markdown.py (신규 - API 라우터)
│   ├── application/
│   │   └── markdown/ (신규)
│   │       ├── __init__.py
│   │       ├── dto/
│   │       │   ├── __init__.py
│   │       │   ├── markdown_request_dto.py
│   │       │   └── markdown_response_dto.py
│   │       └── services/
│   │           ├── __init__.py
│   │           └── markdown_generation_service.py
│   ├── domain/
│   │   └── markdown/ (신규)
│   │       ├── __init__.py
│   │       └── services/
│   │           ├── __init__.py
│   │           └── markdown_table_formatter.py
│   └── infrastructure/
│       └── web/
│           └── dependencies.py (get_markdown_service 추가)
└── static/
    └── markdown-table-demo.html (신규 - 프론트엔드)
```

---

## 🔗 의존성 주입

**파일**: `src/infrastructure/web/dependencies.py`에 추가

```python
"""
FastAPI 의존성 주입 설정
"""

from functools import lru_cache
from src.application.markdown.services.markdown_generation_service import MarkdownGenerationService
from src.domain.markdown.services.markdown_table_formatter import MarkdownTableFormatter


@lru_cache()
def get_markdown_table_formatter() -> MarkdownTableFormatter:
    """
    마크다운 테이블 포매터 싱글톤 인스턴스 반환

    Returns:
        MarkdownTableFormatter: 포매터 인스턴스
    """
    return MarkdownTableFormatter()


@lru_cache()
def get_markdown_service() -> MarkdownGenerationService:
    """
    마크다운 생성 서비스 싱글톤 인스턴스 반환

    Returns:
        MarkdownGenerationService: 서비스 인스턴스
    """
    formatter = get_markdown_table_formatter()
    return MarkdownGenerationService(formatter=formatter)
```

---

## 🧪 테스트 시나리오

### 단위 테스트

#### 1. MarkdownTableFormatter 테스트

```python
"""
마크다운 테이블 포매터 단위 테스트
"""

import pytest
from src.domain.markdown.services.markdown_table_formatter import MarkdownTableFormatter


class TestMarkdownTableFormatter:
    """
    MarkdownTableFormatter 단위 테스트
    """

    @pytest.fixture
    def formatter(self):
        """포매터 인스턴스"""
        return MarkdownTableFormatter()

    @pytest.fixture
    def sample_terms(self):
        """샘플 용어 데이터"""
        return [
            {
                "original_term": "United Nations",
                "term_type": "company",
                "tags": ["#UN", "#global"],
                "translations": {
                    "ko": "유엔",
                    "en": "United Nations",
                    "ja": "国際連合"
                }
            },
            {
                "original_term": "NATO",
                "term_type": "company",
                "tags": ["#NATO", "#defense"],
                "translations": {
                    "ko": "북대서양 조약 기구",
                    "en": "NATO",
                    "ja": "北大西洋条約機構"
                }
            }
        ]

    def test_format_header(self, formatter):
        """헤더 포맷팅 테스트"""
        languages = ["ko", "en", "ja"]
        header = formatter._format_header(languages)

        assert header == "|term|term_type|tags|ko|en|ja|"

    def test_format_separator(self, formatter):
        """구분선 포맷팅 테스트"""
        separator = formatter._format_separator(3)

        assert separator == "|------|----------|------|-----|-----|-----|"

    def test_format_tags(self, formatter):
        """태그 포맷팅 테스트"""
        tags = ["#tag1", "#tag2", "#tag3"]
        formatted = formatter._format_tags(tags)

        assert formatted == "#tag1 #tag2 #tag3"

    def test_format_row(self, formatter):
        """행 포맷팅 테스트"""
        term = {
            "original_term": "Test Term",
            "term_type": "person",
            "tags": ["#test"],
            "translations": {
                "ko": "테스트 용어",
                "en": "Test Term"
            }
        }
        languages = ["ko", "en"]

        row = formatter._format_row(term, languages)

        assert row == "|Test Term|person|#test|테스트 용어|Test Term|"

    def test_format_table(self, formatter, sample_terms):
        """전체 테이블 포맷팅 테스트"""
        languages = ["ko", "en"]
        table = formatter.format_table(sample_terms, languages)

        lines = table.split("\n")

        # 라인 수 확인 (헤더 + 구분선 + 데이터 2개)
        assert len(lines) == 4

        # 헤더 확인
        assert lines[0] == "|term|term_type|tags|ko|en|"

        # 구분선 확인
        assert lines[1] == "|------|----------|------|-----|-----|"
```

#### 2. MarkdownGenerationService 테스트

```python
"""
마크다운 생성 서비스 단위 테스트
"""

import pytest
from src.application.markdown.services.markdown_generation_service import MarkdownGenerationService
from src.application.markdown.dto.markdown_request_dto import MarkdownGenerationRequest
from src.domain.markdown.services.markdown_table_formatter import MarkdownTableFormatter


class TestMarkdownGenerationService:
    """
    MarkdownGenerationService 단위 테스트
    """

    @pytest.fixture
    def service(self):
        """서비스 인스턴스"""
        formatter = MarkdownTableFormatter()
        return MarkdownGenerationService(formatter=formatter)

    @pytest.fixture
    def valid_request(self):
        """유효한 요청 데이터"""
        return MarkdownGenerationRequest(
            terms_data={
                "enhanced_terms": [
                    {
                        "original_term": "Test",
                        "term_type": "person",
                        "tags": ["#test"],
                        "translations": {
                            "ko": "테스트",
                            "en": "Test"
                        }
                    }
                ]
            },
            selected_languages=["ko", "en"]
        )

    @pytest.mark.asyncio
    async def test_generate_markdown_table_success(self, service, valid_request):
        """마크다운 생성 성공 테스트"""
        response = await service.generate_markdown_table(valid_request)

        assert response.term_count == 1
        assert response.column_count == 5  # term + term_type + tags + ko + en
        assert "|Test|person|#test|테스트|Test|" in response.markdown_table

    @pytest.mark.asyncio
    async def test_validate_terms_missing_field(self, service):
        """필수 필드 누락 검증 테스트"""
        request = MarkdownGenerationRequest(
            terms_data={
                "enhanced_terms": [
                    {
                        "original_term": "Test"
                        # term_type, tags, translations 누락
                    }
                ]
            },
            selected_languages=["ko"]
        )

        with pytest.raises(ValueError, match="필수 필드 누락"):
            await service.generate_markdown_table(request)

    @pytest.mark.asyncio
    async def test_validate_terms_missing_translation(self, service):
        """번역 누락 검증 테스트"""
        request = MarkdownGenerationRequest(
            terms_data={
                "enhanced_terms": [
                    {
                        "original_term": "Test",
                        "term_type": "person",
                        "tags": ["#test"],
                        "translations": {
                            "ko": "테스트"
                            # en 번역 누락
                        }
                    }
                ]
            },
            selected_languages=["ko", "en"]
        )

        with pytest.raises(ValueError, match="번역 누락"):
            await service.generate_markdown_table(request)
```

### 통합 테스트

#### API 엔드포인트 테스트

```python
"""
마크다운 생성 API 통합 테스트
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app


class TestMarkdownAPI:
    """
    마크다운 생성 API 통합 테스트
    """

    @pytest.fixture
    def client(self):
        """테스트 클라이언트"""
        return TestClient(app)

    @pytest.fixture
    def valid_payload(self):
        """유효한 요청 페이로드"""
        return {
            "terms_data": {
                "enhanced_terms": [
                    {
                        "original_term": "United Nations",
                        "term_type": "company",
                        "tags": ["#UN", "#global"],
                        "translations": {
                            "ko": "유엔",
                            "en": "United Nations",
                            "ja": "国際連合"
                        }
                    }
                ]
            },
            "selected_languages": ["ko", "en", "ja"]
        }

    def test_generate_markdown_success(self, client, valid_payload):
        """마크다운 생성 API 성공 테스트"""
        response = client.post("/api/v1/markdown/generate", json=valid_payload)

        assert response.status_code == 200

        data = response.json()
        assert "markdown_table" in data
        assert data["term_count"] == 1
        assert data["column_count"] == 6  # term + term_type + tags + 3 languages

    def test_generate_markdown_invalid_language(self, client, valid_payload):
        """잘못된 언어 코드 테스트"""
        valid_payload["selected_languages"] = ["invalid"]

        response = client.post("/api/v1/markdown/generate", json=valid_payload)

        assert response.status_code == 422
        assert "유효하지 않은 언어 코드" in response.json()["detail"]

    def test_generate_markdown_missing_terms(self, client):
        """용어 데이터 누락 테스트"""
        payload = {
            "terms_data": {},  # enhanced_terms 누락
            "selected_languages": ["ko"]
        }

        response = client.post("/api/v1/markdown/generate", json=payload)

        assert response.status_code == 422

    def test_generate_markdown_too_many_languages(self, client, valid_payload):
        """최대 언어 개수 초과 테스트"""
        valid_payload["selected_languages"] = [
            "ko", "en", "zh-CN", "zh-TW", "ja",
            "fr", "ru", "it", "vi", "ar", "es", "de"  # 12개 (초과)
        ]

        response = client.post("/api/v1/markdown/generate", json=valid_payload)

        assert response.status_code == 422
```

---

## 📊 마크다운 테이블 예시

### 입력 JSON
```json
{
  "enhanced_terms": [
    {
      "original_term": "Naciones Unidas",
      "term_type": "company",
      "tags": ["#ONU", "#global", "#politics"],
      "translations": {
        "ko": "유엔",
        "en": "United Nations",
        "ja": "国際連合"
      }
    },
    {
      "original_term": "OTAN",
      "term_type": "company",
      "tags": ["#NATO", "#security"],
      "translations": {
        "ko": "북대서양 조약 기구",
        "en": "NATO",
        "ja": "北大西洋条約機構"
      }
    }
  ]
}
```

### 선택 언어
- Korean (ko) ✓
- English (en) ✓
- Japanese (ja) ✓

### 생성된 마크다운

```markdown
|term|term_type|tags|ko|en|ja|
|------|----------|------|-----|-----|-----|
|Naciones Unidas|company|#ONU #global #politics|유엔|United Nations|国際連合|
|OTAN|company|#NATO #security|북대서양 조약 기구|NATO|北大西洋条約機構|
```

### 렌더링 결과

|term|term_type|tags|ko|en|ja|
|------|----------|------|-----|-----|-----|
|Naciones Unidas|company|#ONU #global #politics|유엔|United Nations|国際連合|
|OTAN|company|#NATO #security|북대서양 조약 기구|NATO|北大西洋条約機構|

---

## 🚀 배포 및 통합

### 1. 라우터 등록

**파일**: `src/main.py`에 추가

```python
from src.presentation.api.routes import markdown

# 라우터 등록
app.include_router(markdown.router)
```

### 2. Demo 페이지 라우트 추가

**파일**: `src/presentation/api/routes/demo.py`에 추가

```python
@router.get(
    "/markdown-table",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    summary="마크다운 테이블 생성 데모 페이지",
    description="""
    용어 추출 결과를 마크다운 테이블로 변환하는 데모 페이지를 제공합니다.

    **주요 기능:**
    - JSON 데이터 입력 (textarea 또는 파일 업로드)
    - 11개 언어 중 선택적 컬럼 구성
    - 서버 API를 통한 마크다운 테이블 생성
    - 클립보드 복사 및 .md 파일 다운로드
    """
)
async def markdown_table_demo() -> HTMLResponse:
    """
    마크다운 테이블 생성 데모 페이지를 반환합니다.
    """
    html_file = Path("static/markdown-table-demo.html")

    if not html_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"데모 페이지 파일을 찾을 수 없습니다: {html_file}"
        )

    try:
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데모 페이지 로드 실패: {str(e)}"
        )

    return HTMLResponse(content=html_content, status_code=200)
```

### 3. Demo 인덱스 페이지 업데이트

**파일**: `static/demo-index.html`에 새 데모 링크 추가

```html
<div class="demo-card">
    <h3>📊 마크다운 테이블 생성</h3>
    <p>용어 추출 결과를 마크다운 테이블 형식으로 변환합니다.</p>
    <ul>
        <li>JSON 데이터 입력</li>
        <li>다국어 컬럼 선택 (11개 언어)</li>
        <li>마크다운 생성 및 다운로드</li>
    </ul>
    <a href="/demo/markdown-table" class="demo-link">데모 시작 →</a>
</div>
```

---

## ✅ 체크리스트

### 개발 단계
- [ ] DTO 클래스 구현 (MarkdownGenerationRequest, MarkdownGenerationResponse)
- [ ] 도메인 서비스 구현 (MarkdownTableFormatter)
- [ ] 애플리케이션 서비스 구현 (MarkdownGenerationService)
- [ ] API 라우터 구현 (markdown.py)
- [ ] 의존성 주입 설정 (dependencies.py)
- [ ] 프론트엔드 HTML 페이지 구현 (markdown-table-demo.html)
- [ ] Demo 라우트 추가 (demo.py)
- [ ] 라우터 등록 (main.py)

### 테스트 단계
- [ ] MarkdownTableFormatter 단위 테스트
- [ ] MarkdownGenerationService 단위 테스트
- [ ] API 엔드포인트 통합 테스트
- [ ] 프론트엔드 기능 테스트 (수동)
- [ ] 언어 선택 검증 테스트
- [ ] 에러 핸들링 테스트

### 문서화 단계
- [ ] API 문서 자동 생성 확인 (Swagger UI)
- [ ] README 업데이트
- [ ] 사용 가이드 작성

### 배포 단계
- [ ] 로컬 환경 테스트
- [ ] 스테이징 환경 배포
- [ ] 프로덕션 환경 배포

---

## 📝 구현 우선순위

### Phase 1: 백엔드 핵심 기능 (1-2일)
1. DTO 클래스 구현
2. MarkdownTableFormatter 구현
3. MarkdownGenerationService 구현
4. 단위 테스트 작성

### Phase 2: API 레이어 (1일)
1. API 라우터 구현
2. 의존성 주입 설정
3. 통합 테스트 작성

### Phase 3: 프론트엔드 (1-2일)
1. HTML 페이지 구현
2. JavaScript 로직 구현
3. CSS 스타일링
4. 수동 테스트

### Phase 4: 통합 및 배포 (1일)
1. Demo 라우트 추가
2. 라우터 등록
3. 전체 기능 테스트
4. 문서 작성 및 배포

---

## 🎯 성공 지표

1. **기능성**: JSON 입력 → 마크다운 테이블 출력 정상 작동
2. **유효성 검증**: 잘못된 입력에 대한 적절한 에러 처리
3. **사용성**: 직관적인 UI/UX, 명확한 안내 메시지
4. **성능**: 100개 용어 기준 1초 이내 생성
5. **확장성**: 새로운 언어 추가 용이한 구조

---

## 📚 참고 자료

- FastAPI 공식 문서: https://fastapi.tiangolo.com/
- Pydantic 공식 문서: https://docs.pydantic.dev/
- Markdown 테이블 스펙: https://www.markdownguide.org/extended-syntax/#tables
- Clean Architecture 패턴: https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
