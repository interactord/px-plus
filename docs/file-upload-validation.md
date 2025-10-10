# 파일 업로드 검증 가이드

## 📋 개요

PX-Plus는 파일 업로드 시 크기, 개수, 확장자를 자동으로 검증하여 서버 리소스를 보호하고 안전한 파일 업로드를 보장합니다.

---

## ⚙️ 환경 변수 설정

### .env 파일 설정

파일 업로드 제한은 `.env` 파일에서 다음 환경 변수로 설정할 수 있습니다:

```bash
# ========================================
# 파일 업로드 설정
# ========================================

# 단일 파일 최대 크기 (바이트 단위, 기본: 10MB)
MAX_FILE_SIZE=10485760

# 전체 업로드 파일 총합 최대 크기 (바이트 단위, 기본: 20MB)
MAX_TOTAL_FILE_SIZE=20971520

# 허용되는 파일 확장자
ALLOWED_EXTENSIONS=.txt,.md,.pdf,.docx,.xlsx,.csv,.json,.pptx,.ppt

# 최대 업로드 파일 개수
MAX_FILES=10

# 업로드 디렉토리
UPLOAD_DIR=./uploads

# 업로드 파일 정리 주기 (일 단위)
CLEANUP_DAYS=30
```

### 환경 변수 설명

| 환경 변수 | 기본값 | 설명 |
|----------|--------|------|
| `MAX_FILE_SIZE` | 10485760 (10MB) | 단일 파일의 최대 크기 (바이트) |
| `MAX_TOTAL_FILE_SIZE` | 20971520 (20MB) | 전체 업로드 파일의 총합 최대 크기 (바이트) |
| `ALLOWED_EXTENSIONS` | .txt,.md,.pdf,... | 허용되는 파일 확장자 (콤마로 구분) |
| `MAX_FILES` | 10 | 한 번에 업로드 가능한 최대 파일 개수 |
| `UPLOAD_DIR` | ./uploads | 업로드 파일 저장 디렉토리 |
| `CLEANUP_DAYS` | 30 | 업로드 파일 정리 주기 (일) |

---

## 🔍 검증 로직

### 1. 검증 순서

파일 업로드 시 다음 순서로 검증이 진행됩니다:

```
1. 파일 개수 검증 (MAX_FILES)
   ↓
2. 각 파일별 검증 반복:
   - 파일 확장자 검증 (ALLOWED_EXTENSIONS)
   - 파일 읽기
   - 단일 파일 크기 검증 (MAX_FILE_SIZE)
   - 총합 크기 누적
   ↓
3. 전체 파일 총합 크기 검증 (MAX_TOTAL_FILE_SIZE)
   ↓
4. 검증 통과 → 유즈케이스 실행
```

### 2. 검증 규칙

#### 2.1 파일 개수 검증

```python
# 검증 조건
if len(files) > MAX_FILES:
    raise HTTPException(400, "최대 {MAX_FILES}개까지 업로드 가능")
```

**예시**:
- `MAX_FILES=10` 설정 시
- 11개 파일 업로드 → ❌ 에러
- 10개 파일 업로드 → ✅ 통과

#### 2.2 파일 확장자 검증

```python
# 검증 조건
if 파일_확장자 not in ALLOWED_EXTENSIONS:
    raise HTTPException(400, "허용되지 않는 파일 형식")
```

**예시**:
- `ALLOWED_EXTENSIONS=.txt,.pdf`
- `example.txt` → ✅ 통과
- `example.exe` → ❌ 에러

#### 2.3 단일 파일 크기 검증

```python
# 검증 조건
if 파일_크기 > MAX_FILE_SIZE:
    raise HTTPException(413, "파일 크기가 최대 크기를 초과")
```

**예시**:
- `MAX_FILE_SIZE=10485760` (10MB)
- 5MB 파일 → ✅ 통과
- 15MB 파일 → ❌ 에러

#### 2.4 전체 파일 총합 크기 검증

```python
# 검증 조건
if 전체_파일_크기_합계 > MAX_TOTAL_FILE_SIZE:
    raise HTTPException(413, "전체 파일 크기가 최대 총합을 초과")
```

**예시**:
- `MAX_TOTAL_FILE_SIZE=20971520` (20MB)
- 5MB × 3개 = 15MB → ✅ 통과
- 8MB × 3개 = 24MB → ❌ 에러

---

## 🛠️ 구현 상세

### 1. 설정 모듈

**파일**: `src/shared/config.py`

```python
from pydantic_settings import BaseSettings

class UploadSettings(BaseSettings):
    """파일 업로드 관련 설정"""
    
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_total_file_size: int = 20 * 1024 * 1024  # 20MB
    allowed_extensions: str = ".txt,.md,.pdf,..."
    max_files: int = 10
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """확장자 리스트 반환"""
        return [ext.strip() for ext in self.allowed_extensions.split(",")]
    
    def format_size(self, size_bytes: int) -> str:
        """바이트를 사람이 읽기 쉬운 형식으로 변환"""
        # 10485760 → "10.0 MB"
```

### 2. 검증 모듈

**파일**: `src/infrastructure/web/validators.py`

```python
class FileUploadValidator:
    """파일 업로드 검증 클래스"""
    
    async def validate_files(
        self, files: List[UploadFile]
    ) -> List[Tuple[str, bytes]]:
        """
        업로드된 파일들을 검증
        
        Returns:
            List[Tuple[str, bytes]]: (파일명, 파일바이트) 리스트
            
        Raises:
            HTTPException: 검증 실패 시
        """
        # 1. 파일 개수 검증
        self._validate_file_count(files)
        
        # 2. 각 파일 검증
        documents = []
        total_size = 0
        
        for file in files:
            # 확장자 검증
            self._validate_file_extension(file.filename)
            
            # 파일 읽기
            file_bytes = await file.read()
            
            # 단일 파일 크기 검증
            self._validate_single_file_size(file.filename, len(file_bytes))
            
            total_size += len(file_bytes)
            documents.append((file.filename, file_bytes))
        
        # 3. 전체 크기 검증
        self._validate_total_file_size(total_size)
        
        return documents
```

### 3. API 라우터 적용

**파일**: `src/infrastructure/web/routes.py`

```python
from .validators import get_file_validator

@router.post("/v1/document-extractor")
async def extract_document_chunks(
    use_case: ExtractDocumentChunksUseCaseDep,
    files: List[UploadFile] = File(...),
):
    # 파일 검증 (크기, 개수, 확장자)
    validator = get_file_validator()
    documents = await validator.validate_files(files)
    
    # 검증 통과 → 유즈케이스 실행
    result = use_case.execute(documents)
    # ...
```

---

## 📊 에러 응답

### 1. HTTP 상태 코드

| 상태 코드 | 상황 | 설명 |
|----------|------|------|
| `400 Bad Request` | 파일 없음, 개수 초과, 확장자 불일치 | 잘못된 요청 |
| `413 Payload Too Large` | 파일 크기 초과 | 단일 또는 총합 크기 초과 |

### 2. 에러 메시지 예시

#### 2.1 파일 없음
```json
{
  "detail": "업로드된 파일이 없습니다."
}
```

#### 2.2 파일 개수 초과
```json
{
  "detail": "최대 10개까지 업로드 가능합니다. (현재: 15개)"
}
```

#### 2.3 확장자 불일치
```json
{
  "detail": "'malware.exe': 허용되지 않는 파일 형식입니다. 허용 형식: .txt, .md, .pdf, .docx, .xlsx, .csv, .json, .pptx, .ppt"
}
```

#### 2.4 단일 파일 크기 초과
```json
{
  "detail": "'large_file.pdf': 파일 크기가 최대 크기(10.0 MB)를 초과했습니다. (현재: 15.5 MB)"
}
```

#### 2.5 전체 파일 총합 크기 초과
```json
{
  "detail": "전체 파일 크기가 최대 총합(20.0 MB)을 초과했습니다. (현재: 25.3 MB)"
}
```

---

## 🧪 테스트 예시

### 1. cURL을 이용한 테스트

#### 성공 케이스
```bash
# 단일 파일 업로드 (5MB)
curl -X POST "http://localhost:8002/v1/document-extractor" \
  -F "files=@document.pdf"

# 다중 파일 업로드 (각 5MB, 총 15MB)
curl -X POST "http://localhost:8002/v1/document-extractor" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.txt" \
  -F "files=@doc3.xlsx"
```

#### 실패 케이스

**파일 크기 초과**:
```bash
# 단일 파일 15MB (MAX_FILE_SIZE=10MB 초과)
curl -X POST "http://localhost:8002/v1/document-extractor" \
  -F "files=@large_file.pdf"

# 응답: 413 Payload Too Large
# "파일 크기가 최대 크기(10.0 MB)를 초과했습니다."
```

**전체 크기 초과**:
```bash
# 8MB × 3개 = 24MB (MAX_TOTAL_FILE_SIZE=20MB 초과)
curl -X POST "http://localhost:8002/v1/document-extractor" \
  -F "files=@file1.pdf" \
  -F "files=@file2.pdf" \
  -F "files=@file3.pdf"

# 응답: 413 Payload Too Large
# "전체 파일 크기가 최대 총합(20.0 MB)을 초과했습니다."
```

**파일 개수 초과**:
```bash
# 11개 파일 업로드 (MAX_FILES=10 초과)
curl -X POST "http://localhost:8002/v1/document-extractor" \
  -F "files=@f1.txt" \
  -F "files=@f2.txt" \
  ... (11개)

# 응답: 400 Bad Request
# "최대 10개까지 업로드 가능합니다. (현재: 11개)"
```

**확장자 불일치**:
```bash
# .exe 파일 업로드
curl -X POST "http://localhost:8002/v1/document-extractor" \
  -F "files=@malware.exe"

# 응답: 400 Bad Request
# "'malware.exe': 허용되지 않는 파일 형식입니다."
```

### 2. Python을 이용한 테스트

```python
import requests

# 성공 케이스
files = [
    ('files', ('doc1.pdf', open('doc1.pdf', 'rb'), 'application/pdf')),
    ('files', ('doc2.txt', open('doc2.txt', 'rb'), 'text/plain')),
]

response = requests.post(
    'http://localhost:8002/v1/document-extractor',
    files=files
)

print(response.status_code)  # 200
print(response.json())

# 실패 케이스 - 크기 초과
large_file = ('files', ('huge.pdf', open('huge.pdf', 'rb'), 'application/pdf'))
response = requests.post(
    'http://localhost:8002/v1/document-extractor',
    files=[large_file]
)

print(response.status_code)  # 413
print(response.json())  # {'detail': '파일 크기가 최대 크기...'}
```

---

## 🔧 커스터마이징

### 1. 크기 제한 변경

**개발 환경**: 더 큰 파일 허용
```bash
# .env
MAX_FILE_SIZE=52428800        # 50MB
MAX_TOTAL_FILE_SIZE=104857600  # 100MB
```

**프로덕션 환경**: 더 엄격한 제한
```bash
# .env
MAX_FILE_SIZE=5242880         # 5MB
MAX_TOTAL_FILE_SIZE=10485760  # 10MB
```

### 2. 허용 확장자 변경

**이미지 파일만 허용**:
```bash
# .env
ALLOWED_EXTENSIONS=.jpg,.jpeg,.png,.gif,.webp
```

**모든 문서 형식 허용**:
```bash
# .env
ALLOWED_EXTENSIONS=.txt,.md,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.csv,.json,.xml,.html
```

### 3. 파일 개수 제한 변경

**단일 파일만 허용**:
```bash
# .env
MAX_FILES=1
```

**무제한 (비권장)**:
```bash
# .env
MAX_FILES=1000  # 실질적으로 무제한
```

---

## ⚠️ 주의사항

### 1. 메모리 사용

현재 구현은 **모든 파일을 메모리에 로드**합니다:

```python
file_bytes = await file.read()  # 전체 파일을 메모리에 적재
```

**대용량 파일 처리 시 주의**:
- `MAX_TOTAL_FILE_SIZE`를 서버 메모리의 50% 이하로 설정
- 예: 4GB 메모리 서버 → 최대 2GB 이하 권장

### 2. 네트워크 타임아웃

FastAPI/Uvicorn의 기본 타임아웃 설정 확인:

```bash
# run.sh 또는 uvicorn 실행 시
uvicorn src.main:app --timeout-keep-alive 300
```

### 3. 프록시 설정 (Nginx, etc.)

Nginx를 사용하는 경우 프록시 설정도 조정 필요:

```nginx
# nginx.conf
client_max_body_size 20M;  # MAX_TOTAL_FILE_SIZE와 동일하게
```

---

## 📚 관련 문서

- [API 라우팅 인터페이스 분석](./api-routing-analysis.md)
- [문서 추출 프로세스](./document_extraction_process.md)
- [FastAPI 파일 업로드 공식 문서](https://fastapi.tiangolo.com/tutorial/request-files/)

---

**작성일**: 2025-10-10  
**버전**: 1.0.0  
**작성자**: Claude (SuperClaude Framework)
