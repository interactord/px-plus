# Domain Layer 상세 설계

## 📋 문서 정보

- **작성일**: 2025-01-10
- **버전**: 1.0.0
- **상태**: ✅ 완료

## 🎯 Domain Layer 개요

Domain Layer는 비즈니스 핵심 로직과 규칙을 담당하는 순수 Python 레이어입니다. 외부 의존성 없이 RFS Framework만 사용하여 비즈니스 개념을 표현합니다.

### 핵심 원칙

- ✅ **외부 의존성 제로**: 순수 Python + RFS Framework만 사용
- ✅ **불변성**: 모든 객체는 생성 후 변경 불가
- ✅ **Result 패턴**: 예외 없이 Result로 에러 처리
- ✅ **타입 안정성**: 완전한 타입 힌트
- ✅ **단일 책임**: 각 컴포넌트가 하나의 책임만 가짐

## 📦 컴포넌트 구조

```
domain/ai_model/
├── entities/           # 비즈니스 엔티티
│   ├── model_request.py
│   ├── model_response.py
│   └── model_config.py
├── value_objects/      # 값 객체
│   ├── model_type.py
│   ├── message.py
│   └── template_context.py
└── ports/             # 인터페이스
    ├── model_port.py
    └── template_port.py
```

## 1️⃣ Value Objects (값 객체)

### 1.1 ModelType (모델 타입 열거형)

**책임**: 지원하는 모델 타입을 표현

**파일**: `value_objects/model_type.py`

```python
from enum import Enum
from typing import Literal


class ModelType(str, Enum):
    """
    OpenAI 모델 타입 열거형

    지원 타입:
        - REASONING: 추론 전용 모델 (o1, o3 등)
        - CHAT: 일반 대화 모델 (gpt-4, gpt-3.5-turbo 등)
    """

    REASONING = "reasoning"
    CHAT = "chat"

    @classmethod
    def from_string(cls, value: str) -> "ModelType":
        """
        문자열로부터 ModelType 생성

        Args:
            value: 모델 타입 문자열

        Returns:
            ModelType: 열거형 값

        Raises:
            ValueError: 지원하지 않는 타입인 경우
        """
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(
                f"지원하지 않는 모델 타입: {value}. "
                f"가능한 값: {', '.join([t.value for t in cls])}"
            )

    def is_reasoning(self) -> bool:
        """추론 모델 여부 확인"""
        return self == ModelType.REASONING

    def is_chat(self) -> bool:
        """대화 모델 여부 확인"""
        return self == ModelType.CHAT


# 타입 힌트용 리터럴
ModelTypeLiteral = Literal["reasoning", "chat"]
```

### 1.2 Message (메시지 값 객체)

**책임**: 대화 메시지를 표현

**파일**: `value_objects/message.py`

```python
from dataclasses import dataclass
from typing import Literal

from rfs.core.result import Result, Success, Failure
from rfs.hof.guard import guard


# 메시지 role 타입
MessageRole = Literal["system", "user", "assistant", "developer"]


@dataclass(frozen=True)
class Message:
    """
    대화 메시지 값 객체 (불변)

    Attributes:
        role: 메시지 역할 (system, user, assistant, developer)
        content: 메시지 내용
    """

    role: MessageRole
    content: str

    @classmethod
    def create(cls, role: str, content: str) -> Result["Message", str]:
        """
        Message 생성 (검증 포함)

        Args:
            role: 메시지 역할
            content: 메시지 내용

        Returns:
            Result[Message, str]: 성공 시 Message 객체, 실패 시 에러 메시지
        """
        # role 검증
        valid_roles = {"system", "user", "assistant", "developer"}
        if role not in valid_roles:
            return Failure(
                f"잘못된 메시지 role: {role}. "
                f"가능한 값: {', '.join(valid_roles)}"
            )

        # content 검증
        if not content or not content.strip():
            return Failure("메시지 내용은 비어있을 수 없습니다")

        return Success(cls(role=role, content=content.strip()))  # type: ignore

    @classmethod
    def system(cls, content: str) -> "Message":
        """시스템 메시지 생성"""
        result = cls.create("system", content)
        if result.is_success():
            return result.unwrap()
        raise ValueError(result.unwrap_error())

    @classmethod
    def user(cls, content: str) -> "Message":
        """사용자 메시지 생성"""
        result = cls.create("user", content)
        if result.is_success():
            return result.unwrap()
        raise ValueError(result.unwrap_error())

    @classmethod
    def assistant(cls, content: str) -> "Message":
        """어시스턴트 메시지 생성"""
        result = cls.create("assistant", content)
        if result.is_success():
            return result.unwrap()
        raise ValueError(result.unwrap_error())

    @classmethod
    def developer(cls, content: str) -> "Message":
        """개발자 메시지 생성"""
        result = cls.create("developer", content)
        if result.is_success():
            return result.unwrap()
        raise ValueError(result.unwrap_error())

    def to_dict(self) -> dict:
        """딕셔너리로 변환 (OpenAI API 포맷)"""
        return {
            "role": self.role,
            "content": self.content
        }
```

### 1.3 TemplateContext (템플릿 컨텍스트)

**책임**: 템플릿 렌더링에 필요한 변수를 표현

**파일**: `value_objects/template_context.py`

```python
from dataclasses import dataclass, field
from typing import Any, Dict

from rfs.core.result import Result, Success, Failure


@dataclass(frozen=True)
class TemplateContext:
    """
    템플릿 렌더링 컨텍스트 값 객체 (불변)

    Attributes:
        variables: 템플릿 변수 딕셔너리
    """

    variables: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, variables: Dict[str, Any]) -> Result["TemplateContext", str]:
        """
        TemplateContext 생성 (검증 포함)

        Args:
            variables: 템플릿 변수 딕셔너리

        Returns:
            Result[TemplateContext, str]: 성공 시 컨텍스트 객체, 실패 시 에러 메시지
        """
        if variables is None:
            return Failure("템플릿 변수 딕셔너리는 None일 수 없습니다")

        # 불변 딕셔너리로 복사 (얕은 복사)
        immutable_vars = dict(variables)

        return Success(cls(variables=immutable_vars))

    @classmethod
    def empty(cls) -> "TemplateContext":
        """빈 컨텍스트 생성"""
        return cls(variables={})

    def get(self, key: str, default: Any = None) -> Any:
        """변수 값 가져오기"""
        return self.variables.get(key, default)

    def has(self, key: str) -> bool:
        """변수 존재 여부 확인"""
        return key in self.variables

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return dict(self.variables)

    def merge(self, other: "TemplateContext") -> "TemplateContext":
        """
        다른 컨텍스트와 병합 (불변 연산)

        Args:
            other: 병합할 컨텍스트

        Returns:
            TemplateContext: 병합된 새 컨텍스트
        """
        merged_vars = {**self.variables, **other.variables}
        return TemplateContext(variables=merged_vars)
```

## 2️⃣ Entities (비즈니스 엔티티)

### 2.1 ModelConfig (모델 설정)

**책임**: 모델 실행 설정을 표현

**파일**: `entities/model_config.py`

```python
from dataclasses import dataclass
from typing import Optional

from rfs.core.result import Result, Success, Failure


@dataclass(frozen=True)
class ModelConfig:
    """
    모델 실행 설정 엔티티 (불변)

    Attributes:
        temperature: 응답 다양성 (0.0 ~ 2.0)
        max_tokens: 최대 토큰 수
        top_p: 누적 확률 임계값 (0.0 ~ 1.0)
        frequency_penalty: 빈도 패널티 (-2.0 ~ 2.0)
        presence_penalty: 존재 패널티 (-2.0 ~ 2.0)
    """

    temperature: float = 1.0
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

    @classmethod
    def create(
        cls,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0
    ) -> Result["ModelConfig", str]:
        """
        ModelConfig 생성 (검증 포함)

        Returns:
            Result[ModelConfig, str]: 성공 시 설정 객체, 실패 시 에러 메시지
        """
        # temperature 검증
        if not (0.0 <= temperature <= 2.0):
            return Failure(
                f"temperature는 0.0 ~ 2.0 사이여야 합니다: {temperature}"
            )

        # max_tokens 검증
        if max_tokens is not None and max_tokens <= 0:
            return Failure(
                f"max_tokens는 양수여야 합니다: {max_tokens}"
            )

        # top_p 검증
        if not (0.0 <= top_p <= 1.0):
            return Failure(
                f"top_p는 0.0 ~ 1.0 사이여야 합니다: {top_p}"
            )

        # frequency_penalty 검증
        if not (-2.0 <= frequency_penalty <= 2.0):
            return Failure(
                f"frequency_penalty는 -2.0 ~ 2.0 사이여야 합니다: {frequency_penalty}"
            )

        # presence_penalty 검증
        if not (-2.0 <= presence_penalty <= 2.0):
            return Failure(
                f"presence_penalty는 -2.0 ~ 2.0 사이여야 합니다: {presence_penalty}"
            )

        return Success(cls(
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty
        ))

    @classmethod
    def default(cls) -> "ModelConfig":
        """기본 설정 생성"""
        return cls()

    def to_dict(self) -> dict:
        """딕셔너리로 변환 (OpenAI API 포맷)"""
        config_dict = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty
        }

        if self.max_tokens is not None:
            config_dict["max_tokens"] = self.max_tokens

        return config_dict
```

### 2.2 ModelRequest (모델 요청)

**책임**: 모델 실행 요청 정보를 표현

**파일**: `entities/model_request.py`

```python
from dataclasses import dataclass, field
from typing import List, Optional

from rfs.core.result import Result, Success, Failure
from rfs.hof.guard import guard

from ..value_objects.model_type import ModelType
from ..value_objects.message import Message
from ..value_objects.template_context import TemplateContext
from .model_config import ModelConfig


@dataclass(frozen=True)
class ModelRequest:
    """
    모델 실행 요청 엔티티 (불변)

    Attributes:
        model_type: 모델 타입 (REASONING or CHAT)
        messages: 대화 메시지 리스트
        config: 모델 설정
        template_name: 사용할 템플릿 이름 (선택)
        template_context: 템플릿 컨텍스트 (선택)
    """

    model_type: ModelType
    messages: List[Message]
    config: ModelConfig = field(default_factory=ModelConfig.default)
    template_name: Optional[str] = None
    template_context: Optional[TemplateContext] = None

    @classmethod
    def create(
        cls,
        model_type: ModelType,
        messages: List[Message],
        config: Optional[ModelConfig] = None,
        template_name: Optional[str] = None,
        template_context: Optional[TemplateContext] = None
    ) -> Result["ModelRequest", str]:
        """
        ModelRequest 생성 (검증 포함)

        Args:
            model_type: 모델 타입
            messages: 대화 메시지 리스트
            config: 모델 설정 (선택)
            template_name: 템플릿 이름 (선택)
            template_context: 템플릿 컨텍스트 (선택)

        Returns:
            Result[ModelRequest, str]: 성공 시 요청 객체, 실패 시 에러 메시지
        """
        # messages 검증
        if not messages:
            return Failure("메시지는 최소 1개 이상이어야 합니다")

        # 템플릿 검증
        if template_name and not template_context:
            return Failure("템플릿 이름이 제공되면 템플릿 컨텍스트도 필요합니다")

        # config 기본값 설정
        final_config = config if config is not None else ModelConfig.default()

        return Success(cls(
            model_type=model_type,
            messages=messages,
            config=final_config,
            template_name=template_name,
            template_context=template_context
        ))

    def has_template(self) -> bool:
        """템플릿 사용 여부 확인"""
        return self.template_name is not None

    def message_count(self) -> int:
        """메시지 개수 반환"""
        return len(self.messages)

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "model_type": self.model_type.value,
            "messages": [msg.to_dict() for msg in self.messages],
            "config": self.config.to_dict(),
            "template_name": self.template_name,
            "template_context": (
                self.template_context.to_dict()
                if self.template_context
                else None
            )
        }
```

### 2.3 ModelResponse (모델 응답)

**책임**: 모델 실행 결과를 표현

**파일**: `entities/model_response.py`

```python
from dataclasses import dataclass
from typing import Dict, Optional

from rfs.core.result import Result, Success, Failure


@dataclass(frozen=True)
class ModelResponse:
    """
    모델 실행 응답 엔티티 (불변)

    Attributes:
        content: 생성된 텍스트
        model: 사용된 모델 이름
        usage: 토큰 사용량 정보
        finish_reason: 완료 이유 (stop, length, content_filter 등)
        metadata: 추가 메타데이터
    """

    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    metadata: Dict[str, any] = None

    @classmethod
    def create(
        cls,
        content: str,
        model: str,
        usage: Dict[str, int],
        finish_reason: str,
        metadata: Optional[Dict[str, any]] = None
    ) -> Result["ModelResponse", str]:
        """
        ModelResponse 생성 (검증 포함)

        Args:
            content: 생성된 텍스트
            model: 사용된 모델 이름
            usage: 토큰 사용량 정보
            finish_reason: 완료 이유
            metadata: 추가 메타데이터 (선택)

        Returns:
            Result[ModelResponse, str]: 성공 시 응답 객체, 실패 시 에러 메시지
        """
        # content 검증
        if not content:
            return Failure("응답 내용이 비어있습니다")

        # model 검증
        if not model or not model.strip():
            return Failure("모델 이름이 필요합니다")

        # usage 검증
        if not usage:
            return Failure("토큰 사용량 정보가 필요합니다")

        return Success(cls(
            content=content.strip(),
            model=model.strip(),
            usage=dict(usage),  # 불변 복사
            finish_reason=finish_reason,
            metadata=dict(metadata) if metadata else {}
        ))

    def total_tokens(self) -> int:
        """전체 토큰 사용량 반환"""
        return self.usage.get("total_tokens", 0)

    def prompt_tokens(self) -> int:
        """프롬프트 토큰 사용량 반환"""
        return self.usage.get("prompt_tokens", 0)

    def completion_tokens(self) -> int:
        """완성 토큰 사용량 반환"""
        return self.usage.get("completion_tokens", 0)

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "content": self.content,
            "model": self.model,
            "usage": dict(self.usage),
            "finish_reason": self.finish_reason,
            "metadata": dict(self.metadata) if self.metadata else {}
        }
```

## 3️⃣ Ports (인터페이스)

### 3.1 ModelPort (모델 실행 포트)

**책임**: 모델 실행 인터페이스 정의

**파일**: `ports/model_port.py`

```python
from abc import ABC, abstractmethod

from rfs.core.result import Result

from ..entities.model_request import ModelRequest
from ..entities.model_response import ModelResponse


class ModelPort(ABC):
    """
    모델 실행 포트 인터페이스

    Infrastructure Layer에서 구현해야 하는 추상 인터페이스입니다.
    """

    @abstractmethod
    def execute(self, request: ModelRequest) -> Result[ModelResponse, str]:
        """
        모델 실행

        Args:
            request: 모델 요청 엔티티

        Returns:
            Result[ModelResponse, str]: 성공 시 응답 엔티티, 실패 시 에러 메시지
        """
        pass
```

### 3.2 TemplatePort (템플릿 렌더링 포트)

**책임**: 템플릿 렌더링 인터페이스 정의

**파일**: `ports/template_port.py`

```python
from abc import ABC, abstractmethod

from rfs.core.result import Result

from ..value_objects.template_context import TemplateContext


class TemplatePort(ABC):
    """
    템플릿 렌더링 포트 인터페이스

    Infrastructure Layer에서 구현해야 하는 추상 인터페이스입니다.
    """

    @abstractmethod
    def render(
        self,
        template_name: str,
        context: TemplateContext
    ) -> Result[str, str]:
        """
        템플릿 렌더링

        Args:
            template_name: 템플릿 파일명
            context: 템플릿 컨텍스트

        Returns:
            Result[str, str]: 성공 시 렌더링된 문자열, 실패 시 에러 메시지
        """
        pass
```

## ✅ 설계 원칙 준수 체크리스트

- [x] **불변성**: 모든 엔티티와 값 객체가 `frozen=True`
- [x] **Result 패턴**: 모든 생성 메서드가 `Result[T, str]` 반환
- [x] **타입 안정성**: 완전한 타입 힌트 적용
- [x] **외부 의존성 제로**: RFS Framework 외 의존성 없음
- [x] **단일 책임**: 각 클래스가 하나의 비즈니스 개념만 표현
- [x] **검증 로직**: `create()` 메서드에서 입력 검증 수행
- [x] **한글 주석**: 모든 docstring 한글 작성

## 📝 다음 단계

1. ✅ **완료**: Domain Layer 상세 설계
2. **다음**: Application Layer 상세 설계 ([03-application-layer.md](03-application-layer.md))
3. **예정**: Infrastructure Layer 상세 설계
4. **예정**: API 명세 문서

## 📚 참고 문서

- [아키텍처 설계 문서](01-architecture.md)
- [RFS Framework 필수 규칙](/rules/00-mandatory-rules.md)
