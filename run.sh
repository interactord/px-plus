#!/bin/bash

# PX-Plus FastAPI 서버 실행 스크립트

set -e  # 에러 발생 시 스크립트 종료

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 포트 설정
PORT=8000

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}PX-Plus: FastAPI + RFS Framework${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 기존 포트 사용 중인 프로세스 종료
echo -e "${YELLOW}포트 ${PORT} 확인 중...${NC}"
PID=$(lsof -ti:${PORT} 2>/dev/null || echo "")

if [ ! -z "$PID" ]; then
    echo -e "${RED}⚠️  포트 ${PORT}를 사용 중인 프로세스(PID: ${PID})를 발견했습니다.${NC}"
    echo -e "${YELLOW}기존 프로세스를 종료합니다...${NC}"
    kill -9 $PID 2>/dev/null || true
    sleep 1
    echo -e "${GREEN}✅ 기존 프로세스 종료 완료${NC}"
else
    echo -e "${GREEN}✅ 포트 ${PORT}는 사용 가능합니다.${NC}"
fi
echo ""

# 가상환경 확인
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}가상환경이 없습니다. 생성 중...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✅ 가상환경 생성 완료${NC}"
fi

# 가상환경 활성화
echo -e "${YELLOW}가상환경 활성화 중...${NC}"
source .venv/bin/activate

# 의존성 설치 확인
echo -e "${YELLOW}의존성 확인 중...${NC}"
if ! .venv/bin/python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}의존성 설치 중...${NC}"
    .venv/bin/pip install --quiet fastapi "uvicorn[standard]" pydantic
    echo -e "${GREEN}✅ 의존성 설치 완료${NC}"
else
    echo -e "${GREEN}✅ 의존성 확인 완료${NC}"
fi

# 서버 실행
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}서버 시작 중...${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}📍 서버 주소: http://localhost:8000${NC}"
echo -e "${YELLOW}📚 API 문서: http://localhost:8000/docs${NC}"
echo -e "${YELLOW}📖 ReDoc: http://localhost:8000/redoc${NC}"
echo ""
echo -e "${YELLOW}종료하려면 Ctrl+C를 누르세요${NC}"
echo ""

# Uvicorn 서버 실행
.venv/bin/uvicorn src.main:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --reload \
    --log-level info
