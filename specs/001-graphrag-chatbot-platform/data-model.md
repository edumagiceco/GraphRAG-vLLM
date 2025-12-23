# Data Model: GraphRAG Chatbot Platform

**Date**: 2025-12-22
**Branch**: `001-graphrag-chatbot-platform`

## Overview

본 문서는 GraphRAG Chatbot Platform의 데이터 모델을 정의한다. 세 가지 저장소(PostgreSQL, Neo4j, Qdrant)에 분산된 데이터 구조를 설명한다.

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   AdminUser     │       │ ChatbotService  │       │    Document     │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │       │ id (PK)         │
│ email           │──1:N──│ admin_id (FK)   │──1:N──│ chatbot_id (FK) │
│ password_hash   │       │ name            │       │ filename        │
│ created_at      │       │ description     │       │ file_path       │
└─────────────────┘       │ persona         │       │ file_size       │
                          │ status          │       │ status          │
                          │ access_url      │       │ version         │
                          │ active_version  │       │ created_at      │
                          │ created_at      │       └─────────────────┘
                          └─────────────────┘               │
                                  │                         │
                                  │                         │
                          ┌───────┴───────┐         ┌───────┴───────┐
                          │               │         │               │
                    ┌─────┴─────┐   ┌─────┴─────┐   │         ┌─────┴─────┐
                    │Conversation│   │IndexVersion│   │         │   Chunk   │
                    │  Session   │   ├───────────┤   │         ├───────────┤
                    ├───────────┤   │ id (PK)   │   │         │ id (PK)   │
                    │ id (PK)   │   │ chatbot_id│   │         │ doc_id(FK)│
                    │chatbot_id │   │ version   │   │         │ content   │
                    │ created_at│   │ status    │   │         │ page_num  │
                    │ expires_at│   │ created_at│   │         │ section   │
                    └───────────┘   └───────────┘   │         │ metadata  │
                          │                         │         └───────────┘
                          │                         │               │
                    ┌─────┴─────┐                   │         ┌─────┴─────┐
                    │  Message  │                   │         │ GraphNode │
                    ├───────────┤                   │         │  (Neo4j)  │
                    │ id (PK)   │                   │         ├───────────┤
                    │session_id │                   │         │ id        │
                    │ role      │                   │         │ type      │
                    │ content   │                   │         │ name      │
                    │ sources   │                   │         │ chunk_ids │
                    │ created_at│                   │         │ chatbot_id│
                    └───────────┘                   │         │ version   │
                                                    │         └───────────┘
                                                    │               │
                                              ┌─────┴─────┐   ┌─────┴─────┐
                                              │VectorChunk│   │ GraphEdge │
                                              │ (Qdrant)  │   │  (Neo4j)  │
                                              ├───────────┤   ├───────────┤
                                              │ id        │   │ source_id │
                                              │ embedding │   │ target_id │
                                              │ payload   │   │ type      │
                                              │ chatbot_id│   │ score     │
                                              │ version   │   └───────────┘
                                              └───────────┘
```

---

## PostgreSQL Entities

### AdminUser

관리자 계정 정보

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| email | VARCHAR(255) | UNIQUE, NOT NULL | 로그인 이메일 |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt 해시 비밀번호 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 생성 시각 |
| updated_at | TIMESTAMP | NOT NULL | 수정 시각 |

```sql
CREATE TABLE admin_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

### ChatbotService

챗봇 서비스 인스턴스

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| admin_id | UUID | FK → admin_users | 소유자 관리자 |
| name | VARCHAR(100) | NOT NULL | 챗봇 이름 |
| description | TEXT | | 챗봇 설명 |
| persona | JSONB | NOT NULL | 페르소나 설정 (톤, 스타일) |
| status | ENUM | NOT NULL | 'active', 'inactive', 'processing' |
| access_url | VARCHAR(100) | UNIQUE, NOT NULL | 접속 URL 슬러그 |
| active_version | INTEGER | NOT NULL, DEFAULT 1 | 현재 활성 인덱스 버전 |
| created_at | TIMESTAMP | NOT NULL | 생성 시각 |
| updated_at | TIMESTAMP | NOT NULL | 수정 시각 |

```sql
CREATE TYPE chatbot_status AS ENUM ('active', 'inactive', 'processing');

CREATE TABLE chatbot_services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    persona JSONB NOT NULL DEFAULT '{"tone": "professional", "language": "ko"}',
    status chatbot_status NOT NULL DEFAULT 'processing',
    access_url VARCHAR(100) UNIQUE NOT NULL,
    active_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chatbot_admin ON chatbot_services(admin_id);
CREATE INDEX idx_chatbot_status ON chatbot_services(status);
```

**Persona JSONB 스키마**:
```json
{
  "tone": "professional | friendly | formal | casual",
  "language": "ko | en",
  "greeting": "안녕하세요! 무엇을 도와드릴까요?",
  "fallback_message": "죄송합니다. 해당 내용에 대한 정보를 찾을 수 없습니다."
}
```

---

### Document

업로드된 PDF 문서

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| chatbot_id | UUID | FK → chatbot_services | 소속 챗봇 |
| filename | VARCHAR(255) | NOT NULL | 원본 파일명 |
| file_path | VARCHAR(500) | NOT NULL | 저장 경로 |
| file_size | BIGINT | NOT NULL | 파일 크기 (bytes) |
| status | ENUM | NOT NULL | 처리 상태 |
| version | INTEGER | NOT NULL | 인덱스 버전 |
| page_count | INTEGER | | 총 페이지 수 |
| processing_progress | INTEGER | DEFAULT 0 | 처리 진행률 (0-100) |
| error_message | TEXT | | 오류 메시지 (실패 시) |
| created_at | TIMESTAMP | NOT NULL | 생성 시각 |

```sql
CREATE TYPE document_status AS ENUM (
    'pending', 'parsing', 'chunking', 'embedding',
    'extracting', 'graphing', 'completed', 'failed'
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chatbot_id UUID NOT NULL REFERENCES chatbot_services(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    status document_status NOT NULL DEFAULT 'pending',
    version INTEGER NOT NULL DEFAULT 1,
    page_count INTEGER,
    processing_progress INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_document_chatbot ON documents(chatbot_id);
CREATE INDEX idx_document_status ON documents(status);
```

---

### IndexVersion

인덱스 버전 관리

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| chatbot_id | UUID | FK → chatbot_services | 소속 챗봇 |
| version | INTEGER | NOT NULL | 버전 번호 |
| status | ENUM | NOT NULL | 버전 상태 |
| created_at | TIMESTAMP | NOT NULL | 생성 시각 |
| activated_at | TIMESTAMP | | 활성화 시각 |

```sql
CREATE TYPE version_status AS ENUM ('building', 'ready', 'active', 'archived');

CREATE TABLE index_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chatbot_id UUID NOT NULL REFERENCES chatbot_services(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    status version_status NOT NULL DEFAULT 'building',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMP,
    UNIQUE(chatbot_id, version)
);
```

---

### ConversationSession

대화 세션

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| chatbot_id | UUID | FK → chatbot_services | 소속 챗봇 |
| created_at | TIMESTAMP | NOT NULL | 생성 시각 |
| expires_at | TIMESTAMP | NOT NULL | 만료 시각 (30분) |
| message_count | INTEGER | DEFAULT 0 | 메시지 수 |

```sql
CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chatbot_id UUID NOT NULL REFERENCES chatbot_services(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL DEFAULT (NOW() + INTERVAL '30 minutes'),
    message_count INTEGER DEFAULT 0
);

CREATE INDEX idx_session_chatbot ON conversation_sessions(chatbot_id);
CREATE INDEX idx_session_expires ON conversation_sessions(expires_at);
```

---

### Message

대화 메시지

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| session_id | UUID | FK → conversation_sessions | 소속 세션 |
| role | ENUM | NOT NULL | 'user' or 'assistant' |
| content | TEXT | NOT NULL | 메시지 내용 |
| sources | JSONB | | 출처 정보 (assistant만) |
| created_at | TIMESTAMP | NOT NULL | 생성 시각 |

```sql
CREATE TYPE message_role AS ENUM ('user', 'assistant');

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    role message_role NOT NULL,
    content TEXT NOT NULL,
    sources JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_message_session ON messages(session_id);
```

**Sources JSONB 스키마**:
```json
[
  {
    "document_id": "uuid",
    "document_name": "example.pdf",
    "page": 5,
    "section": "2.1 개요",
    "chunk_id": "uuid",
    "relevance_score": 0.89
  }
]
```

---

### ChatbotStats

챗봇 사용 통계 (집계 테이블)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| chatbot_id | UUID | FK → chatbot_services | 소속 챗봇 |
| date | DATE | NOT NULL | 통계 날짜 |
| session_count | INTEGER | DEFAULT 0 | 세션 수 |
| message_count | INTEGER | DEFAULT 0 | 메시지 수 |
| avg_response_time_ms | INTEGER | | 평균 응답 시간 |

```sql
CREATE TABLE chatbot_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chatbot_id UUID NOT NULL REFERENCES chatbot_services(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    session_count INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    avg_response_time_ms INTEGER,
    UNIQUE(chatbot_id, date)
);
```

---

## Neo4j Graph Schema

### Node Types

#### Concept (개념)
```cypher
(:Concept {
    id: String,           // UUID
    name: String,         // 개념 이름
    description: String,  // 설명 (optional)
    chunk_ids: [String],  // 연결된 청크 ID들
    chatbot_id: String,   // 소속 챗봇 ID
    version: Integer,     // 인덱스 버전
    confidence: Float     // 추출 신뢰도 (0.0-1.0)
})
```

#### Definition (정의)
```cypher
(:Definition {
    id: String,
    name: String,         // 정의되는 용어
    definition: String,   // 정의 내용
    chunk_ids: [String],
    chatbot_id: String,
    version: Integer,
    confidence: Float
})
```

#### Process (프로세스)
```cypher
(:Process {
    id: String,
    name: String,         // 프로세스 이름
    steps: [String],      // 단계 목록 (optional)
    chunk_ids: [String],
    chatbot_id: String,
    version: Integer,
    confidence: Float
})
```

### Edge Types

#### RELATED_TO (관련)
```cypher
[:RELATED_TO {
    score: Float,         // 관계 강도 (0.0-1.0)
    context: String       // 관계 맥락 (optional)
}]
```

#### DEFINES (정의)
```cypher
[:DEFINES {
    score: Float
}]
```

#### DEPENDS_ON (의존)
```cypher
[:DEPENDS_ON {
    score: Float,
    dependency_type: String  // 'requires', 'uses', 'includes'
}]
```

### Indexes & Constraints

```cypher
// 유니크 제약
CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT definition_id IF NOT EXISTS FOR (d:Definition) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT process_id IF NOT EXISTS FOR (p:Process) REQUIRE p.id IS UNIQUE;

// 복합 인덱스 (챗봇별 + 버전별 조회)
CREATE INDEX concept_chatbot_version IF NOT EXISTS FOR (c:Concept) ON (c.chatbot_id, c.version);
CREATE INDEX definition_chatbot_version IF NOT EXISTS FOR (d:Definition) ON (d.chatbot_id, d.version);
CREATE INDEX process_chatbot_version IF NOT EXISTS FOR (p:Process) ON (p.chatbot_id, p.version);

// 이름 검색용 인덱스
CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name);
CREATE INDEX definition_name IF NOT EXISTS FOR (d:Definition) ON (d.name);
```

### Sample Queries

```cypher
// 특정 챗봇의 활성 버전 노드 조회
MATCH (n {chatbot_id: $chatbot_id, version: $version})
RETURN n

// 2-hop 그래프 탐색
MATCH (start {id: $seed_id})
MATCH path = (start)-[*1..2]-(related)
WHERE related.chatbot_id = $chatbot_id AND related.version = $version
RETURN path

// 신뢰도 기반 필터링
MATCH (n)-[r]->(m)
WHERE n.chatbot_id = $chatbot_id
  AND n.version = $version
  AND r.score >= 0.7
RETURN n, r, m
```

---

## Qdrant Vector Schema

### Collection Naming

```
chatbot_{chatbot_id}_v{version}
```

예: `chatbot_550e8400-e29b-41d4-a716-446655440000_v1`

### Point Structure

```json
{
    "id": "chunk-uuid",
    "vector": [0.1, 0.2, ...],  // 1536 dimensions (embedding model dependent)
    "payload": {
        "chatbot_id": "uuid",
        "document_id": "uuid",
        "document_name": "example.pdf",
        "content": "청크 텍스트 내용...",
        "page_number": 5,
        "section": "2.1 개요",
        "chunk_index": 12,
        "version": 1,
        "metadata": {
            "is_table": false,
            "is_caption": false,
            "heading_level": 2
        }
    }
}
```

### Collection Configuration

```python
from qdrant_client.models import VectorParams, Distance

client.create_collection(
    collection_name=f"chatbot_{chatbot_id}_v{version}",
    vectors_config=VectorParams(
        size=1536,  # embedding dimension
        distance=Distance.COSINE
    )
)

# 인덱스 생성 (필터링 최적화)
client.create_payload_index(
    collection_name=collection_name,
    field_name="document_id",
    field_schema="keyword"
)
```

### Search Example

```python
results = client.search(
    collection_name=f"chatbot_{chatbot_id}_v{active_version}",
    query_vector=query_embedding,
    limit=10,
    with_payload=True,
    score_threshold=0.7
)
```

---

## Data Flow

### 1. Document Upload Flow

```
PDF Upload → PostgreSQL (Document: pending)
    ↓
Parsing → PostgreSQL (Document: parsing, progress: 10%)
    ↓
Chunking → PostgreSQL (Document: chunking, progress: 30%)
    ↓
Embedding → Qdrant (VectorChunk 저장)
         → PostgreSQL (Document: embedding, progress: 50%)
    ↓
Entity Extraction → Neo4j (GraphNode 생성)
                 → PostgreSQL (Document: extracting, progress: 70%)
    ↓
Relation Extraction → Neo4j (GraphEdge 생성)
                   → PostgreSQL (Document: graphing, progress: 90%)
    ↓
Complete → PostgreSQL (Document: completed, progress: 100%)
        → PostgreSQL (IndexVersion: ready)
```

### 2. Query Flow

```
User Query
    ↓
Vector Search (Qdrant) → Top-K Chunks
    ↓
Entity Extraction → Seed Entities
    ↓
Graph Expansion (Neo4j) → 2-hop Related Nodes
    ↓
Context Assembly (priority: Definition > Concept > Process)
    ↓
LLM Generation (Ollama) + Source Attribution
    ↓
Response with Sources
```

---

## Validation Rules

### ChatbotService
- `name`: 2-100자
- `access_url`: 영문, 숫자, 하이픈만 허용, 3-50자
- `persona.tone`: enum 값만 허용

### Document
- `file_size`: 최대 100MB (104857600 bytes)
- `filename`: PDF 확장자 필수

### Message
- `content`: 최대 10000자

### GraphNode
- `confidence`: 0.0-1.0 범위
- `chunk_ids`: 최소 1개 이상

### GraphEdge
- `score`: 0.0-1.0 범위, 0.5 미만은 저장하지 않음 (노이즈 방지)

---

## State Transitions

### ChatbotService.status

```
processing → active (모든 문서 처리 완료 시)
active → inactive (관리자 비활성화)
inactive → active (관리자 활성화)
active → processing (새 문서 추가 시)
```

### Document.status

```
pending → parsing → chunking → embedding → extracting → graphing → completed
    ↓         ↓          ↓           ↓            ↓           ↓
  failed    failed     failed      failed       failed      failed
```

### IndexVersion.status

```
building → ready (빌드 완료)
ready → active (활성화)
active → archived (새 버전 활성화 시)
```
