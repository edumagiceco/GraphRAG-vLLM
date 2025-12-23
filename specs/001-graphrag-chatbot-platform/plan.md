# Implementation Plan: GraphRAG Chatbot Platform

**Branch**: `001-graphrag-chatbot-platform` | **Date**: 2025-12-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-graphrag-chatbot-platform/spec.md`

## Summary

PDF 문서를 업로드하면 GraphRAG 방식으로 지식 그래프를 구축하고, 이를 기반으로 Hybrid Retrieval(Vector Top-K → Graph 확장)을 통해 질문에 답변하는 멀티테넌트 챗봇 플랫폼을 구축한다. Ollama 기반 로컬 LLM(nemotron-3-nano:30b)을 사용하며, Docker 기반 MSA 아키텍처로 프론트엔드/백엔드/DB를 분리한다.

## Technical Context

**Language/Version**: Python 3.11+ (Backend), TypeScript 5.x (Frontend)
**Primary Dependencies**: FastAPI, LangChain, Neo4j, Qdrant, React, Ollama
**Storage**: PostgreSQL (메타데이터), Neo4j (그래프), Qdrant (벡터), MinIO/로컬 (PDF 파일)
**Testing**: pytest (Backend), Vitest (Frontend)
**Target Platform**: Linux server (Docker), 웹 브라우저 (Frontend)
**Project Type**: Web application (frontend + backend + multiple databases)
**Performance Goals**: 첫 응답 토큰 3초 이내, 50개 동시 세션, 10개 챗봇 서비스 동시 운영
**Constraints**: PDF 100MB 제한, 2-hop 그래프 탐색, 로컬 LLM만 사용 (외부 API 없음)
**Scale/Scope**: 단일 서버 환경, 10+ 챗봇 서비스, 관리자 1명 이상

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. GraphRAG-First Architecture | ✅ PASS | Hybrid Retrieval: Vector → Graph 확장 방식 채택, 3개 노드타입/엣지타입 정의 |
| II. Local LLM Integration (Ollama) | ✅ PASS | Ollama 기반 nemotron-3-nano:30b 사용, 모델 교체 가능한 추상화 계층 |
| III. Multi-Tenant Service Architecture | ✅ PASS | 챗봇별 독립 지식 그래프, 서비스 간 데이터 격리, 통합 관리 대시보드 |
| IV. Document Processing Pipeline | ✅ PASS | 파싱→추출→청킹→엔티티→관계→그래프 순서, 진행률 추적, 버전 관리 |
| V. API-First Design | ✅ PASS | RESTful API, SSE 스트리밍, OpenAPI 문서화 |

**Gate Result**: ✅ ALL PASS - Phase 0 진행 가능

## Project Structure

### Documentation (this feature)

```text
specs/001-graphrag-chatbot-platform/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI specs)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/                 # FastAPI 라우터
│   │   ├── admin/           # 관리자 API (챗봇 CRUD, 문서 관리)
│   │   ├── chat/            # 챗봇 대화 API (SSE 스트리밍)
│   │   └── auth/            # 인증 API
│   ├── models/              # SQLAlchemy/Pydantic 모델
│   ├── services/            # 비즈니스 로직
│   │   ├── document/        # PDF 처리 파이프라인
│   │   ├── graph/           # Knowledge Graph 관리
│   │   ├── retrieval/       # Hybrid Retrieval (Vector + Graph)
│   │   └── llm/             # Ollama LLM 통합
│   ├── workers/             # 비동기 작업 (문서 처리)
│   └── core/                # 설정, 의존성
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/
├── Dockerfile
└── requirements.txt

frontend/
├── src/
│   ├── components/          # 재사용 UI 컴포넌트
│   ├── pages/
│   │   ├── admin/           # 관리자 대시보드
│   │   └── chat/            # 챗봇 대화 인터페이스
│   ├── services/            # API 클라이언트
│   └── hooks/               # React 커스텀 훅
├── tests/
├── Dockerfile
└── package.json

docker/
├── docker-compose.yml       # 전체 서비스 오케스트레이션
├── docker-compose.dev.yml   # 개발 환경
└── .env.example

databases/
├── neo4j/                   # Neo4j 초기화 스크립트
├── postgres/                # PostgreSQL 마이그레이션
└── qdrant/                  # Qdrant 설정
```

**Structure Decision**: Web application 구조 채택 - 프론트엔드/백엔드/다중 데이터베이스 분리. MSA 요구사항에 따라 각 서비스를 독립 Docker 컨테이너로 패키징.

## Complexity Tracking

> **No violations detected** - 모든 Constitution 원칙 준수

| Aspect | Justification |
|--------|---------------|
| 다중 데이터베이스 (PostgreSQL + Neo4j + Qdrant) | GraphRAG 요구사항: 메타데이터(관계형), 그래프(Neo4j), 벡터(Qdrant) 각각 최적화된 저장소 필요 |
| MSA 아키텍처 | FR-015 명시적 요구사항: 프론트/백엔드/DB 독립 마이크로서비스 |
