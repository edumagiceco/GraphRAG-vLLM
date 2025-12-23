# Tasks: GraphRAG Chatbot Platform

**Input**: Design documents from `/specs/001-graphrag-chatbot-platform/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL - not explicitly requested in feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`
- Paths shown below follow the plan.md structure

---

## Phase 1: Setup (Shared Infrastructure) ✅ COMPLETE

**Purpose**: Project initialization and Docker/database configuration

- [x] T001 Create backend Python project structure in backend/ with src/, tests/ directories
- [x] T002 [P] Create frontend React project with Vite in frontend/ directory
- [x] T003 [P] Create docker/docker-compose.yml with PostgreSQL, Neo4j, Qdrant, Redis, Ollama, Celery services
- [x] T004 [P] Create docker/docker-compose.dev.yml for development environment with hot reload
- [x] T005 [P] Create docker/.env.example with all required environment variables (including CELERY_BROKER_URL, CELERY_RESULT_BACKEND)
- [x] T006 Initialize backend dependencies in backend/requirements.txt (FastAPI, SQLAlchemy, neo4j, qdrant-client, langchain, pdfplumber, celery, redis)
- [x] T007 [P] Initialize frontend dependencies in frontend/package.json (React, react-router-dom, tanstack/react-query, tailwindcss)
- [x] T008 [P] Create databases/postgres/init.sql with PostgreSQL schema (all tables from data-model.md)
- [x] T009 [P] Create databases/neo4j/init.cypher with Neo4j indexes and constraints
- [x] T010 Create backend/src/core/config.py with Pydantic settings for all environment variables
- [x] T011 [P] Create backend/src/core/database.py with PostgreSQL connection using SQLAlchemy async
- [x] T012 [P] Create backend/src/core/neo4j.py with Neo4j connection client
- [x] T013 [P] Create backend/src/core/qdrant.py with Qdrant client initialization
- [x] T014 [P] Create backend/src/core/redis.py with Redis client for progress tracking (Pub/Sub)
- [x] T015 Create backend/src/core/celery_app.py with Celery configuration (broker, backend, concurrency)
- [x] T016 Create backend/src/main.py with FastAPI app initialization and CORS configuration
- [x] T017 [P] Create backend/Dockerfile for production build
- [x] T018 [P] Create frontend/Dockerfile for production build
- [x] T019 [P] Configure frontend/tailwind.config.js and frontend/src/index.css

**Checkpoint**: All infrastructure ready - Docker services can start (including Celery workers)

---

## Phase 2: Foundational (Blocking Prerequisites) ✅ COMPLETE

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T020 Create backend/src/models/admin_user.py with AdminUser SQLAlchemy model
- [x] T021 Create backend/src/models/chatbot_service.py with ChatbotService SQLAlchemy model
- [x] T022 [P] Create backend/src/models/document.py with Document SQLAlchemy model
- [x] T023 [P] Create backend/src/models/conversation.py with ConversationSession and Message models
- [x] T024 [P] Create backend/src/models/index_version.py with IndexVersion SQLAlchemy model
- [x] T025 [P] Create backend/src/models/stats.py with ChatbotStats SQLAlchemy model
- [x] T026 Create backend/src/models/__init__.py exporting all models
- [x] T027 Create backend/src/api/auth/router.py with POST /auth/login endpoint
- [x] T028 Create backend/src/api/auth/schemas.py with LoginRequest, TokenResponse Pydantic schemas
- [x] T029 Create backend/src/services/auth_service.py with JWT token generation and validation
- [x] T030 Create backend/src/api/deps.py with get_current_user dependency for protected routes
- [x] T031 [P] Create frontend/src/services/api.ts with axios instance and auth interceptor
- [x] T032 [P] Create frontend/src/services/auth.ts with login API call and token management
- [x] T033 [P] Create frontend/src/hooks/useAuth.ts with authentication state hook
- [x] T034 Create frontend/src/pages/Login.tsx with login form UI
- [x] T035 Create frontend/src/App.tsx with React Router setup and protected routes
- [x] T036 Create backend/src/core/llm.py with Ollama ChatOllama wrapper and model configuration
- [x] T037 [P] Create backend/src/core/embeddings.py with embedding model wrapper for Qdrant

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 챗봇 서비스 생성 (Priority: P1) 🎯 MVP ✅ COMPLETE

**Goal**: 관리자가 PDF 업로드 후 GraphRAG 기반 챗봇을 생성할 수 있다

**Independent Test**: PDF 업로드 → 챗봇 생성 → 문서 내용에 대한 질문에 답변 가능 확인

### Implementation for User Story 1

**Backend - Chatbot CRUD**
- [x] T038 [US1] Create backend/src/api/admin/schemas.py with CreateChatbotRequest, Chatbot, ChatbotDetail schemas
- [x] T039 [US1] Create backend/src/services/chatbot_service.py with create, get, list chatbot methods
- [x] T040 [US1] Create backend/src/api/admin/chatbot_router.py with POST /chatbots, GET /chatbots, GET /chatbots/{id} endpoints

**Backend - Document Upload & Storage**
- [x] T041 [US1] Create backend/src/api/admin/document_schemas.py with Document, DocumentProgress schemas
- [x] T042 [US1] Create backend/src/services/document/storage.py with PDF file storage (local/MinIO)
- [x] T043 [US1] Create backend/src/api/admin/document_router.py with POST /chatbots/{id}/documents endpoint (triggers Celery task)
- [x] T044 [US1] Create backend/src/api/admin/document_router.py GET /chatbots/{id}/documents/{docId}/progress endpoint (reads from Redis)

**Backend - Document Processing Pipeline (Celery Tasks)**
- [x] T045 [US1] Create backend/src/services/document/parser.py with pdfplumber PDF text extraction
- [x] T046 [US1] Create backend/src/services/document/chunker.py with LangChain RecursiveCharacterTextSplitter
- [x] T047 [US1] Create backend/src/services/document/embedder.py with chunk embedding and Qdrant storage
- [x] T048 [US1] Create backend/src/services/graph/entity_extractor.py with rule-based + LLM entity extraction (OllamaRateLimitedTask)
- [x] T049 [US1] Create backend/src/services/graph/relation_extractor.py with relationship extraction between entities
- [x] T050 [US1] Create backend/src/services/graph/graph_builder.py with Neo4j node/edge creation
- [x] T051 [US1] Create backend/src/workers/document_tasks.py with Celery task for document processing pipeline
- [x] T052 [US1] Create backend/src/services/document/progress_tracker.py with Redis Pub/Sub progress updates

**Backend - Hybrid Retrieval**
- [x] T053 [US1] Create backend/src/services/retrieval/vector_search.py with Qdrant Top-K search
- [x] T054 [US1] Create backend/src/services/retrieval/graph_expansion.py with Neo4j 2-hop traversal
- [x] T055 [US1] Create backend/src/services/retrieval/context_assembler.py with priority-based context assembly
- [x] T056 [US1] Create backend/src/services/retrieval/hybrid_retriever.py combining vector + graph retrieval

**Backend - Answer Generation**
- [x] T057 [US1] Create backend/src/services/llm/prompt_builder.py with persona and source citation prompts
- [x] T058 [US1] Create backend/src/services/llm/answer_generator.py with Ollama streaming response generation
- [x] T059 [US1] Create backend/src/services/llm/source_formatter.py with source attribution formatting

**Backend - Basic Chat for Testing US1**
- [x] T060 [US1] Create backend/src/api/chat/schemas.py with Session, Message, SendMessageRequest schemas
- [x] T061 [US1] Create backend/src/services/chat_service.py with session creation and message handling
- [x] T062 [US1] Create backend/src/api/chat/router.py with basic POST /chat/{url}/sessions and POST messages endpoint

**Frontend - Admin Dashboard for Chatbot Creation**
- [x] T063 [P] [US1] Create frontend/src/components/Layout.tsx with admin layout (sidebar, header)
- [x] T064 [P] [US1] Create frontend/src/components/Button.tsx with reusable button component
- [x] T065 [P] [US1] Create frontend/src/components/Input.tsx with reusable form input component
- [x] T066 [US1] Create frontend/src/services/chatbots.ts with chatbot API calls
- [x] T067 [US1] Create frontend/src/pages/admin/ChatbotList.tsx with chatbot list page
- [x] T068 [US1] Create frontend/src/pages/admin/ChatbotCreate.tsx with chatbot creation form
- [x] T069 [US1] Create frontend/src/components/FileUpload.tsx with PDF file upload component
- [x] T070 [US1] Create frontend/src/components/ProgressBar.tsx with document processing progress display
- [x] T071 [US1] Create frontend/src/pages/admin/ChatbotDetail.tsx with chatbot detail and document upload
- [x] T072 [US1] Create frontend/src/hooks/useDocumentProgress.ts with polling for document processing status (Redis-backed)

**Checkpoint**: User Story 1 complete - PDF 업로드 후 챗봇 생성 및 기본 질문 응답 가능

---

## Phase 4: User Story 2 - 챗봇 서비스 사용 (Priority: P2) ✅ COMPLETE

**Goal**: 최종 사용자가 챗봇과 실시간 스트리밍 대화를 할 수 있다

**Independent Test**: 챗봇 URL 접속 → 질문 입력 → 스트리밍 응답 + 출처 표시 확인

### Implementation for User Story 2

**Backend - SSE Streaming**
- [x] T073 [US2] Update backend/src/api/chat/router.py with SSE streaming response for POST messages
- [x] T074 [US2] Create backend/src/api/chat/sse.py with EventSourceResponse helpers
- [x] T075 [US2] Create backend/src/api/chat/router.py POST /chat/{url}/sessions/{id}/stop endpoint
- [x] T076 [US2] Update backend/src/services/chat_service.py with streaming token generation and cancellation

**Backend - Context & History**
- [x] T077 [US2] Update backend/src/services/chat_service.py with conversation history retrieval
- [x] T078 [US2] Update backend/src/services/llm/prompt_builder.py with conversation context inclusion

**Frontend - Chat Interface**
- [x] T079 [P] [US2] Create frontend/src/components/ChatMessage.tsx with message bubble component
- [x] T080 [P] [US2] Create frontend/src/components/SourceCitation.tsx with source link display
- [x] T081 [P] [US2] Create frontend/src/components/ChatInput.tsx with message input and send button
- [x] T082 [US2] Create frontend/src/hooks/useSSE.ts with Server-Sent Events hook for streaming
- [x] T083 [US2] Create frontend/src/pages/chat/ChatPage.tsx with full chat interface
- [x] T084 [US2] Create frontend/src/services/chat.ts with chat API calls including SSE
- [x] T085 [US2] Add stop generation button to frontend/src/pages/chat/ChatPage.tsx

**Checkpoint**: User Story 2 complete - 실시간 스트리밍 대화 및 출처 표시 가능

---

## Phase 5: User Story 3 - 챗봇 서비스 관리 (Priority: P3) ✅ COMPLETE

**Goal**: 관리자가 챗봇을 활성화/비활성화/삭제하고 통계를 확인할 수 있다

**Independent Test**: 대시보드에서 챗봇 목록 조회, 상태 변경, 삭제 수행 확인

### Implementation for User Story 3

**Backend - Management APIs**
- [x] T086 [US3] Update backend/src/api/admin/chatbot_router.py with PATCH /chatbots/{id} endpoint
- [x] T087 [US3] Update backend/src/api/admin/chatbot_router.py with DELETE /chatbots/{id} endpoint
- [x] T088 [US3] Update backend/src/api/admin/chatbot_router.py with PATCH /chatbots/{id}/status endpoint
- [x] T089 [US3] Update backend/src/services/chatbot_service.py with update, delete, status change methods
- [x] T090 [US3] Create backend/src/services/cleanup_service.py with Neo4j/Qdrant data cleanup on delete

**Backend - Statistics**
- [x] T091 [US3] Create backend/src/services/stats_service.py with daily stats aggregation
- [x] T092 [US3] Create backend/src/api/admin/stats_router.py with GET /chatbots/{id}/stats endpoint
- [x] T093 [US3] Create backend/src/workers/stats_tasks.py with Celery Beat periodic stats calculation

**Frontend - Management UI**
- [x] T094 [P] [US3] Create frontend/src/components/StatusBadge.tsx with status indicator component
- [x] T095 [P] [US3] Create frontend/src/components/ConfirmDialog.tsx with delete confirmation modal
- [x] T096 [US3] Update frontend/src/pages/admin/ChatbotList.tsx with status toggle and delete buttons
- [x] T097 [US3] Create frontend/src/pages/admin/ChatbotStats.tsx with statistics charts/tables
- [x] T098 [US3] Create frontend/src/services/stats.ts with stats API calls

**Checkpoint**: User Story 3 complete - 챗봇 관리 및 통계 조회 가능

---

## Phase 6: User Story 4 - 문서 추가 및 업데이트 (Priority: P4) ✅ COMPLETE

**Goal**: 관리자가 기존 챗봇에 문서를 추가하거나 삭제하여 지식 베이스를 업데이트할 수 있다

**Independent Test**: 기존 챗봇에 새 PDF 추가 → 새 문서 내용에 대한 질문 응답 확인

### Implementation for User Story 4

**Backend - Index Versioning**
- [x] T099 [US4] Create backend/src/services/version_service.py with new version creation and activation
- [x] T100 [US4] Create backend/src/api/admin/version_router.py with GET /chatbots/{id}/versions endpoint
- [x] T101 [US4] Create backend/src/api/admin/version_router.py with POST /chatbots/{id}/versions/{v}/activate endpoint
- [x] T102 [US4] Update backend/src/services/retrieval/hybrid_retriever.py to use active_version for queries

**Backend - Document Management**
- [x] T103 [US4] Update backend/src/api/admin/document_router.py with DELETE /chatbots/{id}/documents/{docId} endpoint
- [x] T104 [US4] Create backend/src/services/document/document_remover.py with vector/graph cleanup (Celery task)
- [x] T105 [US4] Update backend/src/workers/document_tasks.py to handle incremental updates

**Frontend - Document Management UI**
- [x] T106 [P] [US4] Create frontend/src/components/DocumentList.tsx with document list and delete buttons
- [x] T107 [US4] Update frontend/src/pages/admin/ChatbotDetail.tsx with document management section
- [x] T108 [US4] Create frontend/src/components/VersionSelector.tsx with version selection and activation
- [x] T109 [US4] Create frontend/src/services/versions.ts with version API calls

**Checkpoint**: User Story 4 complete - 문서 추가/삭제 및 버전 관리 가능

---

## Phase 7: Polish & Cross-Cutting Concerns ✅ COMPLETE

**Purpose**: Improvements that affect multiple user stories

- [x] T110 [P] Add error handling middleware in backend/src/core/exceptions.py
- [x] T111 [P] Add request logging middleware in backend/src/core/logging.py
- [x] T112 [P] Create frontend/src/components/ErrorBoundary.tsx with error handling
- [x] T113 [P] Create frontend/src/components/Loading.tsx with loading spinner
- [x] T114 Add API rate limiting in backend/src/core/rate_limit.py
- [x] T115 [P] Add health check endpoint in backend/src/api/health.py (includes Redis, Celery health)
- [x] T116 [P] Configure CORS properly in backend/src/main.py for production
- [x] T117 Add validation for PDF file size (100MB limit) in backend/src/api/admin/document_router.py
- [x] T118 [P] Add empty PDF detection in backend/src/services/document/parser.py
- [x] T119 Run quickstart.md validation with Docker Compose (including Celery workers)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in priority order (P1 → P2 → P3 → P4)
  - P2 depends on P1 (needs working retrieval/generation from P1)
  - P3 can start after P1 (management doesn't need chat streaming)
  - P4 can start after P1 (versioning doesn't need chat streaming)
- **Polish (Final Phase)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Core MVP
- **User Story 2 (P2)**: Depends on US1 completion (needs retrieval/generation infrastructure)
- **User Story 3 (P3)**: Can start after US1 (uses chatbot CRUD, doesn't need chat streaming)
- **User Story 4 (P4)**: Can start after US1 (uses document processing, doesn't need chat streaming)

### Within Each User Story

- Models before services
- Services before endpoints
- Backend before frontend (for same feature)
- Core implementation before integration

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Backend and frontend components marked [P] can run in parallel (within same user story)
- US3 and US4 can run in parallel after US1 completes

---

## Parallel Example: Phase 1 Setup

```bash
# Launch all parallelizable setup tasks together:
Task: "T002 [P] Create frontend React project with Vite"
Task: "T003 [P] Create docker/docker-compose.yml"
Task: "T004 [P] Create docker/docker-compose.dev.yml"
Task: "T005 [P] Create docker/.env.example"
```

## Parallel Example: User Story 1

```bash
# Launch all parallelizable backend model tasks:
Task: "T020 [P] Create Document model"
Task: "T021 [P] Create ConversationSession model"
Task: "T022 [P] Create IndexVersion model"
Task: "T023 [P] Create ChatbotStats model"

# Launch parallelizable frontend components:
Task: "T061 [P] Create Layout component"
Task: "T062 [P] Create Button component"
Task: "T063 [P] Create Input component"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test PDF upload → Chatbot creation → Basic Q&A
5. Deploy/demo if ready (MVP achieved!)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test streaming chat → Deploy/Demo
4. Add User Story 3 → Test management → Deploy/Demo
5. Add User Story 4 → Test versioning → Deploy/Demo
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With 2+ developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 Backend
   - Developer B: User Story 1 Frontend (after backend endpoints ready)
3. After US1 complete:
   - Developer A: User Story 2 (streaming)
   - Developer B: User Story 3 (management)
4. Finally: User Story 4 (versioning)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
