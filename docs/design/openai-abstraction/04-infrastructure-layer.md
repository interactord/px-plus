# Infrastructure Layer 상세 설계

## 📋 문서 정보

- **작성일**: 2025-01-10
- **버전**: 1.0.0
- **상태**: ✅ 완료

## 🎯 Infrastructure Layer 개요

Infrastructure Layer는 외부 시스템(OpenAI API, Jinja2)과의 통합을 담당하는 레이어입니다. Domain Layer에서 정의한 Ports를 구현하며, 외부 라이브러리를 직접 사용합니다.

### 핵심 원칙

- ✅ **Port 구현**: Domain Ports 인터페이스 구현
- ✅ **외부 의존성 격리**: 외부 라이브러리 사용을 이 레이어에만 제한
- ✅ **Result 래핑**: 외부 에러를 Result 패턴으로 래핑
- ✅ **설정 주입**: API key 등 설정을 생성자로 주입
- ✅ **REST API 전용**: SSE 스트리밍 미사용

## 📦 컴포넌트 구조

```
infrastructure/ai_model/
├── adapters/                    # Port 구현체
│   ├── base_openai_adapter.py  # 공통 기반 클래스
│   ├── openai_reasoning_adapter.py  # Reasoning 모델 어댑터
│   ├── openai_chat_adapter.py       # Chat 모델 어댑터
│   └── jinja2_template_adapter.py   # 템플릿 어댑터
└── factories/
    └── model_adapter_factory.py     # 어댑터 생성 팩토리
```

## 1️⃣ OpenAI Adapters

### 1.1 BaseOpenAIAdapter (공통 기반 클래스)

**책임**: OpenAI REST API 공통 기능 제공

**파일**: `adapters/base_openai_adapter.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx

from rfs.core.result import Result, Success, Failure

from ...domain.ai_model.entities.model_request import ModelRequest
from ...domain.ai_model.entities.model_response import ModelResponse
from ...domain.ai_model.ports.model_port import ModelPort


class BaseOpenAIAdapter(ABC, ModelPort):
    """
    OpenAI API 공통 기능 제공 추상 클래스

    단일책임: REST API 통신 및 공통 에러 처리

    Attributes:
        _api_key: OpenAI API 키
        _base_url: API 베이스 URL
        _timeout: HTTP 요청 타임아웃 (초)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60
    ):
        """
        어댑터 초기화

        Args:
            api_key: OpenAI API 키
            base_url: API 베이스 URL (기본: https://api.openai.com/v1)
            timeout: HTTP 요청 타임아웃 초 (기본: 60초)
        """
        if not api_key or not api_key.strip():
            raise ValueError("API 키가 필요합니다")

        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._http_client = self._create_http_client()

    def _create_http_client(self) -> httpx.Client:
        """HTTP 클라이언트 생성"""
        return httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json"
            },
            timeout=self._timeout
        )

    @abstractmethod
    def execute(self, request: ModelRequest) -> Result[ModelResponse, str]:
        """
        모델 실행 (하위 클래스에서 구현)

        Args:
            request: 모델 요청 엔티티

        Returns:
            Result[ModelResponse, str]: 성공 시 응답 엔티티, 실패 시 에러 메시지
        """
        pass

    @abstractmethod
    def _build_payload(self, request: ModelRequest) -> Dict[str, Any]:
        """
        API 요청 페이로드 구성 (하위 클래스에서 구현)

        Args:
            request: 모델 요청 엔티티

        Returns:
            Dict[str, Any]: API 요청 페이로드
        """
        pass

    def _make_request(
        self,
        endpoint: str,
        payload: Dict[str, Any]
    ) -> Result[Dict[str, Any], str]:
        """
        REST API 요청 실행

        Args:
            endpoint: API 엔드포인트 (예: "/chat/completions")
            payload: 요청 페이로드

        Returns:
            Result[Dict[str, Any], str]: 성공 시 응답 JSON, 실패 시 에러 메시지
        """
        try:
            response = self._http_client.post(endpoint, json=payload)
            response.raise_for_status()
            return Success(response.json())
        except httpx.HTTPStatusError as e:
            error_detail = self._extract_error_detail(e.response)
            return Failure(
                f"HTTP {e.response.status_code} 에러: {error_detail}"
            )
        except httpx.TimeoutException:
            return Failure(
                f"요청 타임아웃 ({self._timeout}초 초과)"
            )
        except httpx.RequestError as e:
            return Failure(f"네트워크 에러: {str(e)}")
        except Exception as e:
            return Failure(f"예기치 않은 에러: {str(e)}")

    @staticmethod
    def _extract_error_detail(response: httpx.Response) -> str:
        """
        에러 응답에서 상세 메시지 추출

        Args:
            response: HTTP 응답

        Returns:
            str: 에러 상세 메시지
        """
        try:
            error_data = response.json()
            if "error" in error_data:
                error_info = error_data["error"]
                if isinstance(error_info, dict):
                    return error_info.get("message", str(error_info))
                return str(error_info)
            return response.text
        except Exception:
            return response.text

    def _parse_response(
        self,
        response_data: Dict[str, Any]
    ) -> Result[ModelResponse, str]:
        """
        API 응답을 ModelResponse로 파싱

        Args:
            response_data: API 응답 JSON

        Returns:
            Result[ModelResponse, str]: 성공 시 응답 엔티티, 실패 시 에러 메시지
        """
        try:
            # choices 검증
            choices = response_data.get("choices", [])
            if not choices:
                return Failure("응답에 choices가 없습니다")

            first_choice = choices[0]

            # message 추출
            message = first_choice.get("message", {})
            content = message.get("content", "")

            if not content:
                return Failure("응답 내용이 비어있습니다")

            # 사용량 정보 추출
            usage = response_data.get("usage", {})

            # 모델 정보
            model = response_data.get("model", "unknown")

            # 완료 이유
            finish_reason = first_choice.get("finish_reason", "unknown")

            # 메타데이터 (추가 정보)
            metadata = {
                "id": response_data.get("id"),
                "created": response_data.get("created"),
                "system_fingerprint": response_data.get("system_fingerprint")
            }

            # ModelResponse 생성
            return ModelResponse.create(
                content=content,
                model=model,
                usage=usage,
                finish_reason=finish_reason,
                metadata=metadata
            )

        except KeyError as e:
            return Failure(f"응답 파싱 실패 (필수 키 누락): {str(e)}")
        except Exception as e:
            return Failure(f"응답 파싱 실패: {str(e)}")

    def __del__(self):
        """소멸자: HTTP 클라이언트 정리"""
        if hasattr(self, "_http_client"):
            self._http_client.close()
```

### 1.2 OpenAIReasoningAdapter (Reasoning 모델 어댑터)

**책임**: Reasoning 모델 특화 구현

**파일**: `adapters/openai_reasoning_adapter.py`

```python
from typing import Dict, Any

from rfs.core.result import Result

from ...domain.ai_model.entities.model_request import ModelRequest
from ...domain.ai_model.entities.model_response import ModelResponse
from .base_openai_adapter import BaseOpenAIAdapter


class OpenAIReasoningAdapter(BaseOpenAIAdapter):
    """
    OpenAI Reasoning 모델 전용 어댑터

    단일책임: Reasoning 모델(o1, o3 등) API 호출

    Note:
        - Reasoning 모델은 temperature, top_p 등 일부 파라미터를 지원하지 않음
        - 추론 프로세스가 내부적으로 구조화되어 있음
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "o1-preview",
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 120  # Reasoning 모델은 더 긴 타임아웃 필요
    ):
        """
        Reasoning 어댑터 초기화

        Args:
            api_key: OpenAI API 키
            model_name: 모델 이름 (기본: "o1-preview")
            base_url: API 베이스 URL
            timeout: HTTP 타임아웃 (기본: 120초, Reasoning은 시간이 오래 걸림)
        """
        super().__init__(api_key, base_url, timeout)
        self._model_name = model_name

    def execute(self, request: ModelRequest) -> Result[ModelResponse, str]:
        """
        Reasoning 모델 실행

        Args:
            request: 모델 요청 엔티티

        Returns:
            Result[ModelResponse, str]: 성공 시 응답 엔티티, 실패 시 에러 메시지
        """
        # 1. 페이로드 구성
        payload = self._build_payload(request)

        # 2. API 요청
        response_result = self._make_request("/chat/completions", payload)

        if not response_result.is_success():
            return response_result  # 에러 전파

        # 3. 응답 파싱
        response_data = response_result.unwrap()
        return self._parse_response(response_data)

    def _build_payload(self, request: ModelRequest) -> Dict[str, Any]:
        """
        Reasoning 모델용 페이로드 구성

        Args:
            request: 모델 요청 엔티티

        Returns:
            Dict[str, Any]: API 요청 페이로드
        """
        # 기본 페이로드
        payload = {
            "model": self._model_name,
            "messages": [msg.to_dict() for msg in request.messages]
        }

        # Reasoning 모델은 max_tokens만 지원
        if request.config.max_tokens:
            payload["max_tokens"] = request.config.max_tokens

        return payload
```

### 1.3 OpenAIChatAdapter (Chat 모델 어댑터)

**책임**: Chat Completion 모델 특화 구현

**파일**: `adapters/openai_chat_adapter.py`

```python
from typing import Dict, Any

from rfs.core.result import Result

from ...domain.ai_model.entities.model_request import ModelRequest
from ...domain.ai_model.entities.model_response import ModelResponse
from .base_openai_adapter import BaseOpenAIAdapter


class OpenAIChatAdapter(BaseOpenAIAdapter):
    """
    OpenAI Chat Completion 모델 전용 어댑터

    단일책임: Chat 모델(gpt-4, gpt-3.5-turbo 등) API 호출

    Note:
        - Chat 모델은 모든 설정 파라미터 지원
        - temperature, top_p, frequency_penalty 등 완전 제어 가능
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60
    ):
        """
        Chat 어댑터 초기화

        Args:
            api_key: OpenAI API 키
            model_name: 모델 이름 (기본: "gpt-4o")
            base_url: API 베이스 URL
            timeout: HTTP 타임아웃 (기본: 60초)
        """
        super().__init__(api_key, base_url, timeout)
        self._model_name = model_name

    def execute(self, request: ModelRequest) -> Result[ModelResponse, str]:
        """
        Chat 모델 실행

        Args:
            request: 모델 요청 엔티티

        Returns:
            Result[ModelResponse, str]: 성공 시 응답 엔티티, 실패 시 에러 메시지
        """
        # 1. 페이로드 구성
        payload = self._build_payload(request)

        # 2. API 요청
        response_result = self._make_request("/chat/completions", payload)

        if not response_result.is_success():
            return response_result  # 에러 전파

        # 3. 응답 파싱
        response_data = response_result.unwrap()
        return self._parse_response(response_data)

    def _build_payload(self, request: ModelRequest) -> Dict[str, Any]:
        """
        Chat 모델용 페이로드 구성

        Args:
            request: 모델 요청 엔티티

        Returns:
            Dict[str, Any]: API 요청 페이로드
        """
        # 기본 페이로드
        payload = {
            "model": self._model_name,
            "messages": [msg.to_dict() for msg in request.messages]
        }

        # config를 페이로드에 병합
        config_dict = request.config.to_dict()
        payload.update(config_dict)

        return payload
```

## 2️⃣ Jinja2 Template Adapter

### 2.1 Jinja2TemplateAdapter

**책임**: Jinja2 템플릿 렌더링 구현

**파일**: `adapters/jinja2_template_adapter.py`

```python
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateSyntaxError

from rfs.core.result import Result, Success, Failure
from rfs.hof.guard import guard

from ...domain.ai_model.ports.template_port import TemplatePort
from ...domain.ai_model.value_objects.template_context import TemplateContext


class Jinja2TemplateAdapter(TemplatePort):
    """
    Jinja2 템플릿 렌더링 어댑터

    단일책임: Jinja2를 사용한 템플릿 렌더링

    Attributes:
        _env: Jinja2 Environment
        _template_dir: 템플릿 디렉토리 경로
    """

    def __init__(self, template_dir: str):
        """
        어댑터 초기화

        Args:
            template_dir: 템플릿 디렉토리 경로 (절대 경로)

        Raises:
            ValueError: 디렉토리가 존재하지 않는 경우
        """
        template_path = Path(template_dir)

        if not template_path.exists():
            raise ValueError(f"템플릿 디렉토리가 존재하지 않습니다: {template_dir}")

        if not template_path.is_dir():
            raise ValueError(f"경로가 디렉토리가 아닙니다: {template_dir}")

        self._template_dir = str(template_path)
        self._env = self._create_environment()

    def _create_environment(self) -> Environment:
        """
        Jinja2 Environment 생성

        Returns:
            Environment: 설정된 Jinja2 환경
        """
        return Environment(
            loader=FileSystemLoader(self._template_dir),
            autoescape=True,  # XSS 방지
            trim_blocks=True,  # 블록 후 공백 제거
            lstrip_blocks=True  # 블록 앞 공백 제거
        )

    def render(
        self,
        template_name: str,
        context: TemplateContext
    ) -> Result[str, str]:
        """
        템플릿 렌더링

        Args:
            template_name: 템플릿 파일명 (예: "reasoning/default.j2")
            context: 템플릿 컨텍스트

        Returns:
            Result[str, str]: 성공 시 렌더링된 문자열, 실패 시 에러 메시지
        """
        # 입력 검증
        if not template_name or not template_name.strip():
            return Failure("템플릿 이름이 필요합니다")

        if context is None:
            return Failure("템플릿 컨텍스트가 필요합니다")

        try:
            # 템플릿 로드
            template = self._env.get_template(template_name)

            # 렌더링
            rendered = template.render(context.to_dict())

            return Success(rendered.strip())

        except TemplateNotFound:
            return Failure(
                f"템플릿을 찾을 수 없습니다: {template_name} "
                f"(디렉토리: {self._template_dir})"
            )
        except TemplateSyntaxError as e:
            return Failure(
                f"템플릿 문법 에러: {e.message} "
                f"(파일: {e.filename}, 라인: {e.lineno})"
            )
        except Exception as e:
            return Failure(f"템플릿 렌더링 실패: {str(e)}")

    def list_templates(self) -> Result[list[str], str]:
        """
        사용 가능한 템플릿 목록 반환

        Returns:
            Result[list[str], str]: 성공 시 템플릿 파일명 리스트, 실패 시 에러 메시지
        """
        try:
            templates = self._env.list_templates()
            return Success(sorted(templates))
        except Exception as e:
            return Failure(f"템플릿 목록 조회 실패: {str(e)}")
```

## 3️⃣ Factory Pattern

### 3.1 ModelAdapterFactory

**책임**: 모델 타입에 따라 적절한 어댑터 생성

**파일**: `factories/model_adapter_factory.py`

```python
from typing import Dict, Callable

from rfs.core.registry import Registry
from rfs.core.result import Result, Success, Failure
from rfs.hof.guard import guard_type

from ...domain.ai_model.value_objects.model_type import ModelType
from ...domain.ai_model.ports.model_port import ModelPort

from ..adapters.openai_reasoning_adapter import OpenAIReasoningAdapter
from ..adapters.openai_chat_adapter import OpenAIChatAdapter


class AdapterConfig:
    """
    어댑터 설정

    Attributes:
        api_key: OpenAI API 키
        model_name: 모델 이름 (선택)
        base_url: API 베이스 URL (선택)
        timeout: HTTP 타임아웃 초 (선택)
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self.timeout = timeout


class ModelAdapterFactory:
    """
    모델 어댑터 생성 팩토리

    단일책임: 모델 타입에 맞는 어댑터 인스턴스 생성 및 관리

    RFS Registry 패턴을 사용하여 어댑터 등록 및 조회를 수행합니다.
    """

    def __init__(self):
        """팩토리 초기화 및 어댑터 등록"""
        self._registry = Registry()
        self._register_adapters()

    def _register_adapters(self):
        """어댑터 팩토리 함수 등록"""
        self._registry.register(
            ModelType.REASONING,
            self._create_reasoning_adapter
        )
        self._registry.register(
            ModelType.CHAT,
            self._create_chat_adapter
        )

    @staticmethod
    def _create_reasoning_adapter(config: AdapterConfig) -> ModelPort:
        """
        Reasoning 어댑터 생성

        Args:
            config: 어댑터 설정

        Returns:
            ModelPort: Reasoning 어댑터 인스턴스
        """
        return OpenAIReasoningAdapter(
            api_key=config.api_key,
            model_name=config.model_name or "o1-preview",
            base_url=config.base_url,
            timeout=config.timeout if config.timeout else 120
        )

    @staticmethod
    def _create_chat_adapter(config: AdapterConfig) -> ModelPort:
        """
        Chat 어댑터 생성

        Args:
            config: 어댑터 설정

        Returns:
            ModelPort: Chat 어댑터 인스턴스
        """
        return OpenAIChatAdapter(
            api_key=config.api_key,
            model_name=config.model_name or "gpt-4o",
            base_url=config.base_url,
            timeout=config.timeout
        )

    def create(
        self,
        model_type: ModelType,
        config: AdapterConfig
    ) -> Result[ModelPort, str]:
        """
        모델 타입에 맞는 어댑터 생성

        Args:
            model_type: 모델 타입
            config: 어댑터 설정

        Returns:
            Result[ModelPort, str]: 성공 시 어댑터 인스턴스, 실패 시 에러 메시지
        """
        # 모델 타입 검증
        if not isinstance(model_type, ModelType):
            return Failure(f"잘못된 모델 타입: {type(model_type)}")

        # API 키 검증
        if not config.api_key or not config.api_key.strip():
            return Failure("API 키가 필요합니다")

        try:
            # Registry에서 팩토리 함수 조회
            factory_fn = self._registry.get(model_type)

            # 어댑터 생성
            adapter = factory_fn(config)

            return Success(adapter)

        except KeyError:
            return Failure(
                f"지원하지 않는 모델 타입: {model_type.value}"
            )
        except Exception as e:
            return Failure(f"어댑터 생성 실패: {str(e)}")

    def supported_types(self) -> list[ModelType]:
        """
        지원하는 모델 타입 목록 반환

        Returns:
            list[ModelType]: 지원하는 모델 타입 리스트
        """
        return list(ModelType)
```

## 🔄 사용 예시

### 어댑터 생성 및 사용

```python
from infrastructure.ai_model.factories.model_adapter_factory import (
    ModelAdapterFactory,
    AdapterConfig
)
from domain.ai_model.value_objects.model_type import ModelType

# 팩토리 생성
factory = ModelAdapterFactory()

# Reasoning 어댑터 생성
reasoning_config = AdapterConfig(
    api_key="sk-...",
    model_name="o1-preview",
    timeout=120
)

reasoning_result = factory.create(ModelType.REASONING, reasoning_config)

if reasoning_result.is_success():
    reasoning_adapter = reasoning_result.unwrap()
    # reasoning_adapter.execute(request) 사용
else:
    print(f"에러: {reasoning_result.unwrap_error()}")

# Chat 어댑터 생성
chat_config = AdapterConfig(
    api_key="sk-...",
    model_name="gpt-4o",
    timeout=60
)

chat_result = factory.create(ModelType.CHAT, chat_config)

if chat_result.is_success():
    chat_adapter = chat_result.unwrap()
    # chat_adapter.execute(request) 사용
```

### 템플릿 어댑터 사용

```python
from infrastructure.ai_model.adapters.jinja2_template_adapter import Jinja2TemplateAdapter
from domain.ai_model.value_objects.template_context import TemplateContext

# 템플릿 어댑터 생성
template_adapter = Jinja2TemplateAdapter(
    template_dir="/path/to/templates/ai_model"
)

# 컨텍스트 생성
context_result = TemplateContext.create({
    "problem": "수학 문제",
    "steps": 5,
    "difficulty": "중급"
})

if context_result.is_success():
    context = context_result.unwrap()

    # 템플릿 렌더링
    render_result = template_adapter.render(
        template_name="reasoning/chain_of_thought.j2",
        context=context
    )

    if render_result.is_success():
        rendered_text = render_result.unwrap()
        print(rendered_text)
    else:
        print(f"렌더링 에러: {render_result.unwrap_error()}")
```

## ✅ 설계 원칙 준수 체크리스트

- [x] **Port 구현**: ModelPort, TemplatePort 인터페이스 구현
- [x] **Result 래핑**: 모든 외부 에러를 Result로 래핑
- [x] **설정 주입**: API key 등 설정을 생성자로 주입
- [x] **단일 책임**: 각 어댑터가 하나의 외부 시스템만 담당
- [x] **공통 기능 추출**: BaseOpenAIAdapter로 중복 제거
- [x] **Factory 패턴**: Registry 기반 어댑터 생성
- [x] **타입 안정성**: 완전한 타입 힌트 적용
- [x] **한글 주석**: 모든 docstring 한글 작성

## 📝 다음 단계

1. ✅ **완료**: Infrastructure Layer 상세 설계
2. **다음**: API 명세 문서 ([05-api-spec.md](05-api-spec.md))
3. **예정**: Domain Layer 구현 시작

## 📚 참고 문서

- [아키텍처 설계 문서](01-architecture.md)
- [Domain Layer 설계](02-domain-layer.md)
- [Application Layer 설계](03-application-layer.md)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
