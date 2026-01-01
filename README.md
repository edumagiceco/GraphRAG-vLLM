# GraphRAG Chatbot Platform

GraphRAG(Graph Retrieval Augmented Generation) 기반의 지능형 챗봇 플랫폼입니다. 문서에서 지식 그래프를 자동으로 구축하고, 그래프 기반 검색과 벡터 검색을 결합하여 정확하고 맥락에 맞는 답변을 제공합니다.

## 주요 기능

- **문서 업로드 및 처리**: PDF, TXT 등 다양한 문서 형식 지원
- **자동 지식 그래프 구축**: LLM을 활용한 엔티티 및 관계 자동 추출
- **하이브리드 검색**: 벡터 유사도 검색 + 그래프 기반 검색
- **다중 챗봇 관리**: 여러 챗봇을 생성하고 독립적으로 관리
- **관리자 대시보드**: 문서, 챗봇, 시스템 설정 관리
- **실시간 채팅**: 스트리밍 응답 지원
- **성능 모니터링**: 응답 시간, 토큰 사용량, 검색 메트릭 대시보드
- **API 레이트 리미팅**: Redis 기반 요청 제한으로 리소스 보호

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
- **Recharts**: 데이터 시각화 (차트)

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

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
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
│       ├── api/                    # API 라우터
│       │   ├── admin/              # 관리자 API
│       │   │   └── stats_router.py # 통계 API
│       │   └── chat/               # 채팅 API
│       ├── core/                   # 핵심 설정 및 유틸리티
│       │   ├── config.py           # 환경 설정
│       │   ├── llm.py              # LLM 클라이언트
│       │   ├── embeddings.py       # 임베딩 서비스
│       │   └── token_counter.py    # 토큰 카운터 유틸리티
│       ├── models/                 # SQLAlchemy 모델
│       │   ├── conversation.py     # 세션/메시지 모델 (메트릭 포함)
│       │   └── stats.py            # 통계 모델
│       ├── services/               # 비즈니스 로직
│       │   ├── graph/              # 지식 그래프 서비스
│       │   ├── rag/                # RAG 파이프라인
│       │   ├── chat_service.py     # 채팅 서비스 (메트릭 수집)
│       │   └── stats_service.py    # 통계 서비스 (집계/퍼센타일)
│       └── workers/                # Celery 작업
├── frontend/
│   └── src/
│       ├── components/             # React 컴포넌트
│       │   └── charts/             # 차트 컴포넌트
│       │       ├── MetricCard.tsx
│       │       ├── ResponseTimeChart.tsx
│       │       └── TokenUsageChart.tsx
│       ├── pages/                  # 페이지 컴포넌트
│       │   └── admin/
│       │       └── ChatbotStats.tsx # 통계 대시보드
│       └── services/               # API 서비스
│           └── stats.ts            # 통계 API 클라이언트
├── docker/
│   ├── docker-compose.yml          # Docker Compose 설정
│   └── .env                        # 환경 변수
└── docs/                           # 문서
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

## API 레이트 리미팅

Redis 기반 토큰 버킷 알고리즘을 사용하여 API 요청을 제한합니다. 이를 통해 단일 사용자가 GPU/DB 리소스를 과도하게 사용하는 것을 방지합니다.

### 기본 설정

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `RATE_LIMIT_ENABLED` | `true` | 레이트 리미팅 활성화 여부 |
| `RATE_LIMIT_PER_MINUTE` | `60` | 클라이언트당 분당 최대 요청 수 |
| `RATE_LIMIT_PER_HOUR` | `1000` | 클라이언트당 시간당 최대 요청 수 |

### 제외 경로

다음 경로는 레이트 리미팅에서 제외됩니다:
- `/` - 루트 엔드포인트
- `/health` - 헬스체크
- `/docs`, `/redoc`, `/openapi.json` - API 문서
- `*/health` - 모든 헬스체크 엔드포인트

### 응답 헤더

레이트 리미팅이 적용된 응답에는 다음 헤더가 포함됩니다:

| 헤더 | 설명 |
|------|------|
| `X-RateLimit-Limit-Minute` | 분당 허용 요청 수 |
| `X-RateLimit-Remaining-Minute` | 현재 분에 남은 요청 수 |

### 요청 제한 초과 시

요청 제한을 초과하면 `429 Too Many Requests` 응답이 반환됩니다:

```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

응답에는 `Retry-After` 헤더가 포함되어 다음 요청까지 대기해야 하는 시간(초)을 알려줍니다.

### 클라이언트 식별

- **인증된 사용자**: Bearer 토큰 해시값으로 식별
- **비인증 사용자**: IP 주소로 식별 (`X-Forwarded-For` 헤더 지원)

## 성능 모니터링 대시보드

챗봇별 상세 성능 메트릭을 수집하고 시각화하는 모니터링 대시보드를 제공합니다.

### 수집 메트릭

| 카테고리 | 메트릭 | 설명 |
|---------|--------|------|
| **응답 시간** | 평균 응답 시간 | 모든 응답의 평균 소요 시간 |
| | P50 (중앙값) | 전체 응답의 50%가 이 시간 이내 완료 |
| | P95 | 전체 응답의 95%가 이 시간 이내 완료 (SLA 기준) |
| | P99 | 전체 응답의 99%가 이 시간 이내 완료 |
| **토큰 사용량** | 입력 토큰 | LLM에 전달된 프롬프트 토큰 수 |
| | 출력 토큰 | LLM이 생성한 응답 토큰 수 |
| **검색 메트릭** | 검색 청크 수 | 질문당 검색된 문서 조각 수 |
| | 검색 시간 | 벡터/그래프 DB 검색 소요 시간 |
| **사용량** | 세션 수 | 일별 대화 세션 수 |
| | 메시지 수 | 일별 총 메시지 수 |

### 대시보드 구성

```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 챗봇 통계 대시보드                                            │
├─────────────────────────────────────────────────────────────────┤
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────┐│
│ │총 세션 │ │총 메시지│ │평균응답│ │P95응답 │ │입력토큰│ │출력  ││
│ │   3    │ │   8    │ │ 2.94s │ │ 2.94s │ │  528  │ │토큰  ││
│ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └──────┘│
│                                                                 │
│ ┌─────────────────────────────┐ ┌─────────────────────────────┐│
│ │   📈 응답 시간 추이 차트    │ │   📊 토큰 사용량 차트       ││
│ │      (라인 차트)            │ │     (스택 바 차트)          ││
│ └─────────────────────────────┘ └─────────────────────────────┘│
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │   📋 일별 상세 테이블                                        ││
│ │   날짜 | 세션 | 메시지 | 평균응답 | 입력토큰 | 출력토큰 | 검색 ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │   ℹ️ 용어 설명                                               ││
│ │   P50, P95, P99, 토큰, 검색 청크 등 용어 해설                ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 관련 API 엔드포인트

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/v1/chatbots/{id}/stats` | 일별 통계 조회 |
| `GET /api/v1/chatbots/{id}/stats/performance` | 상세 성능 메트릭 (P50/P95/P99) |
| `POST /api/v1/chatbots/{id}/stats/recalculate` | 통계 재계산 |

### 기술 구현

- **백엔드**: 메시지별 메트릭 수집 및 일별 집계
- **토큰 추정**: 한국어 약 2자/토큰, 영어 약 4자/토큰 기반 추정
- **프론트엔드**: Recharts 라이브러리를 활용한 시각화
- **데이터 저장**: PostgreSQL에 Message 및 ChatbotStats 테이블

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
