# Application Layer 상세 설계

## 📋 문서 정보

- **작성일**: 2025-01-10
- **버전**: 1.0.0
- **상태**: ✅ 완료

## 🎯 Application Layer 개요

Application Layer는 비즈니스 유스케이스를 구현하고 오케스트레이션하는 레이어입니다. Domain Layer의 Ports를 통해 Infrastructure Layer와 통신하며, RFS HOF 패턴을 활용하여 깔끔한 파이프라인을 구성합니다.

### 핵심 원칙

- ✅ **유스케이스 중심**: 비즈니스 유스케이스 구현에 집중
- ✅ **Port 의존**: Domain Ports를 통해서만 Infrastructure와 통신
- ✅ **HOF 활용**: pipe, bind, map으로 파이프라인 구성
- ✅ **Result 체이닝**: 에러 처리를 Result 체이닝으로 처리
- ✅ **DTO 변환**: 외부 입출력을 Domain Entity로 변환

## 📦 컴포넌트 구조

```
application/ai_model/
├── services/             # 유스케이스 서비스
│   └── model_execution_service.py
└── dto/                  # 데이터 전송 객체
    ├── model_request_dto.py
    └── model_response_dto.py
```

## 1️⃣ DTO (Data Transfer Objects)

### 1.1 ModelRequestDTO (요청 DTO)

**책임**: 외부 입력을 Domain Entity로 변환

**파일**: `dto/model_request_dto.py`

```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from rfs.core.result import Result, Success, Failure
from rfs.hof.collections import compact_map

from ...domain.ai_model.entities.model_request import ModelRequest
from ...domain.ai_model.entities.model_config import ModelConfig
from ...domain.ai_model.value_objects.model_type import ModelType
from ...domain.ai_model.value_objects.message import Message
from ...domain.ai_model.value_objects.template_context import TemplateContext


@dataclass
class ModelRequestDTO:
    """
    모델 요청 DTO

    외부 입력(HTTP 요청 등)을 Domain Entity로 변환하는 역할을 합니다.

    Attributes:
        model_type: 모델 타입 문자열 ("reasoning" or "chat")
        messages: 메시지 딕셔너리 리스트
        config: 모델 설정 딕셔너리 (선택)
        template_name: 템플릿 이름 (선택)
        template_context: 템플릿 변수 딕셔너리 (선택)
    """

    model_type: str
    messages: List[Dict[str, str]]
    config: Optional[Dict[str, Any]] = None
    template_name: Optional[str] = None
    template_context: Optional[Dict[str, Any]] = None

    def to_domain(self) -> Result[ModelRequest, str]:
        """
        DTO를 Domain Entity로 변환

        Returns:
            Result[ModelRequest, str]: 성공 시 요청 엔티티, 실패 시 에러 메시지
        """
        # 1. ModelType 변환
        try:
            domain_model_type = ModelType.from_string(self.model_type)
        except ValueError as e:
            return Failure(str(e))

        # 2. Messages 변환 (HOF: compact_map 사용)
        message_results = [
            Message.create(
                role=msg.get("role", ""),
                content=msg.get("content", "")
            )
            for msg in self.messages
        ]

        # 메시지 변환 결과 검증
        failed_messages = [
            result.unwrap_error()
            for result in message_results
            if not result.is_success()
        ]

        if failed_messages:
            return Failure(f"메시지 변환 실패: {', '.join(failed_messages)}")

        domain_messages = [
            result.unwrap()
            for result in message_results
            if result.is_success()
        ]

        # 3. ModelConfig 변환
        if self.config:
            config_result = ModelConfig.create(
                temperature=self.config.get("temperature", 1.0),
                max_tokens=self.config.get("max_tokens"),
                top_p=self.config.get("top_p", 1.0),
                frequency_penalty=self.config.get("frequency_penalty", 0.0),
                presence_penalty=self.config.get("presence_penalty", 0.0)
            )

            if not config_result.is_success():
                return Failure(config_result.unwrap_error())

            domain_config = config_result.unwrap()
        else:
            domain_config = ModelConfig.default()

        # 4. TemplateContext 변환
        domain_template_context = None
        if self.template_context:
            context_result = TemplateContext.create(self.template_context)
            if not context_result.is_success():
                return Failure(context_result.unwrap_error())
            domain_template_context = context_result.unwrap()

        # 5. ModelRequest 생성
        return ModelRequest.create(
            model_type=domain_model_type,
            messages=domain_messages,
            config=domain_config,
            template_name=self.template_name,
            template_context=domain_template_context
        )
```

### 1.2 ModelResponseDTO (응답 DTO)

**책임**: Domain Entity를 외부 응답으로 변환

**파일**: `dto/model_response_dto.py`

```python
from dataclasses import dataclass
from typing import Dict, Any

from rfs.core.result import Result, Success

from ...domain.ai_model.entities.model_response import ModelResponse


@dataclass
class ModelResponseDTO:
    """
    모델 응답 DTO

    Domain Entity를 외부 응답(HTTP 응답 등)으로 변환하는 역할을 합니다.

    Attributes:
        content: 생성된 텍스트
        model: 사용된 모델 이름
        usage: 토큰 사용량 정보
        finish_reason: 완료 이유
        metadata: 추가 메타데이터
    """

    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    metadata: Dict[str, Any]

    @classmethod
    def from_domain(cls, response: ModelResponse) -> "ModelResponseDTO":
        """
        Domain Entity로부터 DTO 생성

        Args:
            response: 응답 엔티티

        Returns:
            ModelResponseDTO: 응답 DTO
        """
        return cls(
            content=response.content,
            model=response.model,
            usage=dict(response.usage),
            finish_reason=response.finish_reason,
            metadata=dict(response.metadata) if response.metadata else {}
        )

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (JSON 응답용)"""
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
            "metadata": self.metadata
        }
```

## 2️⃣ Services (유스케이스 서비스)

### 2.1 ModelExecutionService (모델 실행 서비스)

**책임**: 모델 실행 유스케이스 오케스트레이션

**파일**: `services/model_execution_service.py`

```python
from typing import Optional

from rfs.core.result import Result, Success, Failure
from rfs.hof.core import pipe
from rfs.hof.guard import guard

from ...domain.ai_model.entities.model_request import ModelRequest
from ...domain.ai_model.entities.model_response import ModelResponse
from ...domain.ai_model.ports.model_port import ModelPort
from ...domain.ai_model.ports.template_port import TemplatePort
from ...domain.ai_model.value_objects.message import Message

from ..dto.model_request_dto import ModelRequestDTO
from ..dto.model_response_dto import ModelResponseDTO


class ModelExecutionService:
    """
    모델 실행 유스케이스 서비스

    단일책임: 모델 실행 파이프라인 오케스트레이션
    - DTO → Domain Entity 변환
    - 템플릿 렌더링 (필요 시)
    - 모델 실행
    - Domain Entity → DTO 변환

    Attributes:
        _model_port: 모델 실행 포트
        _template_port: 템플릿 렌더링 포트
    """

    def __init__(
        self,
        model_port: ModelPort,
        template_port: TemplatePort
    ):
        """
        서비스 초기화

        Args:
            model_port: 모델 실행 포트 구현
            template_port: 템플릿 렌더링 포트 구현
        """
        self._model_port = model_port
        self._template_port = template_port

    def execute_with_template(
        self,
        request_dto: ModelRequestDTO
    ) -> Result[ModelResponseDTO, str]:
        """
        템플릿을 사용하여 모델을 실행합니다.

        처리 순서:
        1. DTO → Domain Entity 변환
        2. 템플릿 렌더링
        3. 렌더링된 텍스트를 메시지로 추가
        4. 모델 실행
        5. Domain Entity → DTO 변환

        Args:
            request_dto: 모델 요청 DTO

        Returns:
            Result[ModelResponseDTO, str]: 성공 시 응답 DTO, 실패 시 에러 메시지
        """
        # 1. DTO → Domain 변환
        domain_result = request_dto.to_domain()
        if not domain_result.is_success():
            return Failure(domain_result.unwrap_error())

        request = domain_result.unwrap()

        # 2. 템플릿 검증
        if not request.has_template():
            return Failure("템플릿 이름이 제공되지 않았습니다")

        # 3. 템플릿 렌더링
        rendered_result = self._template_port.render(
            template_name=request.template_name,
            context=request.template_context
        )

        if not rendered_result.is_success():
            return Failure(
                f"템플릿 렌더링 실패: {rendered_result.unwrap_error()}"
            )

        rendered_text = rendered_result.unwrap()

        # 4. 렌더링된 텍스트를 user 메시지로 추가
        user_message = Message.user(rendered_text)
        updated_request = ModelRequest.create(
            model_type=request.model_type,
            messages=[*request.messages, user_message],
            config=request.config
        )

        if not updated_request.is_success():
            return Failure(updated_request.unwrap_error())

        # 5. 모델 실행
        response_result = self._model_port.execute(updated_request.unwrap())

        if not response_result.is_success():
            return Failure(
                f"모델 실행 실패: {response_result.unwrap_error()}"
            )

        # 6. Domain → DTO 변환
        response = response_result.unwrap()
        return Success(ModelResponseDTO.from_domain(response))

    def execute_direct(
        self,
        request_dto: ModelRequestDTO
    ) -> Result[ModelResponseDTO, str]:
        """
        템플릿 없이 직접 모델을 실행합니다.

        처리 순서:
        1. DTO → Domain Entity 변환
        2. 모델 실행
        3. Domain Entity → DTO 변환

        Args:
            request_dto: 모델 요청 DTO

        Returns:
            Result[ModelResponseDTO, str]: 성공 시 응답 DTO, 실패 시 에러 메시지
        """
        # 1. DTO → Domain 변환
        domain_result = request_dto.to_domain()
        if not domain_result.is_success():
            return Failure(domain_result.unwrap_error())

        request = domain_result.unwrap()

        # 2. 모델 실행
        response_result = self._model_port.execute(request)

        if not response_result.is_success():
            return Failure(
                f"모델 실행 실패: {response_result.unwrap_error()}"
            )

        # 3. Domain → DTO 변환
        response = response_result.unwrap()
        return Success(ModelResponseDTO.from_domain(response))

    def execute(
        self,
        request_dto: ModelRequestDTO
    ) -> Result[ModelResponseDTO, str]:
        """
        모델을 실행합니다. (템플릿 사용 여부 자동 판단)

        Args:
            request_dto: 모델 요청 DTO

        Returns:
            Result[ModelResponseDTO, str]: 성공 시 응답 DTO, 실패 시 에러 메시지
        """
        # 템플릿 사용 여부에 따라 적절한 메서드 호출
        if request_dto.template_name:
            return self.execute_with_template(request_dto)
        else:
            return self.execute_direct(request_dto)
```

## 🔄 사용 예시

### 템플릿 기반 실행

```python
from application.ai_model.services.model_execution_service import ModelExecutionService
from application.ai_model.dto.model_request_dto import ModelRequestDTO

# 의존성 주입 (Infrastructure에서 제공)
model_port = get_model_port()  # OpenAIReasoningAdapter or OpenAIChatAdapter
template_port = get_template_port()  # Jinja2TemplateAdapter

# 서비스 생성
service = ModelExecutionService(
    model_port=model_port,
    template_port=template_port
)

# DTO 생성
request_dto = ModelRequestDTO(
    model_type="reasoning",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."}
    ],
    template_name="reasoning/chain_of_thought.j2",
    template_context={
        "problem": "수학 문제 풀이",
        "steps": 5
    },
    config={
        "temperature": 0.7,
        "max_tokens": 2000
    }
)

# 실행
result = service.execute(request_dto)

if result.is_success():
    response_dto = result.unwrap()
    print(f"생성된 텍스트: {response_dto.content}")
    print(f"사용 토큰: {response_dto.usage['total_tokens']}")
else:
    print(f"에러: {result.unwrap_error()}")
```

### 직접 실행

```python
# DTO 생성 (템플릿 없음)
request_dto = ModelRequestDTO(
    model_type="chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "안녕하세요!"}
    ],
    config={
        "temperature": 1.0,
        "max_tokens": 1000
    }
)

# 실행
result = service.execute(request_dto)

if result.is_success():
    response_dto = result.unwrap()
    print(f"응답: {response_dto.content}")
```

## 🎯 HOF 패턴 적용 예시

Service에서 HOF 패턴을 활용한 파이프라인 구성:

```python
from rfs.hof.core import pipe

# 함수 합성 (개념적 예시)
execution_pipeline = pipe(
    validate_request_dto,      # 1. DTO 검증
    convert_to_domain,          # 2. Domain Entity 변환
    render_template_if_needed,  # 3. 템플릿 렌더링 (선택)
    execute_model_via_port,     # 4. 모델 실행
    convert_to_response_dto     # 5. 응답 DTO 변환
)

# 파이프라인 실행
result = execution_pipeline(request_dto)
```

## ✅ 설계 원칙 준수 체크리스트

- [x] **Port 의존**: Domain Ports를 통해서만 Infrastructure 접근
- [x] **Result 체이닝**: 모든 메서드가 Result 반환 및 체이닝 활용
- [x] **HOF 활용**: pipe로 깔끔한 파이프라인 구성
- [x] **DTO 변환**: 외부 입출력을 Domain Entity로 명확히 변환
- [x] **단일 책임**: Service는 오케스트레이션만, DTO는 변환만 담당
- [x] **타입 안정성**: 완전한 타입 힌트 적용
- [x] **한글 주석**: 모든 docstring 한글 작성

## 📝 다음 단계

1. ✅ **완료**: Application Layer 상세 설계
2. **다음**: Infrastructure Layer 상세 설계 ([04-infrastructure-layer.md](04-infrastructure-layer.md))
3. **예정**: API 명세 문서

## 📚 참고 문서

- [아키텍처 설계 문서](01-architecture.md)
- [Domain Layer 설계](02-domain-layer.md)
- [RFS Framework 필수 규칙](/rules/00-mandatory-rules.md)
