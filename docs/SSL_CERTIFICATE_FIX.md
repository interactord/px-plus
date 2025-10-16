# SSL Certificate Verification 문제 해결 가이드

## 🔍 문제 진단

### 에러 메시지
```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
self-signed certificate in certificate chain (_ssl.c:1032)
```

### 원인
- **환경**: 회사 프록시, VPN, 방화벽의 SSL 인터셉션
- **SDK**: `google-genai 1.43.0`이 `httpx` + `requests` 사용
- **위치**: `src/infrastructure/ai_model/adapters/gemini_sdk_adapter.py`

### 발생 시점
- Gemini + Google Search Grounding 사용 시
- Fallback 1 단계에서 Gemini 웹검색 어댑터 호출 시

---

## 💡 해결 방안 (3가지)

### ✅ **방안 1: 환경 변수로 SSL 검증 비활성화** (권장 - 빠른 임시 해결)

**장점**: 코드 수정 없이 즉시 적용 가능
**단점**: 보안 경고 발생 (개발/테스트 환경에서만 사용)

#### 설정 방법

`.env` 파일에 추가:
```bash
# SSL 검증 비활성화 (개발/테스트 환경 전용)
PYTHONHTTPSVERIFY=0
SSL_CERT_FILE=""
REQUESTS_CA_BUNDLE=""
CURL_CA_BUNDLE=""
```

또는 실행 시 환경 변수 설정:
```bash
PYTHONHTTPSVERIFY=0 python run.py
```

---

### 🔧 **방안 2: GeminiSDKAdapter에 SSL 검증 우회 옵션 추가** (중간 - 코드 수정)

**장점**: 선택적 SSL 검증 비활성화, 프로덕션과 개발 환경 분리 가능
**단점**: SDK 수정 필요

#### 구현 방법

`src/infrastructure/ai_model/adapters/gemini_sdk_adapter.py` 수정:

```python
class GeminiSDKAdapter(ModelPort):
    def __init__(
        self,
        api_key: str = None,
        model_name: str = "gemini-2.0-flash-exp",
        enable_grounding: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        timeout: int = 60,
        verify_ssl: bool = True  # 새로운 파라미터
    ):
        # ... 기존 코드 ...

        self._verify_ssl = verify_ssl

        # SSL 검증 설정
        if not self._verify_ssl:
            import ssl
            import httpx

            # httpx 클라이언트용 SSL 컨텍스트
            self._ssl_context = ssl.create_default_context()
            self._ssl_context.check_hostname = False
            self._ssl_context.verify_mode = ssl.CERT_NONE

            # 환경 변수 설정 (requests용)
            os.environ['REQUESTS_CA_BUNDLE'] = ''
            os.environ['CURL_CA_BUNDLE'] = ''
```

팩토리에서 사용:
```python
# development 환경
gemini_adapter = GeminiSDKAdapter(
    api_key=api_key,
    verify_ssl=False  # 개발 환경에서 SSL 검증 비활성화
)

# production 환경
gemini_adapter = GeminiSDKAdapter(
    api_key=api_key,
    verify_ssl=True  # 프로덕션에서는 SSL 검증 활성화
)
```

---

### 🛡️ **방안 3: 자체 서명 인증서를 신뢰 체인에 추가** (권장 - 프로덕션)

**장점**: 보안성 유지하면서 문제 해결
**단점**: 인증서 파일 필요, 설정 복잡

#### 구현 방법

1. **자체 서명 인증서 추출**:
```bash
# 프록시/VPN 인증서 내보내기 (회사 IT 부서에 문의)
# 또는 브라우저에서 인증서 다운로드
```

2. **인증서를 프로젝트에 추가**:
```bash
mkdir -p certs
cp your-company-cert.pem certs/
```

3. **환경 변수 설정** (`.env`):
```bash
# SSL 인증서 경로
SSL_CERT_FILE=/Users/sangbongmoon/Workspace/px-plus/certs/your-company-cert.pem
REQUESTS_CA_BUNDLE=/Users/sangbongmoon/Workspace/px-plus/certs/your-company-cert.pem
```

4. **certifi 번들에 추가** (선택):
```python
import certifi
import os

# certifi CA 번들에 회사 인증서 추가
ca_bundle = certifi.where()
company_cert = '/path/to/your-company-cert.pem'

# 결합된 CA 번들 생성
with open(ca_bundle, 'rb') as f1, open(company_cert, 'rb') as f2:
    combined = f1.read() + b'\n' + f2.read()

custom_bundle = 'certs/combined-ca-bundle.pem'
with open(custom_bundle, 'wb') as f:
    f.write(combined)

os.environ['REQUESTS_CA_BUNDLE'] = custom_bundle
os.environ['SSL_CERT_FILE'] = custom_bundle
```

---

## 🎯 권장 솔루션

### 개발/테스트 환경
→ **방안 1**: 환경 변수로 SSL 검증 비활성화

### 프로덕션 환경
→ **방안 3**: 자체 서명 인증서를 신뢰 체인에 추가

### 중간 단계 (개발과 프로덕션 분리 필요)
→ **방안 2**: 코드에 `verify_ssl` 옵션 추가

---

## ⚡ 즉시 적용 (Quick Fix)

지금 바로 테스트하려면:

```bash
# .env 파일에 추가
echo "PYTHONHTTPSVERIFY=0" >> .env

# 또는 실행 시
PYTHONHTTPSVERIFY=0 ./run.sh dev
```

---

## 🔍 검증 방법

1. **SSL 설정 확인**:
```python
python3 -c "import ssl; print(ssl.get_default_verify_paths())"
```

2. **테스트 실행**:
```bash
curl -X POST http://localhost:8002/api/v1/extract-terms/process-documents \
  -H "Content-Type: multipart/form-data" \
  -F "files=@test.txt"
```

3. **로그 확인**:
```bash
# Fallback 1 성공 메시지 확인
grep "Fallback 1 성공" logs/*.log
```

---

## 📚 참고 자료

- [Python SSL 문서](https://docs.python.org/3/library/ssl.html)
- [Requests SSL 검증](https://requests.readthedocs.io/en/latest/user/advanced/#ssl-cert-verification)
- [HTTPX SSL 설정](https://www.python-httpx.org/advanced/#ssl-certificates)
- [Google Gen AI SDK](https://github.com/googleapis/python-genai)

---

## ⚠️ 보안 주의사항

- **개발 환경에서만** SSL 검증 비활성화 사용
- **프로덕션 환경**에서는 반드시 방안 3 사용
- `.env` 파일은 **절대 Git에 커밋하지 않음**
- 자체 서명 인증서는 **회사 IT 부서 승인** 후 사용
