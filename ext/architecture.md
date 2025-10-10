# 마이크로 헥사고날 아키텍처 가이드

## 목차
1. [개요](#개요)
2. [아키텍처 원칙](#아키텍처-원칙)
3. [바운디드 컨텍스트 구조](#바운디드-컨텍스트-구조)
4. [레이어별 상세 설명](#레이어별-상세-설명)
5. [비동기 모나드 패턴](#비동기-모나드-패턴)
6. [단일책임원칙 적용](#단일책임원칙-적용)
7. [구현 예제](#구현-예제)
8. [새로운 컨텍스트 추가 가이드](#새로운-컨텍스트-추가-가이드)
9. [개발 워크플로우](#개발-워크플로우)
10. [모범 사례와 안티패턴](#모범-사례와-안티패턴)

## 개요

기존 복잡한 모놀리식 엔터프라이즈 구조에서 **마이크로 헥사고날 아키텍처**로 마이그레이션하여 다음과 같은 이점을 제공합니다:

### 🎯 핵심 특징
- **바운디드 컨텍스트**: 도메인별 독립적인 모듈화
- **헥사고날 아키텍처 유지**: 각 컨텍스트 내 완전한 헥사고날 구조
- **점진적 확장**: 새로운 컨텍스트를 쉽게 추가 가능
- **RFS Framework 4.6.5 통합**: ResultAsync, Flux, Saga, HOF 패턴
- **단일책임원칙**: 컨테이너별 명확한 책임 분리
- **의존성 주입**: MasterApplicationContainer를 통한 통합 관리

### 🔄 마이그레이션 전후 비교

**마이그레이션 전 (모놀리식 구조)**:
```
src/
├── api/                    # 거대한 API 레이어
├── application/            # 복잡한 애플리케이션 서비스
├── domain/                 # 혼재된 도메인 로직
├── infrastructure/         # 거대한 인프라 레이어
├── shared/                 # 공유 모듈
└── config/                 # 복잡한 설정 팩토리
```

**마이그레이션 후 (마이크로 헥사고날 + RFS 4.6.5)**:
```
src/
├── shared/                     # 공유 커널
│   ├── container/             # 단일책임 컨테이너 팩토리
│   ├── kernel/                # ResultAsync, Result 패턴
│   ├── middleware/            # 공통 미들웨어
│   ├── px_logging/            # 로깅 시스템
│   └── infrastructure/        # 공통 인프라 (템플릿, LLM 클라이언트)
│       ├── llm/               # LLM 클라이언트 (OpenAI, Anthropic)
│       └── templates/         # 템플릿 시스템 (Jinja2)
├── application/               # 애플리케이션 팩토리
│   └── factories/             # 앱 생성 팩토리
├── api/                       # 전역 API 라우터
├── health/                    # Health 바운디드 컨텍스트
├── config/                    # Config 바운디드 컨텍스트
├── chat/                      # Chat 바운디드 컨텍스트
├── translation/               # Translation 바운디드 컨텍스트 (신규)
├── term_extraction/           # Term Extraction 바운디드 컨텍스트
├── term_extraction_integration/ # Term Extraction Integration (Saga 패턴)
├── document_processor/        # Document Processor (Flux 패턴)
├── document_extraction/       # Document Extraction 바운디드 컨텍스트 (신규)
├── web_extractor/             # Web Extractor 바운디드 컨텍스트
├── llm_cache/                 # LLM Cache 바운디드 컨텍스트
├── demo/                      # Demo 페이지
├── static/                    # 정적 파일
└── main.py                    # MasterApplicationContainer
```

## 아키텍처 원칙

### 1. 바운디드 컨텍스트 (Bounded Context)
- 각 컨텍스트는 독립적인 비즈니스 영역 담당
- 컨텍스트 간 명확한 경계와 인터페이스
- 개별 컨텍스트는 독립적으로 개발/배포 가능

### 2. 마이크로 헥사고날 (Micro Hexagonal)
- 각 바운디드 컨텍스트 내에서 완전한 헥사고날 아키텍처 유지
- 도메인 중심 설계 (Domain-Driven Design)
- 의존성 역전 원칙 (Dependency Inversion Principle)

### 3. 점진적 확장 (Progressive Extension)
- 새로운 바운디드 컨텍스트를 쉽게 추가
- 기존 컨텍스트에 영향 없이 확장
- 독립적인 개발 사이클

### 4. RFS Framework 4.6.5 통합
- **ResultAsync 패턴**: 비동기 연산의 모나드 체이닝
- **Flux 패턴**: 단방향 데이터 흐름 (Action-Dispatcher-Store-View)
- **Saga 패턴**: 긴 트랜잭션 관리와 보상 트랜잭션
- **HOF 라이브러리**: pipe, compose, curry, compact_map 등 함수형 유틸리티
- **함수형 의존성 주입**: curry와 부분 적용을 통한 DI 패턴

### 5. 단일책임원칙 (Single Responsibility Principle)
- **MasterApplicationContainer**: 컨테이너 생명주기 관리만 담당
- **개별 컨테이너**: 각자의 바운디드 컨텍스트만 관리
- **ContainerFactory**: 컨테이너 생성과 조립 전담
- **각 레이어**: 명확한 책임 경계와 단일 목적

## 바운디드 컨텍스트 구조

### 현재 구현된 컨텍스트 (11개)

현재 프로젝트는 다음 11개의 바운디드 컨텍스트로 구성되어 있습니다:

#### 1. Shared Kernel (`src/shared/`)
모든 컨텍스트에서 공유하는 핵심 요소들

```
shared/
├── kernel/                   # 핵심 패턴
│   ├── __init__.py          # Result, Success, Failure 타입
│   └── use_case.py          # UseCase 기본 클래스
├── middleware/              # 공통 미들웨어
│   ├── error_handler.py     # 전역 에러 처리
│   ├── rate_limit.py        # API 제한
│   ├── logging_middleware.py # 요청 로깅
│   ├── cors_middleware.py   # CORS 처리
│   └── security_middleware.py # 보안 미들웨어
├── px_logging/              # 로깅 시스템
│   ├── __init__.py          # 로거 팩토리
│   ├── config.py            # 로깅 설정
│   ├── formatters.py        # 커스텀 포매터
│   └── handlers.py          # 커스텀 핸들러
├── container/               # DI 컨테이너 시스템
│   ├── __init__.py          # 컨테이너 팩토리
│   ├── base_container.py    # 기본 컨테이너
│   └── factory.py           # 컨테이너 생성 팩토리
└── infrastructure/          # 공통 인프라
    ├── llm/                 # LLM 클라이언트
    │   ├── openai_client.py # OpenAI 클라이언트
    │   ├── anthropic_client.py # Anthropic 클라이언트
    │   └── base_client.py   # 기본 클라이언트
    └── templates/           # 템플릿 시스템
        ├── template_loader.py # 템플릿 로더
        ├── template_cache.py  # 템플릿 캐시
        └── template_file_system.py # 파일 시스템
```

#### 2. Health Context (`src/health/`)
시스템 상태 확인 및 모니터링을 담당하는 바운디드 컨텍스트

```
health/
├── domain/                 # 도메인 계층
│   ├── models/            # 도메인 모델
│   │   └── health_status.py
│   ├── ports/             # 포트 (인터페이스)
│   │   └── health_checker.py
│   └── services/          # 도메인 서비스
│       └── health_service.py
├── application/           # 애플리케이션 계층
│   ├── dto/               # 데이터 전송 객체
│   │   └── health_response.py
│   └── use_cases/         # 유스케이스
│       ├── check_health.py
│       ├── check_liveness.py
│       └── check_readiness.py
├── infrastructure/        # 인프라 계층
│   └── adapters/          # 어댑터
│       ├── redis_checker.py
│       ├── gcs_checker.py
│       └── system_monitor.py
└── api/                   # API 계층
    ├── controllers/       # 컨트롤러
    │   └── health_controller.py
    └── routes/            # 라우팅
        └── health_routes.py
```

#### 3. Config Context (`src/config/`)
애플리케이션 설정 관리를 담당하는 바운디드 컨텍스트

```
config/
├── domain/                # 도메인 계층
│   ├── models/           # 도메인 모델
│   │   └── app_config.py
│   ├── ports/            # 포트 (인터페이스)
│   │   └── config_loader.py
│   └── services/         # 도메인 서비스
│       └── config_service.py
├── application/          # 애플리케이션 계층
│   ├── dto/              # 데이터 전송 객체
│   │   └── config_response.py
│   └── use_cases/        # 유스케이스
│       └── load_config.py
└── infrastructure/       # 인프라 계층
    └── adapters/         # 어댑터
        └── env_loader.py
```

#### 4. Translation Context (`src/translation/`) - 신규
다국어 번역 서비스를 담당하는 바운디드 컨텍스트

```
translation/
├── domain/
│   ├── models/           # 번역 모델
│   ├── ports/            # 번역 포트
│   └── services/         # 번역 도메인 서비스
├── application/
│   ├── dto/              # 번역 DTO
│   └── use_cases/        # 번역 유스케이스
├── infrastructure/
│   └── adapters/         # AI Provider 어댑터
└── api/
    ├── controllers/      # 번역 컨트롤러
    └── routes/           # 번역 라우터
```

#### 5. Term Extraction Context (`src/term_extraction/`) - 도메인 코어
**역할**: 순수한 용어 추출 도메인 로직만 담당 (재사용 가능한 코어)

AI 기반 용어 추출을 담당하는 바운디드 컨텍스트로, **직접 API 노출 없이** 다른 컨텍스트에서 라이브러리처럼 사용됩니다.

**주요 기능**:
- LLM 기반 용어 추출 (OpenAI GPT-4o)
- 엔티티 분류 (PERSON, ORGANIZATION, TECHNOLOGY 등)
- 후처리 파이프라인 (중복 제거, 품질 필터링)

**사용 방식**: `term_extraction_integration`에서 import하여 사용

```
term_extraction/
├── domain/
│   ├── models/           # ExtractedEntity, TermExtractionRequest
│   ├── ports/            # LLMProviderPort, PromptTemplateEnginePort
│   └── services/         # TermExtractionDomainService (핵심)
├── application/
│   ├── dto/              # ExtractionRequestDto, ExtractionResponseDto
│   └── use_cases/        # ExtractTermsUseCase
├── infrastructure/
│   └── adapters/         # OpenAILLMProvider, JinjaTemplateEngine
└── api/                  # ⚠️ 현재 미사용 (integration이 API 제공)
    ├── controllers/
    └── routes/
```

#### 6. Term Extraction Integration Context (`src/term_extraction_integration/`) - API 레이어
**역할**: 문서 처리 + 용어 추출 통합 오케스트레이션 (Saga 패턴)

Saga 패턴을 활용한 용어 추출 통합 바운디드 컨텍스트로, **실제 API 엔드포인트를 제공**합니다.

**주요 기능**:
- 문서 파싱 → 청킹 → 용어 추출 → 결과 집계
- Saga 패턴 파이프라인 (단계별 실행 및 롤백)
- 비동기 처리 및 모니터링
- 5개 컨트롤러 (Term, Async, Refactored, Config, Pipeline)

**의존성**: `term_extraction` (도메인 코어 사용), `document_processor` (문서 처리 위임)

**API 엔드포인트**:
- `POST /api/v1/extract-terms/process-documents` - 문서 처리 및 용어 추출
- `POST /api/v2/pipeline/process` - 파이프라인 실행
- `GET /api/v1/extract-terms/config` - 설정 조회

```
term_extraction_integration/
├── domain/
│   ├── models/           # ExtractionConfig, ExtractionResults
│   ├── ports/            # PipelineExecutorPort, PipelineStageManagerPort
│   └── services/         # IntegratedTermExtractionService, PipelineCoordinationService
├── application/
│   ├── dto/              # DocumentProcessingResponseDto, PipelineRequestDto
│   └── use_cases/        # ProcessDocumentsUseCase (핵심)
├── infrastructure/
│   └── adapters/         # SagaPipelineAdapter, TextChunkerAdapter
└── api/
    ├── controllers/      # 5개 컨트롤러 (Term, Async, Refactored, Config, Pipeline)
    ├── routes/           # FastAPI 라우트
    └── validators/       # FileValidators
```

**두 컨텍스트의 관계**:
```
┌─────────────────────────────────────┐
│  term_extraction_integration (API)  │  ← 사용자 대면 엔드포인트
│  - Saga 패턴 오케스트레이션          │
│  - 문서 처리 통합                     │
└──────────────┬──────────────────────┘
               │ depends on
               ↓
┌─────────────────────────────────────┐
│  term_extraction (Domain Core)      │  ← 재사용 가능한 라이브러리
│  - 순수 용어 추출 로직                │
│  - LLM 파이프라인                    │
└─────────────────────────────────────┘
```

**상세 문서**: [docs/09-term-extraction-guide.md](docs/09-term-extraction-guide.md)

#### 7. Document Processor Context (`src/document_processor/`)
Flux 패턴을 활용한 문서 처리 바운디드 컨텍스트

#### 8. Document Extraction Context (`src/document_extraction/`) - 신규
문서 추출을 담당하는 바운디드 컨텍스트

#### 9. Web Extractor Context (`src/web_extractor/`)
웹 콘텐츠 추출 (LinkedIn, 일반 웹사이트)을 담당하는 바운디드 컨텍스트

#### 10. LLM Cache Context (`src/llm_cache/`)
LLM 응답 캐싱 시스템을 담당하는 바운디드 컨텍스트 (Redis 기반)

#### 11. Chat Context (`src/chat/`)
대화형 AI 인터페이스를 담당하는 바운디드 컨텍스트

## 레이어별 상세 설명

### Domain Layer (도메인 계층)
비즈니스 로직의 핵심을 담당하며 외부 의존성이 없음

```python
# src/health/domain/models/health_status.py
from dataclasses import dataclass
from datetime import datetime
from typing import Dict
from src.shared.kernel import Result, Success, Failure

@dataclass(frozen=True)
class HealthStatus:
    """
    시스템 건강 상태를 나타내는 도메인 모델
    """
    service_name: str
    is_healthy: bool
    checks: Dict[str, bool]
    timestamp: datetime
    environment: str
    version: str
    
    def get_failed_checks(self) -> list[str]:
        """
        실패한 체크 항목들을 반환합니다.
        """
        return [name for name, status in self.checks.items() if not status]
    
    def is_critical_failure(self) -> bool:
        """
        중요 서비스의 실패 여부를 확인합니다.
        """
        critical_services = {"redis", "database", "gcs"}
        failed_checks = set(self.get_failed_checks())
        return bool(critical_services.intersection(failed_checks))
```

### Application Layer (애플리케이션 계층)
유스케이스를 조율하고 도메인 객체들을 협력시킴

```python
# src/health/application/use_cases/check_health.py
from src.shared.kernel import Result, Success, Failure
from src.health.domain.services import HealthDomainService
from src.health.application.dto import HealthResponseDto

class CheckHealthUseCase:
    """
    종합적인 헬스체크를 수행하는 유스케이스
    """
    
    def __init__(self, health_domain_service: HealthDomainService):
        self._health_domain_service = health_domain_service
    
    async def execute(
        self, 
        service_name: str, 
        environment: str, 
        version: str
    ) -> Result[HealthResponseDto, str]:
        """
        헬스체크를 실행하고 결과를 반환합니다.
        """
        # 도메인 서비스를 통한 헬스체크 수행
        health_result = await self._health_domain_service.perform_comprehensive_health_check(
            service_name, environment, version
        )
        
        if health_result.is_failure():
            return Failure(health_result.get_error())
        
        health_status = health_result.get_or_none()
        
        # DTO로 변환하여 반환
        response_dto = HealthResponseDto.from_domain(health_status)
        return Success(response_dto)
```

### Infrastructure Layer (인프라 계층)
외부 시스템과의 통합을 담당하며 도메인 포트를 구현

```python
# src/health/infrastructure/adapters/redis_checker.py
from src.shared.kernel import Result, Success, Failure
from src.health.domain.ports import HealthCheckerPort
from src.health.domain.models import CheckResult

class RedisHealthChecker:
    """
    Redis 연결 상태를 확인하는 어댑터
    """
    
    async def check_redis(self) -> Result[CheckResult, str]:
        """
        Redis 연결 상태를 확인합니다.
        """
        try:
            import redis.asyncio as redis
            import time
            
            start_time = time.time()
            
            # Redis 연결 시도 (환경변수에서 URL 가져오기)
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            client = redis.from_url(redis_url)
            
            # 간단한 ping 테스트
            response = await client.ping()
            duration_ms = (time.time() - start_time) * 1000
            
            await client.close()
            
            if response:
                return Success(CheckResult(
                    name="redis",
                    is_healthy=True,
                    message="Redis 연결 정상",
                    duration_ms=duration_ms,
                    details={"redis_url": redis_url}
                ))
            else:
                return Failure("Redis ping 실패")
                
        except Exception as e:
            return Failure(f"Redis 연결 실패: {str(e)}")
```

### API Layer (API 계층)
HTTP 요청을 처리하고 적절한 유스케이스를 호출

```python
# src/health/api/controllers/health_controller.py
from fastapi import Request
from fastapi.responses import JSONResponse
from src.shared.kernel import Result

class HealthController:
    """
    헬스체크 API 컨트롤러
    """
    
    def __init__(
        self,
        check_health_use_case,
        check_liveness_use_case,
        check_readiness_use_case,
        service_name: str,
        service_version: str,
        environment: str
    ):
        self.check_health_use_case = check_health_use_case
        self.check_liveness_use_case = check_liveness_use_case
        self.check_readiness_use_case = check_readiness_use_case
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
    
    async def health(self, request: Request) -> JSONResponse:
        """
        종합적인 헬스체크 엔드포인트
        """
        result = await self.check_health_use_case.execute(
            self.service_name,
            self.environment, 
            self.service_version
        )
        
        if result.is_success():
            health_data = result.get_or_none()
            return JSONResponse(
                status_code=200 if health_data.is_healthy else 503,
                content=health_data.to_dict()
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "service": self.service_name,
                    "status": "unhealthy",
                    "error": result.get_error()
                }
            )
```

## 구현 예제

### ApplicationContainer (DI 컨테이너)

```python
# src/main.py
class ApplicationContainer:
    """
    애플리케이션 DI 컨테이너
    모든 의존성을 관리하는 중앙 컨테이너
    """
    
    def __init__(self):
        # Config 관련 의존성
        self.config_loader = None
        self.config_validator = None
        self.config_domain_service = None
        self.load_config_use_case = None
        self.app_config = None
        
        # Health 관련 의존성
        self.redis_health_checker = None
        self.gcs_health_checker = None
        self.system_monitor = None
        self.health_domain_service = None
        self.health_use_cases = {}
        self.health_controller = None
    
    async def initialize(self) -> Result[None, str]:
        """
        모든 의존성을 초기화합니다.
        """
        try:
            # 1단계: 설정 관련 의존성 초기화
            config_init_result = await self._initialize_config_dependencies()
            if config_init_result.is_failure():
                return config_init_result
            
            # 2단계: 헬스체크 관련 의존성 초기화
            health_init_result = await self._initialize_health_dependencies()
            if health_init_result.is_failure():
                return health_init_result
            
            return Success(None)
            
        except Exception as e:
            return Failure(f"애플리케이션 컨테이너 초기화 실패: {str(e)}")
```

### 라이프사이클 관리

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    애플리케이션 라이프사이클 관리
    시작 시 초기화, 종료 시 정리
    """
    # 시작 로직
    print("🚀 새로운 마이크로 헥사고날 아키텍처로 시작")
    print("📦 바운디드 컨텍스트: Health, Config")
    print("🔧 의존성 주입 컨테이너 초기화 중...")
    
    # 컨테이너 초기화
    container_init_result = await app_container.initialize()
    if container_init_result.is_failure():
        error_message = container_init_result.get_error()
        print(f"❌ 컨테이너 초기화 실패: {error_message}")
        
        # 프로덕션에서는 시스템 종료
        if (app_container.app_config and 
            app_container.app_config.is_production()):
            import sys
            sys.exit(1)
    else:
        print("✅ 의존성 주입 컨테이너 초기화 완료")
    
    yield
    
    # 종료 로직
    print("👋 애플리케이션 종료 완료")
```

## 새로운 컨텍스트 추가 가이드

### 1단계: 폴더 구조 생성

새로운 `user` 컨텍스트를 추가하는 예제:

```bash
mkdir -p src/user/{domain,application,infrastructure,api}
mkdir -p src/user/domain/{models,ports,services}
mkdir -p src/user/application/{dto,use_cases}
mkdir -p src/user/infrastructure/adapters
mkdir -p src/user/api/{controllers,routes}

# __init__.py 파일들 생성
find src/user -type d -exec touch {}/__init__.py \;
```

### 2단계: 도메인 모델 정의

```python
# src/user/domain/models/user.py
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from src.shared.kernel import Result, Success, Failure

@dataclass(frozen=True)
class User:
    """
    사용자 도메인 모델
    """
    user_id: str
    email: str
    name: str
    created_at: datetime
    is_active: bool
    
    def update_email(self, new_email: str) -> Result['User', str]:
        """
        이메일을 업데이트합니다.
        """
        if not self._is_valid_email(new_email):
            return Failure("유효하지 않은 이메일 형식입니다")
        
        return Success(dataclasses.replace(self, email=new_email))
    
    def _is_valid_email(self, email: str) -> bool:
        """
        이메일 형식을 검증합니다.
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
```

### 3단계: 포트 정의

```python
# src/user/domain/ports/user_repository.py
from abc import ABC, abstractmethod
from typing import Optional
from src.shared.kernel import Result
from src.user.domain.models import User

class UserRepositoryPort(ABC):
    """
    사용자 리포지토리 포트
    """
    
    @abstractmethod
    async def find_by_id(self, user_id: str) -> Result[Optional[User], str]:
        """
        ID로 사용자를 조회합니다.
        """
        pass
    
    @abstractmethod
    async def find_by_email(self, email: str) -> Result[Optional[User], str]:
        """
        이메일로 사용자를 조회합니다.
        """
        pass
    
    @abstractmethod
    async def save(self, user: User) -> Result[str, str]:
        """
        사용자를 저장합니다.
        """
        pass
```

### 4단계: 유스케이스 구현

```python
# src/user/application/use_cases/get_user.py
from src.shared.kernel import Result, Success, Failure
from src.user.domain.ports import UserRepositoryPort
from src.user.application.dto import UserResponseDto

class GetUserUseCase:
    """
    사용자 조회 유스케이스
    """
    
    def __init__(self, user_repository: UserRepositoryPort):
        self._user_repository = user_repository
    
    async def execute(self, user_id: str) -> Result[UserResponseDto, str]:
        """
        사용자 ID로 사용자를 조회합니다.
        """
        if not user_id:
            return Failure("사용자 ID가 필요합니다")
        
        user_result = await self._user_repository.find_by_id(user_id)
        if user_result.is_failure():
            return Failure(user_result.get_error())
        
        user = user_result.get_or_none()
        if not user:
            return Failure(f"사용자를 찾을 수 없습니다: {user_id}")
        
        response_dto = UserResponseDto.from_domain(user)
        return Success(response_dto)
```

### 5단계: ApplicationContainer에 등록

```python
# src/main.py - ApplicationContainer 클래스에 추가
async def _initialize_user_dependencies(self) -> Result[None, str]:
    """
    사용자 관련 의존성을 초기화합니다.
    """
    try:
        # User 어댑터들 생성
        self.user_repository = UserRepositoryImpl()
        
        # User 유스케이스들 생성
        self.user_use_cases = {
            "get_user": GetUserUseCase(self.user_repository),
            "create_user": CreateUserUseCase(self.user_repository),
            "update_user": UpdateUserUseCase(self.user_repository),
        }
        
        # User 컨트롤러 생성
        self.user_controller = UserController(
            get_user_use_case=self.user_use_cases["get_user"],
            create_user_use_case=self.user_use_cases["create_user"],
            update_user_use_case=self.user_use_cases["update_user"]
        )
        
        return Success(None)
        
    except Exception as e:
        return Failure(f"사용자 의존성 초기화 실패: {str(e)}")
```

### 6단계: 라우터 등록

```python
# src/main.py - setup_routes_and_middleware 함수에 추가
async def setup_routes_and_middleware(app: FastAPI) -> None:
    """
    라우트와 미들웨어를 설정합니다
    """
    # 기존 Health 라우트
    health_router = create_health_router(app_container.health_controller)
    app.include_router(health_router, tags=["Health Check"])
    
    # 새로운 User 라우트 추가
    user_router = create_user_router(app_container.user_controller)
    app.include_router(user_router, prefix="/api/v1", tags=["Users"])
```

## 개발 워크플로우

### 1. 환경 설정

```bash
# 가상환경 활성화 (필수)
source venv/bin/activate

# 의존성 설치 (pyproject.toml 기반)
pip install -e ".[dev]"  # 개발 의존성
pip install -e ".[ai]"   # AI/ML APIs (선택)
pip install -e ".[cloud]" # 클라우드 서비스 (선택)

# 환경변수 설정
cp .env.example .env
# .env 파일을 적절히 수정
```

### 2. 개발 서버 실행 (run.sh 스크립트 사용)

```bash
# 개발 모드 (권장)
./run.sh dev                    # 자동 재로드, 디버그 모드, 포트 8002
./run.sh dev --force-kill       # 포트 충돌 시 강제 종료

# 환경별 모드
./run.sh stage                  # 스테이징 모드, 포트 8003, 실제 API
./run.sh prod                   # 프로덕션 모드, 포트 8000

# 커스텀 설정
API_PORT=8003 ./run.sh dev     # 커스텀 포트
WORKERS=8 ./run.sh prod        # 커스텀 워커 수
```

### 3. 코드 품질 검증

```bash
# 보수적 검증 (자동 수정 안함)
./scripts/conservative_check.sh

# RFS 규칙 검증 (필수)
python scripts/validate_rfs_rules.py --mode strict
python scripts/validate_functional_rules.py

# 개별 품질 도구
black --check --diff src/      # 포맷 확인만
isort --check-only --diff src/ # 임포트 확인만
flake8 src/                    # 린팅
```

### 4. 테스트 실행

```bash
# 단위 테스트만
pytest -m unit

# 통합 테스트
pytest -m integration

# 커버리지와 함께 실행
pytest --cov=src --cov-report=html

# API 테스트 스크립트들
./scripts/test_translation_api.sh
./scripts/test_term_extraction_api.sh
./scripts/test_health_check.py
```

### 5. API 문서 및 환경 확인

**개발 환경 URL들:**
- **개발**: http://localhost:8002 (`./run.sh dev`)
- **스테이징**: http://localhost:8003 (`./run.sh stage`)
- **프로덕션**: http://localhost:8000 (`./run.sh prod`)
- **API 문서**: /docs (Swagger), /redoc (ReDoc)
- **헬스체크**: /health
- **메트릭**: /metrics (Prometheus 형식)

## 모범 사례

### ✅ 좋은 예시들

1. **Result 패턴 사용**
```python
# 항상 Result를 반환
async def get_user(user_id: str) -> Result[User, str]:
    if not user_id:
        return Failure("사용자 ID가 필요합니다")
    return Success(user)
```

2. **함수형 프로그래밍**
```python
# RFS HOF 사용
from rfs.hof.core import pipe
from rfs.hof.collections import compact_map

result = pipe(
    validate_input,
    lambda r: r.bind(process_data),
    lambda r: r.map(format_output)
)(input_data)
```

3. **한글 주석**
```python
def calculate_total(items: List[Item]) -> Result[Decimal, str]:
    """
    주문 아이템들의 총 가격을 계산합니다.
    
    Args:
        items: 가격을 계산할 아이템 목록
    """
    # 빈 목록 검증
    if not items:
        return Failure("아이템이 없습니다")
    
    # 총액 계산
    total = sum(item.price for item in items)
    return Success(total)
```

### ❌ 피해야 할 패턴들

1. **예외 발생 금지**
```python
# ❌ 금지
def get_user(user_id: str) -> User:
    if not user_id:
        raise ValueError("Invalid ID")  # 금지!
    return user

# ✅ 올바른 방법
async def get_user(user_id: str) -> Result[User, str]:
    if not user_id:
        return Failure("사용자 ID가 필요합니다")
    return Success(user)
```

2. **명령형 루프 금지**
```python
# ❌ 금지
results = []
for item in items:
    if valid(item):
        results.append(transform(item))

# ✅ 올바른 방법
from rfs.hof.collections import compact_map
results = compact_map(
    lambda item: transform(item) if valid(item) else None,
    items
)
```

3. **가변 상태 금지**
```python
# ❌ 금지
user.name = new_name  # 직접 수정 금지!
items.append(new_item)  # 가변 연산 금지!

# ✅ 올바른 방법
updated_user = user.update_name(new_name)  # 새 객체 반환
new_items = items + [new_item]  # 불변 연산
```

## 비동기 모나드 패턴

### ResultAsync 패턴 적용

ResultAsync는 비동기 연산에서의 에러 핸들링과 값 변환을 모나드 법칙에 따라 처리합니다.

#### 기본 사용법

```python
from rfs import ResultAsync

class CacheOrchestrator:
    async def get_or_create_response(
        self, 
        request: LLMRequest, 
        provider_config: LLMProviderConfig
    ) -> ResultAsync[LLMResponse, str]:
        """
        ResultAsync 체이닝을 통한 캐시 오케스트레이션
        """
        return await (
            ResultAsync.from_value(request)
            .bind_async(self._validate_request)
            .bind_async(self._try_get_from_cache)
            .bind_async(lambda context: self._handle_cache_result(context, provider_config))
            .bind_async(self._update_metrics)
        )
```

#### 컨테이너에서의 ResultAsync 적용

```python
class MasterApplicationContainer:
    async def initialize(self) -> ResultAsync[None, str]:
        """
        모든 컨테이너를 순차적으로 초기화합니다.
        ResultAsync.bind() 체이닝으로 의존성 순서 보장
        """
        return await (
            self._create_containers()
            .bind_async(self._initialize_config_first)
            .bind_async(self._initialize_remaining_containers)
            .bind_async(self._validate_all_initialized)
        )
```

#### 올바른 ResultAsync 패턴

```python
# ✅ 올바른 비동기 ResultAsync 사용
async def _validate_request(self, context: Dict[str, any]) -> ResultAsync[Dict[str, any], str]:
    try:
        # 비동기 검증 로직
        if not context.get("request"):
            return await ResultAsync.from_error("요청이 없습니다")
        
        return await ResultAsync.from_value(context)
    except Exception as e:
        return await ResultAsync.from_error(f"검증 실패: {str(e)}")

# ❌ 잘못된 패턴 - 동기 함수에서 ResultAsync
def _validate_request_wrong(self, context) -> ResultAsync[Dict, str]:
    return ResultAsync.from_error(f"검증 실패")  # RuntimeWarning 발생!
```

### Flux 패턴 구현

단방향 데이터 흐름을 통한 상태 관리 패턴입니다.

#### DocumentProcessingStore (Flux Store)

```python
@dataclass(frozen=True)
class ProcessingAction:
    """Flux 액션 정의"""
    type: str
    payload: Dict[str, Any]
    processing_id: str

class DocumentProcessingStore:
    """
    Flux Store - 상태 관리 중앙 집중화
    """
    
    def __init__(self):
        self._state: Dict[str, ProcessingState] = {}
        self._subscribers: List[Callable] = []
    
    async def dispatch(self, action: ProcessingAction) -> ResultAsync[ProcessingState, str]:
        """
        액션을 디스패치하고 상태를 업데이트합니다
        """
        try:
            # 액션 타입에 따른 상태 변경
            if action.type == "START_PROCESSING":
                return await self._handle_start_action(action)
            elif action.type == "UPDATE_DOCUMENT":
                return await self._handle_document_update(action)
            elif action.type == "COMPLETE_PROCESSING":
                return await self._handle_complete_action(action)
            else:
                return AsyncResult.from_error(f"알 수 없는 액션 타입: {action.type}")
        except Exception as e:
            return AsyncResult.from_error(f"액션 처리 실패: {str(e)}")
```

#### Flux 아키텍처 구현

```
View (Controller) → Action → Dispatcher (Store.dispatch) → Store → View
     ↑                                                      ↓
     ←─────────────── State Change Notification ────────────
```

### Saga 패턴 구현

긴 트랜잭션과 보상 트랜잭션을 관리하는 패턴입니다.

#### DocumentProcessingSaga

```python
class DocumentProcessingSaga:
    """
    문서 처리 Saga - 긴 트랜잭션 관리
    """
    
    async def start_transaction(
        self, 
        urls: List[str], 
        processing_id: str
    ) -> ResultAsync[SagaTransaction, str]:
        """
        Saga 트랜잭션을 시작합니다
        """
        transaction = SagaTransaction(
            id=processing_id,
            steps=[
                SagaStep("extract_documents", self._extract_documents, self._rollback_extraction),
                SagaStep("chunk_documents", self._chunk_documents, self._rollback_chunking),
                SagaStep("extract_terms", self._extract_terms, self._rollback_terms),
                SagaStep("finalize_results", self._finalize_results, self._rollback_finalization),
            ],
            compensation_steps=[]
        )
        
        return await self._execute_saga(transaction, urls)
    
    async def _execute_saga(self, transaction: SagaTransaction, data: Any) -> ResultAsync[Any, str]:
        """
        Saga 단계들을 순차적으로 실행하고 실패 시 보상 트랜잭션 실행
        """
        try:
            for step in transaction.steps:
                result = await step.execute(data)
                if await result.is_failure():
                    # 보상 트랜잭션 실행
                    await self._execute_compensation(transaction)
                    return result
                
                data = await result.unwrap_or_async(data)
                transaction.completed_steps.append(step)
            
            return AsyncResult.from_value(data)
        except Exception as e:
            await self._execute_compensation(transaction)
            return AsyncResult.from_error(f"Saga 실행 실패: {str(e)}")
```

### Binding 모나드 (함수형 의존성 주입)

curry와 부분 적용을 통한 함수형 의존성 주입 패턴입니다.

```python
from rfs.hof.core import curry, pipe

@curry
def create_service(config: Config, logger: Logger, service_impl: ServiceImpl):
    """
    커리된 서비스 팩토리 함수
    """
    return service_impl(config, logger)

class FunctionalContainer:
    """
    함수형 의존성 주입 컨테이너
    """
    
    def __init__(self):
        self.config = self._load_config()
        self.logger = self._create_logger()
    
    def create_user_service(self) -> UserService:
        """
        Binding 모나드를 통한 의존성 주입
        """
        # 부분 적용을 통한 의존성 바인딩
        configured_service = create_service(self.config)(self.logger)
        return configured_service(UserServiceImpl)
    
    def create_pipeline(self) -> Callable:
        """
        함수형 파이프라인 구성
        """
        return pipe(
            self._validate_input,
            lambda result: result.bind(self._process_data),
            lambda result: result.bind(self._format_output),
            lambda result: result.map(self._log_result)
        )
```

## 단일책임원칙 적용

### 컨테이너 책임 분리

기존의 거대한 컨테이너를 단일 책임에 따라 분리합니다.

#### 기존 문제점

```python
# ❌ 단일책임원칙 위반 - 모든 기능이 한 클래스에
class TermExtractionIntegrationContainer:
    def __init__(self):
        # 의존성 생성
        # 컨테이너 초기화  
        # 상태 관리
        # 헬스체크
        # 설정 로드
        # 정리 작업
        pass  # 너무 많은 책임!
```

#### 개선된 구조

```python
# ✅ 단일책임원칙 적용 - 책임별 분리

class ServiceFactory:
    """서비스 생성 전담"""
    def create_llm_provider(self, config: Config) -> LLMProvider:
        pass
    
    def create_document_extractor(self, llm_provider: LLMProvider) -> DocumentExtractor:
        pass

class DependencyRegistry:
    """의존성 등록 전담"""
    def __init__(self):
        self.registry: Dict[str, Any] = {}
    
    def register(self, name: str, instance: Any) -> None:
        pass
    
    def get(self, name: str) -> Any:
        pass

class LifecycleManager:
    """생명주기 관리 전담"""
    async def initialize_components(self, registry: DependencyRegistry) -> ResultAsync[None, str]:
        pass
    
    async def cleanup_resources(self, registry: DependencyRegistry) -> ResultAsync[None, str]:
        pass

class HealthChecker:
    """헬스체크 전담"""
    async def check_component_health(self, component: Any) -> ResultAsync[HealthStatus, str]:
        pass

class TermExtractionContainer:
    """컨테이너 조합 및 조율만 담당"""
    def __init__(self):
        self.service_factory = ServiceFactory()
        self.registry = DependencyRegistry()
        self.lifecycle_manager = LifecycleManager()
        self.health_checker = HealthChecker()
    
    async def initialize(self) -> ResultAsync[None, str]:
        """각 전문 컴포넌트에 위임"""
        return await self.lifecycle_manager.initialize_components(self.registry)
```

### 함수 단위 분리

긴 함수를 작은 단위의 순수 함수로 분리합니다.

#### 개선 전

```python
# ❌ 긴 함수 - 여러 책임이 섞임
def process_extraction_request(self, urls: List[str], config: dict) -> dict:
    # 1. 입력 검증 (20줄)
    if not urls:
        raise ValueError("URLs required")
    # ... 더 많은 검증 로직
    
    # 2. 문서 추출 (30줄)  
    documents = []
    for url in urls:
        # ... 복잡한 추출 로직
    
    # 3. 텍스트 청킹 (25줄)
    chunks = []
    for doc in documents:
        # ... 복잡한 청킹 로직
    
    # 4. 용어 추출 (35줄)
    terms = []
    for chunk in chunks:
        # ... 복잡한 용어 추출 로직
    
    # 5. 결과 포매팅 (15줄)
    return {"terms": terms, "chunks": chunks}  # 총 125줄!
```

#### 개선 후

```python
# ✅ 작은 단위 함수들 - 각각 단일 책임
def validate_extraction_request(urls: List[str], config: dict) -> ResultAsync[ValidationResult, str]:
    """입력 검증만 담당"""
    if not urls:
        return AsyncResult.from_error("URLs가 필요합니다")
    return AsyncResult.from_value(ValidationResult(urls, config))

def extract_documents_from_urls(urls: List[str]) -> ResultAsync[List[Document], str]:
    """문서 추출만 담당"""
    # 15줄 내외의 집중된 로직
    pass

def chunk_documents(documents: List[Document]) -> ResultAsync[List[TextChunk], str]:
    """텍스트 청킹만 담당"""  
    # 15줄 내외의 집중된 로직
    pass

def extract_terms_from_chunks(chunks: List[TextChunk]) -> ResultAsync[List[Term], str]:
    """용어 추출만 담당"""
    # 15줄 내외의 집중된 로직
    pass

def format_extraction_results(terms: List[Term], chunks: List[TextChunk]) -> dict:
    """결과 포매팅만 담당"""
    # 10줄 내외의 집중된 로직
    pass

# 파이프라인 기반 통합 (5줄)
async def process_extraction_request(urls: List[str], config: dict) -> ResultAsync[dict, str]:
    """파이프라인 기반 통합 - 각 단계는 위임"""
    return await (
        validate_extraction_request(urls, config)
        .bind_async(lambda result: extract_documents_from_urls(result.urls))
        .bind_async(chunk_documents)
        .bind_async(extract_terms_from_chunks)
        .map_async(lambda terms: format_extraction_results(terms, chunks))
    )
```

### MasterApplicationContainer 책임 분리

```python
class MasterApplicationContainer:
    """
    컨테이너 생명주기 관리만 담당
    """
    
    def __init__(self):
        self.context = ContainerContext()
        self.containers: Dict[str, ApplicationContainerPort] = {}
        self._initialized = False
    
    async def initialize(self) -> ResultAsync[None, str]:
        """
        초기화 단계를 명확히 분리
        각 단계는 전문 메서드에 위임
        """
        return await (
            self._create_containers()
            .bind_async(self._initialize_config_first)
            .bind_async(self._initialize_remaining_containers)
            .bind_async(self._validate_all_initialized)
        )
    
    # 각 단계별로 15줄 내외의 집중된 메서드들...
```

## 모범 사례와 안티패턴

### ✅ ResultAsync 패턴 모범 사례

```python
# 모든 비동기 함수는 ResultAsync 반환
async def get_user_profile(user_id: str) -> ResultAsync[UserProfile, str]:
    """
    사용자 프로필을 가져옵니다.
    """
    if not user_id:
        return await AsyncResult.from_error("사용자 ID가 필요합니다")
    
    try:
        profile = await self.user_repository.find_by_id(user_id)
        if not profile:
            return await AsyncResult.from_error("사용자를 찾을 수 없습니다")
        return await AsyncResult.from_value(profile)
    except Exception as e:
        return await AsyncResult.from_error(f"프로필 조회 실패: {str(e)}")

# HOF와 결합한 파이프라인
validation_pipeline = pipe(
    validate_user_input,
    lambda result: result.bind_async(fetch_user_data),
    lambda result: result.bind_async(enhance_user_profile),
    lambda result: result.map_async(format_response)
)
```

### ❌ 피해야 할 안티패턴들

```python
# 동기 함수에서 ResultAsync 반환 (RuntimeWarning 발생)
def validate_input(data: str) -> ResultAsync[str, str]:
    return ResultAsync.from_error("검증 실패")  # 위험!

# 예외 던지기 (Result 패턴 위반)
def get_user(user_id: str) -> User:
    if not user_id:
        raise ValueError("Invalid user ID")  # 금지!

# 거대한 컨테이너 클래스 (단일책임 위반)
class GiantContainer:
    def __init__(self):
        # 100+ 줄의 초기화 로직  # 위험!

# 명령형 루프 (HOF 미사용)
results = []
for item in items:
    if condition(item):
        results.append(transform(item))  # 개선 필요
```

### 🎯 성능 최적화 가이드

#### ResultAsync 체이닝 최적화

```python
# ✅ 효율적인 체이닝
async def optimized_pipeline(data: InputData) -> ResultAsync[OutputData, str]:
    """
    최적화된 ResultAsync 파이프라인
    """
    # 미리 컴파일된 파이프라인 사용
    pipeline = self._get_cached_pipeline()
    return await pipeline(data)

# 캐시된 파이프라인 생성
@lru_cache(maxsize=1)
def _get_cached_pipeline(self):
    return pipe(
        self._validate_data,
        lambda result: result.bind_async(self._process_data),
        lambda result: result.bind_async(self._finalize_result)
    )
```

#### 배치 처리 최적화

```python
# ✅ 배치 ResultAsync 처리
async def process_batch(items: List[Item]) -> ResultAsync[List[ProcessedItem], str]:
    """
    배치 아이템을 병렬 처리합니다
    """
    # asyncio.gather를 활용한 병렬 처리
    async def process_single(item: Item) -> ResultAsync[ProcessedItem, str]:
        return await self._process_item(item)
    
    try:
        results = await asyncio.gather(
            *[process_single(item) for item in items],
            return_exceptions=True
        )
        
        # 성공/실패 분리
        successes = []
        errors = []
        
        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            elif await result.is_success():
                successes.append(await result.unwrap_or_async(None))
            else:
                errors.append(result.get_error())
        
        if errors:
            return await AsyncResult.from_error(f"배치 처리 실패: {'; '.join(errors[:3])}")
        
        return await AsyncResult.from_value(successes)
        
    except Exception as e:
        return await AsyncResult.from_error(f"배치 처리 예외: {str(e)}")
```

## 결론

마이크로 헥사고날 아키텍처와 RFS Framework 4.6.5의 결합으로 다음과 같은 이점을 얻었습니다:

### 🎯 아키텍처적 이점
- **명확한 경계**: 바운디드 컨텍스트를 통한 도메인 분리
- **단일책임원칙**: 컨테이너와 함수 레벨에서 책임 분리
- **점진적 확장**: 새로운 컨텍스트를 안전하게 추가
- **헥사고날 유지**: 각 컨텍스트 내 완전한 헥사고날 구조

### ⚡ 기술적 이점  
- **ResultAsync 패턴**: 일관된 비동기 에러 핸들링
- **Flux 패턴**: 예측 가능한 상태 관리
- **Saga 패턴**: 신뢰성 있는 분산 트랜잭션
- **Binding 모나드**: 함수형 의존성 주입
- **HOF 활용**: 선언적이고 재사용 가능한 코드

### 📈 운영상 이점
- **독립적 개발**: 컨텍스트별 독립적 개발/배포
- **테스트 용이성**: 단일 책임 함수들의 높은 테스트 가능성
- **유지보수성**: 작은 단위 함수들의 이해하기 쉬운 구조
- **성능 최적화**: 파이프라인 캐싱과 배치 처리 지원

### 🚨 주의사항과 권장사항

1. **ResultAsync 사용 시**: 반드시 `await` 키워드 사용
2. **함수 크기 제한**: 20줄 이내의 작은 함수 지향
3. **파이프라인 활용**: 복잡한 로직은 파이프라인으로 구성
4. **테스트 우선**: 각 함수별 단위 테스트 필수

이 구조를 통해 복잡성을 줄이면서도 확장 가능하고 유지보수하기 쉬운 마이크로서비스 아키텍처를 구축할 수 있습니다.