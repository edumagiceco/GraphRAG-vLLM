-- =============================================================================
-- GraphRAG Chatbot Platform - PostgreSQL Schema Initialization
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- ENUM Types
-- =============================================================================

CREATE TYPE chatbot_status AS ENUM ('active', 'inactive', 'processing');
CREATE TYPE document_status AS ENUM (
    'pending', 'parsing', 'chunking', 'embedding',
    'extracting', 'graphing', 'completed', 'failed'
);
CREATE TYPE version_status AS ENUM ('building', 'ready', 'active', 'archived');
CREATE TYPE message_role AS ENUM ('user', 'assistant');

-- =============================================================================
-- Tables
-- =============================================================================

-- Admin Users
CREATE TABLE admin_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_admin_users_email ON admin_users(email);

-- Chatbot Services
CREATE TABLE chatbot_services (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    admin_id UUID NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    persona JSONB NOT NULL DEFAULT '{"tone": "professional", "language": "ko"}',
    status chatbot_status NOT NULL DEFAULT 'processing',
    access_url VARCHAR(100) UNIQUE NOT NULL,
    active_version INTEGER NOT NULL DEFAULT 1,
    llm_model VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chatbot_admin ON chatbot_services(admin_id);
CREATE INDEX idx_chatbot_status ON chatbot_services(status);
CREATE INDEX idx_chatbot_access_url ON chatbot_services(access_url);

-- Documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id UUID NOT NULL REFERENCES chatbot_services(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    status document_status NOT NULL DEFAULT 'pending',
    version INTEGER NOT NULL DEFAULT 1,
    page_count INTEGER,
    processing_progress INTEGER DEFAULT 0,
    error_message TEXT,
    chunk_count INTEGER,
    entity_count INTEGER,
    processed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_document_chatbot ON documents(chatbot_id);
CREATE INDEX idx_document_status ON documents(status);
CREATE INDEX idx_document_version ON documents(chatbot_id, version);

-- Index Versions
CREATE TABLE index_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id UUID NOT NULL REFERENCES chatbot_services(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    status version_status NOT NULL DEFAULT 'building',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMP,
    UNIQUE(chatbot_id, version)
);

CREATE INDEX idx_version_chatbot ON index_versions(chatbot_id);
CREATE INDEX idx_version_status ON index_versions(chatbot_id, status);

-- Conversation Sessions
CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id UUID NOT NULL REFERENCES chatbot_services(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL DEFAULT (NOW() + INTERVAL '30 minutes'),
    message_count INTEGER DEFAULT 0
);

CREATE INDEX idx_session_chatbot ON conversation_sessions(chatbot_id);
CREATE INDEX idx_session_expires ON conversation_sessions(expires_at);

-- Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    role message_role NOT NULL,
    content TEXT NOT NULL,
    sources JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_message_session ON messages(session_id);
CREATE INDEX idx_message_created ON messages(session_id, created_at);

-- Chatbot Statistics (Daily Aggregation)
CREATE TABLE chatbot_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id UUID NOT NULL REFERENCES chatbot_services(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    session_count INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    avg_response_time_ms INTEGER,
    UNIQUE(chatbot_id, date)
);

CREATE INDEX idx_stats_chatbot_date ON chatbot_stats(chatbot_id, date);

-- System Settings (Key-Value Configuration)
CREATE TABLE system_settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_system_settings_key ON system_settings(key);

-- Trigger for system_settings updated_at
CREATE TRIGGER update_system_settings_updated_at
    BEFORE UPDATE ON system_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Functions
-- =============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- =============================================================================
-- Triggers
-- =============================================================================

CREATE TRIGGER update_admin_users_updated_at
    BEFORE UPDATE ON admin_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chatbot_services_updated_at
    BEFORE UPDATE ON chatbot_services
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON TABLE admin_users IS '관리자 계정 정보';
COMMENT ON TABLE chatbot_services IS '챗봇 서비스 인스턴스';
COMMENT ON TABLE documents IS '업로드된 PDF 문서';
COMMENT ON TABLE index_versions IS '인덱스 버전 관리';
COMMENT ON TABLE conversation_sessions IS '대화 세션';
COMMENT ON TABLE messages IS '대화 메시지';
COMMENT ON TABLE chatbot_stats IS '챗봇 사용 통계 (일별 집계)';

COMMENT ON COLUMN chatbot_services.persona IS '페르소나 설정 (tone, language, greeting, fallback_message)';
COMMENT ON COLUMN messages.sources IS '출처 정보 배열 (document_id, document_name, page, section, relevance_score)';

COMMENT ON TABLE system_settings IS '시스템 전역 설정 (LLM 모델, 임베딩 모델 등)';
