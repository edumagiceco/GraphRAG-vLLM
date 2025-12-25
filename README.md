# GraphRAG Chatbot Platform

GraphRAG(Graph Retrieval Augmented Generation) 기반의 지능형 챗봇 플랫폼입니다. 문서에서 지식 그래프를 자동으로 구축하고, 그래프 기반 검색과 벡터 검색을 결합하여 정확하고 맥락에 맞는 답변을 제공합니다.

## 주요 기능

- **문서 업로드 및 처리**: PDF, TXT 등 다양한 문서 형식 지원
- **자동 지식 그래프 구축**: LLM을 활용한 엔티티 및 관계 자동 추출
- **하이브리드 검색**: 벡터 유사도 검색 + 그래프 기반 검색
- **다중 챗봇 관리**: 여러 챗봇을 생성하고 독립적으로 관리
- **관리자 대시보드**: 문서, 챗봇, 시스템 설정 관리
- **실시간 채팅**: 스트리밍 응답 지원

## 기술 스택

### Backend
- **FastAPI**: 고성능 비동기 웹 프레임워크
- **vLLM**: 고속 LLM 추론 서버 (OpenAI 호환 API)
- **LangChain**: LLM 오케스트레이션
- **Celery + Redis**: 비동기 작업 처리
- **SQLAlchemy**: ORM 및 데이터베이스 관리

### Frontend
- **React 18**: 사용자 인터페이스
- **TypeScript**: 타입 안전성
- **TanStack Query**: 서버 상태 관리
- **Tailwind CSS**: 스타일링

### Databases
- **PostgreSQL**: 메인 관계형 데이터베이스
- **Neo4j**: 지식 그래프 저장소
- **Qdrant**: 벡터 데이터베이스 (임베딩 저장)
- **Redis**: 캐시 및 메시지 브로커

### AI Models (vLLM)
- **LLM**: `spow12/Ko-Qwen2-7B-Instruct` (한국어 최적화)
- **Embedding**: `upskyy/bge-m3-korean` (한국어 임베딩)

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│                      http://localhost:13000                      │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│                      http://localhost:18000                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Chat API   │  │  Admin API  │  │  Document Processing    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                   │                      │
         ▼                   ▼                      ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐
│   vLLM LLM  │    │  vLLM Embed │    │    Celery Workers       │
│  :18001     │    │   :18003    │    │  (Async Processing)     │
└─────────────┘    └─────────────┘    └─────────────────────────┘
                                                   │
                   ┌───────────────────────────────┼───────────────┐
                   ▼                               ▼               ▼
            ┌───────────┐                  ┌───────────┐    ┌───────────┐
            │ PostgreSQL│                  │   Neo4j   │    │  Qdrant   │
            │  :15432   │                  │  :17474   │    │  :16333   │
            └───────────┘                  └───────────┘    └───────────┘
```

## 설치 및 실행

### 사전 요구사항

- Docker & Docker Compose
- NVIDIA GPU (vLLM 실행용, 최소 16GB VRAM 권장)
- NVIDIA Container Toolkit

### 1. 저장소 클론

```bash
git clone https://github.com/edumagiceco/GraphRAG.git
cd GraphRAG
```

### 2. 환경 설정

```bash
cd docker
cp .env.example .env
# .env 파일을 편집하여 필요한 설정 변경
```

주요 환경 변수:
```env
# Database
POSTGRES_USER=graphrag
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=graphrag

# Neo4j
NEO4J_PASSWORD=your_neo4j_password

# JWT
JWT_SECRET_KEY=your_jwt_secret_key_at_least_32_characters

# Admin Account
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin_password

# vLLM Configuration
LLM_BACKEND=vllm
VLLM_BASE_URL=http://vllm:8000/v1
VLLM_MODEL=spow12/Ko-Qwen2-7B-Instruct
VLLM_EMBEDDING_BASE_URL=http://vllm-embedding:8000/v1
VLLM_EMBEDDING_MODEL=upskyy/bge-m3-korean
```

### 3. 서비스 시작

```bash
docker compose up -d
```

### 4. 접속

- **프론트엔드**: http://localhost:13000
- **백엔드 API**: http://localhost:18000
- **API 문서 (Swagger)**: http://localhost:18000/docs
- **Neo4j Browser**: http://localhost:17474
- **Flower (Celery 모니터링)**: http://localhost:15555

## 프로젝트 구조

```
GraphRAG-vLLM/
├── backend/
│   └── src/
│       ├── api/              # API 라우터
│       │   ├── admin/        # 관리자 API
│       │   └── chat/         # 채팅 API
│       ├── core/             # 핵심 설정 및 유틸리티
│       │   ├── config.py     # 환경 설정
│       │   ├── llm.py        # LLM 클라이언트
│       │   └── embeddings.py # 임베딩 서비스
│       ├── models/           # SQLAlchemy 모델
│       ├── services/         # 비즈니스 로직
│       │   ├── graph/        # 지식 그래프 서비스
│       │   └── rag/          # RAG 파이프라인
│       └── workers/          # Celery 작업
├── frontend/
│   └── src/
│       ├── components/       # React 컴포넌트
│       ├── pages/            # 페이지 컴포넌트
│       └── services/         # API 서비스
├── docker/
│   ├── docker-compose.yml    # Docker Compose 설정
│   └── .env                  # 환경 변수
└── docs/                     # 문서
```

## API 엔드포인트

### 채팅 API
- `POST /api/chat/{chatbot_id}/message` - 메시지 전송
- `GET /api/chat/{chatbot_id}/sessions` - 세션 목록
- `GET /api/chat/{chatbot_id}/sessions/{session_id}/messages` - 메시지 히스토리

### 관리자 API
- `POST /api/admin/chatbots` - 챗봇 생성
- `GET /api/admin/chatbots` - 챗봇 목록
- `POST /api/admin/chatbots/{id}/documents` - 문서 업로드
- `GET /api/admin/settings/models` - 모델 설정 조회
- `GET /api/admin/settings/models/test-connection` - vLLM 연결 테스트

## 문서 처리 파이프라인

1. **문서 업로드**: PDF/TXT 파일 업로드
2. **텍스트 추출**: 문서에서 텍스트 추출
3. **청킹**: 텍스트를 의미 단위로 분할
4. **임베딩 생성**: 각 청크의 벡터 임베딩 생성 (BGE-M3)
5. **엔티티 추출**: LLM을 통한 엔티티 추출
6. **관계 추출**: 엔티티 간 관계 추출
7. **그래프 저장**: Neo4j에 지식 그래프 저장
8. **벡터 저장**: Qdrant에 임베딩 벡터 저장

## 검색 및 응답 생성

1. **쿼리 임베딩**: 사용자 질문을 벡터로 변환
2. **벡터 검색**: Qdrant에서 유사 청크 검색
3. **그래프 검색**: Neo4j에서 관련 엔티티 및 관계 검색
4. **컨텍스트 구성**: 검색 결과를 LLM 프롬프트에 통합
5. **응답 생성**: vLLM을 통한 답변 생성

## 개발

### 백엔드 개발

```bash
cd backend
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

### 프론트엔드 개발

```bash
cd frontend
npm install
npm run dev
```

### 테스트 실행

```bash
python run_tests.py
```

## 라이선스

MIT License

## 기여

이슈와 풀 리퀘스트를 환영합니다.
