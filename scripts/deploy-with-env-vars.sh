#!/bin/bash
# ========================================
# Cloud Run 배포 스크립트 (환경 변수 직접 설정)
# ========================================
# Secret Manager 권한 없이 .env.production의 모든 변수를 환경 변수로 설정

set -e

# 색상 출력
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# 설정
PROJECT_ID="${PROJECT_ID:-hyper-personalization-ai}"
REGION="${REGION:-asia-northeast3}"
SERVICE_NAME="${SERVICE_NAME:-px-plus}"
ENV_FILE="${1:-.env.production}"
IMAGE="${2}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Cloud Run 환경 변수 배포${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "프로젝트: ${PROJECT_ID}"
echo -e "환경 파일: ${ENV_FILE}"
echo -e "이미지: ${IMAGE}"
echo ""

# .env 파일 존재 확인
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}✗ $ENV_FILE 파일을 찾을 수 없습니다.${NC}"
    exit 1
fi

# 이미지 확인
if [ -z "$IMAGE" ]; then
    echo -e "${RED}✗ 이미지를 지정해주세요.${NC}"
    echo "Usage: $0 <env-file> <image>"
    exit 1
fi

# .env 파일을 KEY=VALUE 형식으로 변환 (gcloud 형식)
echo -e "${BLUE}.env 파일 파싱 중...${NC}"

ENV_VARS=""
COUNT=0

while IFS= read -r line; do
    # 주석이나 빈 줄 건너뛰기
    if [[ -z "$line" ]] || [[ "$line" =~ ^#.* ]] || [[ "$line" =~ ^=.* ]]; then
        continue
    fi

    # KEY=VALUE 형식인지 확인
    if [[ "$line" =~ ^[A-Z_][A-Z0-9_]*=.* ]]; then
        KEY=$(echo "$line" | cut -d'=' -f1)
        VALUE=$(echo "$line" | cut -d'=' -f2- | sed 's/^"\|"$//g' | sed "s/^'\|'$//g")

        # 값이 비어있거나 플레이스홀더면 건너뛰기
        if [ -z "$VALUE" ] || [[ "$VALUE" == *"your-"* ]] || [[ "$VALUE" == *"placeholder"* ]]; then
            continue
        fi

        # 특수문자 이스케이프 (쉼표, 등호, 대괄호 등)
        # gcloud는 ^^ 구분자를 사용하여 특수문자 처리
        ESCAPED_VALUE=$(echo "$VALUE" | sed 's/,/^^/g' | sed 's/\[/^^/g' | sed 's/\]/^^/g')

        # 환경 변수 문자열 구성
        if [ -z "$ENV_VARS" ]; then
            ENV_VARS="${KEY}=${ESCAPED_VALUE}"
        else
            ENV_VARS="${ENV_VARS},${KEY}=${ESCAPED_VALUE}"
        fi

        ((COUNT++))
        echo -e "${GREEN}✓ ${KEY}${NC}"
    fi
done < "$ENV_FILE"

echo ""
echo -e "${GREEN}총 ${COUNT}개 환경 변수 추출 완료${NC}"
echo ""

# Cloud Run 배포 (2단계: Secret 제거 → 환경 변수 설정)
echo -e "${BLUE}Cloud Run 서비스 업데이트 중...${NC}"
echo -e "${YELLOW}1단계: 기존 Secret 및 환경 변수 제거${NC}"

gcloud run services update "$SERVICE_NAME" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --clear-secrets \
    --clear-env-vars

echo -e "${YELLOW}2단계: 새로운 환경 변수 및 VPC Connector 설정${NC}"

gcloud run services update "$SERVICE_NAME" \
    --image "$IMAGE" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --vpc-connector "hp-connector" \
    --vpc-egress "private-ranges-only" \
    --set-env-vars "$ENV_VARS"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}배포 완료${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 서비스 URL 확인
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --format="value(status.url)")

echo -e "${BLUE}서비스 URL:${NC} ${SERVICE_URL}"
echo ""
