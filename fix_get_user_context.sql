-- Fixed version of get_user_context function
-- This fixes the GROUP BY clause error

CREATE OR REPLACE FUNCTION get_user_context(telegram_user_id BIGINT)
RETURNS TABLE (
    user_data JSONB,
    session_data JSONB,
    recent_messages JSONB
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_user_id INTEGER;
BEGIN
    -- First get the user_id
    SELECT id INTO v_user_id
    FROM users
    WHERE telegram_id = telegram_user_id;
    
    -- If user doesn't exist, return empty result
    IF v_user_id IS NULL THEN
        RETURN;
    END IF;
    
    -- Return the context data
    RETURN QUERY
    SELECT 
        to_jsonb(u.*) as user_data,
        COALESCE(
            (SELECT to_jsonb(s.*)
             FROM sessions s
             WHERE s.user_id = v_user_id 
             AND s.expires_at > NOW()
             ORDER BY s.updated_at DESC
             LIMIT 1),
            '{}'::jsonb
        ) as session_data,
        COALESCE(
            (SELECT jsonb_agg(msg_data ORDER BY msg_data->>'created_at' DESC)
             FROM (
                 SELECT jsonb_build_object(
                     'message_type', cl.message_type,
                     'content', cl.content,
                     'intent', cl.intent,
                     'created_at', cl.created_at::text
                 ) as msg_data
                 FROM conversation_logs cl 
                 WHERE cl.user_id = v_user_id 
                 ORDER BY cl.created_at DESC 
                 LIMIT 100
             ) messages),
            '[]'::jsonb
        ) as recent_messages
    FROM users u
    WHERE u.id = v_user_id;
END;
$$;