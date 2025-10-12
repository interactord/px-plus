# 용어 추출 데모 페이지 사용 가이드

## 개요

용어 추출 API를 테스트할 수 있는 웹 기반 데모 페이지입니다. GPT-4o를 사용하여 텍스트에서 고유명사와 주요 도메인을 추출합니다.

## 파일 정보

- **위치**: `static/term-extraction-demo.html`
- **유형**: 원페이지 HTML (HTML + CSS + JavaScript 통합)
- **API 엔드포인트**: `POST /api/v1/extract-terms/process-documents`

## 접속 방법

### 1. 서버 실행

```bash
# 개발 환경
./run.sh dev

# 또는 직접 실행
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 브라우저 접속

**권장 방법 (라우터 기반)**:
```
http://localhost:8000/demo/term-extraction
```

**대체 방법 (직접 접근)**:
```
http://localhost:8000/static/term-extraction-demo.html
```

### 3. 데모 페이지 목록

모든 사용 가능한 데모 페이지 확인:
```
http://localhost:8000/demo/
```

## 페이지 구조

### 헤더
- 제목: "용어 추출 데모"
- 부제목: "GPT-4o를 사용한 고유명사 및 주요 도메인 추출"

### 입력 섹션

**1. 파일명 입력**
- 추출할 텍스트의 파일명 지정
- 기본값: `test-document.txt`

**2. 텍스트 입력**
- 추출할 텍스트를 입력하는 textarea
- 여러 단락을 입력 가능 (자동으로 하나의 청크로 처리)
- 샘플 버튼으로 예시 텍스트 빠르게 로드

**3. 샘플 버튼**
- **샘플 1 (한국어)**: 홍길동, 삼성전자 등 한국 관련 텍스트
- **샘플 2 (영어)**: Apple, Elon Musk 등 영어 텍스트
- **샘플 3 (혼합)**: Python, React 등 기술 용어 혼합

**4. 옵션 설정**
- **LLM 캐싱 사용**: 동일 텍스트 재추출 시 캐시 활용 (기본값: 체크)
- **병렬 워커 수**: 3개 (기본값)
- **최대 엔티티 수**: 청크당 최대 50개 (기본값)

### 결과 섹션

**1. 통계 카드**
- 총 청크 수
- 추출된 엔티티 수
- 캐시 히트율
- 처리 시간

**2. JSON 응답**
- API 응답을 JSON 형식으로 표시
- 구문 강조 및 들여쓰기 적용
- 복사 가능한 형식

## 사용 방법

### 기본 사용

1. **텍스트 입력**
   - 직접 입력하거나 샘플 버튼 클릭
   
2. **옵션 설정** (선택사항)
   - 캐시 사용 여부
   - 병렬 처리 워커 수
   - 최대 엔티티 수

3. **제출**
   - "용어 추출 시작" 버튼 클릭
   - 로딩 스피너 표시

4. **결과 확인**
   - 통계 확인 (엔티티 수, 처리 시간 등)
   - JSON 응답 확인

### 샘플 사용 예시

**샘플 1 실행 (한국어)**:
```
1. "샘플 1 (한국어)" 버튼 클릭
2. "용어 추출 시작" 버튼 클릭
3. 결과 확인:
   - 추출된 엔티티: 홍길동 (person), 삼성전자 (company), 갤럭시 (product) 등
```

**샘플 3 실행 (기술 용어)**:
```
1. "샘플 3 (혼합)" 버튼 클릭
2. 병렬 워커 수: 3 설정
3. "용어 추출 시작" 버튼 클릭
4. 결과 확인:
   - 추출된 엔티티: Python (technical_term), React (technical_term), Meta (company) 등
```

## API 요청 형식

데모 페이지가 보내는 요청:

```json
{
  "processed_files": [
    {
      "filename": "test-document.txt",
      "chunks": [
        "입력한 텍스트 내용..."
      ],
      "metadata": {
        "timestamp": "2024-01-15T10:30:00.000Z"
      }
    }
  ],
  "use_cache": true,
  "parallel_workers": 3,
  "template_name": "extract_terms.j2",
  "max_entities_per_chunk": 50,
  "include_context": true
}
```

## API 응답 형식

```json
{
  "results": [
    {
      "chunk_index": 0,
      "source_filename": "test-document.txt",
      "entities": [
        {
          "term": "#홍길동",
          "type": "person",
          "primary_domain": "#역사",
          "tags": ["#조선시대", "#의적"],
          "context": "홍길동은 조선시대의 전설적인 의적이다.",
          "multilingual_expressions": {
            "en": "Hong Gildong"
          }
        }
      ],
      "cached": false,
      "processing_time": 1.234,
      "error": null
    }
  ],
  "summary": {
    "total_chunks": 1,
    "processed_chunks": 1,
    "failed_chunks": 0,
    "cache_hits": 0,
    "cache_hit_rate": 0.0,
    "total_entities": 5,
    "total_processing_time": 1.234,
    "average_processing_time": 1.234
  }
}
```

## 추출되는 엔티티 타입

| 타입 | 설명 | 예시 |
|------|------|------|
| `person` | 인물, 전문가, 팀원 | 홍길동, Elon Musk, Steve Jobs |
| `company` | 조직, 기업, 기관, 스타트업 | 삼성전자, Apple, Meta |
| `product` | 제품, 서비스, 브랜드, 애플리케이션 | 갤럭시, iPhone, Tesla Model 3 |
| `technical_term` | 기술 용어, 프레임워크, 도구, 방법론 | Python, React, Django, Machine Learning |

## 특징

### 1. 원페이지 구조
- HTML, CSS, JavaScript 모두 하나의 파일에 통합
- 외부 의존성 없음 (순수 JavaScript)
- 간편한 배포 및 관리

### 2. 사용자 친화적 UI
- 깔끔한 카드 기반 레이아웃
- 반응형 디자인 (모바일 지원)
- 로딩 스피너 및 애니메이션
- 에러 메시지 표시

### 3. 실시간 통계
- 추출된 엔티티 수
- 캐시 히트율
- 처리 시간
- 성공/실패 청크 수

### 4. JSON 응답 표시
- 포맷팅된 JSON 출력
- 코드 블록 스타일링
- 복사 가능한 형식

## 문제 해결

### "용어 추출 중 오류가 발생했습니다"

**원인**:
- API 서버가 실행되지 않음
- OpenAI API 키가 설정되지 않음
- 네트워크 연결 문제

**해결**:
```bash
# 1. 서버 실행 확인
curl http://localhost:8000/api/v1/extract-terms/health

# 2. 환경 변수 확인
echo $OPENAI_API_KEY

# 3. 로그 확인
tail -f logs/app.log
```

### "HTTP 500: Internal Server Error"

**원인**:
- 템플릿 파일 누락
- 의존성 주입 미구현
- OpenAI API 호출 실패

**해결**:
```bash
# 템플릿 파일 확인
ls src/infrastructure/term_extraction/templates/
# extract_terms.j2, system_analyst.j2 존재 확인

# 의존성 주입 구현 확인
grep -r "get_model_port" src/presentation/api/routes/
```

### 캐시가 작동하지 않음

**원인**:
- `use_cache` 옵션이 비활성화됨
- 캐시 구현체가 초기화되지 않음

**해결**:
- 데모 페이지에서 "LLM 캐싱 사용" 체크박스 확인
- 동일한 텍스트로 재시도

## 커스터마이징

### 색상 테마 변경

CSS 변수 수정:

```css
:root {
    --primary: #14B8A6;        /* 청록색 → 원하는 색상 */
    --primary-dark: #0F766E;   /* 어두운 청록색 */
    /* ... */
}
```

### 샘플 텍스트 추가

JavaScript 샘플 객체 수정:

```javascript
const samples = {
    korean: `...`,
    english: `...`,
    mixed: `...`,
    custom: `새로운 샘플 텍스트...`  // 추가
};
```

HTML 버튼 추가:

```html
<button type="button" class="btn-sample" onclick="loadSample('custom')">
    샘플 4 (커스텀)
</button>
```

### API 엔드포인트 변경

```javascript
// 다른 서버로 요청 시
const response = await fetch('https://api.example.com/extract-terms/process-documents', {
    // ...
});
```

## 프로덕션 배포

### FastAPI 정적 파일 서빙 설정

`src/main.py`:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# 정적 파일 마운트
app.mount("/static", StaticFiles(directory="static"), name="static")
```

### Nginx 설정 (선택사항)

```nginx
location /static/ {
    alias /path/to/px-plus/static/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

## 참고 자료

- [용어 추출 API 통합 가이드](../design/term-extraction/05-integration-guide.md)
- [용어 추출 API 구현 완료 보고서](../design/term-extraction/06-implementation-complete.md)
- [FastAPI 정적 파일 문서](https://fastapi.tiangolo.com/tutorial/static-files/)

## 라우터 기반 접근의 장점

### 왜 `/demo/term-extraction`을 사용해야 하나요?

1. **깔끔한 URL 구조**
   - `/demo/term-extraction` (의미 있는 경로)
   - `/static/term-extraction-demo.html` (파일 경로 노출)

2. **유연한 제어**
   - 라우터에서 접근 제어 가능
   - 인증/권한 추가 용이
   - 미들웨어 적용 가능

3. **일관성 있는 API 아키텍처**
   - API 엔드포인트와 동일한 패턴
   - REST 원칙 준수
   - 확장 가능한 구조

4. **향후 확장성**
   - 여러 데모 페이지 관리 용이
   - `/demo/` 인덱스 페이지 제공
   - 동적 렌더링으로 업그레이드 가능

### 라우터 구현 상세

**파일**: `src/presentation/api/routes/demo.py`

```python
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get(
    "/term-extraction",
    response_class=HTMLResponse,
    summary="용어 추출 데모 페이지"
)
async def term_extraction_demo() -> HTMLResponse:
    """
    용어 추출 데모 페이지를 반환합니다.
    
    GPT-4o를 사용하여 텍스트에서 고유명사와 주요 도메인을 추출하는
    기능을 테스트할 수 있는 웹 기반 데모 페이지를 제공합니다.
    """
    html_file = Path("static/term-extraction-demo.html")
    if not html_file.exists():
        raise HTTPException(
            status_code=404, 
            detail="데모 페이지 파일을 찾을 수 없습니다"
        )
    
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    return HTMLResponse(content=html_content, status_code=200)


@router.get("/", response_class=HTMLResponse, summary="데모 페이지 목록")
async def demo_index() -> HTMLResponse:
    """
    사용 가능한 데모 페이지 목록을 반환합니다.
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>데모 페이지 목록</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            h1 { color: #333; }
            .demo-list {
                background: white;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .demo-item {
                padding: 15px;
                border-bottom: 1px solid #eee;
            }
            .demo-item:last-child { border-bottom: none; }
            .demo-link {
                color: #14B8A6;
                text-decoration: none;
                font-size: 18px;
                font-weight: 600;
            }
            .demo-link:hover { text-decoration: underline; }
            .demo-desc { color: #666; margin-top: 5px; }
        </style>
    </head>
    <body>
        <h1>🎯 데모 페이지 목록</h1>
        <div class="demo-list">
            <div class="demo-item">
                <a href="/demo/term-extraction" class="demo-link">
                    용어 추출 데모
                </a>
                <p class="demo-desc">
                    GPT-4o를 사용하여 텍스트에서 고유명사와 주요 도메인을 추출합니다.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content, status_code=200)
```

### main.py 등록

```python
from .presentation.api.routes import term_extraction_router, demo_router

# 라우터 등록
app.include_router(term_extraction_router)
app.include_router(demo_router, prefix="/demo")
```

## 변경 이력

- **2024-01-15**: 초기 버전 생성
  - 원페이지 HTML 구조
  - 3가지 샘플 텍스트
  - JSON 응답 표시
  - 통계 카드 추가
  - 라우터 기반 접근 구현 (`/demo/term-extraction`)
  - 데모 인덱스 페이지 추가 (`/demo/`)
