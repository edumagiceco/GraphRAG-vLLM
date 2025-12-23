<!--
Sync Impact Report
==================
Version change: 0.0.0 → 1.0.0 (MAJOR - initial constitution creation)

Modified principles: N/A (initial creation)

Added sections:
  - Core Principles (5 principles)
  - Technology Stack section
  - Development Workflow section
  - Governance section

Removed sections: N/A

Templates requiring updates:
  - .specify/templates/plan-template.md: ✅ Compatible (no changes needed)
  - .specify/templates/spec-template.md: ✅ Compatible (no changes needed)
  - .specify/templates/tasks-template.md: ✅ Compatible (no changes needed)

Follow-up TODOs: None
==================
-->

# GraphRAG Chatbot System Constitution

## Core Principles

### I. GraphRAG-First Architecture

모든 문서 처리는 Graph-based Retrieval Augmented Generation 방식을 따른다.
- 문서에서 추출된 엔티티와 관계는 반드시 그래프 데이터 구조로 저장한다
- 쿼리 응답 시 그래프 탐색을 통해 관련 컨텍스트를 수집해야 한다
- 단순 벡터 검색보다 그래프 기반 추론을 우선한다
- 그래프 구조는 문서 간 관계 및 개념 간 연결을 명시적으로 표현해야 한다

**근거**: GraphRAG 방식은 단순 RAG보다 복잡한 질문에 대해 더 정확하고 맥락적인 응답을 제공한다.

### II. Local LLM Integration (Ollama)

모든 LLM 추론은 Ollama를 통해 로컬에서 실행한다.
- 기본 모델: nemotron-3-nano:30b
- 외부 API 의존성 없이 자체 호스팅 환경에서 동작해야 한다
- 모델 교체가 용이하도록 추상화 계층을 제공해야 한다
- GPU 메모리 및 성능 제약을 고려한 배치 처리를 지원해야 한다

**근거**: 데이터 프라이버시, 비용 절감, 네트워크 독립성을 위해 로컬 LLM 실행이 필수적이다.

### III. Multi-Tenant Service Architecture

하나의 시스템에서 여러 챗봇 서비스를 독립적으로 운영할 수 있어야 한다.
- 각 PDF 업로드는 독립적인 챗봇 서비스를 생성한다
- 서비스 간 데이터 격리가 보장되어야 한다
- 관리자는 여러 서비스를 통합 관리할 수 있어야 한다
- 각 서비스별 그래프 저장소는 논리적으로 분리되어야 한다

**근거**: 범용 챗봇 플랫폼으로서 다양한 도메인과 사용 사례를 지원해야 한다.

### IV. Document Processing Pipeline

PDF 처리는 체계적인 파이프라인을 통해 수행한다.
- 문서 파싱 → 텍스트 추출 → 청킹 → 엔티티 추출 → 관계 추출 → 그래프 구축 순서를 따른다
- 각 단계는 독립적으로 테스트 가능해야 한다
- 처리 상태와 진행률을 추적할 수 있어야 한다
- 실패한 단계는 재시도 가능해야 한다

**근거**: 복잡한 문서 처리는 명확한 단계 분리를 통해 디버깅과 유지보수가 용이해진다.

### V. API-First Design

모든 기능은 RESTful API를 통해 노출한다.
- 관리자 기능과 챗봇 서비스 모두 API로 접근 가능해야 한다
- API 응답은 JSON 형식을 사용한다
- 스트리밍 응답(SSE)을 지원하여 실시간 챗봇 대화를 제공한다
- API 문서화(OpenAPI/Swagger)를 필수로 제공한다

**근거**: API-First 설계는 프론트엔드 독립성과 시스템 통합 유연성을 보장한다.

## Technology Stack

본 프로젝트의 기술 스택 결정 원칙:

- **LLM Runtime**: Ollama (nemotron-3-nano:30b 기본)
- **Graph Database**: 프로젝트 요구사항에 따라 선택 (Neo4j, NetworkX, 또는 경량 그래프 저장소)
- **Vector Store**: 그래프와 함께 하이브리드 검색 지원을 위해 필요 시 사용
- **Backend Framework**: Python 기반 (FastAPI 권장)
- **Document Processing**: PDF 파싱 라이브러리 활용 (PyPDF2, pdfplumber 등)
- **Frontend**: 관리자 UI는 별도 구현 (React 또는 경량 프레임워크)

기술 선택 시 다음을 우선한다:
1. 로컬 실행 가능성 (외부 서비스 의존 최소화)
2. 오픈소스 우선
3. 커뮤니티 지원 및 문서화 수준
4. 성능과 리소스 효율성 균형

## Development Workflow

### 코드 품질

- 모든 핵심 기능에 대해 단위 테스트를 작성한다
- 문서 처리 파이프라인은 통합 테스트로 검증한다
- 타입 힌트(Python type hints)를 적극 활용한다
- 린터(ruff, mypy)를 통한 코드 품질 유지

### 버전 관리

- 기능 브랜치 기반 개발 (feature/xxx)
- 커밋 메시지는 명확하고 의미 있게 작성
- 주요 변경은 PR을 통해 리뷰

### 문서화

- API 엔드포인트는 자동 문서화 (OpenAPI)
- 주요 아키텍처 결정은 ADR(Architecture Decision Record)로 기록
- README에 설치 및 실행 가이드 포함

## Governance

본 헌법은 GraphRAG Chatbot System 프로젝트의 최상위 지침이다.

### 수정 절차

1. 헌법 수정 제안은 문서화하여 제출한다
2. 주요 원칙 변경(MAJOR)은 팀 합의가 필요하다
3. 수정 시 모든 관련 템플릿과 문서를 함께 업데이트한다
4. 버전은 Semantic Versioning을 따른다:
   - MAJOR: 핵심 원칙 제거 또는 재정의
   - MINOR: 새 원칙/섹션 추가 또는 확장
   - PATCH: 명확화, 오타 수정, 비의미적 개선

### 준수 검증

- 모든 PR은 헌법 원칙 준수 여부를 확인한다
- 복잡성 추가는 명확한 근거와 함께 정당화해야 한다
- 정기적으로 헌법과 실제 개발 관행의 일치 여부를 검토한다

**Version**: 1.0.0 | **Ratified**: 2025-12-22 | **Last Amended**: 2025-12-22
