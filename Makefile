# ========================================
# PX-Plus Makefile - Google Cloud Run Deployment
# ========================================

# ========================================
# 변수 설정
# ========================================
PROJECT_ID ?= hyper-personalization-ai
REGION ?= asia-northeast3
SERVICE_NAME ?= px-plus
IMAGE_NAME ?= px-plus
REGISTRY ?= gcr.io

# 프로덕션 설정
PORT ?= 8080
WORKERS ?= 2
MIN_INSTANCES ?= 1
MAX_INSTANCES ?= 20
CPU ?= 2
MEMORY ?= 2Gi
TIMEOUT ?= 300s

# 이미지 태그
GIT_COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo "latest")
IMAGE_TAG ?= $(GIT_COMMIT)
FULL_IMAGE_NAME := $(REGISTRY)/$(PROJECT_ID)/$(IMAGE_NAME):$(IMAGE_TAG)

# 색상 출력
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# ========================================
# 기본 타겟
# ========================================
.PHONY: help
help: ## 도움말 표시
	@echo "$(BLUE)PX-Plus Cloud Run Deployment Makefile$(NC)"
	@echo ""
	@echo "$(GREEN)사용 가능한 명령어:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)환경변수:$(NC)"
	@echo "  PROJECT_ID=$(PROJECT_ID)"
	@echo "  REGION=$(REGION)"
	@echo "  SERVICE_NAME=$(SERVICE_NAME)"
	@echo "  IMAGE_TAG=$(IMAGE_TAG)"
	@echo "  ENV=$(ENV)"

# ========================================
# 로컬 개발
# ========================================
.PHONY: dev
dev: ## 로컬 개발 서버 실행
	@echo "$(BLUE)로컬 개발 서버 시작...$(NC)"
	uvicorn src.main:app --host 0.0.0.0 --port 8002 --reload

.PHONY: docker-dev
docker-dev: ## Docker Compose로 로컬 개발 환경 실행
	@echo "$(BLUE)Docker Compose로 개발 환경 시작...$(NC)"
	docker-compose up --build

.PHONY: docker-down
docker-down: ## Docker Compose 환경 중지
	@echo "$(YELLOW)Docker Compose 환경 중지...$(NC)"
	docker-compose down

# ========================================
# 빌드
# ========================================
.PHONY: build
build: ## Docker 이미지 빌드
	@echo "$(BLUE)Docker 이미지 빌드 시작...$(NC)"
	@echo "이미지: $(FULL_IMAGE_NAME)"
	docker build --platform linux/amd64 -t $(IMAGE_NAME):latest -t $(FULL_IMAGE_NAME) .
	@echo "$(GREEN)✓ 빌드 완료$(NC)"

.PHONY: build-no-cache
build-no-cache: ## 캐시 없이 Docker 이미지 빌드
	@echo "$(BLUE)캐시 없이 Docker 이미지 빌드 시작...$(NC)"
	docker build --no-cache -t $(IMAGE_NAME):latest -t $(FULL_IMAGE_NAME) .
	@echo "$(GREEN)✓ 빌드 완료$(NC)"

# ========================================
# 배포
# ========================================
.PHONY: push
push: ## GCR에 이미지 푸시
	@echo "$(BLUE)GCR에 이미지 푸시 중...$(NC)"
	@echo "이미지: $(FULL_IMAGE_NAME)"
	docker push $(FULL_IMAGE_NAME)
	@echo "$(GREEN)✓ 푸시 완료$(NC)"

.PHONY: setup-secrets
setup-secrets: ## Secret Manager 설정
	@echo "$(BLUE)Secret Manager 설정 중...$(NC)"
	@chmod +x scripts/setup-secrets.sh
	@PROJECT_ID=$(PROJECT_ID) ./scripts/setup-secrets.sh .env.production
	@echo "$(GREEN)✓ Secret Manager 설정 완료$(NC)"

.PHONY: deploy
deploy: env-to-yaml ## 프로덕션 배포 (Secret Manager 사용)
	@echo "$(RED)프로덕션 환경에 배포하시겠습니까? [y/N]$(NC)"
	@read -r CONFIRM; \
	if [ "$$CONFIRM" = "y" ] || [ "$$CONFIRM" = "Y" ]; then \
		echo "$(BLUE)Cloud Run에 배포 중...$(NC)"; \
		echo "이미지: $(FULL_IMAGE_NAME)"; \
		gcloud run deploy $(SERVICE_NAME) \
			--image $(FULL_IMAGE_NAME) \
			--platform managed \
			--region $(REGION) \
			--project $(PROJECT_ID) \
			--allow-unauthenticated \
			--port $(PORT) \
			--min-instances $(MIN_INSTANCES) \
			--max-instances $(MAX_INSTANCES) \
			--cpu $(CPU) \
			--memory $(MEMORY) \
			--timeout $(TIMEOUT) \
			--env-vars-file config/env-vars-production.yaml \
			--update-secrets=GOOGLE_API_KEY=google-api-key:latest,OPENAI_API_KEY=openai-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,RAPIDAPI_KEY=rapidapi-key:latest,SECRET_KEY=secret-key:latest; \
		echo "$(GREEN)✓ 배포 완료$(NC)"; \
		$(MAKE) describe; \
	else \
		echo "$(YELLOW)배포 취소됨$(NC)"; \
	fi

.PHONY: deploy-full
deploy-full: build push setup-secrets deploy ## 전체 배포 프로세스 (빌드 + 푸시 + Secret 설정 + 배포)
	@echo "$(GREEN)✓ 전체 배포 완료$(NC)"

.PHONY: deploy-with-env
deploy-with-env: build push ## 환경 변수로 배포 (Secret Manager 권한 불필요)
	@echo "$(BLUE)환경 변수로 배포 중...$(NC)"
	@chmod +x scripts/deploy-with-env-vars.sh
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) SERVICE_NAME=$(SERVICE_NAME) \
		./scripts/deploy-with-env-vars.sh .env.production $(FULL_IMAGE_NAME)
	@echo "$(GREEN)✓ 배포 완료$(NC)"

# ========================================
# 환경변수 관리
# ========================================
.PHONY: env-to-yaml
env-to-yaml: ## .env.production → YAML 변환
	@echo "$(BLUE)프로덕션 환경변수를 YAML로 변환 중...$(NC)"
	@mkdir -p config
	@if [ -f .env.production ]; then \
		python3 scripts/env-to-yaml.py .env.production > config/env-vars-production.yaml 2>/dev/null; \
		echo "$(GREEN)✓ config/env-vars-production.yaml 생성 완료$(NC)"; \
	else \
		echo "$(RED)✗ .env.production 파일이 없습니다.$(NC)"; \
		exit 1; \
	fi

# ========================================
# Cloud Run 관리
# ========================================
.PHONY: logs
logs: ## Cloud Run 로그 확인
	@echo "$(BLUE)Cloud Run 로그 확인...$(NC)"
	gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$(SERVICE_NAME)" \
		--project $(PROJECT_ID) \
		--limit 50 \
		--format "table(timestamp,textPayload)"

.PHONY: describe
describe: ## Cloud Run 서비스 정보 확인
	@echo "$(BLUE)Cloud Run 서비스 정보:$(NC)"
	@gcloud run services describe $(SERVICE_NAME) \
		--platform managed \
		--region $(REGION) \
		--project $(PROJECT_ID) \
		--format="table(status.url,status.latestReadyRevisionName,spec.template.spec.containers[0].image)"

.PHONY: list
list: ## 모든 Cloud Run 서비스 목록
	@echo "$(BLUE)Cloud Run 서비스 목록:$(NC)"
	gcloud run services list \
		--platform managed \
		--region $(REGION) \
		--project $(PROJECT_ID)

.PHONY: traffic
traffic: ## 트래픽 분산 확인
	@echo "$(BLUE)트래픽 분산 확인:$(NC)"
	gcloud run services describe $(SERVICE_NAME) \
		--platform managed \
		--region $(REGION) \
		--project $(PROJECT_ID) \
		--format="table(status.traffic[].revisionName,status.traffic[].percent)"

.PHONY: revisions
revisions: ## 리비전 목록 확인
	@echo "$(BLUE)리비전 목록:$(NC)"
	gcloud run revisions list \
		--service $(SERVICE_NAME) \
		--platform managed \
		--region $(REGION) \
		--project $(PROJECT_ID)

# ========================================
# 롤백
# ========================================
.PHONY: rollback
rollback: ## 이전 리비전으로 롤백
	@echo "$(YELLOW)이전 리비전으로 롤백합니다...$(NC)"
	@PREV_REVISION=$$(gcloud run revisions list \
		--service $(SERVICE_NAME) \
		--platform managed \
		--region $(REGION) \
		--project $(PROJECT_ID) \
		--format="value(name)" \
		--limit 2 | tail -n 1); \
	echo "롤백 대상: $$PREV_REVISION"; \
	gcloud run services update-traffic $(SERVICE_NAME) \
		--to-revisions $$PREV_REVISION=100 \
		--platform managed \
		--region $(REGION) \
		--project $(PROJECT_ID)
	@echo "$(GREEN)✓ 롤백 완료$(NC)"

# ========================================
# 정리
# ========================================
.PHONY: clean
clean: ## 로컬 빌드 아티팩트 정리
	@echo "$(YELLOW)로컬 빌드 아티팩트 정리 중...$(NC)"
	rm -rf config/env-vars-*.yaml
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf uploads/*
	rm -rf logs/*
	@echo "$(GREEN)✓ 정리 완료$(NC)"

.PHONY: docker-clean
docker-clean: ## Docker 이미지 정리
	@echo "$(YELLOW)Docker 이미지 정리 중...$(NC)"
	docker rmi $(IMAGE_NAME):latest $(FULL_IMAGE_NAME) 2>/dev/null || true
	@echo "$(GREEN)✓ Docker 이미지 정리 완료$(NC)"

# ========================================
# 테스트
# ========================================
.PHONY: test
test: ## 단위 테스트 실행
	@echo "$(BLUE)단위 테스트 실행 중...$(NC)"
	pytest tests/ -v

.PHONY: test-cov
test-cov: ## 커버리지 포함 테스트 실행
	@echo "$(BLUE)커버리지 포함 테스트 실행 중...$(NC)"
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# ========================================
# 기본 타겟
# ========================================
.DEFAULT_GOAL := help
