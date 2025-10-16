# Cloud Run 배포 가이드

## 📋 목차
1. [배포 프로세스 개요](#배포-프로세스-개요)
2. [환경 변수 설정 방식](#환경-변수-설정-방식)
3. [Secret Manager 자동화](#secret-manager-자동화)
4. [배포 명령어](#배포-명령어)
5. [문제 해결](#문제-해결)

## 배포 프로세스 개요

### 기존 문제점

**Makefile의 `deploy-full` 명령이 환경 변수를 자동으로 설정하지 못했던 이유**:

1. **env-to-yaml.py의 필터링 동작**:
   ```python
   # scripts/env-to-yaml.py (Line 69-72)
   sensitive_keywords = [
       'API_KEY', 'SECRET', 'PASSWORD', 'TOKEN', ...
   ]
   ```
   - `GOOGLE_API_KEY`, `OPENAI_API_KEY` 등 민감한 변수는 YAML에서 제외
   - config/env-vars-production.yaml에 주석으로만 표시

2. **Cloud Run 배포 시 환경 변수 누락**:
   ```makefile
   # Makefile (Line 115)
   --env-vars-file config/env-vars-production.yaml
   ```
   - YAML 파일에 API 키가 없어서 서비스 초기화 실패
   - 수동으로 환경 변수나 Secret을 설정해야 함

### 해결 방안

**방안 1: Secret Manager 자동화 (권장)**
- .env.production의 민감한 변수를 Secret Manager에 자동 생성/업데이트
- Cloud Run 배포 시 Secret Manager에서 자동으로 불러옴
- 보안성과 자동화를 모두 만족

**방안 2: 환경 변수 직접 설정 (간단)**
- gcloud run services update --update-env-vars 사용
- 빠르고 간단하지만 보안성이 낮음
- 개발/테스트 환경에 적합

## 환경 변수 설정 방식

### 비교표

| 방식 | 보안성 | 자동화 | 권한 필요 | 추천 환경 |
|-----|-------|-------|----------|----------|
| Secret Manager | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 프로젝트 IAM 권한 | 프로덕션 |
| 환경 변수 직접 설정 | ⭐⭐ | ⭐⭐⭐ | Cloud Run 배포 권한 | 개발/테스트 |
| env-vars.yaml 수동 편집 | ⭐ | ⭐ | 파일 수정 권한 | 테스트 전용 |

### Secret Manager 장점
✅ API 키가 코드베이스에 포함되지 않음
✅ 버전 관리 및 롤백 가능
✅ 세밀한 접근 제어 (IAM 기반)
✅ 자동 로테이션 및 감사 로그
✅ Cloud Run에서 자동으로 마운트

### 환경 변수 직접 설정 장점
✅ 설정이 간단하고 빠름
✅ 특별한 권한 불필요
✅ 개발/테스트에 적합

❌ 프로덕션 환경에는 부적합 (보안 위험)

## Secret Manager 자동화

### 1. Secret 자동 생성 스크립트

`scripts/setup-secrets.sh`가 다음 작업을 수행:

1. .env.production에서 민감한 환경 변수 추출
2. Secret Manager에 Secret 생성 또는 업데이트
3. (권한이 있는 경우) 서비스 계정에 접근 권한 부여

**지원하는 민감한 변수**:
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `RAPIDAPI_KEY`
- `SECRET_KEY`
- `SLACK_WEBHOOK_URL`
- `OPENAI_MAX_TOKENS`
- `TERM_EXTRACTION_OPENAI_MAX_TOKENS`

### 2. IAM 권한 설정 (프로젝트 관리자가 실행)

Secret Manager 사용을 위해 서비스 계정에 권한 부여:

```bash
# 방법 1: 프로젝트 레벨 권한 (권장)
gcloud projects add-iam-policy-binding hyper-personalization-ai \
  --member="serviceAccount:623004189757-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 방법 2: 개별 Secret 권한
gcloud secrets add-iam-policy-binding google-api-key \
  --member="serviceAccount:623004189757-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**필요한 권한**:
- `secretmanager.secrets.setIamPolicy` - IAM 정책 설정
- `iam.serviceAccounts.actAs` - 서비스 계정으로 실행

### 3. Makefile 통합

개선된 `deploy-full` 타겟:

```makefile
.PHONY: deploy-full
deploy-full: build push setup-secrets deploy
	@echo "✓ 전체 배포 완료"
```

**실행 순서**:
1. `build`: Docker 이미지 빌드
2. `push`: GCR에 이미지 푸시
3. `setup-secrets`: Secret Manager에 민감한 변수 설정
4. `deploy`: Cloud Run에 배포 (Secret + 일반 환경 변수)

## 배포 명령어

### 전체 자동화 배포 (Secret Manager 사용)

```bash
# 1. Secret Manager 설정 (프로젝트 관리자 실행 필요)
gcloud projects add-iam-policy-binding hyper-personalization-ai \
  --member="serviceAccount:623004189757-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 2. 전체 배포 실행
SKIP_TYPE_CHECK=true make deploy-full
```

### 수동 배포 (환경 변수 직접 설정)

```bash
# 1. 빌드 및 푸시
make build push

# 2. 환경 변수로 배포
gcloud run services update px-plus \
  --region asia-northeast3 \
  --update-env-vars GOOGLE_API_KEY="...",OPENAI_API_KEY="..."
```

### Secret만 업데이트

```bash
# Secret Manager 재설정
make setup-secrets

# Cloud Run 서비스 업데이트 없이 Secret만 변경
# (다음 배포 시 자동 반영)
```

## 문제 해결

### Secret Manager 권한 오류

**증상**:
```
ERROR: Permission denied on secret: ...
The service account used must be granted the 'Secret Manager Secret Accessor' role
```

**해결**:
```bash
# 프로젝트 소유자나 관리자에게 요청
gcloud projects add-iam-policy-binding hyper-personalization-ai \
  --member="serviceAccount:623004189757-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 환경 변수 설정 충돌

**증상**:
```
ERROR: Cannot update environment variable [GOOGLE_API_KEY] to string literal
because it has already been set with a different type.
```

**해결**:
```bash
# Secret 제거 후 환경 변수로 재설정
gcloud run services update px-plus \
  --region asia-northeast3 \
  --clear-secrets
```

### SSL 인증서 검증 오류 (로컬 환경)

**증상**:
```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
self-signed certificate in certificate chain
```

**원인**: 기업 프록시의 자체 서명 인증서

**해결**:
- Cloud Run 프로덕션 환경에서는 발생하지 않음
- 로컬 개발 시 SSL 검증 비활성화 (개발 전용)

### 배포 테스트 결과

**로컬 환경** (기업 프록시):
- ❌ SSL 인증서 오류 발생
- 3개 용어 모두 실패

**Cloud Run 프로덕션**:
- ✅ SSL 에러 없음
- ✅ 3개 용어 모두 성공 (Android, MobSF, Docker)
- ✅ HTTP 200 OK, 7.78초 처리 시간

## 베스트 프랙티스

### 프로덕션 환경
1. ✅ Secret Manager 사용
2. ✅ .env.production은 .gitignore에 추가
3. ✅ CI/CD 파이프라인에서 자동 배포
4. ✅ 주기적인 API 키 로테이션

### 개발/테스트 환경
1. ✅ 환경 변수 직접 설정 (빠른 테스트)
2. ✅ .env.development 사용
3. ✅ 로컬 Docker 환경에서 테스트
4. ⚠️ 민감한 정보는 절대 커밋하지 않기

## 참고 자료

- [Google Cloud Run 문서](https://cloud.google.com/run/docs)
- [Secret Manager 문서](https://cloud.google.com/secret-manager/docs)
- [Cloud Run에서 Secret 사용](https://cloud.google.com/run/docs/configuring/secrets)
- [환경 변수 설정](https://cloud.google.com/run/docs/configuring/environment-variables)
