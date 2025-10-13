# PX-Plus Google Cloud Run 프로덕션 배포 가이드

## 목차
- [사전 준비](#사전-준비)
- [프로덕션 환경 설정](#프로덕션-환경-설정)
- [배포 프로세스](#배포-프로세스)
- [환경변수 관리](#환경변수-관리)
- [모니터링 및 로그](#모니터링-및-로그)
- [문제 해결](#문제-해결)

---

## 사전 준비

### 1. Google Cloud SDK 설치
```bash
# macOS
brew install google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### 2. gcloud 인증 및 프로젝트 설정
```bash
# 로그인
gcloud auth login

# 프로젝트 설정
gcloud config set project hyper-personalization-ai

# Docker 인증
gcloud auth configure-docker gcr.io
```

### 3. 필요한 API 활성화
```bash
gcloud services enable \
  run.googleapis.com \
  containerregistry.googleapis.com \
  cloudbuild.googleapis.com
```

---

## 프로덕션 환경 설정

### .env.production 파일 생성

```bash
cp .env.sample .env.production
# .env.production 파일을 편집하여 프로덕션 환경 설정
```

### 주요 설정 사항

.env.production 파일에서 다음 항목을 반드시 설정하세요:

```bash
# 환경 설정
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false

# 서버 설정
WORKERS=2

# Redis (Cloud Memorystore 사용 시)
REDIS_URL=redis://your-redis-ip:6379

# CORS (프로덕션 도메인만 허용)
CORS_ORIGINS=https://your-domain.com

# 보안
SECRET_KEY=your-strong-secret-key-here
```

### 민감한 환경변수 관리 (Secret Manager)

#### Secret 생성
```bash
# Google API Key
echo -n "your-actual-api-key" | gcloud secrets create google-api-key \
  --data-file=- \
  --replication-policy=automatic

# OpenAI API Key
echo -n "your-actual-api-key" | gcloud secrets create openai-api-key \
  --data-file=- \
  --replication-policy=automatic

# Anthropic API Key
echo -n "your-actual-api-key" | gcloud secrets create anthropic-api-key \
  --data-file=- \
  --replication-policy=automatic
```

#### Cloud Run 서비스에 Secret 접근 권한 부여
```bash
# Compute Engine 기본 서비스 계정 확인
PROJECT_NUMBER=$(gcloud projects describe hyper-personalization-ai --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Secret 접근 권한 부여
for SECRET in google-api-key openai-api-key anthropic-api-key; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
done
```

---

## 배포 프로세스

### Makefile 명령어

#### 도움말 확인
```bash
make help
```

#### 로컬 테스트
```bash
# 로컬 개발 서버 실행
make dev

# Docker Compose로 로컬 테스트
make docker-dev
```

#### 프로덕션 배포

**방법 1: 전체 배포 (권장)**
```bash
# 빌드 + 푸시 + 배포를 한 번에
make deploy-full
```

**방법 2: 단계별 배포**
```bash
# 1. Docker 이미지 빌드
make build

# 2. GCR에 푸시
make push

# 3. Cloud Run 배포 (확인 프롬프트 표시됨)
make deploy
```

### 리소스 설정

기본 프로덕션 설정 (Makefile에서 수정 가능):
```makefile
MIN_INSTANCES = 1      # 최소 인스턴스
MAX_INSTANCES = 20     # 최대 인스턴스
CPU = 2                # CPU 코어
MEMORY = 2Gi           # 메모리
TIMEOUT = 300s         # 타임아웃
```

---

## 환경변수 관리

### .env 파일을 YAML로 변환

#### 자동 변환 (Makefile 사용)
```bash
make env-to-yaml
```

이 명령어는:
1. `.env.production` 파일을 읽어서
2. `config/env-vars-production.yaml` 파일을 생성합니다
3. 민감한 환경변수(API_KEY, SECRET 등)는 주석 처리되며 Secret Manager 사용을 권장합니다

#### 수동 변환 (스크립트 직접 실행)
```bash
python3 scripts/env-to-yaml.py .env.production > config/env-vars-production.yaml
```

### YAML 파일 구조

생성된 YAML 파일은 다음과 같은 구조입니다:

```yaml
# config/env-vars-production.yaml
env:
  - name: API_HOST
    value: "0.0.0.0"
  - name: API_PORT
    value: "8080"
  - name: ENVIRONMENT
    value: production

# 민감한 환경변수는 주석으로 표시됨
# Secret Manager를 통해 별도로 설정해야 함
# - GOOGLE_API_KEY
# - OPENAI_API_KEY
# - ANTHROPIC_API_KEY
```

---

## 모니터링 및 로그

### Cloud Run 서비스 상태 확인
```bash
# 서비스 정보 확인
make describe

# 모든 서비스 목록
make list
```

### 로그 확인
```bash
# 최근 로그 확인 (50줄)
make logs

# 실시간 로그 스트리밍
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=px-plus-api" \
  --project=hyper-personalization-ai
```

### 트래픽 및 리비전 관리
```bash
# 트래픽 분산 확인
make traffic

# 리비전 목록 확인
make revisions
```

### 롤백
```bash
# 이전 리비전으로 롤백
make rollback
```

---

## 문제 해결

### 1. 빌드 실패

#### Docker 빌드 캐시 정리
```bash
make build-no-cache
```

#### spacy 모델 다운로드 실패
Dockerfile에서 spacy 모델 다운로드가 실패하는 경우:
```dockerfile
# Dockerfile 수정
# RUN python -m spacy download ko_core_news_sm 대신
RUN pip install https://github.com/explosion/spacy-models/releases/download/ko_core_news_sm-3.7.0/ko_core_news_sm-3.7.0-py3-none-any.whl
```

### 2. 배포 실패

#### 환경변수 파일 확인
```bash
# YAML 파일이 존재하는지 확인
ls -la config/

# YAML 파일 내용 확인
cat config/env-vars-production.yaml
```

#### 권한 문제
```bash
# Cloud Run Admin 권한 확인
gcloud projects get-iam-policy hyper-personalization-ai \
  --flatten="bindings[].members" \
  --filter="bindings.role:roles/run.admin"
```

### 3. 메모리 부족 에러

Makefile에서 MEMORY 값 증가:
```makefile
MEMORY ?= 4Gi  # 2Gi에서 4Gi로 증가
```

### 4. Cold Start 문제

Makefile에서 MIN_INSTANCES 증가:
```makefile
MIN_INSTANCES ?= 2  # 1에서 2로 증가
```

### 5. 로그 확인 안 됨

로그 뷰어 권한 확인:
```bash
gcloud projects add-iam-policy-binding hyper-personalization-ai \
  --member="user:your-email@example.com" \
  --role="roles/logging.viewer"
```

---

## 유용한 명령어

### Docker 이미지 관리
```bash
# 로컬 이미지 목록
docker images | grep px-plus

# 이미지 삭제
make docker-clean
```

### GCR 이미지 관리
```bash
# GCR 이미지 목록
gcloud container images list --repository=gcr.io/hyper-personalization-ai

# 특정 이미지의 태그 목록
gcloud container images list-tags gcr.io/hyper-personalization-ai/px-plus

# 오래된 이미지 삭제 (최근 3개 제외)
gcloud container images list-tags gcr.io/hyper-personalization-ai/px-plus \
  --format="get(digest)" \
  --sort-by="~timestamp" \
  --limit=999 \
  | tail -n +4 \
  | xargs -I {} gcloud container images delete gcr.io/hyper-personalization-ai/px-plus@{} --quiet
```

### Cloud Run 관리
```bash
# 서비스 삭제
gcloud run services delete px-plus-api \
  --platform=managed \
  --region=asia-northeast3 \
  --project=hyper-personalization-ai

# 특정 리비전 삭제
gcloud run revisions delete REVISION_NAME \
  --platform=managed \
  --region=asia-northeast3 \
  --project=hyper-personalization-ai
```

---

## 배포 체크리스트

### 배포 전
- [ ] `.env.production` 파일이 올바르게 설정되어 있는가?
- [ ] Secret Manager에 민감한 환경변수가 등록되어 있는가?
- [ ] 로컬에서 Docker 빌드가 성공하는가?
- [ ] 테스트가 모두 통과하는가?
- [ ] Git에 커밋되지 않은 변경사항이 없는가?

### 배포 후
- [ ] 서비스가 정상적으로 시작되었는가? (`make describe`)
- [ ] 헬스 체크가 통과하는가?
- [ ] API 엔드포인트가 정상적으로 응답하는가?
- [ ] 로그에 에러가 없는가? (`make logs`)
- [ ] 모니터링 대시보드가 정상인가?

---

## 참고 문서

- [Google Cloud Run 공식 문서](https://cloud.google.com/run/docs)
- [Cloud Run 가격 정책](https://cloud.google.com/run/pricing)
- [Secret Manager 사용 가이드](https://cloud.google.com/secret-manager/docs)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)
