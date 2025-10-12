# OpenAI 모델 추상화 아키텍처 설계

## 📋 문서 정보

- **작성일**: 2025-01-10
- **버전**: 1.0.0
- **상태**: ✅ 완료

## 🎯 설계 목표

OpenAI의 Reasoning 모델과 Chat Completion 모델을 범용적으로 사용할 수 있는 추상화 레이어를 헥사고날 아키텍처 기반으로 구현합니다.

### 핵심 요구사항

1. **헥사고날 아키텍처 준수**: Domain-Application-Infrastructure 레이어 분리
2. **단일 책임 원칙**: 각 컴포넌트가 하나의 책임만 가짐
3. **RFS Framework 통합**: Result 패턴, HOF, Guard, Registry 활용
4. **Jinja2 템플릿**: 프롬프트 템플릿 관리
5. **REST API 전용**: SSE 스트리밍 미사용

## 🏗️ 헥사고날 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                      외부 세계 (External)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  FastAPI     │  │  Jinja2      │  │  OpenAI      │      │
│  │  Endpoint    │  │  Templates   │  │  REST API    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│              Infrastructure Layer (어댑터)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Primary Adapters (Inbound)                          │   │
│  │  • FastAPIController (HTTP 요청 → DTO 변환)          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Secondary Adapters (Outbound)                       │   │
│  │  • OpenAIReasoningAdapter  (ModelPort 구현)          │   │
│  │  • OpenAIChatAdapter       (ModelPort 구현)          │   │
│  │  • Jinja2TemplateAdapter   (TemplatePort 구현)       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Factory                                              │   │
│  │  • ModelAdapterFactory (어댑터 생성 및 Registry 관리) │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              Application Layer (유스케이스)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Services                                             │   │
│  │  • ModelExecutionService                              │   │
│  │    - execute_with_template()                          │   │
│  │    - execute_direct()                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  DTO (Data Transfer Objects)                          │   │
│  │  • ModelRequestDTO                                    │   │
│  │  • ModelResponseDTO                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                  Domain Layer (핵심 비즈니스)                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Entities (비즈니스 엔티티)                            │   │
│  │  • ModelRequest  (모델 요청 엔티티)                   │   │
│  │  • ModelResponse (모델 응답 엔티티)                   │   │
│  │  • ModelConfig   (모델 설정 엔티티)                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Value Objects (불변 값 객체)                          │   │
│  │  • ModelType (REASONING, CHAT)                        │   │
│  │  • Message   (role, content)                          │   │
│  │  • TemplateContext (템플릿 변수)                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Ports (인터페이스)                                    │   │
│  │  • ModelPort     (모델 실행 포트)                     │   │
│  │  • TemplatePort  (템플릿 렌더링 포트)                 │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 📦 레이어별 책임

### 1. Domain Layer (핵심 비즈니스 로직)

**책임**: 비즈니스 규칙과 도메인 모델 정의

**컴포넌트**:
- **Entities**: 비즈니스 개념을 표현하는 불변 객체
  - `ModelRequest`: 모델 실행 요청 정보
  - `ModelResponse`: 모델 실행 결과
  - `ModelConfig`: 모델 설정 (temperature, max_tokens 등)

- **Value Objects**: 식별자 없는 불변 값
  - `ModelType`: 모델 타입 열거형 (REASONING, CHAT)
  - `Message`: 대화 메시지 (role, content)
  - `TemplateContext`: 템플릿 렌더링 컨텍스트

- **Ports** (인터페이스): 외부 의존성 추상화
  - `ModelPort`: 모델 실행 추상화
  - `TemplatePort`: 템플릿 렌더링 추상화

**특징**:
- ✅ 외부 의존성 없음 (순수 Python + RFS Framework만 사용)
- ✅ 모든 메서드는 `Result[T, E]` 반환
- ✅ 불변성 유지
- ✅ 타입 힌트 완전 적용

### 2. Application Layer (유스케이스)

**책임**: 비즈니스 유스케이스 구현 및 오케스트레이션

**컴포넌트**:
- **Services**: 유스케이스 구현
  - `ModelExecutionService`: 모델 실행 오케스트레이션
    - 템플릿 렌더링 → 모델 실행 → 응답 변환 파이프라인

- **DTO**: 레이어 간 데이터 전송
  - `ModelRequestDTO`: 외부 입력 → Domain 변환
  - `ModelResponseDTO`: Domain → 외부 응답 변환

**특징**:
- ✅ Domain Ports를 통해 Infrastructure와 통신
- ✅ RFS HOF 패턴 활용 (pipe, bind, map)
- ✅ Result 체이닝으로 에러 처리
- ✅ 비즈니스 로직 집중

### 3. Infrastructure Layer (어댑터)

**책임**: 외부 시스템과의 통합 구현

**컴포넌트**:

**Primary Adapters (Inbound)**:
- `FastAPIController`: HTTP 요청 → DTO 변환

**Secondary Adapters (Outbound)**:
- `BaseOpenAIAdapter`: OpenAI REST API 공통 기능
- `OpenAIReasoningAdapter`: Reasoning 모델 특화 구현
- `OpenAIChatAdapter`: Chat Completion 모델 특화 구현
- `Jinja2TemplateAdapter`: Jinja2 템플릿 렌더링 구현

**Factory**:
- `ModelAdapterFactory`:
  - RFS Registry 기반 어댑터 생성
  - 모델 타입에 따른 적절한 어댑터 반환

**특징**:
- ✅ Domain Ports 구현
- ✅ 외부 라이브러리 직접 사용 (openai, jinja2)
- ✅ Result 패턴으로 에러 래핑
- ✅ 설정 주입 (API key, base URL 등)

## 🔄 데이터 흐름

### 템플릿 기반 실행 플로우

```
1. HTTP Request (FastAPI)
   ↓
2. Primary Adapter (Controller)
   → ModelRequestDTO 생성
   ↓
3. Application Service
   → DTO → Domain Entity 변환
   ↓
4. TemplatePort (Jinja2Adapter)
   → 템플릿 렌더링: Result[str, str]
   ↓
5. ModelPort (OpenAI Adapter)
   → REST API 호출: Result[ModelResponse, str]
   ↓
6. Application Service
   → Domain Entity → DTO 변환
   ↓
7. Primary Adapter (Controller)
   → HTTP Response 변환
```

### 직접 실행 플로우

```
1. HTTP Request (FastAPI)
   ↓
2. Primary Adapter (Controller)
   → ModelRequestDTO 생성
   ↓
3. Application Service
   → DTO → Domain Entity 변환
   ↓
4. ModelPort (OpenAI Adapter)
   → REST API 직접 호출: Result[ModelResponse, str]
   ↓
5. Application Service
   → Domain Entity → DTO 변환
   ↓
6. Primary Adapter (Controller)
   → HTTP Response 변환
```

## 🧩 컴포넌트 의존성 맵

```
FastAPI Controller
    ↓ (의존)
ModelExecutionService
    ↓ (의존)
┌─────────────┬─────────────┐
ModelPort     TemplatePort
(인터페이스)   (인터페이스)
    ↑              ↑
    │              │
    │ (구현)       │ (구현)
    │              │
OpenAIAdapter  Jinja2Adapter
    ↑
    │ (생성)
    │
ModelAdapterFactory
    ↑
    │ (사용)
    │
Registry (RFS)
```

## 🔐 RFS Framework 통합

### 1. Result 패턴

모든 비즈니스 로직은 예외를 던지지 않고 `Result[T, E]` 반환:

```python
from rfs.core.result import Result, Success, Failure

def execute_model(request: ModelRequest) -> Result[ModelResponse, str]:
    # 성공 시
    return Success(response)

    # 실패 시
    return Failure("모델 실행 실패: API 에러")
```

### 2. HOF (Higher-Order Functions)

함수 합성과 체이닝으로 파이프라인 구성:

```python
from rfs.hof.core import pipe

execution_pipeline = pipe(
    validate_request,           # 입력 검증
    render_template_if_needed,  # 템플릿 렌더링
    execute_model,              # 모델 실행
    parse_response              # 응답 파싱
)

result = execution_pipeline(request_dto)
```

### 3. Guard 패턴

입력 검증에 Swift 스타일 guard 사용:

```python
from rfs.hof.guard import guard, guard_let, guard_type

def validate_request(request: ModelRequest) -> Result[ModelRequest, str]:
    guard(request.messages, "메시지가 필요합니다")
    guard_type(request.model_type, ModelType, "잘못된 모델 타입")
    return Success(request)
```

### 4. Registry 패턴

어댑터 등록 및 관리:

```python
from rfs.core.registry import Registry

registry = Registry()
registry.register(ModelType.REASONING, OpenAIReasoningAdapter)
registry.register(ModelType.CHAT, OpenAIChatAdapter)
```

## 📂 디렉토리 구조

```
src/
├── domain/
│   └── ai_model/
│       ├── __init__.py
│       ├── entities/
│       │   ├── __init__.py
│       │   ├── model_request.py
│       │   ├── model_response.py
│       │   └── model_config.py
│       ├── value_objects/
│       │   ├── __init__.py
│       │   ├── model_type.py
│       │   ├── message.py
│       │   └── template_context.py
│       └── ports/
│           ├── __init__.py
│           ├── model_port.py
│           └── template_port.py
│
├── application/
│   └── ai_model/
│       ├── __init__.py
│       ├── services/
│       │   ├── __init__.py
│       │   └── model_execution_service.py
│       └── dto/
│           ├── __init__.py
│           ├── model_request_dto.py
│           └── model_response_dto.py
│
├── infrastructure/
│   └── ai_model/
│       ├── __init__.py
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── base_openai_adapter.py
│       │   ├── openai_reasoning_adapter.py
│       │   ├── openai_chat_adapter.py
│       │   └── jinja2_template_adapter.py
│       └── factories/
│           ├── __init__.py
│           └── model_adapter_factory.py
│
└── templates/
    └── ai_model/
        ├── reasoning/
        │   ├── default.j2
        │   └── chain_of_thought.j2
        └── chat/
            ├── default.j2
            └── system_user.j2
```

## ✅ 설계 원칙 준수 체크리스트

- [x] **헥사고날 아키텍처**: Domain-Application-Infrastructure 명확히 분리
- [x] **단일 책임 원칙**: 각 컴포넌트가 하나의 책임만 가짐
- [x] **의존성 역전**: Domain이 Infrastructure에 의존하지 않음 (Ports 사용)
- [x] **RFS Result 패턴**: 모든 메서드가 Result 반환
- [x] **RFS HOF 패턴**: pipe, bind, map 활용
- [x] **RFS Guard 패턴**: 입력 검증
- [x] **RFS Registry**: 어댑터 관리
- [x] **불변성**: Value Objects와 Entities 불변
- [x] **타입 안정성**: 완전한 타입 힌트
- [x] **한글 주석**: 모든 주석 한글 작성

## 📝 다음 단계

1. ✅ **완료**: 아키텍처 설계 문서
2. **다음**: Domain Layer 상세 설계 ([02-domain-layer.md](02-domain-layer.md))
3. **예정**: Application Layer 상세 설계
4. **예정**: Infrastructure Layer 상세 설계
5. **예정**: API 명세 문서

## 📚 참고 문서

- [RFS Framework 필수 규칙](/rules/00-mandatory-rules.md)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
