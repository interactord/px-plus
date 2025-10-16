# 서버 로그 관리 가이드

## 개요

`run.sh` 스크립트는 서버 실행 시 자동으로 로그를 파일에 저장합니다.

## 로그 파일 위치

```
logs/
├── server_20251015_181217_port8000.log  # 타임스탬프가 포함된 실제 로그 파일
└── latest_port8000.log                   # 최신 로그 파일로의 심볼릭 링크
```

## 로그 파일 명명 규칙

```
server_<날짜>_<시간>_port<포트번호>.log
```

예시:
- `server_20251015_181217_port8000.log` - 2025년 10월 15일 18시 12분 17초에 시작된 포트 8000 서버
- `server_20251015_180500_port8005.log` - 2025년 10월 15일 18시 05분에 시작된 포트 8005 서버

## 사용 방법

### 1. 서버 시작 (기본 포트 8000)

```bash
./run.sh
```

로그 파일: `logs/server_<timestamp>_port8000.log`

### 2. 서버 시작 (커스텀 포트)

```bash
API_PORT=8005 ./run.sh
```

로그 파일: `logs/server_<timestamp>_port8005.log`

### 3. 실시간 로그 확인

**방법 1: 터미널 출력 (화면에 표시됨)**
- 서버 실행 시 자동으로 터미널에 출력됩니다.

**방법 2: 로그 파일 직접 확인**
```bash
# 최신 로그 확인 (포트 8000)
tail -f logs/latest_port8000.log

# 특정 로그 파일 확인
tail -f logs/server_20251015_181217_port8000.log

# 로그에서 에러만 필터링
tail -f logs/latest_port8000.log | grep ERROR

# SSL 관련 로그만 확인
tail -f logs/latest_port8000.log | grep SSL
```

### 4. 로그 검색

```bash
# SSL 오류 검색
grep "SSL.*CERTIFICATE_VERIFY_FAILED" logs/latest_port8000.log

# Gemini 관련 로그 검색
grep "Gemini" logs/latest_port8000.log

# 특정 시간대 로그 검색
grep "18:10:" logs/latest_port8000.log

# 여러 로그 파일에서 검색
grep -r "ERROR" logs/
```

## 로그 파일 구조

각 로그 파일은 다음과 같은 헤더로 시작합니다:

```
================================================================================
PX-Plus Server Log
================================================================================
시작 시간: 2025-10-15 18:12:17
포트: 8000
로그 파일: logs/server_20251015_181217_port8000.log
================================================================================
```

## 로그 레벨

서버는 다음과 같은 로그 레벨을 사용합니다:

- `INFO`: 일반 정보 (서버 시작, API 호출 등)
- `WARNING`: 주의 필요 (SSL 비활성화 등)
- `ERROR`: 오류 발생 (SSL 인증서 오류, API 실패 등)
- `DEBUG`: 디버그 정보 (상세한 실행 정보)

## 로그 관리

### 오래된 로그 삭제

```bash
# 7일 이상된 로그 삭제
find logs/ -name "*.log" -mtime +7 -delete

# 특정 날짜 이전 로그 삭제
rm logs/server_202510{01..14}_*.log
```

### 로그 압축

```bash
# 오늘 로그를 제외한 모든 로그 압축
find logs/ -name "server_*.log" ! -name "*$(date +%Y%m%d)*" -exec gzip {} \;
```

## 트러블슈팅

### 문제: SSL 인증서 오류가 로그에 표시됨

```bash
# SSL 오류 확인
grep "CERTIFICATE_VERIFY_FAILED" logs/latest_port8000.log
```

**해결 방법**: [SSL_FIX_FINAL_REPORT.md](../SSL_FIX_FINAL_REPORT.md) 참조

### 문제: 로그 파일이 생성되지 않음

```bash
# logs 디렉토리 확인
ls -la logs/

# 권한 확인
ls -ld logs/
```

**해결 방법**:
```bash
# logs 디렉토리 생성
mkdir -p logs

# 권한 설정
chmod 755 logs
```

### 문제: 로그 파일이 너무 큼

```bash
# 로그 파일 크기 확인
du -sh logs/*

# 큰 로그 파일 찾기
find logs/ -size +100M
```

**해결 방법**: 로그 로테이션 또는 압축 사용

## 참고 문서

- [SSL 인증서 문제 해결](../SSL_FIX_FINAL_REPORT.md)
- [Gemini SDK 인증서 플로우](../GEMINI_SDK_CERTIFICATE_FLOW.md)
