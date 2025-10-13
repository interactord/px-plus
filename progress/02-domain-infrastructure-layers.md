# Domain & Infrastructure Layers 구현

## 📋 개요

**구현 날짜**: 2025-10-13  
**상태**: ✅ 완료

Domain Layer와 Infrastructure Layer 구현을 완료했습니다.

---

## 🏗️ Domain Layer (Phase 2)

### 1. Entities

#### EnhancedTerm
**위치**: `src/domain/web_enhancement/entities/enhanced_term.py`

**역할**: 웹 검색으로 강화된 용어 엔티티

**주요 기능**:
```python
@dataclass
class EnhancedTerm:
    original_term: str           # 원본 용어
    term_type: str               # person, company, etc.
    primary_domain: str          # politics, media, etc.
    context: str                 # 맥락 정보
    tags: List[str]              # 태그
    translations: Dict[str, str] # 언어별 번역 (10개)
    web_sources: List[str]       # 웹 출처 URL
    source: str                  # "gpt4o_web" or "gemini_web"
    confidence_score: float      # 신뢰도 (0.0-1.0)
    search_timestamp: datetime   # 검색 시각
```

**주요 메서드**:
- `create()`: 팩토리 메서드 (유효성 검증)
- `add_translation()`: 번역 추가
- `add_web_source()`: 웹 출처 URL 추가
- `is_complete()`: 10개 언어 완성 여부
- `get_completion_rate()`: 번역 완성도 (0.0-1.0)

### 2. Value Objects

#### LanguageCode
**위치**: `src/domain/web_enhancement/value_objects/language_code.py`

**역할**: 언어 코드 값 객체 (불변)

**지원 언어** (10개):
```python
SUPPORTED_LANGUAGES = {
    "ko", "zh-CN", "zh-TW", "en", "ja",
    "fr", "ru", "it", "vi", "ar", "es"
}
```

**편의 상수**:
```python
KOREAN = LanguageCode(code="ko")
ENGLISH = LanguageCode(code="en")
JAPANESE = LanguageCode(code="ja")
# ... 나머지 언어들
```

#### TermInfo
**위치**: `src/domain/web_enhancement/value_objects/term_info.py`

**역할**: 용어 기본 정보 값 객체 (불변)

**구조**:
```python
@dataclass(frozen=True)
class TermInfo:
    term: str                # 용어
    type: str                # 타입 (person, company, etc.)
    primary_domain: str      # 도메인 (politics, etc.)
    context: str             # 맥락
    tags: List[str]          # 태그
```

**주요 메서드**:
- `create()`: 팩토리 메서드 (타입/도메인 검증)
- `from_dict()`: sample_term.json 호환

### 3. Ports

#### WebEnhancementPort
**위치**: `src/domain/web_enhancement/ports/web_enhancement_port.py`

**역할**: LLM 어댑터가 구현해야 할 인터페이스

**메서드**:
```python
@abstractmethod
def enhance_terms(
    term_infos: List[TermInfo],
    target_languages: List[str]
) -> Result[List[EnhancedTerm], str]:
    """Single-shot: 웹검색 + 10개 언어 번역"""
    pass

@abstractmethod
def get_source_name() -> str:
    """LLM 소스 이름 ("gpt4o_web" or "gemini_web")"""
    pass
```

### 4. Services

#### WebEnhancementService
**위치**: `src/domain/web_enhancement/services/web_enhancement_service.py`

**역할**: 웹 강화 도메인 서비스 (폴백 전략)

**핵심 로직**:
```python
def enhance_terms(term_infos, target_languages):
    # 1. Primary 어댑터 시도 (GPT-4o)
    result = primary_adapter.enhance_terms(...)
    
    if result.is_success():
        # 2. 결과 검증
        if self._validate_results(...):
            return result
    
    # 3. 실패 시 Fallback 어댑터 (Gemini)
    return self._try_fallback(...)
```

**검증 항목**:
- 결과 개수 일치
- 필수 번역 존재 (10개 언어)
- 신뢰도 임계값 (≥ 0.5)
- 웹 출처 존재 (≥ 1개)

---

## 🔧 Infrastructure Layer (Phase 3)

### 1. 프롬프트 템플릿

#### enhance_terms_with_web.j2
**위치**: `src/infrastructure/web_enhancement/templates/enhance_terms_with_web.j2`

**역할**: Single-shot 웹강화 프롬프트 템플릿

**핵심 전략**:
```
1. Web Search First
   - 각 용어에 대해 웹 검색 수행
   - 공식 번역 확인
   - 권위 있는 출처 수집

2. Translation Requirements
   - 10개 언어 동시 번역
   - 공식 번역 우선
   - 일관성 유지

3. Source Documentation
   - 2-3개 권위 있는 출처 기록

4. Quality Requirements
   - 완전성: 10개 언어 모두 제공
   - 정확성: 권위 있는 출처 기반
   - 신뢰도: 0.5-1.0 점수
```

**출력 형식**:
```json
{
  "enhanced_terms": [
    {
      "original_term": "string",
      "translations": {
        "ko": "...", "zh-CN": "...", "zh-TW": "...",
        "en": "...", "ja": "...", "fr": "...",
        "ru": "...", "it": "...", "vi": "...",
        "ar": "...", "es": "..."
      },
      "web_sources": ["url1", "url2"],
      "confidence_score": 0.95
    }
  ]
}
```

### 2. Adapters

#### GPT4oWebEnhancementAdapter
**위치**: `src/infrastructure/web_enhancement/adapters/gpt4o_web_enhancement_adapter.py`

**역할**: GPT-4o + 웹서치 어댑터

**특징**:
- GPT-4o 모델 (자동 웹서치)
- Jinja2 템플릿 기반 프롬프트
- JSON 응답 파싱 및 엔티티 변환

**주요 메서드**:
```python
def enhance_terms(term_infos, target_languages):
    # 1. 프롬프트 생성 (템플릿)
    prompt = template_adapter.render(term_infos)
    
    # 2. GPT-4o 호출
    response = openai_adapter.execute(request)
    
    # 3. JSON 파싱 → EnhancedTerm 변환
    return self._parse_response(response.content)
```

#### GeminiWebEnhancementAdapter
**위치**: `src/infrastructure/web_enhancement/adapters/gemini_web_enhancement_adapter.py`

**역할**: Gemini + Google Search Grounding 어댑터

**특징**:
- Gemini 2.0 Flash 모델
- Google Search Grounding (동적 웹 검색)
- 동일한 프롬프트 템플릿 사용

**주요 메서드**:
```python
def enhance_terms(term_infos, target_languages):
    # 1. 프롬프트 생성 (동일 템플릿)
    prompt = template_adapter.render(term_infos)
    
    # 2. Gemini 호출 (Google Search Grounding)
    response = gemini_adapter.execute(request)
    
    # 3. JSON 파싱 → EnhancedTerm 변환
    return self._parse_response(response.content)
```

### 3. Factory

#### EnhancementServiceFactory
**위치**: `src/infrastructure/web_enhancement/factories/enhancement_service_factory.py`

**역할**: 환경 변수 기반 서비스 생성

**주요 메서드**:
```python
@classmethod
def create_service(
    openai_api_key=None,
    google_api_key=None,
    primary="gpt4o",
    fallback="gemini"
) -> Result[WebEnhancementService, str]:
    """
    웹 강화 서비스 생성
    
    환경 변수:
    - OPENAI_API_KEY: OpenAI API 키
    - GOOGLE_API_KEY: Google API 키
    """
    # 1. API 키 가져오기 (환경 변수 or 인자)
    # 2. Primary 어댑터 생성
    # 3. Fallback 어댑터 생성
    # 4. WebEnhancementService 생성
    return Success(service)
```

**편의 메서드**:
```python
create_gpt4o_adapter()   # GPT-4o 어댑터만
create_gemini_adapter()  # Gemini 어댑터만
```

---

## 📊 구현 결과

### 파일 구조
```
src/domain/web_enhancement/
├── entities/
│   ├── __init__.py
│   └── enhanced_term.py
├── value_objects/
│   ├── __init__.py
│   ├── language_code.py
│   └── term_info.py
├── ports/
│   ├── __init__.py
│   └── web_enhancement_port.py
├── services/
│   ├── __init__.py
│   └── web_enhancement_service.py
└── __init__.py

src/infrastructure/web_enhancement/
├── adapters/
│   ├── __init__.py
│   ├── gpt4o_web_enhancement_adapter.py
│   └── gemini_web_enhancement_adapter.py
├── factories/
│   ├── __init__.py
│   └── enhancement_service_factory.py
├── templates/
│   └── enhance_terms_with_web.j2
└── __init__.py
```

### 핵심 기능

✅ **Domain Layer**:
- EnhancedTerm 엔티티 (10개 언어 번역)
- LanguageCode 값 객체 (불변)
- TermInfo 값 객체 (불변)
- WebEnhancementPort 인터페이스
- WebEnhancementService (폴백 전략)

✅ **Infrastructure Layer**:
- Single-shot 프롬프트 템플릿
- GPT4oWebEnhancementAdapter
- GeminiWebEnhancementAdapter
- EnhancementServiceFactory

---

## 🔜 다음 단계

1. ✅ Domain Layer 구현
2. ✅ Infrastructure Layer 구현
3. 🔜 Application Layer 구현
4. 🔜 Presentation Layer 구현
5. 🔜 E2E 테스트 및 배포

---

**완료일**: 2025-10-13  
**다음 문서**: Application Layer 구현 예정
