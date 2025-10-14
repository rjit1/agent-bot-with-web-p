-- Order Collection Sessions Schema for Phase 2: Smart Session Management
-- This table stores order collection sessions for persistence and recovery

CREATE TABLE IF NOT EXISTS order_collection_sessions (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('initial', 'collecting_details', 'confirming_details', 'creating_payment', 'completed', 'cancelled', 'product_change_requested')),
    product_details JSONB NOT NULL DEFAULT '{}',
    customer_info JSONB NOT NULL DEFAULT '{}',
    shipping_address JSONB NOT NULL DEFAULT '{}',
    quantity INTEGER NOT NULL DEFAULT 1,
    errors JSONB DEFAULT '[]',
    step_history JSONB DEFAULT '[]',
    preserved_customer_info JSONB DEFAULT NULL, -- For product switching
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours')
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_order_collection_sessions_telegram_id ON order_collection_sessions(telegram_id);
CREATE INDEX IF NOT EXISTS idx_order_collection_sessions_user_id ON order_collection_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_order_collection_sessions_state ON order_collection_sessions(state);
CREATE INDEX IF NOT EXISTS idx_order_collection_sessions_created_at ON order_collection_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_order_collection_sessions_expires_at ON order_collection_sessions(expires_at);

-- Function to cleanup expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_order_sessions()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM order_collection_sessions 
    WHERE expires_at < NOW() 
    AND state IN ('completed', 'cancelled');
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$;

-- Function to get active order collection session
CREATE OR REPLACE FUNCTION get_active_order_session(p_telegram_id BIGINT)
RETURNS TABLE (
    id BIGINT,
    telegram_id BIGINT,
    user_id BIGINT,
    state TEXT,
    product_details JSONB,
    customer_info JSONB,
    shipping_address JSONB,
    quantity INTEGER,
    errors JSONB,
    step_history JSONB,
    preserved_customer_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ocs.id,
        ocs.telegram_id,
        ocs.user_id,
        ocs.state,
        ocs.product_details,
        ocs.customer_info,
        ocs.shipping_address,
        ocs.quantity,
        ocs.errors,
        ocs.step_history,
        ocs.preserved_customer_info,
        ocs.created_at,
        ocs.updated_at
    FROM order_collection_sessions ocs
    WHERE ocs.telegram_id = p_telegram_id
    AND ocs.expires_at > NOW()
    AND ocs.state NOT IN ('completed', 'cancelled');
END;
$$;

-- Row Level Security (RLS) policies
ALTER TABLE order_collection_sessions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own order collection sessions
-- FIXED: Use proper type casting for auth.uid() comparison
CREATE POLICY "Users can access their own order collection sessions" ON order_collection_sessions
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = order_collection_sessions.user_id 
            AND users.telegram_id::text = auth.uid()::text
        )
    );

-- Policy: Service role can access all sessions (for bot operations)
CREATE POLICY "Service role can access all order collection sessions" ON order_collection_sessions
    FOR ALL USING (auth.role() = 'service_role');

-- Grant permissions
GRANT ALL ON order_collection_sessions TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON order_collection_sessions TO authenticated;
GRANT USAGE ON SEQUENCE order_collection_sessions_id_seq TO service_role;
GRANT USAGE ON SEQUENCE order_collection_sessions_id_seq TO authenticated;