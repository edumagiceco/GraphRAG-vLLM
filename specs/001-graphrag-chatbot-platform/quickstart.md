# Quickstart: GraphRAG Chatbot Platform

이 문서는 GraphRAG Chatbot Platform을 로컬 환경에서 실행하고 테스트하는 방법을 설명합니다.

## Prerequisites

### 필수 소프트웨어

- **Docker**: 24.0+ & Docker Compose v2
- **Git**: 2.40+
- **GPU (권장)**: NVIDIA GPU + CUDA 12.0+ (Ollama 성능 향상)

### 하드웨어 요구사항

| 구성 | 최소 | 권장 |
|------|------|------|
| CPU | 4 cores | 8+ cores |
| RAM | 16GB | 32GB |
| Storage | 50GB SSD | 100GB+ SSD |
| GPU | - | NVIDIA RTX 3060+ |

## Quick Start

### 1. 저장소 클론

```bash
git clone https://github.com/your-org/graphrag-chatbot.git
cd graphrag-chatbot
```

### 2. 환경 변수 설정

```bash
cp docker/.env.example docker/.env
```

`.env` 파일 편집:
```env
# Database
POSTGRES_USER=graphrag
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=graphrag

# Neo4j
NEO4J_AUTH=neo4j/your_secure_password

# JWT
JWT_SECRET_KEY=your_jwt_secret_key_at_least_32_chars

# Ollama
OLLAMA_MODEL=nemotron-mini:4b

# Admin (초기 계정)
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin_password
```

### 3. 서비스 시작

```bash
# 모든 서비스 시작 (백그라운드)
docker compose -f docker/docker-compose.yml up -d

# 로그 확인
docker compose -f docker/docker-compose.yml logs -f
```

### 4. Ollama 모델 다운로드

```bash
# 컨테이너 내부에서 모델 다운로드
docker compose -f docker/docker-compose.yml exec ollama ollama pull nemotron-mini:4b

# 임베딩 모델도 필요시
docker compose -f docker/docker-compose.yml exec ollama ollama pull nomic-embed-text
```

### 5. 서비스 확인

| 서비스 | URL | 설명 |
|--------|-----|------|
| Frontend (Admin) | http://localhost:3000 | 관리자 대시보드 |
| Backend API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Neo4j Browser | http://localhost:7474 | 그래프 DB 관리 |
| Qdrant Dashboard | http://localhost:6333/dashboard | 벡터 DB 관리 |

## First Chatbot Creation

### Step 1: 관리자 로그인

1. http://localhost:3000 접속
2. 초기 계정으로 로그인:
   - Email: `admin@example.com`
   - Password: `.env`에서 설정한 값

### Step 2: 챗봇 생성

1. "새 챗봇 만들기" 클릭
2. 정보 입력:
   - **이름**: 예) "회사 규정 챗봇"
   - **URL 슬러그**: 예) `company-rules`
   - **페르소나**: 톤과 언어 선택

### Step 3: PDF 업로드

1. 챗봇 상세 페이지 → "문서 업로드"
2. PDF 파일 선택 (최대 100MB)
3. 처리 진행률 확인 (약 2-5분 소요)

### Step 4: 챗봇 테스트

1. 처리 완료 후 "챗봇 열기" 클릭
2. 또는 직접 접속: `http://localhost:3000/chat/company-rules`
3. 질문 입력하여 테스트

## API Usage Examples

### 인증

```bash
# 로그인
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "your_password"}'

# 응답에서 access_token 추출
export TOKEN="your_access_token"
```

### 챗봇 생성

```bash
curl -X POST http://localhost:8000/api/v1/chatbots \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "테스트 챗봇",
    "access_url": "test-bot",
    "persona": {
      "tone": "friendly",
      "language": "ko"
    }
  }'
```

### PDF 업로드

```bash
curl -X POST http://localhost:8000/api/v1/chatbots/{chatbot_id}/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/document.pdf"
```

### 대화 (스트리밍)

```bash
# 세션 생성
curl -X POST http://localhost:8000/api/v1/chat/test-bot/sessions

# 질문 전송 (SSE 스트리밍)
curl -N http://localhost:8000/api/v1/chat/test-bot/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "이 문서의 주요 내용은 무엇인가요?"}'
```

## Development Mode

### 개발 환경 실행

```bash
# 개발 모드 (핫 리로드 활성화)
docker compose -f docker/docker-compose.dev.yml up -d
```

### 백엔드 로컬 개발

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 환경 변수 설정
export DATABASE_URL="postgresql://graphrag:password@localhost:5432/graphrag"
export NEO4J_URI="bolt://localhost:7687"
export QDRANT_HOST="localhost"
export OLLAMA_BASE_URL="http://localhost:11434"

# 개발 서버 실행
uvicorn src.main:app --reload --port 8000
```

### 프론트엔드 로컬 개발

```bash
cd frontend
npm install
npm run dev
```

## Testing

### 백엔드 테스트

```bash
cd backend

# 단위 테스트
pytest tests/unit -v

# 통합 테스트 (Docker 서비스 필요)
pytest tests/integration -v

# 전체 테스트 + 커버리지
pytest --cov=src tests/
```

### 프론트엔드 테스트

```bash
cd frontend
npm run test
```

## Troubleshooting

### 문제: Ollama 모델 로딩 실패

```bash
# 메모리 확인
docker stats ollama

# 모델 재다운로드
docker compose exec ollama ollama rm nemotron-mini:4b
docker compose exec ollama ollama pull nemotron-mini:4b
```

### 문제: Neo4j 연결 실패

```bash
# Neo4j 로그 확인
docker compose logs neo4j

# Neo4j 재시작
docker compose restart neo4j
```

### 문제: PDF 처리 실패

1. 관리자 대시보드에서 문서 상태 확인
2. 백엔드 로그 확인: `docker compose logs backend`
3. 오류 메시지에 따라 조치:
   - "Invalid PDF": PDF 파일 손상 → 다른 PDF로 재시도
   - "OCR required": 스캔 PDF → 텍스트 기반 PDF 사용

### 문제: 느린 응답 속도

1. GPU 사용 확인: `nvidia-smi`
2. Ollama 설정에서 GPU 할당 확인
3. 모델 크기 축소 고려: `nemotron-mini:4b` → 더 작은 모델

## Stopping Services

```bash
# 서비스 중지
docker compose -f docker/docker-compose.yml down

# 볼륨 포함 완전 삭제 (데이터 삭제됨!)
docker compose -f docker/docker-compose.yml down -v
```

## Next Steps

- [API 문서](http://localhost:8000/docs) - 전체 API 스펙 확인
- [데이터 모델](./data-model.md) - 데이터베이스 스키마 상세
- [아키텍처 결정](./research.md) - 기술 선택 배경
