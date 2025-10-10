# 웹 데모 페이지 가이드

## 개요

PX-Plus의 문서 텍스트 추출 기능을 테스트할 수 있는 웹 기반 데모 페이지입니다.

## 접속 방법

서버 실행 후 다음 URL로 접속:

```
http://localhost:8000/demo/document-extractor
```

## 주요 기능

### 1. 파일 업로드
- **드래그 앤 드롭**: 파일을 드래그하여 업로드 영역에 드롭
- **파일 선택**: 클릭하여 파일 선택 대화상자 열기
- **다중 파일**: 한 번에 최대 10개 파일 업로드 가능

### 2. 파일 검증
자동으로 다음 항목을 검증합니다:

- **파일 확장자**: `.txt`, `.md`, `.pdf`, `.docx`, `.xlsx`, `.csv`, `.json`, `.pptx`, `.ppt`
- **개별 파일 크기**: 최대 10MB
- **전체 파일 크기**: 최대 20MB (모든 파일 합계)
- **파일 개수**: 최대 10개

### 3. 텍스트 추출 및 결과 표시

#### 청크 카드 뷰
- 추출된 텍스트를 청크 단위로 카드 형식으로 표시
- 각 청크마다 파일명, 텍스트 내용, 문자 수 표시
- 읽기 쉬운 UI 제공

#### JSON 뷰
- "JSON 보기" 버튼 클릭하여 원본 JSON 데이터 확인
- API 응답 구조 확인 가능
- 개발 및 디버깅에 유용

## 사용 예시

### 정상적인 파일 업로드

1. 데모 페이지 접속
2. `.txt` 또는 `.md` 파일 준비
3. 파일을 드래그하거나 선택
4. "텍스트 추출 시작" 버튼 클릭
5. 결과 확인

### 검증 실패 예시

#### 확장자 검증 실패
```
업로드: test.bin
결과: ❌ 'test.bin': 허용되지 않는 파일 형식입니다.
```

#### 파일 크기 초과
```
업로드: large_file.txt (15MB)
결과: ❌ 'large_file.txt': 파일 크기가 최대 크기(10.0 MB)를 초과했습니다. (현재: 15.0 MB)
```

#### 전체 크기 초과
```
업로드: file1.txt (8MB), file2.txt (8MB), file3.txt (8MB)
결과: ❌ 전체 파일 크기가 최대 총합(20.0 MB)을 초과했습니다. (현재: 24.0 MB)
```

## 기술 구현

### 프론트엔드
- **원페이지 HTML**: HTML, CSS, JavaScript 모두 단일 파일에 포함
- **Vanilla JavaScript**: 프레임워크 없이 순수 JavaScript 사용
- **반응형 디자인**: 모바일, 태블릿, 데스크탑 지원
- **접근성**: ARIA 레이블, 키보드 네비게이션 지원

### 백엔드 라우팅
- **GET `/demo/document-extractor`**: 데모 페이지 HTML 서빙
- **POST `/v1/document-extractor`**: 실제 API 엔드포인트

### 파일 구조
```
px-plus/
├── static/
│   └── demo-upload.html        # 원페이지 데모 HTML
├── src/
│   ├── main.py                 # /demo/** 라우팅 추가
│   └── infrastructure/
│       └── web/
│           ├── routes.py       # /v1/document-extractor API
│           └── validators.py   # 파일 검증 로직
```

## API 응답 형식

### 성공 응답
```json
{
  "processed": [
    {
      "filename": "example.txt",
      "total_characters": 183,
      "total_chunks": 1,
      "chunks": [
        "추출된 텍스트 내용..."
      ]
    }
  ],
  "skipped": []
}
```

### 에러 응답
```json
{
  "detail": "에러 메시지"
}
```

## 환경 설정

데모 페이지는 `.env` 파일의 다음 설정을 사용합니다:

```bash
# 단일 파일 최대 크기 (바이트)
MAX_FILE_SIZE=10485760

# 전체 파일 총합 최대 크기 (바이트)
MAX_TOTAL_FILE_SIZE=20971520

# 최대 파일 개수
MAX_FILES=10

# 허용 확장자
ALLOWED_EXTENSIONS=.txt,.md,.pdf,.docx,.xlsx,.csv,.json,.pptx,.ppt
```

## 향후 개선 사항

- [ ] 파일 형식별 아이콘 표시
- [ ] 추출 진행률 표시
- [ ] 다국어 지원
- [ ] 다크 모드 지원
- [ ] 결과 다운로드 기능
- [ ] 파일 미리보기 기능

## 문제 해결

### 페이지가 로드되지 않음
```bash
# static/ 폴더 및 파일 확인
ls -la static/demo-upload.html

# 서버 재시작
./run.sh dev
```

### API 호출 실패
```bash
# API 엔드포인트 확인
curl http://localhost:8000/v1/document-extractor

# 서버 로그 확인
tail -f logs/app.log
```

### 파일 업로드 실패
- 파일 크기 확인
- 파일 확장자 확인
- 브라우저 콘솔 로그 확인

## 관련 문서

- [API Routing Analysis](./api-routing-analysis.md)
- [File Upload Validation](./file-upload-validation.md)
- [API Documentation](http://localhost:8000/docs)
