# 웹 강화 API 배포 가이드

## 📋 개요

**작성일**: 2025-10-13  
**상태**: ✅ 완료

웹 강화 API의 배포 및 테스트 가이드입니다.

---

## 🔧 환경 변수 설정

### 필수 환경 변수

#### 개발 환경 (.env.development)
```bash
# OpenAI API
OPENAI_API_KEY=sk-...

# Google API (Gemini)
GOOGLE_API_KEY=AIza...

# Redis (로컬 Docker)
REDIS_URL=redis://localhost:6379
CACHE_TTL=86400

# 앱 설정
ENVIRONMENT=development
LOG_LEVEL=INFO
API_PORT=8000
```

#### 프로덕션 환경 (.env.production)
```bash
# OpenAI API
OPENAI_API_KEY=sk-...

# Google API (Gemini)
GOOGLE_API_KEY=AIza...

# Redis (Google Cloud Memorystore)
REDIS_URL=redis://10.x.x.x:6379
CACHE_TTL=86400

# 앱 설정
ENVIRONMENT=production
LOG_LEVEL=WARNING
```

---

## 🐳 로컬 개발 환경

### 1. Redis 시작 (Docker)

```bash
# Redis 컨테이너 시작
docker run -d \
  --name px-plus-redis \
  -p 6379:6379 \
  redis:7-alpine

# Redis 연결 확인
docker exec -it px-plus-redis redis-cli ping
# 응답: PONG
```

### 2. 애플리케이션 시작

```bash
# 환경 변수 로드
export $(cat .env.development | xargs)

# 개발 서버 시작
ENVIRONMENT=development API_PORT=8000 ./run.sh dev --force-kill
```

### 3. API 테스트

```bash
# 헬스 체크
curl http://localhost:8000/api/v1/web-enhancement/health

# 웹 강화 테스트 (1개 용어)
curl -X POST "http://localhost:8000/api/v1/web-enhancement/enhance" \
  -H "Content-Type: application/json" \
  -d '{
    "terms": [
      {
        "term": "Partido Popular",
        "type": "company",
        "primary_domain": "politics",
        "context": "Major Spanish political party",
        "tags": ["#PP", "#Spain"]
      }
    ],
    "use_cache": true,
    "batch_size": 5,
    "concurrent_batches": 3
  }'
```

---

## 🧪 E2E 테스트 (sample_term.json)

### 1. 전체 33개 용어 테스트

```bash
# sample_term.json 로드
curl -X POST "http://localhost:8000/api/v1/web-enhancement/enhance" \
  -H "Content-Type: application/json" \
  -d @sample/sample_term.json

# 예상 결과:
# - total_terms: 33
# - total_batches: 7 (33 ÷ 5 = 7)
# - processing_time: ~42초 (캐시 없음)
# - cache_hit_rate: 0.0 (첫 요청)
```

### 2. 캐시 효과 테스트

```bash
# 첫 번째 요청 (캐시 없음)
time curl -X POST "http://localhost:8000/api/v1/web-enhancement/enhance" \
  -H "Content-Type: application/json" \
  -d @sample/sample_term.json
# 처리 시간: ~45초

# 두 번째 요청 (캐시 히트)
time curl -X POST "http://localhost:8000/api/v1/web-enhancement/enhance" \
  -H "Content-Type: application/json" \
  -d @sample/sample_term.json
# 처리 시간: <1초
# cache_hit_rate: 1.0 (100%)
```

### 3. 배치 처리 테스트

```bash
# 배치 크기 변경 테스트
curl -X POST "http://localhost:8000/api/v1/web-enhancement/enhance" \
  -H "Content-Type: application/json" \
  -d '{
    "terms": [...],
    "batch_size": 3,        # 5 → 3
    "concurrent_batches": 2  # 3 → 2
  }'

# 예상 배치 수: 33 ÷ 3 = 11
# 예상 라운드: 11 ÷ 2 = 6
```

### 4. Fallback 테스트

```bash
# 잘못된 OpenAI API 키로 Fallback 트리거
OPENAI_API_KEY=invalid curl -X POST ...

# 예상 결과:
# - source: "gemini_web" (Fallback 사용)
# - fallback_count: 1-7 (배치별)
```

---

## 📊 성능 벤치마크

### 예상 성능 (33개 용어)

| 시나리오 | 배치 수 | 처리 시간 | 설명 |
|---------|--------|----------|------|
| 캐시 없음 | 7 | ~45초 | 첫 요청 |
| 캐시 100% | 0 | <1초 | 재요청 |
| 캐시 50% | 3-4 | ~22초 | 부분 캐시 |

### 배치 크기별 성능

| 배치 크기 | 동시 배치 | 전체 배치 | 라운드 | 예상 시간 |
|----------|----------|----------|-------|----------|
| 5 (권장) | 3 | 7 | 3 | ~18초 |
| 3 | 3 | 11 | 4 | ~24초 |
| 10 (최대) | 3 | 4 | 2 | ~12초 |

### 병목 지점

1. **LLM API 호출**: 배치당 ~6초 (가장 큰 병목)
2. **네트워크 지연**: ~0.5초
3. **JSON 파싱**: <0.1초
4. **Redis I/O**: <0.1초

---

## 🚀 Cloud Run 배포

### 1. Docker 이미지 빌드

```bash
# 프로덕션 이미지 빌드
./docker-run-production.sh build

# 이미지 확인
docker images | grep px-plus
```

### 2. Google Container Registry 푸시

```bash
# 프로젝트 설정
export GCP_PROJECT_ID="hyper-personalization-ai"
export IMAGE_NAME="gcr.io/${GCP_PROJECT_ID}/px-plus:latest"

# 이미지 태그
docker tag px-plus:production ${IMAGE_NAME}

# GCR 푸시
docker push ${IMAGE_NAME}
```

### 3. Cloud Run 배포

```bash
# 배포 (환경 변수 포함)
gcloud run deploy px-plus \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --set-env-vars "ENVIRONMENT=production" \
  --set-env-vars "OPENAI_API_KEY=${OPENAI_API_KEY}" \
  --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY}" \
  --set-env-vars "REDIS_URL=${REDIS_URL}" \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 10

# 배포 확인
gcloud run services describe px-plus --region asia-northeast3
```

### 4. Redis Memorystore 연결

```bash
# Memorystore 인스턴스 확인
gcloud redis instances describe px-plus-redis \
  --region asia-northeast3

# IP 주소 확인
export REDIS_IP=$(gcloud redis instances describe px-plus-redis \
  --region asia-northeast3 \
  --format="value(host)")

echo "Redis IP: ${REDIS_IP}"

# Cloud Run에 Redis URL 설정
gcloud run services update px-plus \
  --set-env-vars "REDIS_URL=redis://${REDIS_IP}:6379" \
  --region asia-northeast3
```

---

## 🔍 모니터링

### 1. Cloud Run 메트릭

```bash
# 요청 수
gcloud monitoring metrics list \
  --filter="metric.type=run.googleapis.com/request_count"

# 응답 시간
gcloud monitoring metrics list \
  --filter="metric.type=run.googleapis.com/request_latencies"

# 에러율
gcloud monitoring metrics list \
  --filter="metric.type=run.googleapis.com/request_count AND metric.label.response_code_class='5xx'"
```

### 2. Redis 모니터링

```bash
# Redis 통계
gcloud redis instances describe px-plus-redis \
  --region asia-northeast3 \
  --format="table(currentLocationId,memorySizeGb,persistenceIamRole)"

# 캐시 히트율
curl "https://px-plus-xxx.run.app/api/v1/web-enhancement/cache/stats"
```

### 3. 로그 확인

```bash
# Cloud Run 로그
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=px-plus" \
  --limit 50 \
  --format json

# 에러 로그만
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
  --limit 20
```

---

## 🛡️ 보안

### API 키 관리

```bash
# Secret Manager에 API 키 저장
echo -n "${OPENAI_API_KEY}" | \
  gcloud secrets create openai-api-key --data-file=-

echo -n "${GOOGLE_API_KEY}" | \
  gcloud secrets create google-api-key --data-file=-

# Cloud Run에서 Secret 사용
gcloud run services update px-plus \
  --update-secrets OPENAI_API_KEY=openai-api-key:latest \
  --update-secrets GOOGLE_API_KEY=google-api-key:latest \
  --region asia-northeast3
```

### 네트워크 보안

```bash
# VPC Connector 사용 (Memorystore 접근)
gcloud compute networks vpc-access connectors create px-plus-connector \
  --region asia-northeast3 \
  --network default \
  --range 10.8.0.0/28

# Cloud Run에 VPC Connector 연결
gcloud run services update px-plus \
  --vpc-connector px-plus-connector \
  --region asia-northeast3
```

---

## 🧹 유지보수

### 캐시 관리

```bash
# 캐시 통계 확인
curl "https://px-plus-xxx.run.app/api/v1/web-enhancement/cache/stats"

# 캐시 삭제
curl -X DELETE "https://px-plus-xxx.run.app/api/v1/web-enhancement/cache/clear"
```

### 배포 롤백

```bash
# 이전 버전으로 롤백
gcloud run services update-traffic px-plus \
  --to-revisions PREVIOUS=100 \
  --region asia-northeast3
```

### 스케일링 조정

```bash
# 최소/최대 인스턴스 조정
gcloud run services update px-plus \
  --min-instances 1 \
  --max-instances 20 \
  --region asia-northeast3
```

---

## 📈 비용 최적화

### 예상 비용 (월간)

| 항목 | 사용량 | 비용 |
|------|--------|------|
| Cloud Run | 10K requests | $5 |
| Memorystore | 1GB | $40 |
| OpenAI API | 7 calls/request | $50 |
| Gemini API | Fallback only | $5 |
| **총계** | | **$100** |

### 캐싱 효과

- **캐시 없음**: $100/월
- **캐시 50%**: $50/월 (50% 절감)
- **캐시 80%**: $20/월 (80% 절감)

---

## ✅ 체크리스트

### 배포 전

- [ ] 환경 변수 설정 완료
- [ ] Redis 연결 확인
- [ ] API 키 검증
- [ ] 로컬 테스트 성공

### 배포 후

- [ ] 헬스 체크 통과
- [ ] E2E 테스트 성공
- [ ] 캐시 동작 확인
- [ ] 모니터링 설정 완료

### 운영

- [ ] 알림 설정 (에러율 >5%)
- [ ] 로그 모니터링
- [ ] 주간 캐시 통계 확인
- [ ] 월간 비용 리뷰

---

**완료일**: 2025-10-13  
**문서**: 웹 강화 API 구현 완료
