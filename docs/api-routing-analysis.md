# API 라우팅 인터페이스 분석 보고서

## 📋 개요

**분석 일시**: 2025-10-10  
**프로젝트**: PX-Plus (FastAPI + RFS Framework)  
**분석 범위**: API 라우팅 데코레이터 및 멀티파트 폼데이터 지원

---

## 🎯 핵심 결론

### ✅ 지원 현황 요약

| 기능 | 지원 여부 | 구현 방식 |
|------|-----------|----------|
| **@GET 데코레이터** | ✅ 지원 | FastAPI 표준 `@router.get()` |
| **@POST 데코레이터** | ✅ 지원 | FastAPI 표준 `@router.post()` |
| **멀티파트 폼데이터** | ✅ 완전 지원 | FastAPI `File` + `UploadFile` |
| **다중 파일 업로드** | ✅ 지원 | `List[UploadFile]` 패턴 |
| **파일 크기 제한** | ⚠️ 부분 지원 | 주석에만 명시 (10MB 권장) |

---

## 📐 라우팅 아키텍처

### 1. 라우팅 구조

```
FastAPI Application (src/main.py)
    ↓
APIRouter (src/infrastructure/web/routes.py)
    ↓
엔드포인트 (@router.get / @router.post)
```

### 2. 핵심 구성 요소

#### 2.1 메인 애플리케이션 설정
**파일**: [src/main.py](src/main.py:14-15)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .infrastructure.web.routes import router

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="PX-Plus: FastAPI + RFS Framework",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 라우터 등록
app.include_router(router, tags=["greetings"])
```

#### 2.2 APIRouter 정의
**파일**: [src/infrastructure/web/routes.py](src/infrastructure/web/routes.py:23)

```python
from fastapi import APIRouter, File, HTTPException, UploadFile, status

# API 라우터 생성
router = APIRouter()
```

---

## 🔧 라우팅 데코레이터 상세 분석

### 1. @GET 데코레이터 구현

**구현 방식**: FastAPI 표준 `@router.get()` 사용

#### 예제 1: 루트 엔드포인트
**파일**: [src/infrastructure/web/routes.py](src/infrastructure/web/routes.py:26-44)

```python
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
```

#### 예제 2: 헬스 체크 엔드포인트
**파일**: [src/infrastructure/web/routes.py](src/infrastructure/web/routes.py:47-65)

```python
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
```

### 2. @POST 데코레이터 구현

**구현 방식**: FastAPI 표준 `@router.post()` 사용

#### 예제: 문서 추출 엔드포인트 (멀티파트 지원)
**파일**: [src/infrastructure/web/routes.py](src/infrastructure/web/routes.py:68-120)

```python
@router.post(
    "/v1/document-extractor",
    response_model=DocumentExtractionSummaryResponse,
    responses={400: {"model": ErrorResponse}},
    summary="문서 텍스트 추출 및 청크 분할",
    description="지원되는 문서에서 텍스트를 추출하고 약 2000자 단위로 청크를 생성합니다.",
)
async def extract_document_chunks(
    use_case: ExtractDocumentChunksUseCaseDep,
    files: List[UploadFile] = File(..., description="처리할 파일 목록 (최대 10MB 권장)"),
) -> DocumentExtractionSummaryResponse:
    """
    문서 텍스트 추출 엔드포인트
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="업로드된 파일이 없습니다.",
        )

    documents: List[Tuple[str, bytes]] = []
    for file in files:
        filename = file.filename or "unnamed"
        file_bytes = await file.read()
        documents.append((filename, file_bytes))

    result = use_case.execute(documents)
    if not result.is_success():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=result.unwrap_error()
        )

    summary = result.unwrap()
    # ... 응답 생성 로직
```

---

## 📤 멀티파트 폼데이터 지원 상세

### 1. 구현 방식

**FastAPI 표준 구성 요소 사용**:
- `fastapi.File`: 파일 업로드 파라미터 정의
- `fastapi.UploadFile`: 비동기 파일 처리 지원
- `typing.List`: 다중 파일 업로드 지원

### 2. UploadFile 클래스 특성

FastAPI의 `UploadFile`은 다음 속성과 메서드를 제공합니다:

#### 주요 속성
```python
file.filename      # 업로드된 파일 이름 (str | None)
file.content_type  # MIME 타입 (str | None)
file.file          # SpooledTemporaryFile 객체
```

#### 주요 메서드
```python
await file.read()       # 전체 파일 내용 읽기 (bytes)
await file.write(data)  # 파일에 쓰기
await file.seek(0)      # 파일 포인터 이동
await file.close()      # 파일 닫기
```

### 3. 다중 파일 업로드 구현

**파일**: [src/infrastructure/web/routes.py](src/infrastructure/web/routes.py:77)

```python
files: List[UploadFile] = File(..., description="처리할 파일 목록 (최대 10MB 권장)")
```

**처리 로직**:
```python
documents: List[Tuple[str, bytes]] = []
for file in files:
    filename = file.filename or "unnamed"
    file_bytes = await file.read()  # 비동기 파일 읽기
    documents.append((filename, file_bytes))
```

### 4. 지원되는 콘텐츠 타입

**문서 참조**: [docs/document_extraction_process.md](docs/document_extraction_process.md)

**지원 파일 형식**:
- **프레젠테이션**: `.ppt`, `.pptx` (python-pptx)
- **스프레드시트**: `.xls`, `.xlsx` (openpyxl)
- **문서**: `.pdf` (pypdf)
- **텍스트**: `.txt`
- **마크다운**: `.md`, `.markdown`
- **JSON**: `.json`

---

## ⚙️ 의존성 주입 (Dependency Injection)

### FastAPI DI와 RFS Registry 통합

**파일**: [src/infrastructure/web/dependencies.py](src/infrastructure/web/dependencies.py)

```python
from typing import Annotated
from fastapi import Depends

# RFS Registry와 FastAPI DI 연결
def get_use_case_dependency():
    registry = get_registry()
    return registry.resolve(ExtractDocumentChunksUseCase)

ExtractDocumentChunksUseCaseDep = Annotated[
    ExtractDocumentChunksUseCase,
    Depends(get_use_case_dependency)
]
```

**사용 예**:
```python
async def extract_document_chunks(
    use_case: ExtractDocumentChunksUseCaseDep,  # 자동 주입
    files: List[UploadFile] = File(...),
) -> DocumentExtractionSummaryResponse:
    # use_case는 자동으로 주입됨
    result = use_case.execute(documents)
```

---

## 🔒 보안 및 검증

### 1. 파일 크기 제한

**현재 상태**: ⚠️ **주석으로만 명시**

**파일**: [src/infrastructure/web/routes.py](src/infrastructure/web/routes.py:77)
```python
files: List[UploadFile] = File(..., description="처리할 파일 목록 (최대 10MB 권장)")
```

**문제점**:
- 주석에 "최대 10MB 권장"이라고 명시되어 있으나
- 실제 코드상 파일 크기 검증 로직이 **없음**
- 악의적 사용자가 대용량 파일을 업로드할 수 있음

**권장 사항**: 파일 크기 검증 미들웨어 추가 필요

```python
# 권장 구현 예시
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def extract_document_chunks(
    use_case: ExtractDocumentChunksUseCaseDep,
    files: List[UploadFile] = File(...),
) -> DocumentExtractionSummaryResponse:
    # 파일 크기 검증
    for file in files:
        file_bytes = await file.read()
        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"파일 '{file.filename}'이 최대 크기(10MB)를 초과했습니다."
            )
        await file.seek(0)  # 포인터 리셋
    
    # ... 나머지 로직
```

### 2. 파일 타입 검증

**현재 구현**: 도메인 서비스 레벨에서 검증

**파일**: [src/domain/services.py](src/domain/services.py) (추정)

- 허용된 확장자만 처리
- 지원되지 않는 파일은 `SkippedDocument`로 반환

### 3. CORS 설정

**파일**: [src/main.py](src/main.py)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ 프로덕션에서는 특정 도메인으로 제한 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**보안 권장 사항**:
```python
# 프로덕션 환경 권장 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://app.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
```

---

## 📊 DTO (Data Transfer Objects)

### 응답 모델

**파일**: [src/application/dto.py](src/application/dto.py)

#### 1. ErrorResponse
```python
class ErrorResponse(BaseModel):
    """에러 응답 DTO"""
    error: str = Field(..., description="에러 메시지")
    code: str = Field(default="BUSINESS_ERROR", description="에러 코드")
    details: Optional[dict] = Field(None, description="추가 에러 상세 정보")
```

#### 2. HealthResponse
```python
class HealthResponse(BaseModel):
    """헬스 체크 응답 DTO"""
    status: str = Field(..., description="서비스 상태")
    service: str = Field(..., description="서비스 이름")
    version: str = Field(..., description="서비스 버전")
    timestamp: str = Field(..., description="응답 시각")
```

#### 3. DocumentExtractionSummaryResponse
```python
class DocumentExtractionSummaryResponse(BaseModel):
    """문서 추출 API 응답 DTO"""
    processed: List[ProcessedDocumentResponse] = Field(
        ..., description="처리된 문서 목록"
    )
    skipped: List[SkippedDocumentResponse] = Field(
        ..., description="처리에서 제외된 문서 목록"
    )
```

---

## 🛠️ FastAPI 공식 패턴과의 비교

### 1. 표준 준수도

| 항목 | PX-Plus 구현 | FastAPI 공식 권장 | 준수 여부 |
|------|-------------|-----------------|----------|
| 라우팅 데코레이터 | `@router.get/post()` | `@router.get/post()` | ✅ 완전 준수 |
| 파일 업로드 | `UploadFile` + `File()` | `UploadFile` + `File()` | ✅ 완전 준수 |
| 다중 파일 | `List[UploadFile]` | `List[UploadFile]` | ✅ 완전 준수 |
| 비동기 처리 | `async def` + `await` | `async def` + `await` | ✅ 완전 준수 |
| 응답 모델 | Pydantic BaseModel | Pydantic BaseModel | ✅ 완전 준수 |
| DI 패턴 | `Annotated` + `Depends` | `Annotated` + `Depends` | ✅ 완전 준수 |

### 2. FastAPI 공식 문서 참조

**출처**: Context7 - FastAPI 공식 문서

#### 파일 업로드 패턴
```python
# FastAPI 공식 권장 패턴
from typing import Annotated
from fastapi import FastAPI, File, UploadFile

app = FastAPI()

@app.post("/files/")
async def create_files(
    files: Annotated[list[UploadFile], File(description="Multiple files")],
):
    return {"filenames": [file.filename for file in files]}
```

**PX-Plus 구현**:
```python
# PX-Plus는 완전히 동일한 패턴 사용
@router.post("/v1/document-extractor")
async def extract_document_chunks(
    use_case: ExtractDocumentChunksUseCaseDep,
    files: List[UploadFile] = File(..., description="처리할 파일 목록 (최대 10MB 권장)"),
) -> DocumentExtractionSummaryResponse:
    # ... 구현
```

---

## 🎨 아키텍처 패턴

### 헥사고날 아키텍처 (Ports & Adapters)

```
┌─────────────────────────────────────────────┐
│         Presentation Layer (FastAPI)        │
│  ┌─────────────────────────────────────┐   │
│  │  routes.py (@router.get/post)       │   │
│  │  dependencies.py (FastAPI DI)       │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                    ↓ HTTP 요청
┌─────────────────────────────────────────────┐
│         Application Layer                   │
│  ┌─────────────────────────────────────┐   │
│  │  dto.py (Pydantic Models)           │   │
│  │  ExtractDocumentChunksUseCase       │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                    ↓ 비즈니스 로직
┌─────────────────────────────────────────────┐
│         Domain Layer                        │
│  ┌─────────────────────────────────────┐   │
│  │  FileTextExtractionService          │   │
│  │  DocumentChunkingService            │   │
│  │  Result Pattern (Success/Failure)   │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### Result 패턴을 활용한 에러 처리

```python
# 도메인 레벨: Result 패턴
result = use_case.execute(documents)

# 인프라 레벨: HTTP 예외 변환
if not result.is_success():
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=result.unwrap_error()
    )

summary = result.unwrap()
```

---

## 📝 API 엔드포인트 목록

### 1. GET /
- **요약**: 루트 헬스 체크
- **응답**: `HealthResponse`
- **인증**: 불필요

### 2. GET /health
- **요약**: 헬스 체크
- **응답**: `HealthResponse`
- **인증**: 불필요

### 3. POST /v1/document-extractor
- **요약**: 문서 텍스트 추출 및 청크 분할
- **요청**: `multipart/form-data`
  - `files`: 파일 목록 (최대 10MB 권장)
- **응답**: `DocumentExtractionSummaryResponse`
  - `processed`: 처리 성공 문서 목록
  - `skipped`: 처리 실패 문서 목록
- **에러**: 
  - `400 Bad Request`: 파일 업로드 실패, 처리 실패
- **인증**: 불필요 (현재)

---

## 🔍 추가 분석

### 1. 커스텀 라우팅 데코레이터 존재 여부

**결론**: ❌ **커스텀 데코레이터 없음**

- RFS Framework 검색 결과: 커스텀 라우팅 데코레이터 발견되지 않음
- 프로젝트 전체 검색: `@GET`, `@POST` 형태의 커스텀 데코레이터 없음
- **FastAPI 표준 방식만 사용**

### 2. python-multipart 의존성

**파일**: `pyproject.toml` (추정)

FastAPI에서 멀티파트 폼데이터를 처리하려면 `python-multipart` 패키지가 필요합니다.

```toml
[tool.poetry.dependencies]
python-multipart = "^0.0.6"  # 멀티파트 지원
```

---

## ⚡ 성능 고려사항

### 1. 비동기 파일 처리

```python
# ✅ 비동기 방식 (권장)
file_bytes = await file.read()

# ❌ 동기 방식 (비권장)
file_bytes = file.file.read()
```

### 2. 메모리 관리

**현재 구현**:
```python
documents: List[Tuple[str, bytes]] = []
for file in files:
    file_bytes = await file.read()  # 전체 파일을 메모리에 로드
    documents.append((filename, file_bytes))
```

**대용량 파일 처리 시 개선 방안**:
```python
# 스트리밍 처리 예시
async def process_large_file(file: UploadFile):
    chunk_size = 1024 * 1024  # 1MB 청크
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        # 청크 단위로 처리
        process_chunk(chunk)
```

---

## 📋 권장 사항

### 1. 보안 강화

#### 1.1 파일 크기 검증 추가
```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_file_size(file: UploadFile):
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"파일 크기가 10MB를 초과했습니다."
        )
    await file.seek(0)
    return file_bytes
```

#### 1.2 CORS 정책 강화
```python
# 프로덕션 환경용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
```

#### 1.3 Rate Limiting 추가
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/v1/document-extractor")
@limiter.limit("10/minute")  # 분당 10회 제한
async def extract_document_chunks(...):
    # ... 구현
```

### 2. 모니터링 및 로깅

```python
import logging

logger = logging.getLogger(__name__)

@router.post("/v1/document-extractor")
async def extract_document_chunks(...):
    logger.info(f"파일 업로드 요청: {len(files)}개 파일")
    
    for file in files:
        logger.info(f"파일 처리: {file.filename} ({file.content_type})")
    
    # ... 구현
```

### 3. API 문서화 개선

```python
@router.post(
    "/v1/document-extractor",
    response_model=DocumentExtractionSummaryResponse,
    responses={
        200: {
            "description": "문서 처리 성공",
            "content": {
                "application/json": {
                    "example": {
                        "processed": [...],
                        "skipped": [...]
                    }
                }
            }
        },
        400: {"model": ErrorResponse},
        413: {"description": "파일 크기 초과"},
        429: {"description": "요청 횟수 제한 초과"},
    },
    summary="문서 텍스트 추출 및 청크 분할",
    description="""
    지원되는 문서에서 텍스트를 추출하고 약 2000자 단위로 청크를 생성합니다.
    
    **지원 파일 형식**:
    - 프레젠테이션: .ppt, .pptx
    - 스프레드시트: .xls, .xlsx
    - 문서: .pdf
    - 텍스트: .txt, .md, .markdown
    - 데이터: .json
    
    **제한 사항**:
    - 최대 파일 크기: 10MB
    - 최대 파일 수: 제한 없음 (권장 10개 이하)
    """,
)
async def extract_document_chunks(...):
    # ... 구현
```

---

## 📚 참고 자료

### 내부 문서
- [src/main.py](src/main.py) - FastAPI 애플리케이션 메인
- [src/infrastructure/web/routes.py](src/infrastructure/web/routes.py) - API 라우터 정의
- [src/infrastructure/web/dependencies.py](src/infrastructure/web/dependencies.py) - FastAPI DI 레이어
- [src/application/dto.py](src/application/dto.py) - Pydantic 응답 모델
- [docs/document_extraction_process.md](docs/document_extraction_process.md) - 문서 추출 프로세스

### 외부 참조
- FastAPI 공식 문서: https://fastapi.tiangolo.com/
- FastAPI 파일 업로드: https://fastapi.tiangolo.com/tutorial/request-files/
- Pydantic 문서: https://docs.pydantic.dev/
- python-multipart: https://andrew-d.github.io/python-multipart/

---

## 🎯 결론

### ✅ 주요 강점

1. **표준 준수**: FastAPI 공식 권장 패턴 100% 준수
2. **타입 안정성**: Pydantic과 타입 힌트를 활용한 강력한 타입 검증
3. **아키텍처**: 헥사고날 아키텍처로 관심사 분리 명확
4. **에러 처리**: Result 패턴으로 안전한 에러 핸들링
5. **비동기 처리**: async/await를 활용한 효율적인 파일 처리

### ⚠️ 개선 필요 사항

1. **파일 크기 검증**: 주석으로만 명시된 10MB 제한을 코드로 구현 필요
2. **CORS 정책**: 프로덕션 환경에서 특정 도메인만 허용하도록 제한 필요
3. **Rate Limiting**: API 남용 방지를 위한 요청 제한 추가 권장
4. **대용량 파일**: 스트리밍 처리 방식 도입 고려

### 📊 최종 평가

| 항목 | 평가 | 점수 |
|------|------|------|
| FastAPI 표준 준수 | 완벽 | ⭐⭐⭐⭐⭐ |
| 멀티파트 폼데이터 지원 | 완전 지원 | ⭐⭐⭐⭐⭐ |
| 보안 구현 | 부분 구현 | ⭐⭐⭐☆☆ |
| 코드 품질 | 우수 | ⭐⭐⭐⭐☆ |
| 문서화 | 양호 | ⭐⭐⭐⭐☆ |

---

**작성자**: Claude (SuperClaude Framework)  
**분석 도구**: Serena MCP, Context7 MCP, Sequential MCP  
**문서 버전**: 1.0.0
