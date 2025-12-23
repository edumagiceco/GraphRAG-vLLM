# GraphRAG Chatbot Platform - Test Scenarios

## Test Environment
- Docker Compose 환경
- Backend: http://localhost:18000
- Frontend: http://localhost:13000
- Flower (Celery Monitor): http://localhost:15555

---

## Pre-Test Checklist
- [ ] Docker Compose 서비스 모두 실행 중
- [ ] PostgreSQL, Neo4j, Redis, Qdrant 정상 연결
- [ ] Celery Worker 활성화 확인
- [ ] Ollama 모델 로드 확인

---

## Test Scenario 1: Authentication (인증)

### TC1.1: Admin Login
**목적**: 관리자 로그인 기능 테스트
**Steps**:
1. POST /api/v1/auth/login
2. Body: `{"email": "admin@example.com", "password": "Admin123456"}`
**Expected**: 200 OK, JWT access_token 반환

### TC1.2: Protected Endpoint Access
**목적**: JWT 인증 확인
**Steps**:
1. GET /api/v1/chatbots (without token)
2. GET /api/v1/chatbots (with token)
**Expected**:
- Without token: 401 Unauthorized
- With token: 200 OK

---

## Test Scenario 2: User Story 1 - Chatbot Creation (챗봇 생성)

### TC2.1: Create Chatbot
**목적**: 새 챗봇 서비스 생성
**Steps**:
1. POST /api/v1/chatbots
2. Body:
```json
{
  "name": "Test Support Bot",
  "description": "A test chatbot for GraphRAG platform",
  "persona": {
    "name": "Helper",
    "description": "Friendly support assistant",
    "greeting": "Hello! How can I help you today?",
    "system_prompt": "You are a helpful assistant."
  },
  "access_url": "test-bot"
}
```
**Expected**: 201 Created, chatbot ID 반환

### TC2.2: Upload PDF Document
**목적**: PDF 문서 업로드 및 처리
**Steps**:
1. POST /api/v1/chatbots/{id}/documents
2. Form-data: file=sample.pdf
**Expected**: 202 Accepted, document processing started

### TC2.3: Check Document Processing Progress
**목적**: 문서 처리 진행 상황 확인
**Steps**:
1. GET /api/v1/chatbots/{id}/documents/{doc_id}/progress
**Expected**: 200 OK, progress percentage and stage

### TC2.4: List Documents
**목적**: 챗봇의 문서 목록 조회
**Steps**:
1. GET /api/v1/chatbots/{id}/documents
**Expected**: 200 OK, document list with status

---

## Test Scenario 3: User Story 2 - Chat Interface (채팅)

### TC3.1: Create Chat Session
**목적**: 새 채팅 세션 생성
**Steps**:
1. POST /api/v1/chat/test-bot/sessions
**Expected**: 200 OK, session_id 반환

### TC3.2: Send Message (SSE Streaming)
**목적**: 메시지 전송 및 스트리밍 응답
**Steps**:
1. POST /api/v1/chat/test-bot/sessions/{session_id}/messages
2. Body: `{"message": "What is this document about?"}`
3. Accept: text/event-stream
**Expected**: SSE stream with tokens and sources

### TC3.3: Stop Generation
**목적**: 응답 생성 중단
**Steps**:
1. POST /api/v1/chat/test-bot/sessions/{session_id}/stop
**Expected**: 200 OK, generation stopped

### TC3.4: Get Chat History
**목적**: 대화 히스토리 조회
**Steps**:
1. GET /api/v1/chat/test-bot/sessions/{session_id}/history
**Expected**: 200 OK, message list

---

## Test Scenario 4: User Story 3 - Chatbot Management (챗봇 관리)

### TC4.1: List Chatbots
**목적**: 챗봇 목록 조회
**Steps**:
1. GET /api/v1/chatbots
**Expected**: 200 OK, paginated list

### TC4.2: Update Chatbot
**목적**: 챗봇 정보 수정
**Steps**:
1. PATCH /api/v1/chatbots/{id}
2. Body: `{"description": "Updated description"}`
**Expected**: 200 OK, updated chatbot

### TC4.3: Toggle Chatbot Status
**목적**: 챗봇 활성화/비활성화
**Steps**:
1. PATCH /api/v1/chatbots/{id}/status
2. Body: `{"status": "inactive"}`
**Expected**: 200 OK, status changed

### TC4.4: Get Chatbot Statistics
**목적**: 챗봇 통계 조회
**Steps**:
1. GET /api/v1/chatbots/{id}/stats?days=30
**Expected**: 200 OK, stats summary

### TC4.5: Delete Chatbot
**목적**: 챗봇 삭제
**Steps**:
1. DELETE /api/v1/chatbots/{id}
**Expected**: 204 No Content

---

## Test Scenario 5: User Story 4 - Version Management (버전 관리)

### TC5.1: List Versions
**목적**: 챗봇 버전 목록 조회
**Steps**:
1. GET /api/v1/chatbots/{id}/versions
**Expected**: 200 OK, version list

### TC5.2: Activate Version
**목적**: 특정 버전 활성화
**Steps**:
1. POST /api/v1/chatbots/{id}/versions/{version}/activate
**Expected**: 200 OK, version activated

### TC5.3: Delete Document
**목적**: 문서 삭제 및 데이터 정리
**Steps**:
1. DELETE /api/v1/chatbots/{id}/documents/{doc_id}
**Expected**: 204 No Content, vectors/graph cleaned

---

## Test Scenario 6: Cross-Cutting Concerns

### TC6.1: Health Check (Simple)
**목적**: 간단한 헬스 체크
**Steps**:
1. GET /health
**Expected**: 200 OK, `{"status": "healthy"}`

### TC6.2: Health Check (Detailed)
**목적**: 상세 헬스 체크
**Steps**:
1. GET /api/v1/health
**Expected**: 200 OK, all services status

### TC6.3: Liveness Probe
**목적**: Kubernetes liveness 프로브
**Steps**:
1. GET /api/v1/health/live
**Expected**: 200 OK

### TC6.4: Readiness Probe
**목적**: Kubernetes readiness 프로브
**Steps**:
1. GET /api/v1/health/ready
**Expected**: 200 OK when ready

### TC6.5: Rate Limiting
**목적**: API rate limiting 테스트
**Steps**:
1. Send 70 requests in 1 minute
**Expected**: 429 Too Many Requests after limit

### TC6.6: File Size Validation
**목적**: 대용량 파일 거부 확인
**Steps**:
1. Upload file > 100MB
**Expected**: 413 Request Entity Too Large

### TC6.7: Invalid PDF Rejection
**목적**: 잘못된 PDF 거부
**Steps**:
1. Upload non-PDF file with .pdf extension
**Expected**: 400 Bad Request

---

## Test Scenario 7: Frontend UI Tests

### TC7.1: Login Page
- [ ] Login form 표시
- [ ] 잘못된 자격증명 에러 표시
- [ ] 로그인 성공 시 대시보드 리다이렉트

### TC7.2: Dashboard
- [ ] 챗봇 목록 표시
- [ ] 빈 상태 메시지 표시
- [ ] 생성 버튼 동작

### TC7.3: Chatbot Creation
- [ ] 폼 검증 동작
- [ ] 성공적 생성 후 리다이렉트
- [ ] 에러 메시지 표시

### TC7.4: Chatbot Detail
- [ ] 문서 업로드 영역
- [ ] 처리 진행률 표시
- [ ] Documents/Versions 탭 전환
- [ ] 삭제 확인 다이얼로그

### TC7.5: Chat Interface
- [ ] 메시지 입력 및 전송
- [ ] 스트리밍 응답 표시
- [ ] 출처 링크 표시
- [ ] 중지 버튼 동작

### TC7.6: Statistics Page
- [ ] 차트 렌더링
- [ ] 기간 선택 동작
- [ ] 일별 통계 테이블

---

## Post-Test Actions
1. 테스트 결과 기록
2. 발견된 버그 문서화
3. 성능 메트릭 수집
4. 테스트 데이터 정리
