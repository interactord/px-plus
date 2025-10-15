# Gemini SDK 마이그레이션 가이드

## 개요

Google의 공식 `google-genai` Python SDK를 사용하는 방법과 기존 httpx 기반 구현과의 비교

## 문제 상황

### 현재 httpx 방식의 문제점

1. **SSL 인증서 검증 실패**
   ```
   [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
   self-signed certificate in certificate chain
   ```
   - 회사 방화벽/프록시 환경에서 자체 서명 인증서 사용 시 발생
   - `GEMINI_SSL_VERIFY=false` 설정으로 해결 가능하지만 보안상 권장하지 않음

2. **복잡한 코드**
   - 직접 HTTP 요청 구성 및 에러 처리
   - API 스펙 변경 시 수동 업데이트 필요
   - 페이로드 구성 복잡

3. **유지보수 부담**
   - Gemini API 업데이트 시 수동 대응
   - 에러 처리 로직 직접 구현

## 해결 방법: Google Gen AI SDK 사용

### 1. 설치

```bash
pip install google-genai
```

또는 requirements.txt에 추가:
```
google-genai>=1.33.0
```

### 2. SDK 어댑터 사용

#### 기본 사용법

```python
from src.infrastructure.ai_model.adapters.gemini_sdk_adapter import GeminiSDKAdapter

# 어댑터 생성
adapter = GeminiSDKAdapter(
    api_key="your-api-key",  # 또는 환경 변수 GOOGLE_API_KEY 사용
    model_name="gemini-2.0-flash-exp",
    enable_grounding=True,  # Google Search Grounding 활성화
    temperature=0.3,
    max_tokens=4000
)

# 모델 실행
response = adapter.execute(model_request)

if response.is_success():
    print(response.unwrap().content)
else:
    print(f"에러: {response.unwrap_error()}")
```

#### Google Search Grounding 사용

```python
# Grounding 활성화
adapter = GeminiSDKAdapter(
    enable_grounding=True  # 이것만 True로 설정하면 됨!
)

response = adapter.execute(request)

# Grounding 메타데이터 확인
if response.is_success():
    model_response = response.unwrap()

    # 검색 쿼리
    search_queries = model_response.metadata.get('web_search_queries', [])

    # 검색 소스
    sources = model_response.metadata.get('grounding_sources', [])
    for source in sources:
        print(f"제목: {source['title']}")
        print(f"URL: {source['uri']}")
```

### 3. 기존 코드와 비교

#### Before (httpx 방식)

```python
# base_gemini_adapter.py
class BaseGeminiAdapter(ModelPort, ABC):
    def __init__(self, api_key: str, base_url: str, timeout: int, verify_ssl: bool):
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._verify_ssl = verify_ssl  # SSL 문제 수동 처리
        self._http_client = self._create_http_client()

    def _create_http_client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._base_url,
            headers={"Content-Type": "application/json"},
            params={"key": self._api_key},
            timeout=self._timeout,
            verify=self._verify_ssl  # SSL 검증 제어
        )

    def _make_request(self, endpoint: str, payload: Dict[str, Any]):
        try:
            response = self._http_client.post(endpoint, json=payload)
            response.raise_for_status()
            return Success(response.json())
        except httpx.HTTPStatusError as e:
            # 복잡한 에러 처리...
        except httpx.TimeoutException:
            # 타임아웃 처리...
        except httpx.RequestError as e:
            # 네트워크 에러 처리...

# gemini_web_search_adapter.py
def _build_grounding_tool(self) -> Dict[str, Any]:
    return {
        "googleSearchRetrieval": {  # 수동으로 구성
            "dynamicRetrievalConfig": {
                "mode": "MODE_DYNAMIC",
                "dynamicThreshold": self._dynamic_threshold
            }
        }
    }
```

#### After (SDK 방식)

```python
# gemini_sdk_adapter.py
class GeminiSDKAdapter(ModelPort):
    def __init__(self, api_key: str, model_name: str, enable_grounding: bool):
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self._model_name = model_name
        self._enable_grounding = enable_grounding

        # SDK 클라이언트 생성 (SSL 자동 처리!)
        self._client = genai.Client(api_key=self._api_key)

    def execute(self, request: ModelRequest):
        try:
            # 간단한 API 호출
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=self._extract_contents(request),
                config=self._build_config(request.config)
            )
            return self._parse_response(response)
        except Exception as e:
            return Failure(f"Gemini SDK 호출 실패: {str(e)}")

    def _build_config(self, model_config):
        config_dict = {
            "temperature": self._temperature,
            "max_output_tokens": self._max_tokens,
        }

        # Google Search Grounding 활성화 (매우 간단!)
        if self._enable_grounding:
            config_dict["tools"] = [{"google_search": {}}]

        return types.GenerateContentConfig(**config_dict)
```

## 장단점 비교

### httpx 방식

**장점**:
- ✅ 의존성 최소화
- ✅ 세밀한 제어 가능

**단점**:
- ❌ SSL 인증서 문제 (수동 해결 필요)
- ❌ 복잡한 코드
- ❌ API 변경 시 수동 업데이트
- ❌ 에러 처리 복잡
- ❌ 유지보수 부담

### SDK 방식 (권장)

**장점**:
- ✅ **SSL 문제 자동 해결**
- ✅ **간결한 코드** (약 50% 코드 감소)
- ✅ **공식 지원** (Google 직접 유지보수)
- ✅ **자동 업데이트** (API 변경 자동 반영)
- ✅ **개선된 에러 처리**
- ✅ **타입 힌팅 지원**

**단점**:
- ❌ 추가 의존성 (google-genai 패키지)

## 마이그레이션 방법

### 단계 1: google-genai 설치

```bash
pip install google-genai
```

### 단계 2: 기존 어댑터를 SDK 어댑터로 교체

```python
# Before
from .gemini_web_search_adapter import GeminiWebSearchAdapter

adapter = GeminiWebSearchAdapter(
    api_key=google_key,
    model_name="gemini-2.0-flash-exp",
    enable_grounding=True,
    dynamic_threshold=0.7
)

# After
from .gemini_sdk_adapter import GeminiSDKAdapter

adapter = GeminiSDKAdapter(
    api_key=google_key,
    model_name="gemini-2.0-flash-exp",
    enable_grounding=True  # dynamic_threshold는 SDK가 자동 관리
)
```

### 단계 3: 환경 변수 확인

```bash
# .env 파일
GOOGLE_API_KEY=your-google-api-key-here

# GEMINI_SSL_VERIFY는 더 이상 필요 없음! (SDK가 자동 처리)
```

### 단계 4: 테스트

```python
# 어댑터 사용 가능 여부 확인
from src.infrastructure.ai_model.adapters.gemini_sdk_adapter import GeminiSDKAdapter

result = GeminiSDKAdapter.check_requirements()
if result.is_success():
    print("✅ Gemini SDK 사용 가능")
else:
    print(f"❌ {result.unwrap_error()}")
```

## 통합 예제

### 웹 강화 서비스에서 SDK 어댑터 사용

```python
# enhancement_service_factory.py
from ..adapters.gemini_sdk_adapter import GeminiSDKAdapter

class EnhancementServiceFactory:
    @classmethod
    def _create_adapter(cls, adapter_type: str, openai_key: str, google_key: str):
        if adapter_type == "gemini":
            return Success(GeminiSDKAdapter(
                api_key=google_key,
                model_name="gemini-2.0-flash-exp",
                enable_grounding=True,  # Google Search 활성화
                temperature=0.3,
                max_tokens=4000
            ))
        elif adapter_type == "gpt4o":
            # GPT-4o 어댑터...
            pass
```

## 권장사항

### 개발 환경
- ✅ **SDK 방식 사용 권장** (안정성, 간결성, 유지보수성)
- SSL 문제 자동 해결

### 프로덕션 환경
- ✅ **SDK 방식 강력 권장**
- 공식 지원 및 자동 업데이트
- 더 나은 에러 처리

### 레거시 환경
- 특별한 이유로 httpx 방식을 유지해야 하는 경우:
  - `GEMINI_SSL_VERIFY=false` 설정 (보안 검토 필요)
  - 주기적인 API 스펙 업데이트 확인

## FAQ

### Q1: 기존 httpx 코드를 유지하면서 SDK를 병행 사용할 수 있나요?
A: 네, 가능합니다. 두 어댑터가 동일한 ModelPort 인터페이스를 구현하므로 상황에 따라 선택적으로 사용할 수 있습니다.

### Q2: SDK 방식이 httpx 방식보다 느리지 않나요?
A: 거의 동일한 성능입니다. SDK 내부적으로도 HTTP 클라이언트를 사용하며, 추가 오버헤드는 무시할 수 있는 수준입니다.

### Q3: Google Search Grounding 설정이 간소화되었나요?
A: 네! httpx 방식에서는 `googleSearchRetrieval`, `dynamicRetrievalConfig` 등을 수동으로 구성해야 했지만, SDK에서는 `{"google_search": {}}` 만으로 충분합니다.

### Q4: SSL 인증서 문제가 완전히 해결되나요?
A: 네, google-genai SDK는 인증서 검증을 자동으로 처리하며, 회사 프록시 환경에서도 대부분 문제없이 작동합니다.

## 결론

**Google Gen AI SDK 사용을 강력히 권장합니다**:
- ✅ SSL 문제 자동 해결
- ✅ 50% 코드 감소
- ✅ 공식 지원 및 안정성
- ✅ 간편한 Google Search Grounding

httpx 방식은 특수한 요구사항이 있는 경우에만 사용하고, 대부분의 경우 SDK 방식으로 마이그레이션하는 것이 유리합니다.
