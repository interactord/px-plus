# 용어 추출 시스템 아키텍처 설계

## 1. 개요

본 문서는 청크로 잘려진 텍스트에서 고유명사와 Primary Domain을 추출하는 시스템의 아키텍처를 정의합니다.

### 1.1 시스템 목적

- 문서를 청크 단위로 분할하여 GPT-4o를 사용한 용어 추출
- LLM 캐싱을 통한 빠른 처리 속도 제공
- 3개 워커 스레드를 활용한 병렬 처리
- 헥사고날 아키텍처 기반의 확장 가능한 구조

### 1.2 핵심 요구사항

1. **입력**: JSON 형식의 청크 데이터 (파일명 + 청크 배열)
2. **처리**: gpt-4o 모델을 사용한 용어 추출
3. **템플릿**: Jinja2 기반 프롬프트 관리
4. **캐싱**: LLM 응답 캐싱으로 성능 최적화
5. **병렬처리**: 3개 워커 스레드로 동시 처리
6. **출력**: 구조화된 JSON 응답 (엔티티 배열)

## 2. 아키텍처 개요

### 2.1 레이어 구조

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │  POST /api/v1/extract-terms/process-documents   │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│              Application Layer                          │
│  ┌────────────────────────────────────────────┐         │
│  │   CachedTermExtractionService              │         │
│  │     ├─ Cache Check                         │         │
│  │     └─ TermExtractionService               │         │
│  │          ├─ ParallelExecutor (3 workers)   │         │
│  │          └─ Batch Processing               │         │
│  └────────────────────────────────────────────┘         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│                 Domain Layer                            │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Entities:                                       │   │
│  │    - ExtractedEntity (term, type, domain, ...)  │   │
│  │    - ExtractionResult (entities list)           │   │
│  │  Value Objects:                                  │   │
│  │    - ChunkText                                   │   │
│  │    - EntityType (enum)                           │   │
│  │  Ports:                                          │   │
│  │    - TermExtractionPort                          │   │
│  │    - CachePort                                   │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│            Infrastructure Layer                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Adapters:                                       │   │
│  │    - OpenAITermExtractor                         │   │
│  │      └─ Uses: OpenAIChatAdapter (ai_model)      │   │
│  │    - MemoryCacheAdapter                          │   │
│  │  Executors:                                      │   │
│  │    - ParallelExecutor (asyncio + ThreadPool)    │   │
│  │  Templates:                                      │   │
│  │    - Jinja2TemplateAdapter (ai_model)           │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 기존 시스템 통합

본 시스템은 기존에 구현된 `ai_model` 시스템을 활용합니다:

**재사용 컴포넌트**:
- `ModelPort`: LLM 실행 인터페이스
- `OpenAIChatAdapter`: GPT-4o 통신
- `Jinja2TemplateAdapter`: 프롬프트 템플릿 렌더링
- `ModelExecutionService`: 템플릿 기반 실행
- `Result` 패턴: 함수형 에러 처리

**새로 추가되는 컴포넌트**:
- `TermExtractionPort`: 용어 추출 특화 인터페이스
- `CachePort`: 캐싱 추상화
- `ParallelExecutor`: 병렬 처리 엔진
- Term Extraction Domain 모델들

## 3. 핵심 컴포넌트

### 3.1 Domain Layer

#### 3.1.1 Value Objects

**ChunkText**
```python
@dataclass(frozen=True)
class ChunkText:
    """청크로 분할된 텍스트"""
    content: str
    chunk_index: int
    source_filename: str
    
    def cache_key(self) -> str:
        """캐시 키 생성"""
        return hashlib.sha256(self.content.encode()).hexdigest()
```

**EntityType**
```python
class EntityType(str, Enum):
    """추출 가능한 엔티티 타입"""
    PERSON = "person"
    COMPANY = "company"
    PRODUCT = "product"
    TECHNICAL_TERM = "technical_term"
```

#### 3.1.2 Entities

**ExtractedEntity**
```python
@dataclass(frozen=True)
class ExtractedEntity:
    """추출된 엔티티"""
    term: str
    type: EntityType
    primary_domain: str
    tags: List[str]
    context: str
    multilingual_expressions: Optional[Dict[str, str]]
```

**ExtractionResult**
```python
@dataclass(frozen=True)
class ExtractionResult:
    """청크 단위 추출 결과"""
    chunk: ChunkText
    entities: List[ExtractedEntity]
    cached: bool
    processing_time: float
```

#### 3.1.3 Ports

**TermExtractionPort**
```python
class TermExtractionPort(ABC):
    @abstractmethod
    def extract(self, chunk: ChunkText) -> Result[ExtractionResult, str]:
        """청크에서 용어 추출"""
        pass
```

**CachePort**
```python
class CachePort(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[ExtractionResult]:
        """캐시에서 결과 조회"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: ExtractionResult, ttl: int = 86400):
        """캐시에 결과 저장 (기본 TTL: 24시간)"""
        pass
```

### 3.2 Application Layer

#### 3.2.1 DTOs

**ExtractionRequestDTO**
```python
@dataclass
class ExtractionRequestDTO:
    """용어 추출 요청"""
    processed: List[Dict[str, Any]]  # [{filename, chunks}]
    use_cache: bool = True
    parallel_workers: int = 3
    template_name: str = "extract_terms.j2"
```

**ExtractionResponseDTO**
```python
@dataclass
class ExtractionResponseDTO:
    """용어 추출 응답"""
    results: List[Dict[str, Any]]
    summary: Dict[str, Any]
```

#### 3.2.2 Services

**TermExtractionService**
```python
class TermExtractionService:
    """용어 추출 오케스트레이션"""
    
    def __init__(
        self,
        extractor: TermExtractionPort,
        executor: ParallelExecutor
    ):
        self._extractor = extractor
        self._executor = executor
    
    async def extract_from_documents(
        self,
        request: ExtractionRequestDTO
    ) -> Result[ExtractionResponseDTO, str]:
        """문서들에서 병렬로 용어 추출"""
        pass
```

**CachedTermExtractionService**
```python
class CachedTermExtractionService:
    """캐싱 레이어가 추가된 용어 추출"""
    
    def __init__(
        self,
        service: TermExtractionService,
        cache: CachePort
    ):
        self._service = service
        self._cache = cache
    
    async def extract_with_cache(
        self,
        request: ExtractionRequestDTO
    ) -> Result[ExtractionResponseDTO, str]:
        """캐시를 활용한 용어 추출"""
        pass
```

### 3.3 Infrastructure Layer

#### 3.3.1 Adapters

**OpenAITermExtractor**
```python
class OpenAITermExtractor(TermExtractionPort):
    """OpenAI를 사용한 용어 추출 구현"""
    
    def __init__(
        self,
        model_service: ModelExecutionService,
        template_name: str = "extract_terms.j2"
    ):
        self._model_service = model_service
        self._template_name = template_name
    
    def extract(self, chunk: ChunkText) -> Result[ExtractionResult, str]:
        """OpenAI API로 용어 추출"""
        # 1. 템플릿 컨텍스트 구성
        # 2. ModelExecutionService 호출
        # 3. JSON 파싱 및 Entity 변환
        # 4. ExtractionResult 생성
        pass
```

**MemoryCacheAdapter**
```python
class MemoryCacheAdapter(CachePort):
    """인메모리 캐시 구현 (기본)"""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, Tuple[ExtractionResult, float]] = {}
        self._max_size = max_size
    
    def get(self, key: str) -> Optional[ExtractionResult]:
        """캐시 조회"""
        pass
    
    def set(self, key: str, value: ExtractionResult, ttl: int = 86400):
        """캐시 저장"""
        pass
```

#### 3.3.2 Executors

**ParallelExecutor**
```python
class ParallelExecutor:
    """병렬 처리 엔진"""
    
    def __init__(self, num_workers: int = 3):
        self._num_workers = num_workers
        self._executor = ThreadPoolExecutor(max_workers=num_workers)
    
    async def execute_batch(
        self,
        chunks: List[ChunkText],
        extractor: TermExtractionPort
    ) -> List[Result[ExtractionResult, str]]:
        """청크 배치 병렬 처리"""
        # asyncio.gather()로 병렬 실행
        pass
```

## 4. 데이터 흐름

### 4.1 정상 흐름 (Cache Miss)

```
1. API Request
   └─> ExtractionRequestDTO
   
2. CachedTermExtractionService
   ├─> Cache Check (miss)
   └─> TermExtractionService
   
3. TermExtractionService
   ├─> ChunkText 생성
   └─> ParallelExecutor
   
4. ParallelExecutor (3 workers)
   ├─> Worker 1: Chunk 0, 3, 6, ...
   ├─> Worker 2: Chunk 1, 4, 7, ...
   └─> Worker 3: Chunk 2, 5, 8, ...
   
5. OpenAITermExtractor (per chunk)
   ├─> Template rendering (Jinja2)
   ├─> ModelExecutionService call
   ├─> OpenAIChatAdapter (gpt-4o)
   └─> JSON parsing
   
6. Results aggregation
   ├─> Cache storage
   └─> ExtractionResponseDTO
   
7. API Response
```

### 4.2 캐시 히트 흐름

```
1. API Request
   └─> ExtractionRequestDTO
   
2. CachedTermExtractionService
   ├─> Cache Check (hit!)
   └─> Return cached result
   
3. API Response (fast path)
```

## 5. 성능 최적화

### 5.1 LLM 캐싱 전략

**OpenAI Prompt Caching 활용**:
```python
# System message는 캐싱되도록 구성
messages = [
    {
        "role": "system",
        "content": system_prompt,  # 고정 내용 → 캐시됨
    },
    {
        "role": "user",
        "content": f"Extract from: {chunk_text}"  # 변경 내용
    }
]
```

**Application-level Caching**:
- Key: `sha256(chunk_content + template_name)`
- TTL: 24시간 (설정 가능)
- 동일 청크 재처리 시 즉시 반환

### 5.2 병렬 처리 전략

**워커 분배**:
```python
# 3 workers로 균등 분배
chunks = [chunk0, chunk1, chunk2, chunk3, chunk4, chunk5, ...]

Worker 1: [chunk0, chunk3, chunk6, ...]
Worker 2: [chunk1, chunk4, chunk7, ...]
Worker 3: [chunk2, chunk5, chunk8, ...]
```

**성능 목표**:
- 100 청크 처리: ~30초 (캐시 없이)
- 100 청크 처리: ~1초 (캐시 히트)
- 워커당 처리 속도: ~3초/청크

## 6. 에러 처리

### 6.1 에러 타입

1. **청크 레벨 에러**: 개별 청크 처리 실패
   - 전략: 부분 성공 반환
   - Result 패턴으로 실패 캡슐화

2. **템플릿 에러**: 프롬프트 렌더링 실패
   - 전략: Fallback 템플릿 사용
   - 기본 템플릿으로 재시도

3. **OpenAI API 에러**: Rate limit, timeout 등
   - 전략: 지수 백오프 재시도 (최대 3회)
   - Circuit breaker 패턴 적용

4. **JSON 파싱 에러**: LLM 응답 파싱 실패
   - 전략: Raw text 응답 반환
   - 에러 로깅 및 알림

### 6.2 Result 패턴 활용

```python
# Success case
result = Success(ExtractionResult(...))

# Failure case
result = Failure("OpenAI API timeout")

# Chaining
result = (
    create_chunk(text)
    .bind(lambda chunk: extract_terms(chunk))
    .bind(lambda entities: validate_entities(entities))
    .map(lambda entities: to_dto(entities))
)
```

## 7. 확장성 고려사항

### 7.1 수평 확장

- **현재**: 단일 서버, 3 워커
- **확장**: 
  - 다중 FastAPI 인스턴스
  - 분산 캐시 (Redis Cluster)
  - 메시지 큐 (RabbitMQ, Kafka)

### 7.2 모델 확장

- **현재**: gpt-4o
- **확장**: 
  - 다른 OpenAI 모델
  - Claude, Gemini 등 타 LLM
  - 로컬 모델 (Ollama)

### 7.3 캐시 확장

- **현재**: In-memory
- **확장**:
  - Redis
  - Memcached
  - Database-backed cache

## 8. 모니터링 및 관측성

### 8.1 메트릭

- **처리량**: 청크/초
- **레이턴시**: P50, P95, P99
- **캐시 히트율**: %
- **에러율**: 청크 실패 비율
- **LLM 비용**: 토큰 사용량

### 8.2 로깅

```python
logger.info(
    "Chunk processed",
    extra={
        "chunk_index": chunk.chunk_index,
        "filename": chunk.source_filename,
        "entities_count": len(result.entities),
        "cached": result.cached,
        "processing_time": result.processing_time
    }
)
```

## 9. 보안 고려사항

### 9.1 입력 검증

- 청크 크기 제한: 최대 10,000자
- 파일 개수 제한: 최대 100개
- Rate limiting: IP당 100 req/min

### 9.2 민감정보 처리

- API 키: 환경변수 관리
- 청크 데이터: 로깅 시 마스킹
- 캐시 데이터: TTL 설정으로 자동 삭제

## 10. 배포 전략

### 10.1 환경 구성

- **개발**: SQLite cache, 1 worker
- **스테이징**: Redis cache, 3 workers
- **프로덕션**: Redis cluster, 5+ workers

### 10.2 의존성

```
- FastAPI >= 0.104.0
- httpx >= 0.27.0
- jinja2 >= 3.1.4
- asyncio (표준 라이브러리)
- rfs-framework (Result, HOF 등)
```

## 11. 다음 단계

1. **Phase 2**: Domain Layer 구현
2. **Phase 3**: Application Layer 구현
3. **Phase 4**: Infrastructure Layer 구현
4. **Phase 5**: Template 배치
5. **Phase 6**: API 엔드포인트 구현
6. **Phase 7**: 통합 테스트 및 성능 검증
