-- Supabase Schema for Gurtoy Telegram Bot Knowledge Base
-- This file contains all the necessary tables and functions for Phase 1
-- Updated for 768-dimensional embeddings (text-embedding-004 model)

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Knowledge Base Table
CREATE TABLE IF NOT EXISTS gurtoy_knowledge (
    id BIGSERIAL PRIMARY KEY,
    chunk_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    keywords TEXT[] DEFAULT '{}',
    priority INTEGER DEFAULT 3 CHECK (priority >= 1 AND priority <= 5),
    language TEXT DEFAULT 'en',
    metadata JSONB DEFAULT '{}',
    embedding VECTOR(768), -- text-embedding-004 dimension (768)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_gurtoy_knowledge_category ON gurtoy_knowledge(category);
CREATE INDEX IF NOT EXISTS idx_gurtoy_knowledge_priority ON gurtoy_knowledge(priority);
CREATE INDEX IF NOT EXISTS idx_gurtoy_knowledge_keywords ON gurtoy_knowledge USING GIN(keywords);
-- Use HNSW index for optimal performance with 768 dimensions
CREATE INDEX IF NOT EXISTS idx_gurtoy_knowledge_embedding ON gurtoy_knowledge USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Users table for conversation management
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code TEXT DEFAULT 'en',
    phone_number TEXT,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Sessions table for conversation context
CREATE TABLE IF NOT EXISTS sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    telegram_chat_id BIGINT NOT NULL,
    session_data JSONB DEFAULT '{}',
    context JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours')
);

-- Conversation logs for analytics and improvement
CREATE TABLE IF NOT EXISTS conversation_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    session_id BIGINT REFERENCES sessions(id) ON DELETE CASCADE,
    message_type TEXT NOT NULL CHECK (message_type IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    intent TEXT,
    confidence FLOAT,
    function_calls JSONB DEFAULT '[]',
    response_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Sentiment analysis and tags
CREATE TABLE IF NOT EXISTS sentiment_tags (
    id BIGSERIAL PRIMARY KEY,
    conversation_log_id BIGINT REFERENCES conversation_logs(id) ON DELETE CASCADE,
    sentiment TEXT CHECK (sentiment IN ('positive', 'negative', 'neutral')),
    sentiment_score FLOAT CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
    emotions TEXT[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Handoff requests for human escalation
CREATE TABLE IF NOT EXISTS handoff_requests (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    session_id BIGINT REFERENCES sessions(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'assigned', 'resolved', 'cancelled')),
    assigned_to TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Function to search knowledge base using vector similarity
CREATE OR REPLACE FUNCTION search_knowledge(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5,
    filter_category TEXT DEFAULT NULL,
    min_priority INT DEFAULT 5
)
RETURNS TABLE (
    chunk_id TEXT,
    title TEXT,
    content TEXT,
    category TEXT,
    keywords TEXT[],
    priority INT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gk.chunk_id,
        gk.title,
        gk.content,
        gk.category,
        gk.keywords,
        gk.priority,
        (gk.embedding <=> query_embedding) * -1 + 1 AS similarity
    FROM gurtoy_knowledge gk
    WHERE 
        (gk.embedding <=> query_embedding) * -1 + 1 > match_threshold
        AND (filter_category IS NULL OR gk.category = filter_category)
        AND gk.priority <= min_priority
    ORDER BY gk.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to get user context
CREATE OR REPLACE FUNCTION get_user_context(telegram_user_id BIGINT)
RETURNS TABLE (
    user_data JSONB,
    session_data JSONB,
    recent_messages JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        to_jsonb(u.*) as user_data,
        COALESCE(s.session_data, '{}'::jsonb) as session_data,
        COALESCE(
            (SELECT jsonb_agg(
                jsonb_build_object(
                    'message_type', cl.message_type,
                    'content', cl.content,
                    'intent', cl.intent,
                    'created_at', cl.created_at
                )
            )
            FROM conversation_logs cl 
            WHERE cl.user_id = u.id 
            ORDER BY cl.created_at DESC 
            LIMIT 10), 
            '[]'::jsonb
        ) as recent_messages
    FROM users u
    LEFT JOIN sessions s ON s.user_id = u.id AND s.expires_at > NOW()
    WHERE u.telegram_id = telegram_user_id
    ORDER BY s.updated_at DESC
    LIMIT 1;
END;
$$;

-- Function to update user activity
CREATE OR REPLACE FUNCTION update_user_activity(telegram_user_id BIGINT)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE users 
    SET last_active = NOW(), updated_at = NOW()
    WHERE telegram_id = telegram_user_id;
END;
$$;

-- Trigger to automatically update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply the trigger to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_knowledge_updated_at BEFORE UPDATE ON gurtoy_knowledge FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE sentiment_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE handoff_requests ENABLE ROW LEVEL SECURITY;

-- Policy for users table (users can only access their own data)
CREATE POLICY "Users can view own data" ON users FOR SELECT USING (auth.uid()::text = telegram_id::text);
CREATE POLICY "Users can update own data" ON users FOR UPDATE USING (auth.uid()::text = telegram_id::text);

-- Policy for sessions (users can only access their own sessions)
CREATE POLICY "Users can view own sessions" ON sessions FOR SELECT USING (
    EXISTS (SELECT 1 FROM users WHERE users.id = sessions.user_id AND users.telegram_id::text = auth.uid()::text)
);

-- Service role can access everything (for bot operations)
CREATE POLICY "Service role full access users" ON users FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access sessions" ON sessions FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access logs" ON conversation_logs FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access sentiment" ON sentiment_tags FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access handoff" ON handoff_requests FOR ALL USING (auth.role() = 'service_role');

-- Knowledge base is publicly readable (no RLS needed for bot operations)
-- But we'll add a policy for safety
CREATE POLICY "Knowledge base readable" ON gurtoy_knowledge FOR SELECT USING (true);
CREATE POLICY "Service role full access knowledge" ON gurtoy_knowledge FOR ALL USING (auth.role() = 'service_role');

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_user_id ON conversation_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_created_at ON conversation_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_handoff_requests_status ON handoff_requests(status);
CREATE INDEX IF NOT EXISTS idx_handoff_requests_priority ON handoff_requests(priority);

-- Insert some sample data for testing (optional)
-- This will be replaced by the actual knowledge data from the Python script
INSERT INTO gurtoy_knowledge (chunk_id, title, content, category, keywords, priority) VALUES
('test_chunk', 'Test Knowledge', 'This is a test knowledge chunk for Gurtoy bot.', 'test', ARRAY['test', 'sample'], 5)
ON CONFLICT (chunk_id) DO NOTHING;

COMMENT ON TABLE gurtoy_knowledge IS 'Stores company knowledge chunks with embeddings for vector search (768-dimensional)';
COMMENT ON TABLE users IS 'Telegram bot users with preferences and profile data';
COMMENT ON TABLE sessions IS 'Active conversation sessions with context';
COMMENT ON TABLE conversation_logs IS 'Complete conversation history for analytics';
COMMENT ON TABLE sentiment_tags IS 'Sentiment analysis results for conversations';
COMMENT ON TABLE handoff_requests IS 'Requests for human agent escalation';