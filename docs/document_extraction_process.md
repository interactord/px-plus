# Document Extraction API 개발 프로세스

## 목표
- 업로드된 문서들에서 텍스트를 추출하고 SpaCy `xx_sent_ud_sm` 모델을 이용해 약 2000자 단위로 청크를 생성한다.
- 허용된 파일(ppt/pptx, xls/xlsx, pdf, txt, md/markdown, json) 외에는 처리에서 제외한다.
- 모든 문서가 제외되는 경우 사용자에게 명확한 오류를 반환한다.

## 구현 단계
1. **의존성 확장**
   - `pyproject.toml`에 `spacy`, `python-multipart`, `python-pptx`, `openpyxl`, `pypdf`를 추가해 필요한 파서들과 업로드 지원을 활성화한다.
   - 배포 환경에서 `xx_sent_ud_sm` 모델이 없을 수 있으므로, 실행 시점에 모델이 없으면 다운로드하도록 처리한다.
2. **도메인 서비스 정의**
   - `FileTextExtractionService`: 확장자별로 텍스트를 추출한다.
     - 파워포인트는 `python-pptx`, 엑셀은 `openpyxl`, PDF는 `pypdf`, 나머지는 기본 디코딩으로 처리한다.
     - 텍스트가 비어 있을 경우 실패 결과를 반환해 후속 단계가 스킵 처리를 결정할 수 있게 한다.
   - `DocumentChunkingService`: SpaCy 모델을 로드하고 문장을 기준으로 청크를 만들며, 모델은 싱글톤으로 캐시한다.
3. **유즈케이스 작성**
   - `ExtractDocumentChunksUseCase`를 추가해 파일 리스트를 순회하며
     1) 지원 여부 확인
     2) 텍스트 추출
     3) 청크 분할
     을 차례로 수행한다.
   - 실패한 단계는 `SkippedDocument`로 수집하며, 성공한 결과는 `ProcessedDocument`에 청크와 문자 수를 담아 돌려준다.
   - 처리된 문서가 하나도 없다면 `Failure`를 반환해 API에서 400 에러를 발생시킨다.
4. **의존성 주입 구성**
   - `registry.py`에 새 서비스와 유즈케이스를 등록하고 싱글톤/프로토타입 스코프를 지정한다.
   - `dependencies.py`에 FastAPI DI 레이어를 추가한다.
5. **API 라우트 구현**
   - `routes.py`에 `POST /v1/document-extractor` 엔드포인트를 추가하고 멀티파트 업로드를 처리한다.
   - 업로드된 파일을 바이트로 읽어 유즈케이스에 전달하고, 결과를 DTO(`DocumentExtractionSummaryResponse`)로 직렬화한다.
   - 실패 시 `HTTPException(400)`으로 메시지를 전달한다.
6. **DTO 정의**
   - `ProcessedDocumentResponse`, `SkippedDocumentResponse`, `DocumentExtractionSummaryResponse`를 추가해 응답 스키마를 명확히 한다.
7. **검증**
   - 최소한 `python3 -m compileall src`를 실행해 구문 오류를 확인한다.
   - 통합 환경에서는 모델 다운로드와 대용량 파일 처리 관련 예외를 모니터링한다.

## 운영 시 고려사항
- SpaCy 모델 다운로드는 애플리케이션 최초 실행 시 진행되므로, 배포 전에 미리 모델을 준비하거나 캐시 위치를 공유하면 초기 응답 지연을 줄일 수 있다.
- 대용량 파일 처리나 추출 라이브러리에서 발생할 수 있는 예외에 대비해 로깅과 타임아웃 정책을 설정한다.
- 필요 시 `max_chars` 파라미터를 환경 변수로 노출해 청크 크기를 조정할 수 있다.
