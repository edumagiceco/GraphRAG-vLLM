# Research: GraphRAG Chatbot Platform

**Date**: 2025-12-22
**Branch**: `001-graphrag-chatbot-platform`

## 1. GraphRAG 구현 전략

### Decision
Microsoft GraphRAG 아키텍처를 참조하되, 경량화된 커스텀 구현 채택

### Rationale
- Microsoft GraphRAG는 전체 문서를 커뮤니티 요약하는 방식으로 비용이 높음
- 본 프로젝트는 로컬 LLM 사용으로 비용 제약이 적지만, 처리 시간 최적화 필요
- 엔티티-관계 추출 → 그래프 구축 → Hybrid Retrieval 방식이 적합

### Alternatives Considered
| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| LlamaIndex PropertyGraph | 통합 프레임워크 | Neo4j 외 그래프 DB 지원 제한 |
| LangChain Graph RAG | 유연한 체인 구성 | 그래프 탐색 최적화 부족 |
| 순수 Vector RAG | 간단한 구현 | 복잡한 관계 추론 불가 |

### Implementation Notes
```python
# Hybrid Retrieval 흐름
1. Vector Search: ChromaDB에서 Top-K 청크 검색
2. Entity Extraction: 검색된 청크에서 엔티티 식별
3. Graph Expansion: Neo4j에서 2-hop 관계 탐색
4. Context Assembly: 우선순위 기반 컨텍스트 조립
5. LLM Generation: Ollama로 답변 생성 + 출처 표시
```

---

## 2. Graph Database 선택

### Decision
Neo4j Community Edition (Docker)

### Rationale
- 성숙한 그래프 데이터베이스로 Cypher 쿼리 지원
- Docker 이미지 제공으로 MSA 아키텍처 적합
- Python 드라이버(neo4j-python-driver) 안정성
- 멀티테넌트: 라벨/프로퍼티로 챗봇 서비스별 격리 가능

### Alternatives Considered
| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| NetworkX (in-memory) | 간단, 의존성 없음 | 영속성 없음, 대용량 불가 |
| ArangoDB | 멀티모델 | 학습 곡선, 커뮤니티 규모 |
| Memgraph | 빠른 성능 | 라이선스 제약 |

### Configuration
```yaml
# docker-compose.yml
neo4j:
  image: neo4j:5.15-community
  environment:
    NEO4J_AUTH: neo4j/password
    NEO4J_PLUGINS: '["apoc"]'
  ports:
    - "7474:7474"  # Browser
    - "7687:7687"  # Bolt
```

---

## 3. Vector Store 선택

### Decision
Qdrant (Docker)

### Rationale
- 고성능 벡터 검색 엔진
- 강력한 필터링 및 페이로드 지원
- Docker 이미지 제공으로 로컬 실행 가능
- LangChain 통합 지원 (langchain-qdrant)
- 컬렉션 기반 멀티테넌트 지원
- REST API 및 gRPC 지원

### Alternatives Considered
| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| Pinecone | 관리형, 확장성 | 외부 서비스 의존 (Constitution 위반) |
| Milvus | 고성능 | 운영 복잡성 |
| FAISS | 빠른 검색 | 영속성/관리 기능 부족 |
| ChromaDB | 간단한 설치 | 대규모 확장성 제한 |

### Configuration
```yaml
# docker-compose.yml
qdrant:
  image: qdrant/qdrant:latest
  ports:
    - "6333:6333"  # REST API
    - "6334:6334"  # gRPC
  volumes:
    - qdrant_storage:/qdrant/storage
```

```python
# 챗봇 서비스별 컬렉션 분리
from qdrant_client import QdrantClient

client = QdrantClient(host="qdrant", port=6333)
collection_name = f"chatbot_{chatbot_id}_v{version}"
```

---

## 4. PDF 처리 파이프라인

### Decision
pdfplumber + LangChain TextSplitter + 커스텀 엔티티 추출

### Rationale
- pdfplumber: 테이블/구조 추출 우수
- LangChain RecursiveCharacterTextSplitter: 의미 단위 청킹
- 룰 기반(헤더/정의 패턴) + LLM 혼합 엔티티 추출

### Pipeline Stages
```
Stage 1: PDF 파싱 (pdfplumber)
  - 텍스트 추출
  - 페이지/섹션 메타데이터 보존
  - 테이블/이미지 캡션 분리

Stage 2: 청킹 (LangChain)
  - RecursiveCharacterTextSplitter
  - chunk_size: 1000, overlap: 200
  - 페이지/섹션 ID 유지

Stage 3: 임베딩 (로컬)
  - Ollama embeddings 또는 sentence-transformers
  - ChromaDB 저장

Stage 4: 엔티티/관계 추출
  - 룰 기반: 헤더, 정의 패턴, 번호 목록
  - LLM 기반: 복잡한 관계 추출
  - 노드타입: 개념, 정의, 프로세스
  - 엣지타입: 관련, 정의, 의존

Stage 5: 그래프 구축 (Neo4j)
  - 엔티티 → 노드
  - 관계 → 엣지
  - chunk ↔ node 양방향 링크
  - 신뢰도 score 저장
```

### Alternatives Considered
| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| PyPDF2 | 경량 | 테이블 추출 불가 |
| Unstructured.io | 강력한 파싱 | 무거움, 외부 의존성 |
| LlamaParse | 정확도 높음 | 유료 서비스 |

---

## 5. LLM 통합 (Ollama)

### Decision
Ollama + LangChain ChatOllama 래퍼

### Rationale
- 로컬 실행으로 데이터 프라이버시 보장
- 모델 교체 용이 (설정 변경만으로 가능)
- 스트리밍 응답 지원

### Configuration
```python
from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="nemotron-mini:4b",  # 기본값, 설정으로 변경 가능
    temperature=0.7,
    base_url="http://ollama:11434"
)
```

### Prompt Engineering
```
시스템 프롬프트:
- 페르소나 설정 반영
- "문서에 근거한 답변만 제공"
- "출처(페이지/섹션) 필수 포함"
- "근거 없으면 '답변 불가' 응답"

컨텍스트 조립 우선순위:
1. 정의/규칙 (최우선)
2. 결론/요약
3. 예시/상세
```

---

## 6. 실시간 스트리밍 (SSE)

### Decision
FastAPI + Server-Sent Events (SSE)

### Rationale
- HTTP 기반으로 구현 간단
- 브라우저 기본 지원 (EventSource API)
- 단방향 스트리밍에 적합
- LLM 토큰 스트리밍과 자연스러운 매핑

### Implementation
```python
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse

@app.get("/chat/{chatbot_id}/stream")
async def chat_stream(chatbot_id: str, query: str):
    async def event_generator():
        async for token in llm.astream(prompt):
            yield {"event": "token", "data": token}
        yield {"event": "done", "data": json.dumps(sources)}

    return EventSourceResponse(event_generator())
```

### Alternatives Considered
| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| WebSocket | 양방향 | 오버헤드, 복잡성 |
| HTTP Long Polling | 호환성 | 비효율적 |
| gRPC Streaming | 성능 | 브라우저 직접 지원 없음 |

---

## 7. 인증 및 권한 관리

### Decision
JWT 기반 인증 + 역할 기반 권한

### Rationale
- Stateless로 MSA 적합
- FastAPI 통합 용이 (python-jose)
- 관리자/사용자 역할 분리 간단

### Implementation
```python
# 관리자: JWT 토큰 필요
# 챗봇 사용자: 토큰 없이 URL 직접 접근

roles:
  - admin: 챗봇 CRUD, 문서 관리, 통계 조회
  - user: 챗봇 대화만 (인증 불필요)
```

---

## 8. 버전 관리 및 인덱스 관리

### Decision
버전 분리 방식 + 활성화 전환

### Rationale
- 롤백 가능성 보장
- 운영 중 무중단 업데이트
- 검증 후 전환으로 안정성 확보

### Implementation
```
인덱스 버전 스키마:
- chatbot_{id}_v{version}_vectors (ChromaDB 컬렉션)
- chatbot_{id}_v{version} 라벨 (Neo4j 노드)

버전 전환:
1. 새 버전 인덱스 생성
2. 검증 (샘플 쿼리 테스트)
3. active_version 메타데이터 업데이트
4. 이전 버전 보존 (설정된 기간)
```

---

## 9. 프론트엔드 프레임워크

### Decision
React 18 + Vite + TailwindCSS

### Rationale
- 컴포넌트 기반 UI 구축
- Vite: 빠른 개발 서버
- TailwindCSS: 빠른 스타일링

### Key Libraries
```json
{
  "react": "^18.2.0",
  "react-router-dom": "^6.x",
  "tanstack/react-query": "^5.x",
  "tailwindcss": "^3.x"
}
```

---

## 10. 백그라운드 작업 처리 (병렬 처리)

### Decision
Celery + Redis

### Rationale
- PDF 처리는 장시간 소요 (파싱, 청킹, 임베딩, 그래프 구축)
- 동시 다수 문서 업로드 시 리소스 관리 필요
- 진행률 실시간 업데이트 필요
- 작업 실패 시 재시도 메커니즘 필요
- 가장 성숙하고 검증된 Python 작업 큐 솔루션

### Alternatives Considered
| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| ARQ (Async RQ) | 경량, asyncio 네이티브 | 커뮤니티 규모 작음, 모니터링 도구 부족 |
| FastAPI BackgroundTasks | 단순, 의존성 없음 | 확장성 제한, 재시도/모니터링 없음 |
| Dramatiq | 간단한 API | Celery 대비 생태계 작음 |
| Huey | 경량 | 기능 제한적 |

### Architecture
```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   FastAPI   │────▶│    Redis    │────▶│  Celery Worker  │
│   Backend   │     │   (Broker)  │     │  (PDF 처리)     │
└─────────────┘     └─────────────┘     └─────────────────┘
       │                   │                     │
       │                   │                     ▼
       │                   │            ┌───────────────┐
       │                   └───────────▶│ Redis (Result │
       │                                │   Backend)    │
       └────────────────────────────────┴───────────────┘
                    진행률 조회 (Pub/Sub)
```

### Configuration
```python
# backend/src/core/celery_app.py
from celery import Celery

celery_app = Celery(
    "graphrag",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    # 동시 처리 제한
    worker_concurrency=3,  # PDF 처리 워커 수
    # 작업 재시도
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # 메모리 관리
    worker_max_tasks_per_child=50,
)
```

### Task Definition
```python
# backend/src/workers/document_tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_document(self, document_id: str, chatbot_id: str):
    """PDF 문서 처리 작업"""
    try:
        # 1. 파싱 (10%)
        update_progress(document_id, 10, "parsing")
        text = parse_pdf(document_id)

        # 2. 청킹 (30%)
        update_progress(document_id, 30, "chunking")
        chunks = chunk_text(text)

        # 3. 임베딩 (50%)
        update_progress(document_id, 50, "embedding")
        embed_chunks(chunks, chatbot_id)

        # 4. 엔티티 추출 (70%)
        update_progress(document_id, 70, "extracting")
        entities = extract_entities(chunks)

        # 5. 그래프 구축 (90%)
        update_progress(document_id, 90, "graphing")
        build_graph(entities, chatbot_id)

        # 6. 완료 (100%)
        update_progress(document_id, 100, "completed")

    except Exception as exc:
        update_progress(document_id, -1, "failed", str(exc))
        raise self.retry(exc=exc)
```

### Progress Tracking (Redis Pub/Sub)
```python
# 진행률 업데이트
import redis

redis_client = redis.Redis(host="redis", port=6379, db=2)

def update_progress(document_id: str, progress: int, stage: str, error: str = None):
    data = {"progress": progress, "stage": stage, "error": error}
    redis_client.publish(f"doc_progress:{document_id}", json.dumps(data))
    redis_client.hset(f"doc_status:{document_id}", mapping=data)
```

### Concurrency Control
```python
# LLM 동시 요청 제한 (Ollama)
from celery import Task
import threading

class OllamaRateLimitedTask(Task):
    _semaphore = threading.Semaphore(2)  # 최대 2개 동시 LLM 요청

    def __call__(self, *args, **kwargs):
        with self._semaphore:
            return super().__call__(*args, **kwargs)
```

---

## 11. Docker 및 오케스트레이션

### Decision
Docker Compose (단일 서버)

### Rationale
- 단일 서버 환경 요구사항 충족
- 서비스 간 네트워크 격리
- 간단한 배포 및 관리

### Services
```yaml
services:
  backend:
    build: ./backend
    depends_on: [postgres, neo4j, qdrant, redis, ollama]
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1

  celery-worker:
    build: ./backend
    command: celery -A src.core.celery_app worker --loglevel=info --concurrency=3
    depends_on: [redis, postgres, neo4j, qdrant, ollama]
    deploy:
      resources:
        limits:
          memory: 4G

  celery-beat:
    build: ./backend
    command: celery -A src.core.celery_app beat --loglevel=info
    depends_on: [redis]

  flower:
    image: mher/flower:latest
    command: celery --broker=redis://redis:6379/0 flower --port=5555
    ports:
      - "5555:5555"  # Celery 모니터링 대시보드
    depends_on: [redis]

  frontend:
    build: ./frontend
    depends_on: [backend]

  postgres:
    image: postgres:15

  neo4j:
    image: neo4j:5.15-community

  qdrant:
    image: qdrant/qdrant:latest

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  ollama:
    image: ollama/ollama:latest
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]  # GPU 사용 시

volumes:
  redis_data:
```

---

## Summary of Decisions

| Area | Decision | Key Reason |
|------|----------|------------|
| GraphRAG | 커스텀 Hybrid Retrieval | 로컬 LLM 최적화 |
| Graph DB | Neo4j Community | 성숙도, Docker 지원 |
| Vector Store | Qdrant | 고성능, 필터링, Docker 지원 |
| PDF Processing | pdfplumber + LangChain | 구조 추출 + 청킹 |
| LLM | Ollama + ChatOllama | 로컬 실행, 스트리밍 |
| Streaming | SSE (FastAPI) | 단순성, 브라우저 지원 |
| Auth | JWT + Role-based | Stateless, MSA 적합 |
| Versioning | 버전 분리 | 롤백, 무중단 업데이트 |
| Frontend | React + Vite | 생산성, 성능 |
| **Background Tasks** | **Celery + Redis** | **병렬 처리, 재시도, 모니터링** |
| Deployment | Docker Compose | 단일 서버, 간단함 |
