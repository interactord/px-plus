# 📊 PX 프로젝트 로깅 시스템 가이드

## 목차
1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [파라미터 상세](#파라미터-상세)
4. [사용 패턴](#사용-패턴)
5. [마이그레이션 가이드](#마이그레이션-가이드)
6. [베스트 프랙티스](#베스트-프랙티스)

## 개요

PX 프로젝트는 RFS Framework 4.5.1 기반의 통합 로깅 시스템을 사용합니다. 이 시스템은 동기/비동기 컨텍스트를 모두 지원하며, 구조화된 JSON 로깅을 제공합니다.

### 핵심 특징
- ✅ 동기/비동기 통합 지원
- ✅ 구조화된 JSON 출력
- ✅ 컨텍스트 자동 포함
- ✅ ResultAsync 패턴 통합
- ✅ 성능 메트릭 자동 수집

## 아키텍처

### 디렉토리 구조
```
src/shared/px_logging/
├── __init__.py         # 메인 export 모듈
├── logger.py           # ResultAsync 기반 로거 (레거시)
├── unified_logger.py   # 통합 로거 (현재 사용)
└── error_tracker.py    # 에러 추적 시스템
```

### 로거 생성 체인
```python
get_logger(name, context) 
  → get_async_result_logger(name, context)
    → get_unified_logger(name, context)
      → UnifiedLogger(name, context)
```

## 파라미터 상세

### 1. 로거 생성

#### get_logger(name, context)
| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| `name` | `str` | ✅ | 로거 네임스페이스 | `__name__`, `"app.service"` |
| `context` | `Dict[str, Any]` | ❌ | 기본 컨텍스트 | `{"service": "api", "version": "1.0"}` |

```python
from src.shared.px_logging import get_logger

# 기본 사용
logger = get_logger(__name__)

# 컨텍스트 포함
logger = get_logger(__name__, {
    "service": "term_extraction",
    "environment": "production"
})
```

### 2. 로그 레벨 메서드

#### 동기 메서드
```python
logger.debug(message: str, **kwargs: Any) -> None
logger.info(message: str, **kwargs: Any) -> None
logger.warning(message: str, **kwargs: Any) -> None
logger.error(message: str, **kwargs: Any) -> None
logger.critical(message: str, **kwargs: Any) -> None
```

#### 비동기 메서드
```python
await logger.debug_async(message: str, **kwargs: Any) -> ResultAsync[None, str]
await logger.info_async(message: str, **kwargs: Any) -> ResultAsync[None, str]
await logger.warning_async(message: str, **kwargs: Any) -> ResultAsync[None, str]
await logger.error_async(message: str, **kwargs: Any) -> ResultAsync[None, str]
await logger.critical_async(message: str, **kwargs: Any) -> ResultAsync[None, str]
```

### 3. 특수 메서드

#### log_operation
작업의 시작/완료/실패를 로깅합니다.

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `operation` | `str` | - | 작업 이름 |
| `status` | `str` | `"started"` | 작업 상태 |
| `**metadata` | `Any` | - | 추가 메타데이터 |

```python
# 작업 시작
logger.log_operation("file_upload", "started", 
                    file_name="test.pdf", 
                    size_mb=2.5)

# 작업 완료
logger.log_operation("file_upload", "completed", 
                    file_name="test.pdf",
                    duration_ms=1250)

# 작업 실패
logger.log_operation("file_upload", "failed",
                    file_name="test.pdf",
                    error="Size limit exceeded")
```

#### log_performance
성능 메트릭을 로깅합니다.

| 파라미터 | 타입 | 단위 | 설명 |
|---------|------|------|------|
| `operation` | `str` | - | 측정 대상 작업 |
| `duration_ms` | `float` | 밀리초 | 실행 시간 |
| `**metadata` | `Any` | - | 추가 성능 지표 |

```python
logger.log_performance(
    "database_query",
    duration_ms=45.2,
    query_type="SELECT",
    rows_returned=100,
    cache_hit=True
)
```

#### log_error_with_context
에러와 디버깅 컨텍스트를 함께 로깅합니다.

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `error` | `Exception` | 발생한 예외 |
| `operation` | `str` | 에러 발생 작업 |
| `**context` | `Any` | 디버깅 컨텍스트 |

```python
try:
    result = process_file(file_path)
except Exception as e:
    logger.log_error_with_context(
        e, 
        "file_processing",
        file_path=file_path,
        user_id=user_id,
        request_id=request_id
    )
```

### 4. 컨텍스트 관리

#### with_context
새로운 컨텍스트를 추가한 로거를 생성합니다.

```python
# 기본 로거
logger = get_logger(__name__)

# 요청별 로거
request_logger = logger.with_context(
    request_id="abc-123",
    user_id=456,
    ip_address="192.168.1.1"
)

# 모든 로그에 컨텍스트 포함됨
request_logger.info("Processing request")
```

## 사용 패턴

### 1. 기본 패턴

```python
from src.shared.px_logging import get_logger

class DocumentProcessor:
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def process(self, document):
        self.logger.info("문서 처리 시작", 
                        document_id=document.id,
                        document_type=document.type)
        
        try:
            # 처리 로직
            result = self._do_process(document)
            
            self.logger.info("문서 처리 완료",
                           document_id=document.id,
                           result_count=len(result))
            return result
            
        except Exception as e:
            self.logger.log_error_with_context(
                e, 
                "document_processing",
                document_id=document.id
            )
            raise
```

### 2. 비동기 패턴

```python
class AsyncDocumentProcessor:
    def __init__(self):
        self.logger = get_logger(__name__)
    
    async def process(self, document):
        # 비동기 로깅 (ResultAsync 반환)
        await self.logger.info_async(
            "비동기 처리 시작",
            document_id=document.id
        )
        
        try:
            result = await self._async_process(document)
            
            await self.logger.info_async(
                "비동기 처리 완료",
                document_id=document.id,
                result_count=len(result)
            )
            return result
            
        except Exception as e:
            await self.logger.log_error_with_context_async(
                e,
                "async_processing",
                document_id=document.id
            )
            raise
```

### 3. 성능 측정 패턴

```python
import time

class PerformanceAwareProcessor:
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def process_with_metrics(self, data):
        start_time = time.time()
        
        self.logger.log_operation("data_processing", "started",
                                 data_size=len(data))
        
        try:
            result = self._process(data)
            duration_ms = (time.time() - start_time) * 1000
            
            self.logger.log_performance(
                "data_processing",
                duration_ms=duration_ms,
                input_size=len(data),
                output_size=len(result),
                success=True
            )
            
            self.logger.log_operation("data_processing", "completed")
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            self.logger.log_performance(
                "data_processing",
                duration_ms=duration_ms,
                input_size=len(data),
                success=False,
                error_type=type(e).__name__
            )
            
            self.logger.log_operation("data_processing", "failed",
                                     error=str(e))
            raise
```

### 4. 컨텍스트 전파 패턴

```python
class RequestHandler:
    def __init__(self):
        self.base_logger = get_logger(__name__)
    
    async def handle_request(self, request):
        # 요청별 로거 생성
        logger = self.base_logger.with_context(
            request_id=request.id,
            user_id=request.user_id,
            endpoint=request.endpoint
        )
        
        logger.info("요청 처리 시작")
        
        # 다른 서비스에 로거 전달
        processor = DocumentProcessor(logger)
        result = await processor.process(request.document)
        
        logger.info("요청 처리 완료", 
                   result_count=len(result))
        return result

class DocumentProcessor:
    def __init__(self, logger):
        # 전달받은 로거 사용 (컨텍스트 유지)
        self.logger = logger
    
    async def process(self, document):
        self.logger.debug("문서 처리 중",
                         document_type=document.type)
        # 처리 로직...
```

## 마이그레이션 가이드

### print → logger 변환

#### ❌ 이전 (print 사용)
```python
print(f"[DEBUG] Processing file: {file_name}")
print(f"[ERROR] Failed to process: {error}")
print(f"[INFO] Completed in {duration}ms")
```

#### ✅ 현재 (logger 사용)
```python
logger.debug("Processing file", file_name=file_name)
logger.error("Failed to process", error=error)
logger.info("Completed", duration_ms=duration)
```

### 구조화된 로깅

#### ❌ 이전 (문자열 포맷팅)
```python
logger.info(f"User {user_id} uploaded {file_name} ({file_size} bytes)")
```

#### ✅ 현재 (구조화된 파라미터)
```python
logger.info("File uploaded",
           user_id=user_id,
           file_name=file_name,
           file_size=file_size)
```

### 에러 처리

#### ❌ 이전
```python
try:
    result = process()
except Exception as e:
    print(f"Error: {e}")
    raise
```

#### ✅ 현재
```python
try:
    result = process()
except Exception as e:
    logger.log_error_with_context(
        e,
        "process_operation",
        input_data=data,
        config=config
    )
    raise
```

## 베스트 프랙티스

### 1. 로거 초기화
- 모듈 레벨에서 한 번만 생성
- `__name__`을 사용하여 네임스페이스 자동 설정

```python
# ✅ 좋은 예
logger = get_logger(__name__)

class MyService:
    def __init__(self):
        # 모듈 로거 재사용
        pass

# ❌ 나쁜 예
class MyService:
    def __init__(self):
        # 매번 새 로거 생성 (비효율적)
        self.logger = get_logger(__name__)
```

### 2. 구조화된 데이터
- 문자열 포맷팅 대신 키워드 인자 사용
- 검색과 필터링이 쉬운 구조화된 데이터

```python
# ✅ 좋은 예
logger.info("API 호출",
           method="POST",
           endpoint="/api/users",
           status_code=200,
           duration_ms=125.5)

# ❌ 나쁜 예
logger.info(f"POST /api/users returned 200 in 125.5ms")
```

### 3. 적절한 로그 레벨
- **DEBUG**: 개발/디버깅 정보
- **INFO**: 정상 작동 정보
- **WARNING**: 주의가 필요한 상황
- **ERROR**: 에러 발생 (복구 가능)
- **CRITICAL**: 치명적 에러 (시스템 중단)

```python
logger.debug("캐시 조회", key=cache_key)
logger.info("사용자 로그인", user_id=user_id)
logger.warning("메모리 사용량 높음", usage_percent=85)
logger.error("API 호출 실패", status_code=500)
logger.critical("데이터베이스 연결 실패")
```

### 4. 민감 정보 제외
- 비밀번호, 토큰, 개인정보 로깅 금지
- 필요시 마스킹 처리

```python
# ✅ 좋은 예
logger.info("사용자 인증",
           user_id=user.id,
           email=mask_email(user.email))

# ❌ 나쁜 예
logger.info("사용자 인증",
           password=user.password,  # 절대 금지!
           credit_card=user.cc_number)  # 절대 금지!
```

### 5. 컨텍스트 활용
- 요청별, 세션별 컨텍스트 추가
- 디버깅과 추적에 유용한 정보 포함

```python
# 요청 처리 시작 시
request_logger = logger.with_context(
    request_id=generate_request_id(),
    session_id=session.id,
    user_id=user.id
)

# 이후 모든 로그에 컨텍스트 자동 포함
request_logger.info("처리 시작")
request_logger.debug("검증 통과")
request_logger.info("처리 완료")
```

## 로그 출력 형식

### JSON 형식 (Production)
```json
{
  "timestamp": "2025-01-08T14:51:29.090602Z",
  "level": "INFO",
  "logger": "term_extraction.controller",
  "message": "File uploaded successfully",
  "module": "term_extraction_controller",
  "function": "process_documents",
  "line": 195,
  "extra_data": {
    "logger_type": "unified",
    "framework_version": "rfs-4.5.1",
    "file_name": "test.pdf",
    "file_size": 1024,
    "user_id": 123,
    "request_id": "abc-123"
  }
}
```

### 텍스트 형식 (Development)
```
2025-01-08 14:51:29 - term_extraction.controller - INFO - File uploaded successfully
```

## 환경별 설정

### Development
```python
setup_logging(
    level=LogLevel.DEBUG,
    enable_json=False  # 읽기 쉬운 텍스트 형식
)
```

### Production
```python
setup_logging(
    level=LogLevel.INFO,
    enable_json=True  # 구조화된 JSON 형식
)
```

## 트러블슈팅

### 1. 로그가 출력되지 않음
- 로그 레벨 확인 (DEBUG 로그는 INFO 레벨에서 출력 안됨)
- 로거 초기화 확인

### 2. JSON 파싱 에러
- 특수 문자 이스케이프 확인
- ensure_ascii=False 설정 확인

### 3. 성능 이슈
- 과도한 DEBUG 로깅 제거
- 큰 객체 로깅 자제
- 비동기 로깅 고려

## 참고 자료

- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [RFS Framework Documentation](https://rfs-framework.readthedocs.io/)
- [Structured Logging Best Practices](https://www.structlog.org/)