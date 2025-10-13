# Application & Presentation Layers 구현

## 📋 개요

**구현 날짜**: 2025-10-13  
**상태**: ✅ 완료

Application Layer와 Presentation Layer 구현을 완료했습니다.

---

## 🎯 Application Layer (Phase 4)

### 1. DTO (Data Transfer Objects)

#### EnhancementRequestDTO
**위치**: `src/application/web_enhancement/dto/enhancement_request_dto.py`

**역할**: API 요청 → Domain 엔티티 변환

**구조**:
```python
@dataclass
class EnhancementRequestDTO:
    terms: List[dict]              # 강화할 용어 목록
    target_languages: Optional[List[str]]  # 번역 대상 언어
    use_cache: bool = True         # 캐시 사용 여부
    batch_size: int = 5            # 배치 크기
    concurrent_batches: int = 3    # 동시 배치 수
```

**주요 메서드**:
- `create()`: 팩토리 메서드 (검증)
- `to_term_infos()`: TermInfo 리스트 변환
- `get_target_languages()`: 언어 목록 조회 (기본: 10개)
- `get_total_batches()`: 전체 배치 수 계산

#### EnhancementResponseDTO
**위치**: `src/application/web_enhancement/dto/enhancement_response_dto.py`

**역할**: Domain → API 응답 변환

**구조**:
```python
@dataclass
class EnhancementResponseDTO:
    enhanced_terms: List[EnhancedTermDTO]  # 강화된 용어
    summary: SummaryDTO                     # 처리 요약
    errors: List[str]                       # 에러 (선택)
```

**SummaryDTO**:
```python
@dataclass
class SummaryDTO:
    total_terms: int          # 전체 용어 수
    enhanced_terms: int       # 강화 성공 수
    failed_terms: int         # 강화 실패 수
    cache_hits: int           # 캐시 히트 수
    cache_hit_rate: float     # 캐시 히트율
    total_batches: int        # 전체 배치 수
    fallback_count: int       # Fallback 사용 횟수
    processing_time: float    # 처리 시간 (초)
```

### 2. Services

#### BatchEnhancementService
**위치**: `src/application/web_enhancement/services/batch_enhancement_service.py`

**역할**: 라운드 로빈 방식 배치 처리

**핵심 전략**:
```python
# 33개 용어, 5개 배치, 3 동시
Round 1: Batch A(1-5), B(6-10), C(11-15)  ← 3개 동시
Round 2: Batch D(16-20), E(21-25), F(26-30)
Round 3: Batch G(31-33)

예상 시간: 3 라운드 × 6초 = ~18초 (캐시 없음)
```

**주요 메서드**:
```python
async def enhance_terms_batch(
    term_infos,
    target_languages,
    batch_size=5,
    concurrent_batches=3
) -> Tuple[List[EnhancedTerm], int, float]:
    # 1. 배치 생성
    batches = self._create_batches(term_infos, batch_size)
    
    # 2. 라운드 생성
    rounds = self._create_rounds(batches, concurrent_batches)
    
    # 3. 라운드별 동시 처리
    for round_batches in rounds:
        results = await self._process_round(round_batches, ...)
        enhanced_terms.extend(results)
    
    return enhanced_terms, fallback_count, processing_time
```

**최적화**:
- 비동기 처리 (`asyncio.gather`)
- 라운드 로빈 스케줄링
- Fallback 카운팅

#### CachedEnhancementService
**위치**: `src/application/web_enhancement/services/cached_enhancement_service.py`

**역할**: Redis 캐싱 지원

**캐싱 전략**:
```python
# 키 형식
web_enhancement:{normalized_term}:{lang_hash}

# 예시
web_enhancement:partido_popular:a3f2c1d5

# TTL
24시간 (86400초)
```

**주요 메서드**:
```python
async def enhance_terms_with_cache(
    term_infos,
    target_languages,
    use_cache=True
) -> Tuple[List[EnhancedTerm], int, int, float]:
    # 1. 캐시 조회
    cached_terms = []
    terms_to_process = []
    
    for term_info in term_infos:
        cached = self._get_from_cache(term_info, ...)
        if cached.is_success():
            cached_terms.append(cached.unwrap())
            cache_hits += 1
        else:
            terms_to_process.append(term_info)
    
    # 2. 캐시 미스 → 배치 처리
    if terms_to_process:
        enhanced = await batch_service.enhance_terms_batch(...)
        
        # 3. 캐시 저장
        for term in enhanced:
            self._save_to_cache(term, ...)
    
    # 4. 병합
    return cached_terms + enhanced, cache_hits, ...
```

**유틸리티 메서드**:
- `clear_cache()`: 캐시 삭제
- `get_cache_stats()`: 통계 조회
- `check_connection()`: Redis 연결 확인

---

## 🌐 Presentation Layer (Phase 5)

### API 라우터

**위치**: `src/presentation/api/routes/web_enhancement.py`

**엔드포인트**:

#### 1. POST /api/v1/web-enhancement/enhance
**역할**: 용어 웹 강화

**요청**:
```json
{
  "terms": [
    {
      "term": "Partido Popular",
      "type": "company",
      "primary_domain": "politics",
      "context": "Major Spanish political party",
      "tags": ["#PP", "#Spain"]
    }
  ],
  "target_languages": null,
  "use_cache": true,
  "batch_size": 5,
  "concurrent_batches": 3
}
```

**응답**:
```json
{
  "enhanced_terms": [
    {
      "original_term": "Partido Popular",
      "term_type": "company",
      "primary_domain": "politics",
      "translations": {
        "ko": "국민당",
        "zh-CN": "人民党",
        "zh-TW": "人民黨",
        "en": "People's Party",
        "ja": "国民党",
        "fr": "Parti populaire",
        "ru": "Народная партия",
        "it": "Partito Popolare",
        "vi": "Đảng Nhân dân",
        "ar": "الحزب الشعبي",
        "es": "Partido Popular"
      },
      "web_sources": [
        "https://www.pp.es",
        "https://en.wikipedia.org/wiki/People%27s_Party_(Spain)"
      ],
      "source": "gpt4o_web",
      "confidence_score": 0.96
    }
  ],
  "summary": {
    "total_terms": 33,
    "enhanced_terms": 33,
    "failed_terms": 0,
    "cache_hits": 15,
    "cache_hit_rate": 0.45,
    "total_batches": 7,
    "fallback_count": 0,
    "processing_time": 42.3
  }
}
```

#### 2. GET /api/v1/web-enhancement/cache/stats
**역할**: 캐시 통계 조회

**응답**:
```json
{
  "total_cached_terms": 150,
  "pattern": "web_enhancement:*"
}
```

#### 3. DELETE /api/v1/web-enhancement/cache/clear
**역할**: 캐시 삭제

**응답**:
```json
{
  "message": "캐시가 삭제되었습니다",
  "deleted_keys": 150
}
```

#### 4. GET /api/v1/web-enhancement/health
**역할**: 헬스 체크

**응답**:
```json
{
  "status": "healthy",
  "api": "ok",
  "redis": "connected",
  "redis_error": null
}
```

### 의존성 주입

```python
def get_cached_enhancement_service() -> CachedEnhancementService:
    """
    환경 변수:
    - OPENAI_API_KEY: OpenAI API 키
    - GOOGLE_API_KEY: Google API 키
    - REDIS_URL: Redis 연결 URL (기본: redis://localhost:6379)
    - CACHE_TTL: 캐시 TTL 초 (기본: 86400)
    """
    # 1. 웹 강화 도메인 서비스
    service = EnhancementServiceFactory.create_service()
    
    # 2. 배치 서비스
    batch_service = BatchEnhancementService(service.unwrap())
    
    # 3. 캐시 서비스
    cached_service = CachedEnhancementService(batch_service, ...)
    
    return cached_service
```

### FastAPI 통합

**위치**: `src/main.py`

```python
from .presentation.api.routes.web_enhancement import router as web_enhancement_router

app.include_router(web_enhancement_router)  # 웹 강화 API
```

---

## 📊 구현 결과

### 전체 파일 구조
```
src/
├── domain/web_enhancement/
│   ├── entities/enhanced_term.py
│   ├── value_objects/language_code.py, term_info.py
│   ├── ports/web_enhancement_port.py
│   └── services/web_enhancement_service.py
│
├── infrastructure/web_enhancement/
│   ├── adapters/
│   │   ├── gpt4o_web_enhancement_adapter.py
│   │   └── gemini_web_enhancement_adapter.py
│   ├── factories/enhancement_service_factory.py
│   └── templates/enhance_terms_with_web.j2
│
├── application/web_enhancement/
│   ├── dto/
│   │   ├── enhancement_request_dto.py
│   │   └── enhancement_response_dto.py
│   └── services/
│       ├── batch_enhancement_service.py
│       └── cached_enhancement_service.py
│
└── presentation/api/routes/
    └── web_enhancement.py
```

### 핵심 기능

✅ **Application Layer**:
- EnhancementRequestDTO (검증)
- EnhancementResponseDTO (요약)
- BatchEnhancementService (라운드 로빈)
- CachedEnhancementService (Redis)

✅ **Presentation Layer**:
- POST /api/v1/web-enhancement/enhance
- GET /api/v1/web-enhancement/cache/stats
- DELETE /api/v1/web-enhancement/cache/clear
- GET /api/v1/web-enhancement/health

---

## 🚀 사용 예시

### cURL 예시
```bash
# 1. 웹 강화 요청
curl -X POST "http://localhost:8000/api/v1/web-enhancement/enhance" \
  -H "Content-Type: application/json" \
  -d '{
    "terms": [
      {
        "term": "Partido Popular",
        "type": "company",
        "primary_domain": "politics",
        "context": "Major Spanish political party",
        "tags": ["#PP", "#Spain"]
      }
    ],
    "use_cache": true,
    "batch_size": 5,
    "concurrent_batches": 3
  }'

# 2. 캐시 통계
curl "http://localhost:8000/api/v1/web-enhancement/cache/stats"

# 3. 헬스 체크
curl "http://localhost:8000/api/v1/web-enhancement/health"
```

### Python SDK 예시
```python
import httpx

# 웹 강화 요청
response = httpx.post(
    "http://localhost:8000/api/v1/web-enhancement/enhance",
    json={
        "terms": [
            {
                "term": "Partido Popular",
                "type": "company",
                "primary_domain": "politics",
                "context": "Major Spanish political party",
                "tags": ["#PP", "#Spain"]
            }
        ],
        "use_cache": True,
        "batch_size": 5,
        "concurrent_batches": 3
    }
)

data = response.json()
print(f"처리 시간: {data['summary']['processing_time']}초")
print(f"캐시 히트율: {data['summary']['cache_hit_rate']*100}%")
```

---

## 🔜 다음 단계

1. ✅ Domain Layer
2. ✅ Infrastructure Layer
3. ✅ Application Layer
4. ✅ Presentation Layer
5. 🔜 E2E 테스트 (sample_term.json)
6. 🔜 성능 벤치마크
7. 🔜 Cloud Run 배포

---

**완료일**: 2025-10-13  
**다음 문서**: E2E 테스트 및 배포 가이드
