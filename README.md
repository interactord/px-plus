# PX-Plus: FastAPI + RFS Framework

FastAPI와 RFS Framework를 결합한 헥사고날 아키텍처 기반 웹 애플리케이션입니다.

## 🎯 핵심 특징

- **헥사고날 아키텍처**: 비즈니스 로직과 인프라를 완전히 분리
- **Result 패턴**: 예외 대신 명시적인 Result<T, E> 사용
- **의존성 주입**: RFS Registry 기반 DI 시스템
- **불변성**: 모든 엔티티는 불변(immutable) 데이터 구조
- **함수형 프로그래밍**: 순수 함수와 HOF 활용
- **타입 안정성**: 완전한 타입 힌트와 Pydantic 검증

## 📁 프로젝트 구조

```
px-plus/
├── src/
│   ├── domain/              # 도메인 레이어 (비즈니스 로직)
│   │   ├── entities.py      # 불변 엔티티
│   │   └── services.py      # 도메인 서비스 (Result 패턴)
│   ├── application/         # 애플리케이션 레이어
│   │   ├── dto.py           # Pydantic DTO
│   │   └── use_cases.py     # 유즈케이스
│   ├── infrastructure/      # 인프라 레이어
│   │   ├── registry.py      # DI 레지스트리
│   │   └── web/
│   │       ├── dependencies.py  # FastAPI 의존성
│   │       ├── responses.py     # Result → HTTP 변환
│   │       └── routes.py        # API 엔드포인트
│   └── main.py              # FastAPI 앱 초기화
├── tests/                   # 테스트
├── rules/                   # 개발 규칙 문서
├── pyproject.toml          # 프로젝트 설정
└── run.sh                  # 서버 실행 스크립트
```

## 🚀 빠른 시작

### 1. 서버 실행

```bash
# 간편 실행 (권장)
./run.sh

# 또는 수동 실행
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi "uvicorn[standard]" pydantic
uvicorn src.main:app --reload
```

### 2. API 문서 확인

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### 3. API 테스트

```bash
# 기본 인사말 (Hello World)
curl http://localhost:8000/

# 개인화된 인사말
curl http://localhost:8000/hello/Alice

# 커스텀 인사말 생성
curl -X POST http://localhost:8000/greetings \
  -H "Content-Type: application/json" \
  -d '{"recipient": "Bob", "custom_message": "Good morning"}'

# 사용자 생성
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Charlie", "email": "charlie@example.com"}'

# 헬스 체크
curl http://localhost:8000/health
```

## 🏗️ 아키텍처 설명

### 헥사고날 아키텍처 (Ports & Adapters)

```
┌─────────────────────────────────────────────┐
│         Infrastructure Layer                │
│  ┌─────────────────────────────────────┐   │
│  │        FastAPI (Web Adapter)        │   │
│  │  - Routes                            │   │
│  │  - Dependencies (DI)                 │   │
│  │  - Response Converters               │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│         Application Layer                   │
│  ┌─────────────────────────────────────┐   │
│  │         Use Cases                    │   │
│  │  - CreateGreetingUseCase             │   │
│  │  - CreateUserUseCase                 │   │
│  │  - GetDefaultGreetingUseCase         │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │         DTOs (Pydantic)              │   │
│  │  - GreetingRequest/Response          │   │
│  │  - UserRequest/Response              │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│         Domain Layer (Core Business)        │
│  ┌─────────────────────────────────────┐   │
│  │      Domain Services                 │   │
│  │  - GreetingService (Result 패턴)     │   │
│  │  - UserService (Result 패턴)         │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │      Entities (Immutable)            │   │
│  │  - Greeting                          │   │
│  │  - User                              │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### Result 패턴 예제

```python
# ❌ 전통적인 예외 기반 방식
def create_user(name: str):
    if not name:
        raise ValueError("이름은 필수입니다")
    return User(name=name)

# ✅ Result 패턴 방식
def create_user(name: str) -> Result[User, str]:
    if not name:
        return Failure("이름은 필수입니다")
    return Success(User(name=name))

# Result 사용
result = create_user("Alice")
if result.is_success():
    user = result.unwrap()
    print(f"사용자 생성: {user.name}")
else:
    error = result.unwrap_error()
    print(f"에러: {error}")
```

## 📚 개발 규칙

프로젝트는 [rules/](./rules/) 디렉토리의 규칙을 따릅니다:

- **[필수 준수 규칙](./rules/00-mandatory-rules.md)**: RFS Framework 우선 사용, 한글 주석, Result 패턴
- **[Result 패턴](./rules/01-result-pattern.md)**: 명시적 에러 처리
- **[함수형 프로그래밍](./rules/02-functional-programming.md)**: 불변성, 순수 함수, HOF
- **[코드 스타일](./rules/03-code-style.md)**: 타입 힌트, 명명 규칙
- **[헥사고날 아키텍처](./rules/04-hexagonal-architecture.md)**: 포트-어댑터 패턴
- **[의존성 주입](./rules/05-dependency-injection.md)**: Registry 기반 DI

## 🧪 테스트

```bash
# 테스트 실행
pytest

# 커버리지 포함
pytest --cov=src --cov-report=html

# 특정 테스트만 실행
pytest tests/test_domain.py
```

## 🔧 개발 도구

```bash
# 코드 포맷팅
black src/ tests/
isort src/ tests/

# 타입 체크
mypy src/

# 린트
ruff check src/
```

## 📝 API 엔드포인트

### Greetings

- `GET /` - 기본 인사말 (Hello World)
- `GET /hello/{name}` - 개인화된 인사말
- `POST /greetings` - 커스텀 인사말 생성

### Users

- `POST /users` - 사용자 생성

### Health

- `GET /health` - 서비스 상태 확인

## 🤝 기여 가이드

1. 이슈 생성 또는 기존 이슈 선택
2. 브랜치 생성: `git checkout -b feature/your-feature`
3. 변경사항 커밋: `git commit -m "feat: add feature"`
4. 푸시: `git push origin feature/your-feature`
5. Pull Request 생성

## 📄 라이선스

MIT License

## 🙏 감사의 글

- [FastAPI](https://fastapi.tiangolo.com/) - 현대적인 Python 웹 프레임워크
- [Pydantic](https://pydantic-docs.helpmanual.io/) - 데이터 검증 라이브러리
- [RFS Framework](https://github.com/rfs-framework) - Result 패턴 및 함수형 프로그래밍 도구
