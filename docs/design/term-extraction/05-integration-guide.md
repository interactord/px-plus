# 용어 추출 API 통합 가이드

## 개요

이 문서는 용어 추출 API를 기존 FastAPI 애플리케이션에 통합하는 방법을 설명합니다.

## 1. 라우터 등록

### src/main.py 수정

```python
from fastapi import FastAPI
from .presentation.api.routes import term_extraction_router, demo_router

app = FastAPI(
    title="PX-Plus: FastAPI + RFS Framework",
    description="헥사고날 아키텍처 기반 FastAPI 애플리케이션",
    version="0.1.0"
)

# 라우터 등록
app.include_router(router, tags=["greetings"])
app.include_router(term_extraction_router)
app.include_router(demo_router, prefix="/demo")

# 기존 라우터들...
```

### 등록된 엔드포인트

**용어 추출 API**:
- `POST /api/v1/extract-terms/process-documents` - 문서 용어 추출
- `GET /api/v1/extract-terms/health` - 헬스 체크
- `GET /api/v1/extract-terms/cache-stats` - 캐시 통계

**데모 페이지**:
- `GET /demo/` - 데모 페이지 목록
- `GET /demo/term-extraction` - 용어 추출 데모 페이지

## 2. 의존성 주입 설정

### 방법 1: 컨테이너 기반 (권장)

`src/shared/container` 패턴을 사용하는 경우:

```python
# src/presentation/api/routes/term_extraction.py 수정

from ....shared.container import get_model_port, get_template_port

# 기존 placeholder 함수들을 제거하고
# 컨테이너에서 가져온 함수 사용
```

### 방법 2: 직접 생성

컨테이너가 없는 경우, 다음과 같이 직접 생성:

```python
# src/presentation/api/routes/term_extraction.py

from ....infrastructure.ai_model.adapters.openai_chat_adapter import OpenAIChatAdapter
from ....infrastructure.ai_model.adapters.jinja2_template_adapter import Jinja2TemplateAdapter

async def get_model_port() -> ModelPort:
    """AI 모델 포트를 반환합니다."""
    return OpenAIChatAdapter(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o"
    )

async def get_template_port() -> TemplatePort:
    """템플릿 포트를 반환합니다."""
    return Jinja2TemplateAdapter(
        template_dir="src/infrastructure/term_extraction/templates"
    )
```

## 3. 환경 변수 설정

`.env` 파일에 다음 변수 추가:

```bash
# OpenAI API 설정
OPENAI_API_KEY=your-api-key-here

# 템플릿 디렉토리
TEMPLATE_DIR=src/infrastructure/term_extraction/templates

# 병렬 처리 설정 (선택사항)
MAX_PARALLEL_WORKERS=3
```

## 4. 템플릿 파일 배치

템플릿 파일은 Infrastructure Layer에 위치합니다 (헥사고날 아키텍처 준수).

확인:
```bash
ls src/infrastructure/term_extraction/templates/
# extract_terms.j2
# system_analyst.j2
```

## 5. API 사용 예시

### 기본 요청

```bash
curl -X POST "http://localhost:8000/api/v1/extract-terms/process-documents" \
  -H "Content-Type: application/json" \
  -d '{
    "processed_files": [
      {
        "filename": "document.txt",
        "chunks": [
          "홍길동은 조선시대의 전설적인 의적이다. 탐관오리들의 재물을 빼앗아 백성들에게 나누어 주었다.",
          "애플(Apple Inc.)은 미국의 다국적 기술 기업이다. 아이폰, 맥북 등의 제품으로 유명하다."
        ]
      }
    ],
    "use_cache": true,
    "parallel_workers": 3,
    "template_name": "extract_terms.j2"
  }'
```

### 타입 필터링 요청

```bash
curl -X POST "http://localhost:8000/api/v1/extract-terms/process-documents" \
  -H "Content-Type: application/json" \
  -d '{
    "processed_files": [...],
    "type_filter": ["person", "company"],
    "max_entities_per_chunk": 10
  }'
```

### 헬스 체크

```bash
curl "http://localhost:8000/api/v1/extract-terms/health"
```

### 캐시 통계

```bash
curl "http://localhost:8000/api/v1/extract-terms/cache-stats"
```

## 6. 응답 형식

### 성공 응답 (200 OK)

```json
{
  "results": [
    {
      "chunk_index": 0,
      "source_filename": "document.txt",
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
    "total_chunks": 2,
    "processed_chunks": 2,
    "failed_chunks": 0,
    "cache_hits": 0,
    "cache_hit_rate": 0.0,
    "total_entities": 8,
    "total_processing_time": 2.456,
    "average_processing_time": 1.228
  }
}
```

### 오류 응답 (400 Bad Request)

```json
{
  "detail": "청크 배열은 비어있을 수 없습니다"
}
```

### 오류 응답 (500 Internal Server Error)

```json
{
  "detail": "용어 추출 실패: LLM 실행 오류"
}
```

## 7. 성능 최적화

### 캐시 활용

- `use_cache: true`로 설정하면 동일한 청크에 대한 재추출 시 캐시 사용
- 캐시 TTL: 24시간 (기본값)
- 캐시 키: SHA256(청크 내용 + 템플릿명)

### 병렬 처리

- `parallel_workers: 3`으로 설정하면 3개 워커가 동시 처리
- 권장값: 3-5 (너무 높으면 API 레이트 리밋 위험)
- 청크 수가 적으면 자동으로 순차 처리

### 배치 크기

- 한 번에 너무 많은 청크를 보내면 타임아웃 가능
- 권장: 청크 10-50개씩 배치 처리
- 필요 시 클라이언트에서 여러 요청으로 분할

## 8. 모니터링

### 로그 확인

```python
# 로깅 설정 추가 권장
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 서비스에서 로그 남기기
logger.info(f"처리 완료: {len(chunks)}개 청크, {total_entities}개 엔티티")
```

### 메트릭 수집

- 처리 시간: `summary.average_processing_time`
- 캐시 히트율: `summary.cache_hit_rate`
- 성공률: `processed_chunks / total_chunks`
- 엔티티 수: `summary.total_entities`

## 9. 프로덕션 체크리스트

### 필수 구성
- [ ] OpenAI API 키 설정 (`.env`에 `OPENAI_API_KEY`)
- [ ] 템플릿 파일 배치 확인 (`src/infrastructure/term_extraction/templates/`)
- [ ] 의존성 주입 구현 완료 (`get_model_port`, `get_template_port`)
- [ ] 라우터 등록 완료 (`main.py`에 `term_extraction_router`, `demo_router`)
- [ ] 환경 변수 설정 (`.env` 파일)

### 테스트
- [ ] 헬스 체크 통과 (`GET /api/v1/extract-terms/health`)
- [ ] 기본 추출 테스트 (샘플 텍스트)
- [ ] 에러 핸들링 테스트 (잘못된 요청, API 실패)
- [ ] 성능 테스트 (병렬 처리, 10+ 청크)
- [ ] 캐시 동작 확인 (동일 텍스트 재추출)

### 모니터링
- [ ] 로깅 설정 (`LOG_LEVEL=INFO`)
- [ ] 메트릭 수집 (처리 시간, 캐시 히트율)
- [ ] API 문서 확인 (`/docs`, `/redoc`)

### 데모 페이지
- [ ] 데모 라우터 등록 (`/demo/term-extraction`)
- [ ] 데모 인덱스 페이지 (`/demo/`)
- [ ] 데모 페이지 동작 확인 (브라우저 테스트)

## 10. 문제 해결

### "NotImplementedError: ModelPort 의존성 주입이 필요합니다"

→ `get_model_port()` 함수를 실제 구현으로 교체하세요.

### "TemplateNotFoundError"

→ 템플릿 파일이 올바른 경로에 있는지 확인하세요.

### "OpenAI API Error"

→ API 키가 올바른지, 레이트 리밋을 초과하지 않았는지 확인하세요.

### 캐시가 작동하지 않음

→ `use_cache: true`로 설정했는지, 동일한 청크 내용인지 확인하세요.
