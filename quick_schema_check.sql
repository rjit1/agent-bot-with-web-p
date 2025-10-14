-- Quick Phase 3 Schema Verification
-- Run this in Supabase SQL Editor to verify Phase 3 schema is applied
-- Expected: All checks should return TRUE

DO $
DECLARE
    v_tables_exist BOOLEAN;
    v_functions_exist BOOLEAN;
    v_indexes_exist BOOLEAN;
    v_triggers_exist BOOLEAN;
    v_policies_exist BOOLEAN;
    v_all_passed BOOLEAN := TRUE;
BEGIN
    RAISE NOTICE '=========================================';
    RAISE NOTICE 'Phase 3 Payment Schema Verification';
    RAISE NOTICE '=========================================';
    RAISE NOTICE '';
    
    -- Check 1: Tables exist
    RAISE NOTICE '1. Checking tables...';
    SELECT COUNT(*) = 5 INTO v_tables_exist
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name IN ('orders', 'order_items', 'payments', 'customer_addresses', 'order_status_history');
    
    IF v_tables_exist THEN
        RAISE NOTICE '   ✅ All 5 tables exist';
    ELSE
        RAISE NOTICE '   ❌ Missing tables!';
        v_all_passed := FALSE;
    END IF;
    
    -- Check 2: RPC Functions exist
    RAISE NOTICE '2. Checking RPC functions...';
    SELECT COUNT(*) = 5 INTO v_functions_exist
    FROM information_schema.routines 
    WHERE routine_schema = 'public' 
    AND routine_name IN ('create_order', 'add_order_item', 'update_order_status', 'get_order_details', 'validate_indian_address');
    
    IF v_functions_exist THEN
        RAISE NOTICE '   ✅ All 5 RPC functions exist';
    ELSE
        RAISE NOTICE '   ❌ Missing RPC functions!';
        v_all_passed := FALSE;
    END IF;
    
    -- Check 3: Critical indexes exist
    RAISE NOTICE '3. Checking indexes...';
    SELECT COUNT(*) >= 10 INTO v_indexes_exist
    FROM pg_indexes 
    WHERE schemaname = 'public' 
    AND tablename IN ('orders', 'order_items', 'payments', 'customer_addresses', 'order_status_history');
    
    IF v_indexes_exist THEN
        RAISE NOTICE '   ✅ Critical indexes exist';
    ELSE
        RAISE NOTICE '   ❌ Missing indexes!';
        v_all_passed := FALSE;
    END IF;
    
    -- Check 4: Triggers exist
    RAISE NOTICE '4. Checking triggers...';
    SELECT COUNT(*) = 3 INTO v_triggers_exist
    FROM information_schema.triggers 
    WHERE trigger_schema = 'public' 
    AND event_object_table IN ('orders', 'payments', 'customer_addresses')
    AND trigger_name LIKE '%updated_at%';
    
    IF v_triggers_exist THEN
        RAISE NOTICE '   ✅ All 3 triggers exist';
    ELSE
        RAISE NOTICE '   ❌ Missing triggers!';
        v_all_passed := FALSE;
    END IF;
    
    -- Check 5: RLS policies exist
    RAISE NOTICE '5. Checking RLS policies...';
    SELECT COUNT(*) >= 10 INTO v_policies_exist
    FROM pg_policies 
    WHERE schemaname = 'public' 
    AND tablename IN ('orders', 'order_items', 'payments', 'customer_addresses', 'order_status_history');
    
    IF v_policies_exist THEN
        RAISE NOTICE '   ✅ RLS policies exist';
    ELSE
        RAISE NOTICE '   ❌ Missing RLS policies!';
        v_all_passed := FALSE;
    END IF;
    
    RAISE NOTICE '';
    RAISE NOTICE '=========================================';
    IF v_all_passed THEN
        RAISE NOTICE '🎉 All checks passed! Phase 3 schema is properly applied.';
    ELSE
        RAISE NOTICE '⚠️  Some checks failed. Review errors above.';
    END IF;
    RAISE NOTICE '=========================================';
END $;

-- Detailed table information
SELECT 
    'Table Details' as check_type,
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE columns.table_name = tables.table_name) as column_count
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('orders', 'order_items', 'payments', 'customer_addresses', 'order_status_history')
ORDER BY table_name;

-- Function details
SELECT 
    'Function Details' as check_type,
    routine_name as function_name,
    routine_type
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_name IN ('create_order', 'add_order_item', 'update_order_status', 'get_order_details', 'validate_indian_address')
ORDER BY routine_name;
