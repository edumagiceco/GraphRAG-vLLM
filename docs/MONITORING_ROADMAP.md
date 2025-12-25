# 챗봇 모니터링 개발 로드맵

## 개요

GraphRAG 챗봇 플랫폼의 모니터링 기능 개발 계획입니다.

---

## Phase 1: 기본 메트릭 수집 및 대시보드 ✅ 완료

### 완료일: 2025-12-25

### 구현 내용

| 항목 | 상태 | 설명 |
|------|------|------|
| Message 모델 메트릭 필드 | ✅ | response_time_ms, input_tokens, output_tokens, retrieval_count, retrieval_time_ms |
| ChatbotStats 집계 필드 | ✅ | total_input_tokens, total_output_tokens, total_retrieval_count, avg_retrieval_time_ms |
| 토큰 카운터 유틸리티 | ✅ | 한국어/영어 토큰 추정 (token_counter.py) |
| 메트릭 수집 로직 | ✅ | chat_service.py에서 실시간 수집 |
| P50/P95/P99 계산 | ✅ | stats_service.py에서 퍼센타일 계산 |
| 통계 API | ✅ | GET /stats, GET /stats/performance, POST /stats/recalculate |
| 차트 컴포넌트 | ✅ | Recharts 기반 (ResponseTimeChart, TokenUsageChart, MetricCard) |
| 통계 대시보드 UI | ✅ | 메트릭 카드, 차트, 일별 테이블 |
| 용어 설명 섹션 | ✅ | P50/P95/P99, 토큰, 검색 메트릭 설명 |

### 관련 파일

**백엔드:**
- `backend/src/models/conversation.py` - 메트릭 필드 추가
- `backend/src/models/stats.py` - 집계 필드 추가
- `backend/src/core/token_counter.py` - 토큰 카운터 (신규)
- `backend/src/services/chat_service.py` - 메트릭 수집
- `backend/src/services/stats_service.py` - 집계 및 퍼센타일
- `backend/src/api/admin/stats_router.py` - 통계 API

**프론트엔드:**
- `frontend/src/components/charts/` - 차트 컴포넌트
- `frontend/src/pages/admin/ChatbotStats.tsx` - 통계 대시보드
- `frontend/src/services/stats.ts` - API 클라이언트

---

## Phase 2: 알림 및 경고 시스템 📋 계획됨

### 목표
성능 이상 감지 시 관리자에게 자동으로 알림을 보내는 시스템 구축

### 기능 목록

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 응답 시간 임계값 알림 | P95가 설정값(예: 5초) 초과 시 알림 | 높음 |
| 토큰 사용량 한도 | 일일/월간 토큰 사용량 한도 설정 및 알림 | 높음 |
| 오류율 모니터링 | 응답 실패율이 임계값 초과 시 알림 | 중간 |
| 이메일 알림 | SMTP를 통한 이메일 발송 | 높음 |
| Slack 알림 | Slack Webhook 연동 | 중간 |
| 웹훅 알림 | 커스텀 웹훅 URL 호출 | 낮음 |
| 알림 이력 조회 | 발생한 알림 기록 및 확인 상태 | 높음 |

### 구현 항목

```
백엔드:
├── models/alert.py                  # 알림 규칙 및 이력 모델
├── services/alert_service.py        # 알림 로직 (임계값 체크, 알림 발송)
├── services/notification/           # 알림 채널
│   ├── __init__.py
│   ├── base.py                      # 기본 인터페이스
│   ├── email_sender.py              # 이메일 발송
│   ├── slack_sender.py              # Slack 발송
│   └── webhook_sender.py            # 웹훅 호출
├── api/admin/alerts_router.py       # 알림 설정 API
└── workers/alert_checker.py         # 주기적 임계값 체크 (Celery Beat)

프론트엔드:
├── pages/admin/AlertSettings.tsx    # 알림 규칙 설정 UI
├── pages/admin/AlertHistory.tsx     # 알림 이력 조회
├── components/AlertBadge.tsx        # 알림 표시 배지
└── services/alerts.ts               # 알림 API 클라이언트
```

### 데이터베이스 스키마

```sql
-- 알림 규칙
CREATE TABLE alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chatbot_id UUID REFERENCES chatbot_services(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,  -- 'p95_response_time', 'daily_tokens', 'error_rate'
    threshold_value FLOAT NOT NULL,
    comparison VARCHAR(10) NOT NULL,   -- 'gt', 'lt', 'gte', 'lte'
    notification_channels JSONB DEFAULT '[]',  -- ['email', 'slack']
    notification_config JSONB DEFAULT '{}',    -- 채널별 설정 (이메일 주소, Slack URL 등)
    cooldown_minutes INT DEFAULT 60,   -- 재알림 대기 시간
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 알림 이력
CREATE TABLE alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID REFERENCES alert_rules(id) ON DELETE CASCADE,
    chatbot_id UUID REFERENCES chatbot_services(id) ON DELETE CASCADE,
    triggered_at TIMESTAMP DEFAULT NOW(),
    metric_value FLOAT NOT NULL,
    threshold_value FLOAT NOT NULL,
    message TEXT,
    notified_channels JSONB DEFAULT '[]',
    notification_status JSONB DEFAULT '{}',  -- 채널별 발송 결과
    acknowledged_at TIMESTAMP,
    acknowledged_by UUID REFERENCES admin_users(id)
);

-- 인덱스
CREATE INDEX idx_alert_rules_chatbot ON alert_rules(chatbot_id);
CREATE INDEX idx_alert_history_chatbot ON alert_history(chatbot_id);
CREATE INDEX idx_alert_history_triggered ON alert_history(triggered_at DESC);
```

### API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/v1/chatbots/{id}/alerts/rules` | 알림 규칙 목록 |
| POST | `/api/v1/chatbots/{id}/alerts/rules` | 알림 규칙 생성 |
| PUT | `/api/v1/chatbots/{id}/alerts/rules/{rule_id}` | 알림 규칙 수정 |
| DELETE | `/api/v1/chatbots/{id}/alerts/rules/{rule_id}` | 알림 규칙 삭제 |
| GET | `/api/v1/chatbots/{id}/alerts/history` | 알림 이력 조회 |
| POST | `/api/v1/alerts/history/{id}/acknowledge` | 알림 확인 처리 |
| POST | `/api/v1/alerts/test` | 알림 테스트 발송 |

---

## Phase 3: 실시간 모니터링 📋 계획됨

### 목표
WebSocket 기반 실시간 대시보드로 현재 시스템 상태 모니터링

### 기능 목록

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 실시간 활성 세션 수 | 현재 진행 중인 대화 세션 수 | 높음 |
| 실시간 응답 시간 | 최근 N분간 평균 응답 시간 | 높음 |
| 실시간 토큰 사용량 | 분당 토큰 사용량 | 중간 |
| 시스템 상태 모니터링 | vLLM, DB 등 서비스 상태 | 높음 |
| 실시간 차트 업데이트 | 자동 갱신되는 차트 | 중간 |

### 구현 항목

```
백엔드:
├── api/websocket/
│   ├── __init__.py
│   ├── realtime_stats.py        # 실시간 통계 WebSocket
│   └── system_status.py         # 시스템 상태 WebSocket
├── services/realtime_service.py # 실시간 데이터 집계
└── core/redis_pubsub.py         # Redis Pub/Sub 연동

프론트엔드:
├── hooks/useRealtimeStats.ts    # WebSocket 훅
├── pages/admin/RealtimeDashboard.tsx  # 실시간 대시보드
└── components/realtime/
    ├── ActiveSessionsCard.tsx
    ├── ResponseTimeGauge.tsx
    └── SystemStatusIndicator.tsx
```

### 기술 스택

- **WebSocket**: FastAPI WebSocket + React useWebSocket
- **실시간 데이터**: Redis Pub/Sub
- **차트**: Recharts with real-time updates

---

## Phase 4: 고급 분석 📋 계획됨

### 목표
심층적인 사용 패턴 분석 및 인사이트 제공

### 기능 목록

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 시간대별 사용량 히트맵 | 요일/시간별 사용량 시각화 | 중간 |
| 질문 유형 분류 | LLM 기반 질문 카테고리 분류 | 낮음 |
| 사용자 만족도 피드백 | 응답에 대한 좋아요/싫어요 | 중간 |
| 응답 품질 평가 | 자동 응답 품질 점수 | 낮음 |
| 비용 추정 | 토큰 기반 비용 계산 | 높음 |
| 데이터 내보내기 | CSV/Excel 다운로드 | 높음 |
| 챗봇 비교 분석 | 여러 챗봇 성능 비교 | 중간 |

### 구현 항목

```
백엔드:
├── services/analytics/
│   ├── hourly_distribution.py   # 시간대별 분포
│   ├── question_classifier.py   # 질문 분류 (LLM)
│   ├── cost_estimator.py        # 비용 추정
│   └── export_service.py        # 데이터 내보내기
├── api/admin/analytics_router.py
└── models/feedback.py           # 피드백 모델

프론트엔드:
├── pages/admin/Analytics.tsx    # 고급 분석 페이지
├── components/analytics/
│   ├── HourlyHeatmap.tsx
│   ├── QuestionCategories.tsx
│   ├── CostEstimation.tsx
│   └── ExportButton.tsx
└── services/analytics.ts
```

---

## 기타 개선 사항 📋 백로그

| 항목 | 설명 | 우선순위 |
|------|------|----------|
| 자동 통계 재계산 | Celery Beat으로 일일 자동 집계 | 높음 |
| 통계 캐싱 | Redis 캐시로 조회 성능 향상 | 중간 |
| 대시보드 커스터마이징 | 사용자별 위젯 배치 | 낮음 |
| 모바일 대응 | 반응형 통계 대시보드 | 중간 |
| API 사용량 제한 | Rate limiting 및 사용량 추적 | 중간 |

---

## 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 1.0.0 | 2025-12-25 | Phase 1 완료 - 기본 메트릭 및 대시보드 |

---

## 참고 자료

- [Phase 1 구현 계획](/home/magic/.claude/plans/rustling-fluttering-raven.md)
- [README - 성능 모니터링 섹션](/README.md#성능-모니터링-대시보드)
