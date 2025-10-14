-- ============================================================================
-- DEPLOYMENT SCRIPT FOR KEYWORD SEARCH FUNCTION
-- ============================================================================
-- This script creates/updates the keyword_search_products function in Supabase
-- 
-- INSTRUCTIONS:
-- 1. Open your Supabase project dashboard
-- 2. Go to SQL Editor
-- 3. Copy and paste this entire script
-- 4. Click "Run" to execute
-- ============================================================================

-- Drop the existing function if it exists (to ensure clean update)
DROP FUNCTION IF EXISTS keyword_search_products(TEXT, INT, TEXT, DECIMAL, DECIMAL, TEXT);

-- Create the keyword search function with correct type (DOUBLE PRECISION)
CREATE OR REPLACE FUNCTION keyword_search_products(
    search_term TEXT,
    match_count INT DEFAULT 10,
    filter_category TEXT DEFAULT NULL,
    min_price DECIMAL DEFAULT NULL,
    max_price DECIMAL DEFAULT NULL,
    filter_stock_status TEXT DEFAULT 'in_stock'
)
RETURNS TABLE (
    product_id TEXT,
    title TEXT,
    category TEXT,
    description TEXT,
    age_range TEXT,
    colors JSONB,
    specifications JSONB,
    images JSONB,
    price DECIMAL,
    discount_price DECIMAL,
    stock_status TEXT,
    warranty TEXT,
    similarity DOUBLE PRECISION,
    match_type TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.product_id,
        p.title,
        p.category,
        p.description,
        p.age_range,
        p.colors,
        p.specifications,
        p.images,
        p.price,
        p.discount_price,
        p.stock_status,
        p.warranty,
        CASE
            -- Exact product_id match (highest priority)
            WHEN LOWER(p.product_id) = LOWER(search_term) THEN 1.0::DOUBLE PRECISION
            -- Exact title match
            WHEN LOWER(p.title) = LOWER(search_term) THEN 0.95::DOUBLE PRECISION
            -- Product_id contains search term
            WHEN LOWER(p.product_id) LIKE '%' || LOWER(search_term) || '%' THEN 0.90::DOUBLE PRECISION
            -- Title starts with search term
            WHEN LOWER(p.title) LIKE LOWER(search_term) || '%' THEN 0.88::DOUBLE PRECISION
            -- Title contains search term
            WHEN LOWER(p.title) LIKE '%' || LOWER(search_term) || '%' THEN 0.85::DOUBLE PRECISION
            -- Description contains search term
            WHEN LOWER(p.description) LIKE '%' || LOWER(search_term) || '%' THEN 0.75::DOUBLE PRECISION
            ELSE 0.5::DOUBLE PRECISION
        END AS similarity,
        CASE
            WHEN LOWER(p.product_id) = LOWER(search_term) THEN 'exact_id'
            WHEN LOWER(p.title) = LOWER(search_term) THEN 'exact_title'
            WHEN LOWER(p.product_id) LIKE '%' || LOWER(search_term) || '%' THEN 'partial_id'
            WHEN LOWER(p.title) LIKE LOWER(search_term) || '%' THEN 'title_start'
            WHEN LOWER(p.title) LIKE '%' || LOWER(search_term) || '%' THEN 'title_contains'
            WHEN LOWER(p.description) LIKE '%' || LOWER(search_term) || '%' THEN 'description_contains'
            ELSE 'other'
        END AS match_type
    FROM products p
    WHERE 
        -- Main search condition
        (
            LOWER(p.product_id) LIKE '%' || LOWER(search_term) || '%'
            OR LOWER(p.title) LIKE '%' || LOWER(search_term) || '%'
            OR LOWER(p.description) LIKE '%' || LOWER(search_term) || '%'
        )
        -- Category filter
        AND (filter_category IS NULL OR p.category = filter_category)
        -- Price filters
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        -- Stock status filter
        AND (filter_stock_status IS NULL OR p.stock_status = filter_stock_status)
    ORDER BY 
        -- Order by similarity score (highest first)
        CASE
            WHEN LOWER(p.product_id) = LOWER(search_term) THEN 1.0
            WHEN LOWER(p.title) = LOWER(search_term) THEN 0.95
            WHEN LOWER(p.product_id) LIKE '%' || LOWER(search_term) || '%' THEN 0.90
            WHEN LOWER(p.title) LIKE LOWER(search_term) || '%' THEN 0.88
            WHEN LOWER(p.title) LIKE '%' || LOWER(search_term) || '%' THEN 0.85
            WHEN LOWER(p.description) LIKE '%' || LOWER(search_term) || '%' THEN 0.75
            ELSE 0.5
        END DESC
    LIMIT match_count;
END;
$$;

-- Grant execute permissions to authenticated users
GRANT EXECUTE ON FUNCTION keyword_search_products(TEXT, INT, TEXT, DECIMAL, DECIMAL, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION keyword_search_products(TEXT, INT, TEXT, DECIMAL, DECIMAL, TEXT) TO anon;

-- Test the function with a simple query
SELECT * FROM keyword_search_products('2188', 5);

-- ============================================================================
-- DEPLOYMENT COMPLETE
-- ============================================================================
-- If you see results from the test query above, the function is working!
-- ============================================================================