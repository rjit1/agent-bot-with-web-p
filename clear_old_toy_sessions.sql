-- Clear Old Toy Store Session Data
-- This script removes or resets session data that contains toy-related context

-- OPTION 1: Clear all sessions (nuclear option - use if you want fresh start)
-- TRUNCATE TABLE sessions;

-- OPTION 2: Update sessions to remove toy-related product types (safer option)
UPDATE sessions
SET session_data = jsonb_set(
    session_data,
    '{product_type}',
    '"unknown"'::jsonb
)
WHERE session_data->>'product_type' IN ('jeep', 'bike', 'car', 'scooter', 'toy', 'doll', 'puzzle');

-- OPTION 3: Remove conversation summaries that mention toys
UPDATE sessions
SET session_data = jsonb_set(
    session_data,
    '{conversation_summary}',
    '""'::jsonb
)
WHERE session_data->>'conversation_summary' LIKE '%jeep%'
   OR session_data->>'conversation_summary' LIKE '%bike%'
   OR session_data->>'conversation_summary' LIKE '%car%'
   OR session_data->>'conversation_summary' LIKE '%scooter%'
   OR session_data->>'conversation_summary' LIKE '%toy%';

-- OPTION 4: Clear recent_products array if it contains toy references
UPDATE sessions
SET session_data = jsonb_set(
    session_data,
    '{recent_products}',
    '[]'::jsonb
)
WHERE session_data ? 'recent_products';

-- Verify changes
SELECT 
    id,
    telegram_id,
    session_data->>'product_type' as product_type,
    session_data->>'conversation_summary' as summary,
    updated_at
FROM sessions
ORDER BY updated_at DESC
LIMIT 20;

-- Check if any toy-related data remains
SELECT COUNT(*) as toy_sessions_remaining
FROM sessions
WHERE session_data->>'product_type' IN ('jeep', 'bike', 'car', 'scooter', 'toy', 'doll', 'puzzle')
   OR session_data->>'conversation_summary' LIKE '%jeep%'
   OR session_data->>'conversation_summary' LIKE '%bike%';