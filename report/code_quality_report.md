# GraphRAG-vLLM 코드 품질 리포트 (2026-01-01)

## 범위 및 방법
- 리포지터리 문서와 대표적인 백엔드 모듈(코어 설정, 인증, 챗 API/서비스, 검색 파이프라인), Celery 워커, 프론트엔드 챗 흐름, 커스텀 `run_tests.py` 하네스를 검토했습니다.
- 현재 환경에는 Postgres/Neo4j/Qdrant/Redis/vLLM 등 런타임 스택이 없으므로 정적 분석만 수행했고, 자동화 테스트나 E2E 시나리오 실행은 제외했습니다.
- `rg`로 테스트 파일 존재 여부를 확인했으며(`test_*.py` 부재) 기본 설정값을 점검해 보안 노출 가능성을 살폈습니다.

## 장점
- API 라우터 → 서비스 → 영속/인프라 계층으로 관심사가 명확히 구분되어 있어 백엔드 구조를 이해하기 쉽습니다.
- 검색 파이프라인이 벡터 + 그래프 하이브리드를 이미 캡슐화하고, 스트리밍 응답도 단계별 SSE 청크를 정의해 UX 기반을 잘 마련했습니다.

## 주요 문제 및 리스크

1. **치명적 – 기본 관리자 계정이 공개 자격증명으로 자동 생성됨.** 앱은 매 부팅마다 `create_initial_admin`을 호출하고, 이는 `settings.admin_email`/`settings.admin_password` 값(`admin@example.com`/`admin123`)으로 계정을 만듭니다. 관련 코드: `backend/src/core/config.py:99-111`, `backend/src/services/auth_service.py:187-209`, `backend/src/main.py:22-56`. 운영자가 최초 실행 전에 환경변수를 교체하지 않으면 누구든 `/api/v1/auth/login`으로 시스템을 탈취할 수 있습니다. *대응:* 안전한 비밀번호가 없으면 부팅을 중단하거나 경고 후 종료하고, 마이그레이션에서 명시적으로 관리자 생성/회전을 처리하세요.

2. **높음 – 레이트 리미터 미적용.** Redis 기반 `RateLimitMiddleware`가 존재하지만 `src/main.py` 어디에도 `setup_rate_limiting` 호출이 없습니다(`backend/src/core/rate_limit.py:195-214`, `backend/src/main.py:85-154`). 현재 상태로는 `/api/v1/chat` 등 모든 공용 엔드포인트가 무제한 호출을 허용하므로 단일 사용자가 GPU/DB 자원을 소진할 수 있습니다. *대응:* FastAPI 앱에 미들웨어를 추가(설정 플래그 허용)하고 통합 테스트를 마련하세요.

3. **높음 – 대화/통계 카운터가 갱신되지 않음.** `ConversationSession.message_count` 컬럼이 존재하지만 `ChatService.add_message`에서 값을 증가시키지 않아 API 응답이 항상 0을 반환합니다(`backend/src/models/conversation.py:46-74`, `backend/src/services/chat_service.py:275-325`, `backend/src/api/chat/router.py:63-93`). `StatsService.increment_session_count`/`increment_message_count`도 어디에서도 호출되지 않아 실시간 대시보드가 Celery 백필 작업에만 의존합니다. *대응:* `add_message` 내부에서 세션 및 통계 서비스를 연동하거나 이벤트를 발행해 즉시 반영하세요.

4. **높음 – LLM에 전달되는 대화 기록이 가장 오래된 메시지로 고정됨.** `get_session_messages`는 `created_at ASC` 정렬 후 `limit`을 적용하고, `get_chat_history`는 그대로 반환합니다(`backend/src/services/chat_service.py:250-347`). 10턴 이후에는 초기 메시지만 전달되어 최신 맥락이 완전히 무시됩니다. *대응:* DESC 정렬 후 역순 정렬하거나, 전체를 가져온 뒤 후행 N개만 전달하도록 수정하세요.

5. **높음 – 스트리밍 중단 API가 실질적으로 미구현.** `/chat/{access_url}/sessions/{session_id}/stop`는 세션만 확인하고 아무 동작도 하지 않습니다(`backend/src/api/chat/router.py:288-323`). 프론트는 요청을 보내지만 `ChatService.generate_response_stream`은 취소 플래그를 검사하지 않아 서버/GPU가 계속 실행됩니다. *대응:* Redis 등으로 취소 토큰을 저장하고 제너레이터가 청크 사이마다 확인하도록 변경하세요.

6. **중간 – 벡터 검색이 설정을 무시하고 이벤트 루프를 블로킹.** `settings.qdrant_collection_name`이 있음에도 `COLLECTION_NAME = "document_chunks"`로 고정되어 `.env`에서 컬렉션을 바꿔도 적용되지 않습니다(`backend/src/services/retrieval/vector_search.py:13-34`). 또한 `async def search`가 임베딩을 await한 뒤 동기 `QdrantClient.search`를 호출해 FastAPI 이벤트 루프를 막습니다(`backend/src/services/retrieval/vector_search.py:55-71`). *대응:* 설정값을 사용하고, Qdrant 호출을 쓰레드풀로 넘기거나 비동기 클라이언트를 사용하세요.

7. **중간 – `initial_message` 필드를 무시.** `POST /chat/{access_url}/sessions`는 `CreateSessionRequest.initial_message`를 받지만 검증도 실행도 하지 않고 빈 세션만 반환합니다(`backend/src/api/chat/router.py:63-93`, `backend/src/api/chat/schemas.py:74-86`). 초기 인사 자동 실행을 기대하는 UX가 깨집니다. *대응:* 본문에 메시지가 있으면 즉시 `ChatService.add_message` 및 응답 생성을 트리거하세요.

8. **중간 – `run_tests.py` 경로 하드코딩 및 자격증명 노출.** 하네스가 `/home/magic/work/GraphRAG/*.json`을 사용해 현재 리포지터리(`GraphRAG-vLLM`)에서는 실패하며, 관리자 비밀번호 `Admin123456`을 포함하고 사용되지 않는 `get_token`이 남아 있습니다(`run_tests.py:14-41`, `run_tests.py:67-199`). *대응:* `Path(__file__).parent` 기반 상대 경로와 환경변수 기반 자격증명을 사용하세요.

9. **중간 – 자동화 테스트 부재.** `backend/requirements.txt:55-64`에서 pytest 관련 의존성이 주석 처리돼 있고, `rg --files -g 'test_*.py'` 결과가 비어 있어 핵심 플로우(인증, 챗, 검색)가 전혀 검증되지 않습니다. *대응:* 최소한 FastAPI + SQLAlchemy in-memory 환경의 서비스 테스트를 작성하고 CI에 포함하세요.

10. **낮음 – 벡터 검색이 실패하면 그래프 확장이 아예 실행되지 않음.** `HybridRetriever.retrieve`는 `vector_results`가 비면 곧바로 종료해 `include_graph=True`라도 그래프 탐색을 시도하지 않습니다(`backend/src/services/retrieval/hybrid_retriever.py:133-170`). Neo4j에만 존재하는 엔티티 질의는 항상 “자료 없음”으로 끝납니다. *대응:* 쿼리 자체에서 키워드를 추출해 그래프 탐색을 진행하도록 분기하세요.

## 권장 조치
1. 안전한 관리자 크리덴셜과 JWT 시크릿이 설정될 때까지 기동을 차단하거나 강력 경고 후 종료하고, 명시적 마이그레이션으로 초기 관리자를 생성하세요.
2. 레이트 리미터, 취소 플래그, 메시지/통계 카운터를 우선 패치하고 해당 플로우를 증명하는 테스트를 추가하세요.
3. 검색 모듈을 재구성해 설정을 준수하고 이벤트 루프를 막지 않도록 비동기화하거나 워커 풀을 도입하세요.
4. Pytest 기반 최소 테스트 세트를 구축해 인증·챗 엔드포인트 회귀를 감지하세요.
5. `run_tests.py` 및 Celery 통계 훅 등 운영 도구를 리포지터리 기준 경로로 정리하고 실행 방법을 문서화하세요.
