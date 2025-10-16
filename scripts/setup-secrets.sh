#!/bin/bash
# ========================================
# Google Secret Manager 자동 설정 스크립트
# ========================================
# .env.production의 민감한 환경변수를 Secret Manager에 자동으로 생성/업데이트

set -e

# 색상 출력
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# 설정
PROJECT_ID="${PROJECT_ID:-hyper-personalization-ai}"
ENV_FILE="${1:-.env.production}"
REGION="${REGION:-asia-northeast3}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-623004189757-compute@developer.gserviceaccount.com}"

# 민감한 환경변수 키 목록
SENSITIVE_KEYS=(
    "GOOGLE_API_KEY"
    "OPENAI_API_KEY"
    "ANTHROPIC_API_KEY"
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
    "RAPIDAPI_KEY"
    "SECRET_KEY"
    "SLACK_WEBHOOK_URL"
    "OPENAI_MAX_TOKENS"
    "TERM_EXTRACTION_OPENAI_MAX_TOKENS"
)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Google Secret Manager 설정${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "프로젝트: ${PROJECT_ID}"
echo -e "환경 파일: ${ENV_FILE}"
echo ""

# .env 파일 존재 확인
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}✗ $ENV_FILE 파일을 찾을 수 없습니다.${NC}"
    exit 1
fi

# Secret Manager API 활성화 확인
echo -e "${BLUE}Secret Manager API 확인 중...${NC}"
if ! gcloud services list --enabled --project="$PROJECT_ID" --filter="name:secretmanager.googleapis.com" --format="value(name)" | grep -q secretmanager; then
    echo -e "${YELLOW}Secret Manager API 활성화 중...${NC}"
    gcloud services enable secretmanager.googleapis.com --project="$PROJECT_ID"
fi
echo -e "${GREEN}✓ Secret Manager API 활성화됨${NC}"
echo ""

# 각 민감한 변수에 대해 Secret 생성/업데이트
CREATED_COUNT=0
UPDATED_COUNT=0
SKIPPED_COUNT=0

for KEY in "${SENSITIVE_KEYS[@]}"; do
    # .env 파일에서 값 추출
    VALUE=$(grep "^${KEY}=" "$ENV_FILE" | cut -d'=' -f2- | sed 's/^"\|"$//g' | sed "s/^'\|'$//g")

    # 값이 비어있거나 플레이스홀더면 건너뛰기
    if [ -z "$VALUE" ] || [[ "$VALUE" == *"your-"* ]] || [[ "$VALUE" == *"placeholder"* ]]; then
        echo -e "${YELLOW}⊘ ${KEY}: 값이 없거나 플레이스홀더입니다. 건너뜀.${NC}"
        ((SKIPPED_COUNT++))
        continue
    fi

    # Secret 이름 (소문자 + 하이픈)
    SECRET_NAME=$(echo "$KEY" | tr '[:upper:]' '[:lower:]' | tr '_' '-')

    # Secret이 이미 존재하는지 확인
    if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
        echo -e "${YELLOW}📝 ${KEY}: Secret 업데이트 중 (${SECRET_NAME})...${NC}"
        echo -n "$VALUE" | gcloud secrets versions add "$SECRET_NAME" \
            --data-file=- \
            --project="$PROJECT_ID" &>/dev/null
        echo -e "${GREEN}✓ ${KEY}: Secret 업데이트 완료${NC}"
        ((UPDATED_COUNT++))
    else
        echo -e "${BLUE}🔐 ${KEY}: Secret 생성 중 (${SECRET_NAME})...${NC}"
        echo -n "$VALUE" | gcloud secrets create "$SECRET_NAME" \
            --data-file=- \
            --replication-policy="automatic" \
            --project="$PROJECT_ID" &>/dev/null
        echo -e "${GREEN}✓ ${KEY}: Secret 생성 완료${NC}"
        ((CREATED_COUNT++))
    fi

    # 서비스 계정에 접근 권한 부여 (이미 있으면 무시)
    gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor" \
        --project="$PROJECT_ID" &>/dev/null || true
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Secret Manager 설정 완료${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "생성: ${CREATED_COUNT}개"
echo -e "업데이트: ${UPDATED_COUNT}개"
echo -e "건너뜀: ${SKIPPED_COUNT}개"
echo -e "총: $((CREATED_COUNT + UPDATED_COUNT))개 Secret 처리됨"
echo ""
