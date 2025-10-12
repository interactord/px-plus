# OpenAI API 명세 문서

## 📋 문서 정보

- **작성일**: 2025-01-10
- **버전**: 1.0.0
- **상태**: ✅ 완료

## 🎯 API 개요

본 문서는 OpenAI REST API 통합에 필요한 명세를 정의합니다. Reasoning 모델과 Chat Completion 모델 두 가지 타입을 지원하며, SSE 스트리밍은 사용하지 않습니다.

### 기본 정보

- **Base URL**: `https://api.openai.com/v1`
- **인증 방식**: Bearer Token (API Key)
- **Content-Type**: `application/json`
- **통신 방식**: REST API (HTTP POST)
- **스트리밍**: 미사용 (stream=false)

## 1️⃣ Chat Completions API

### 엔드포인트

```
POST /chat/completions
```

### 헤더

```http
Authorization: Bearer {API_KEY}
Content-Type: application/json
```

### 요청 본문 (Reasoning 모델)

```json
{
  "model": "o1-preview",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Explain quantum computing in simple terms."
    }
  ],
  "max_tokens": 2000
}
```

**Note**: Reasoning 모델은 `temperature`, `top_p`, `frequency_penalty`, `presence_penalty` 파라미터를 지원하지 않습니다.

### 요청 본문 (Chat 모델)

```json
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Hello! How are you?"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0
}
```

### 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 | Reasoning | Chat |
|---------|------|------|------|-----------|------|
| `model` | string | ✅ | 사용할 모델 이름 | ✅ | ✅ |
| `messages` | array | ✅ | 대화 메시지 배열 | ✅ | ✅ |
| `max_tokens` | integer | ❌ | 최대 생성 토큰 수 | ✅ | ✅ |
| `temperature` | float | ❌ | 응답 다양성 (0.0~2.0) | ❌ | ✅ |
| `top_p` | float | ❌ | 누적 확률 임계값 (0.0~1.0) | ❌ | ✅ |
| `frequency_penalty` | float | ❌ | 빈도 패널티 (-2.0~2.0) | ❌ | ✅ |
| `presence_penalty` | float | ❌ | 존재 패널티 (-2.0~2.0) | ❌ | ✅ |
| `stream` | boolean | ❌ | 스트리밍 사용 여부 | ❌ | ❌ |

**Note**: 본 구현에서는 `stream`을 사용하지 않으며, 항상 `false` 또는 생략합니다.

### Message 객체

```json
{
  "role": "system" | "user" | "assistant" | "developer",
  "content": "메시지 내용"
}
```

**Role 설명**:
- `system`: 시스템 프롬프트 (모델 동작 지시)
- `user`: 사용자 메시지
- `assistant`: 어시스턴트 응답 (대화 이력)
- `developer`: 개발자 메시지 (특수 지시)

### 응답 본문 (성공)

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4o-2024-08-06",
  "system_fingerprint": "fp_44709d6fcb",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "안녕하세요! 저는 잘 지내고 있습니다. 오늘 무엇을 도와드릴까요?"
      },
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 50,
    "total_tokens": 75
  }
}
```

### 응답 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | string | 응답 고유 ID |
| `object` | string | 객체 타입 (항상 "chat.completion") |
| `created` | integer | 생성 시간 (Unix timestamp) |
| `model` | string | 사용된 모델 이름 |
| `system_fingerprint` | string | 시스템 fingerprint |
| `choices` | array | 생성 결과 배열 (보통 1개) |
| `choices[].index` | integer | 선택지 인덱스 |
| `choices[].message` | object | 생성된 메시지 |
| `choices[].message.role` | string | 역할 (항상 "assistant") |
| `choices[].message.content` | string | 생성된 텍스트 |
| `choices[].finish_reason` | string | 완료 이유 |
| `usage` | object | 토큰 사용량 정보 |
| `usage.prompt_tokens` | integer | 프롬프트 토큰 수 |
| `usage.completion_tokens` | integer | 완성 토큰 수 |
| `usage.total_tokens` | integer | 전체 토큰 수 |

### Finish Reason 값

| 값 | 설명 |
|----|------|
| `stop` | 정상 완료 (자연스러운 종료) |
| `length` | 최대 토큰 수 도달 |
| `content_filter` | 콘텐츠 필터에 의해 차단됨 |
| `tool_calls` | 함수 호출 요청 (본 구현에서 미사용) |

### 응답 본문 (에러)

```json
{
  "error": {
    "message": "Incorrect API key provided: sk-proj-****. You can find your API key at https://platform.openai.com/account/api-keys.",
    "type": "invalid_request_error",
    "param": null,
    "code": "invalid_api_key"
  }
}
```

### HTTP 상태 코드

| 코드 | 의미 | 설명 |
|------|------|------|
| 200 | OK | 정상 처리 |
| 400 | Bad Request | 잘못된 요청 (파라미터 오류) |
| 401 | Unauthorized | 인증 실패 (API 키 오류) |
| 403 | Forbidden | 권한 없음 |
| 429 | Too Many Requests | Rate limit 초과 |
| 500 | Internal Server Error | 서버 내부 오류 |
| 503 | Service Unavailable | 서비스 일시 중단 |

## 2️⃣ 지원 모델

### Reasoning 모델

| 모델명 | 설명 | max_tokens | 특징 |
|--------|------|------------|------|
| `o1-preview` | O1 프리뷰 모델 | 128,000 | 고급 추론 능력 |
| `o1-mini` | O1 경량 모델 | 65,536 | 빠른 추론 속도 |

**특징**:
- 복잡한 추론 작업에 최적화
- `temperature` 등 샘플링 파라미터 미지원
- 긴 응답 시간 (보통 30초 이상)

### Chat 모델

| 모델명 | 설명 | max_tokens | 특징 |
|--------|------|------------|------|
| `gpt-4o` | GPT-4 Optimized | 128,000 | 최신 GPT-4 모델 |
| `gpt-4o-mini` | GPT-4 Mini | 128,000 | 빠르고 경제적 |
| `gpt-4-turbo` | GPT-4 Turbo | 128,000 | 고성능 모델 |
| `gpt-3.5-turbo` | GPT-3.5 Turbo | 16,385 | 빠르고 저렴 |

**특징**:
- 일반 대화 및 텍스트 생성에 최적화
- 모든 샘플링 파라미터 지원
- 빠른 응답 시간 (보통 5초 이내)

## 3️⃣ 에러 처리 전략

### 에러 타입별 처리

#### 1. 인증 에러 (401)

```python
# 에러 응답 예시
{
  "error": {
    "message": "Incorrect API key provided",
    "type": "invalid_request_error",
    "code": "invalid_api_key"
  }
}

# 처리 방법
return Failure("API 키가 올바르지 않습니다. 설정을 확인해주세요.")
```

#### 2. Rate Limit 에러 (429)

```python
# 에러 응답 예시
{
  "error": {
    "message": "Rate limit reached for requests",
    "type": "rate_limit_error",
    "code": "rate_limit_exceeded"
  }
}

# 처리 방법
return Failure("API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
```

#### 3. 모델 오버로드 에러 (503)

```python
# 에러 응답 예시
{
  "error": {
    "message": "The server is currently overloaded with other requests",
    "type": "server_error",
    "code": "service_unavailable"
  }
}

# 처리 방법
return Failure("서버가 혼잡합니다. 잠시 후 다시 시도해주세요.")
```

#### 4. 타임아웃 에러

```python
# httpx TimeoutException 발생
# 처리 방법
return Failure("요청 타임아웃 (60초 초과). 네트워크를 확인해주세요.")
```

### 재시도 전략

일부 에러는 재시도로 해결 가능:

| 에러 코드 | 재시도 권장 | 대기 시간 |
|----------|------------|----------|
| 429 | ✅ | 지수 백오프 (1s, 2s, 4s) |
| 500 | ✅ | 1초 |
| 503 | ✅ | 2초 |
| 401 | ❌ | - |
| 400 | ❌ | - |

**Note**: 본 구현에서는 재시도 로직을 포함하지 않습니다. 상위 레이어(Application/Controller)에서 필요 시 구현 권장.

## 4️⃣ 요청/응답 예시

### 예시 1: Reasoning 모델로 수학 문제 풀이

**요청**:
```bash
curl -X POST https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "o1-preview",
    "messages": [
      {
        "role": "user",
        "content": "Solve the equation: 3x + 7 = 22. Show your reasoning step by step."
      }
    ],
    "max_tokens": 1000
  }'
```

**응답**:
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1704067200,
  "model": "o1-preview-2024-09-12",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Let me solve this step by step:\n\n1. Start with: 3x + 7 = 22\n2. Subtract 7 from both sides: 3x = 15\n3. Divide both sides by 3: x = 5\n\nTherefore, x = 5."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 30,
    "completion_tokens": 85,
    "total_tokens": 115
  }
}
```

### 예시 2: Chat 모델로 일반 대화

**요청**:
```bash
curl -X POST https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful assistant that speaks Korean."
      },
      {
        "role": "user",
        "content": "파이썬으로 Hello World를 출력하는 방법을 알려줘."
      }
    ],
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

**응답**:
```json
{
  "id": "chatcmpl-xyz789",
  "object": "chat.completion",
  "created": 1704067800,
  "model": "gpt-4o-2024-08-06",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "파이썬으로 \"Hello World\"를 출력하는 방법은 매우 간단합니다:\n\n```python\nprint(\"Hello World\")\n```\n\n이 코드를 실행하면 터미널에 \"Hello World\"가 출력됩니다."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 45,
    "completion_tokens": 65,
    "total_tokens": 110
  }
}
```

## 5️⃣ 통합 체크리스트

### 필수 구현 사항

- [x] Bearer Token 인증 구현
- [x] POST 요청 헤더 설정
- [x] JSON 요청 본문 직렬화
- [x] JSON 응답 본문 역직렬화
- [x] HTTP 상태 코드 처리
- [x] 에러 응답 파싱
- [x] 타임아웃 설정
- [x] Result 패턴으로 에러 래핑

### 테스트 시나리오

1. **정상 요청 테스트**
   - Reasoning 모델 호출
   - Chat 모델 호출
   - 다양한 파라미터 조합

2. **에러 처리 테스트**
   - 잘못된 API 키
   - 잘못된 모델명
   - 빈 메시지
   - 타임아웃 시뮬레이션

3. **경계값 테스트**
   - max_tokens 경계값
   - temperature 경계값
   - 매우 긴 프롬프트

## 📚 참고 문서

- [OpenAI API Reference](https://platform.openai.com/docs/api-reference/chat)
- [OpenAI Models](https://platform.openai.com/docs/models)
- [OpenAI Error Codes](https://platform.openai.com/docs/guides/error-codes)
- [Rate Limits](https://platform.openai.com/docs/guides/rate-limits)

## 📝 다음 단계

1. ✅ **완료**: 모든 설계 문서 작성 완료
2. **다음**: Domain Layer 구현 시작
3. **예정**: 실제 API 통합 테스트

---

**설계 Phase 1 완료** ✅

모든 설계 문서가 작성되었습니다. 이제 구현 단계로 진행할 수 있습니다.
