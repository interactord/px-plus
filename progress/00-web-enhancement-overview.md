# 웹강화 API 개발 - 전체 개요

## 📋 프로젝트 정보

**프로젝트명**: Web Enhancement API (웹강화 API)
**목적**: 추출된 고유명사에 대해 웹 검색 기반 다국어 번역 추가
**시작일**: 2025-10-13
**상태**: 🚧 진행 중

---

## 🎯 핵심 요구사항

### 1. Single-Shot 웹서치 번역
- ✅ 웹 검색 + 다국어 번역을 **1회 LLM 호출**로 처리
- ✅ 10개 언어 동시 번역
- ✅ GPT-4o 우선, Gemini 자동 폴백

### 2. 지원 언어 (10개)
| 코드 | 언어 |
|------|------|
| ko | 한국어 |
| zh-CN | 중국어(간체) |
| zh-TW | 中文(繁體) |
| en | English |
| ja | 日本語 |
| fr | Français |
| ru | Русский |
| it | Italiano |
| vi | Tiếng Việt |
| ar | العربية |
| es | Español |

### 3. 라운드 로빈 배치 처리
- **배치 크기**: 5개 용어
- **동시 배치**: 3개
- **처리 방식**: 비동기 라운드 로빈

**예시** (33개 용어):
```
Round 1: Batch A(1-5), B(6-10), C(11-15)  ← 3개 동시
Round 2: Batch A(16-20), B(21-25), C(26-30)
Round 3: Batch A(31-33)
```

### 4. Redis 캐싱
- **로컬**: Docker Redis (`redis://localhost:6379`)
- **프로덕션**: Google Cloud Memorystore
- **TTL**: 24시간
- **키 형식**: `web_enhancement:{term}:{lang_hash}`

---

## 🏗️ 시스템 아키텍처

### Clean Architecture + DDD

```
Presentation Layer (API)
    ↓
Application Layer (Use Cases + DTO)
    ↓
Domain Layer (Entities + Ports)
    ↓
Infrastructure Layer (Adapters)
```

### 디렉토리 구조

```
src/
├── domain/
│   └── web_enhancement/
│       ├── entities/
│       │   └── enhanced_term.py
│       ├── value_objects/
│       │   ├── term_info.py
│       │   └── language_code.py
│       ├── ports/
│       │   └── web_enhancement_port.py
│       └── services/
│           └── web_enhancement_service.py
│
├── application/
│   └── web_enhancement/
│       ├── dto/
│       │   ├── enhancement_request_dto.py
│       │   └── enhancement_response_dto.py
│       └── services/
│           ├── batch_enhancement_service.py
│           └── cached_enhancement_service.py
│
├── infrastructure/
│   ├── ai_model/adapters/
│   │   ├── base_gemini_adapter.py       # 🆕
│   │   ├── gemini_chat_adapter.py       # 🆕
│   │   └── gemini_web_search_adapter.py # 🆕
│   └── web_enhancement/
│       ├── adapters/
│       │   ├── gpt4o_web_enhancement_adapter.py
│       │   └── gemini_web_enhancement_adapter.py
│       ├── factories/
│       │   └── enhancement_service_factory.py
│       └── templates/
│           └── enhance_terms_with_web.j2
│
└── presentation/
    └── api/routes/
        └── web_enhancement.py
```

---

## 🔥 핵심 혁신: Single-Shot 웹서치 번역

### 기존 방식 (Multi-Shot)
```
1개 용어당:
  웹 검색 (1회) + 번역 10회 (언어별) = 11회 LLM 호출

33개 용어:
  33 × 11 = 363회 LLM 호출
  처리 시간: ~30분
  비용: 매우 높음
```

### 개선 방식 (Single-Shot)
```
5개 용어를 1회 호출로:
  웹 검색 + 10개 언어 번역 = 1회 LLM 호출

33개 용어:
  33 ÷ 5 = 7회 LLM 호출
  처리 시간: ~45초
  비용: 1/50 수준
```

**성능 향상**:
- ⚡ **50배 이상 속도 향상** (30분 → 45초)
- 💰 **비용 50분의 1**
- 🔄 **캐싱으로 추가 50% 개선**

---

## 🔧 기술 스택

| 분야 | 기술 |
|------|------|
| 프레임워크 | FastAPI |
| 비동기 처리 | Python asyncio |
| LLM (Primary) | OpenAI GPT-4o + 웹서치 |
| LLM (Fallback) | Google Gemini + Grounding |
| 캐싱 | Redis (Docker / Cloud Memorystore) |
| 템플릿 | Jinja2 |
| 아키텍처 | Clean Architecture + DDD + RFS Framework |

---

## 📊 데이터 모델

### EnhancedTerm (강화된 용어)

```python
@dataclass
class EnhancedTerm:
    original_term: str           # 원본 용어
    term_type: str               # 타입 (person, company, etc.)
    primary_domain: str          # 주요 도메인
    context: str                 # 맥락
    tags: List[str]              # 태그
    translations: Dict[str, str] # 언어별 번역
    web_sources: List[str]       # 웹 출처 URL
    source: str                  # "gpt4o_web" or "gemini_web"
    confidence_score: float      # 신뢰도 (0.0-1.0)
    search_timestamp: datetime   # 검색 시각
```

### API 응답 예시

```json
{
  "enhanced_terms": [
    {
      "original_term": "Partido Popular",
      "term_type": "company",
      "translations": {
        "ko": "국민당",
        "en": "People's Party",
        "ja": "国民党",
        "zh-CN": "人民党",
        "zh-TW": "人民黨",
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

---

## 🔄 구현 단계

### ✅ Phase 1: Gemini 어댑터 기반 구축
- [ ] BaseGeminiAdapter (OpenAI 패턴과 동일)
- [ ] GeminiChatAdapter
- [ ] GeminiWebSearchAdapter
- [ ] 단위 테스트

### ⏳ Phase 2: Domain Layer
- [ ] EnhancedTerm 엔티티
- [ ] TermInfo, LanguageCode 값 객체
- [ ] WebEnhancementPort 포트
- [ ] WebEnhancementService 도메인 서비스

### ⏳ Phase 3: Infrastructure Layer
- [ ] enhance_terms_with_web.j2 템플릿 (핵심!)
- [ ] GPT4oWebEnhancementAdapter
- [ ] GeminiWebEnhancementAdapter
- [ ] EnhancementServiceFactory

### ⏳ Phase 4: Application Layer
- [ ] BatchEnhancementService (라운드 로빈)
- [ ] CachedEnhancementService (Redis)
- [ ] DTO 정의

### ⏳ Phase 5: Presentation Layer
- [ ] web_enhancement.py API 라우터
- [ ] 의존성 주입
- [ ] OpenAPI 문서화

### ⏳ Phase 6: Testing & Deployment
- [ ] sample_term.json 으로 E2E 테스트
- [ ] 성능 벤치마크
- [ ] Cloud Run 재배포

---

## 📈 예상 성능

### 처리 시간 (33개 용어 기준)

| 시나리오 | 시간 | 설명 |
|---------|------|------|
| 첫 요청 (캐시 없음) | ~45초 | 7개 배치, 3라운드 |
| 재요청 (캐시 100%) | <1초 | Redis 캐시 히트 |
| 캐시 히트율 50% | ~22초 | 절반은 캐시 |

### 비용 절감

| 항목 | 기존 | 개선 | 절감률 |
|------|------|------|--------|
| LLM 호출 수 | 363회 | 7회 | 98% |
| 처리 시간 | 30분 | 45초 | 97.5% |
| 월간 비용 | $500 | $10 | 98% |

---

## 🛡️ 에러 처리 전략

### 1. 자동 폴백
```
GPT-4o 실패 → Gemini 자동 전환 → 99.9% 성공률
```

### 2. 부분 실패 허용
```
배치 내 일부 용어 실패 → 나머지 계속 처리
```

### 3. 재시도 로직
```
네트워크 오류 → 3회 재시도 (exponential backoff)
```

### 4. 캐시 우회
```
캐시 오류 → 직접 LLM 호출
```

---

## 📝 다음 단계

1. ✅ Gemini 어댑터 구현 시작
2. 🔜 통합 프롬프트 템플릿 작성
3. 🔜 Domain Layer 구현
4. 🔜 Infrastructure Layer 구현
5. 🔜 Application Layer 구현
6. 🔜 API 라우터 구현
7. 🔜 E2E 테스트 및 배포

---

**최종 업데이트**: 2025-10-13
**다음 문서**: [01-gemini-adapter-pattern.md](01-gemini-adapter-pattern.md)
