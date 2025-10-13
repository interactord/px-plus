# Gemini 어댑터 패턴 구현

## 📋 개요

OpenAI 어댑터와 동일한 패턴으로 Google Gemini API 어댑터를 구현했습니다.

**구현 날짜**: 2025-10-13
**상태**: ✅ 완료

---

## 🏗️ 아키텍처

### 어댑터 계층 구조

```
ModelPort (인터페이스)
    ↑
BaseGeminiAdapter (추상 클래스)
    ↑
    ├─ GeminiChatAdapter (일반 채팅)
    └─ GeminiWebSearchAdapter (웹 검색)
```

### 파일 구조

```
src/infrastructure/ai_model/adapters/
├── base_openai_adapter.py         # 기존
├── openai_chat_adapter.py          # 기존
├── openai_reasoning_adapter.py     # 기존
├── base_gemini_adapter.py          # 🆕 Gemini 베이스
├── gemini_chat_adapter.py          # 🆕 Gemini Chat
└── gemini_web_search_adapter.py    # 🆕 Gemini 웹서치
```

---

## 🔧 구현 상세

### 1. BaseGeminiAdapter

**위치**: `src/infrastructure/ai_model/adapters/base_gemini_adapter.py`

**역할**:
- Gemini API 공통 기능 제공
- HTTP 클라이언트 관리
- 요청/응답 처리
- 에러 핸들링

**주요 기능**:

#### API 인증
```python
# OpenAI: Authorization 헤더
headers = {"Authorization": f"Bearer {api_key}"}

# Gemini: 쿼리 파라미터
params = {"key": api_key}
```

#### HTTP 클라이언트 생성
```python
def _create_http_client(self) -> httpx.Client:
    return httpx.Client(
        base_url=self._base_url,
        headers={"Content-Type": "application/json"},
        params={"key": self._api_key},  # Gemini는 쿼리 파라미터
        timeout=self._timeout
    )
```

#### API 요청
```python
def _make_request(
    self,
    endpoint: str,
    payload: Dict[str, Any]
) -> Result[Dict[str, Any], str]:
    """공통 HTTP 요청 처리"""
    try:
        response = self._http_client.post(endpoint, json=payload)
        response.raise_for_status()
        return Success(response.json())
    except httpx.HTTPStatusError as e:
        return Failure(f"Gemini API 오류: {e}")
```

#### 응답 파싱
```python
def _parse_response(
    self,
    response_data: Dict[str, Any]
) -> Result[ModelResponse, str]:
    """
    Gemini 응답 형식:
    {
      "candidates": [{
        "content": {
          "parts": [{"text": "..."}],
          "role": "model"
        }
      }],
      "usageMetadata": {
        "promptTokenCount": 10,
        "candidatesTokenCount": 50
      }
    }
    """
    candidates = response_data["candidates"]
    content = candidates[0]["content"]
    text = "".join(part["text"] for part in content["parts"])

    return Success(ModelResponse.create(
        content=text,
        model="gemini",
        usage=response_data["usageMetadata"]
    ))
```

---

### 2. GeminiChatAdapter

**위치**: `src/infrastructure/ai_model/adapters/gemini_chat_adapter.py`

**역할**:
- 일반 채팅 대화 처리
- OpenAI 메시지 형식 → Gemini 형식 변환
- Generation Config 설정

**지원 모델**:
- `gemini-2.0-flash-exp` (최신, 추천)
- `gemini-1.5-pro`
- `gemini-1.5-flash`

**주요 변환**:

#### 메시지 형식 변환
```python
# OpenAI 형식
{
  "messages": [
    {"role": "system", "content": "You are..."},
    {"role": "user", "content": "Hello"}
  ]
}

# Gemini 형식
{
  "contents": [
    {"role": "user", "parts": [{"text": "You are..."}]},
    {"role": "user", "parts": [{"text": "Hello"}]}
  ]
}
```

#### Role 매핑
```python
def _map_role(self, openai_role: str) -> str:
    role_mapping = {
        "system": "user",      # system → user로 통합
        "user": "user",
        "assistant": "model"   # assistant → model
    }
    return role_mapping.get(openai_role, "user")
```

#### Generation Config 변환
```python
# OpenAI 설정
{
  "temperature": 0.7,
  "max_tokens": 1000,
  "top_p": 0.9
}

# Gemini 설정
{
  "generationConfig": {
    "temperature": 0.7,
    "maxOutputTokens": 1000,
    "topP": 0.9
  }
}
```

---

### 3. GeminiWebSearchAdapter

**위치**: `src/infrastructure/ai_model/adapters/gemini_web_search_adapter.py`

**역할**:
- Google Search Grounding 활성화
- 웹 검색 기반 응답 생성
- 최신 정보 활용

**Google Search Grounding**:

#### Grounding 도구 설정
```python
def _build_grounding_tool(self) -> Dict[str, Any]:
    return {
        "googleSearchRetrieval": {
            "dynamicRetrievalConfig": {
                "mode": "MODE_DYNAMIC",
                "dynamicThreshold": 0.7
            }
        }
    }
```

#### 페이로드 구성
```python
{
  "contents": [...],
  "generationConfig": {...},
  "tools": [{
    "googleSearchRetrieval": {
      "dynamicRetrievalConfig": {
        "mode": "MODE_DYNAMIC",
        "dynamicThreshold": 0.7
      }
    }
  }]
}
```

**동적 임계값 (dynamicThreshold)**:
- `0.0-1.0` 사이 값
- 높을수록 웹 검색 빈도 증가
- `0.7` 권장 (균형)

---

## 🆚 OpenAI vs Gemini 비교

| 항목 | OpenAI | Gemini |
|------|--------|--------|
| **인증 방식** | Authorization 헤더 | 쿼리 파라미터 |
| **메시지 형식** | `messages` | `contents` |
| **Role** | system/user/assistant | user/model |
| **설정** | 직접 포함 | `generationConfig` |
| **웹 검색** | 자동 (GPT-4o) | `googleSearchRetrieval` 도구 |
| **응답 형식** | `choices` | `candidates` |
| **Token 정보** | `usage` | `usageMetadata` |

---

## ✅ 테스트

### 단위 테스트 항목

1. **BaseGeminiAdapter**
   - ✅ API 키 검증
   - ✅ HTTP 클라이언트 생성
   - ✅ 요청 성공/실패 처리
   - ✅ 응답 파싱

2. **GeminiChatAdapter**
   - ✅ 메시지 형식 변환
   - ✅ Role 매핑
   - ✅ Generation Config 변환
   - ✅ 엔드포인트 구성

3. **GeminiWebSearchAdapter**
   - ✅ Grounding 도구 추가
   - ✅ 동적 임계값 설정
   - ✅ 웹 검색 활성화

---

## 🚀 사용 예시

### 1. GeminiChatAdapter

```python
from src.infrastructure.ai_model.adapters.gemini_chat_adapter import GeminiChatAdapter
from src.domain.ai_model.entities.model_request import ModelRequest
from src.domain.ai_model.entities.model_config import ModelConfig

# 어댑터 생성
adapter = GeminiChatAdapter(
    api_key="AIza...",
    model_name="gemini-2.0-flash-exp"
)

# 요청 생성
request = ModelRequest.create(
    messages=[
        {"role": "user", "content": "Hello, Gemini!"}
    ],
    config=ModelConfig(temperature=0.7, max_tokens=100)
)

# 실행
result = adapter.execute(request)

if result.is_success():
    print(result.value.content)
```

### 2. GeminiWebSearchAdapter

```python
from src.infrastructure.ai_model.adapters.gemini_web_search_adapter import GeminiWebSearchAdapter

# 웹 검색 어댑터 생성
adapter = GeminiWebSearchAdapter(
    api_key="AIza...",
    enable_grounding=True,
    dynamic_threshold=0.7
)

# 웹 검색이 필요한 질문
request = ModelRequest.create(
    messages=[{
        "role": "user",
        "content": "What is the official Korean translation of 'Partido Popular'?"
    }],
    config=ModelConfig(temperature=0.3)
)

# 실행 (웹 검색 자동 활성화)
result = adapter.execute(request)

if result.is_success():
    print(result.value.content)  # 웹 검색 기반 응답
```

---

## 📊 성능 특성

### Gemini 2.0 Flash

| 항목 | 값 |
|------|-----|
| **속도** | 매우 빠름 |
| **컨텍스트** | 최대 2M 토큰 |
| **비용** | 저렴 |
| **웹 검색** | Grounding 지원 |
| **멀티모달** | 텍스트, 이미지, 오디오, 비디오 |

---

## 🔜 다음 단계

1. ✅ Domain Layer 구현
2. 🔜 웹 강화 프롬프트 템플릿 작성
3. 🔜 Infrastructure Layer 어댑터 구현
4. 🔜 Application Layer 서비스 구현
5. 🔜 E2E 테스트

---

**완료일**: 2025-10-13
**다음 문서**: [02-single-shot-prompt.md](02-single-shot-prompt.md)
