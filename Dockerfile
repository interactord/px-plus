# ========================================
# PX-Plus Dockerfile for Google Cloud Run
# ========================================
# Multi-stage build for optimal image size

# ========================================
# Stage 1: Builder
# ========================================
FROM python:3.10-slim as builder

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# spacy 모델 다운로드 (한국어 + 다국어 문장 분리)
RUN python -m spacy download ko_core_news_sm && \
    python -m spacy download xx_sent_ud_sm

# ========================================
# Stage 2: Runtime
# ========================================
FROM python:3.10-slim

# 메타데이터
LABEL maintainer="sangbong@example.com"
LABEL description="PX-Plus FastAPI Application for Google Cloud Run"

# 비root 사용자 생성
RUN useradd -m -u 1000 appuser

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (최소한만)
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 복사 (전역 site-packages 포함)
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 환경변수 설정
ENV PATH=/usr/local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# 애플리케이션 코드 복사
COPY --chown=appuser:appuser . .

# 필요한 디렉토리 생성
RUN mkdir -p /app/uploads /app/logs && \
    chown -R appuser:appuser /app

# 비root 사용자로 전환
USER appuser

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:${PORT}/health', timeout=5)"

# Cloud Run에서 포트를 동적으로 할당하므로 PORT 환경변수 사용
# LOG_LEVEL을 소문자로 변환 (uvicorn 요구사항)
CMD sh -c 'LOG_LEVEL_LOWER=$(echo "${LOG_LEVEL:-INFO}" | tr "[:upper:]" "[:lower:]"); \
    exec uvicorn src.main:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --workers ${WORKERS:-1} \
    --log-level $LOG_LEVEL_LOWER \
    --no-access-log'
