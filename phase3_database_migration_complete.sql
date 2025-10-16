-- =====================================================
-- PHASE 3 DATABASE MIGRATION: COMPLETE FUNCTION UPDATES
-- =====================================================
-- This script fixes all database functions for Fashion Mart
-- Addresses: Parameter mismatches, type issues, missing functions

-- =====================================================
-- STEP 1: DROP ALL EXISTING FUNCTIONS TO AVOID CONFLICTS
-- =====================================================

-- Drop search_products function (multiple signatures possible)
DROP FUNCTION IF EXISTS search_products(VECTOR, DOUBLE PRECISION, INTEGER, TEXT, TEXT, NUMERIC, NUMERIC, TEXT);
DROP FUNCTION IF EXISTS search_products(VECTOR, FLOAT, INTEGER, TEXT, TEXT, DECIMAL, DECIMAL, TEXT);

-- Drop keyword_search_products function
DROP FUNCTION IF EXISTS keyword_search_products(TEXT, INTEGER, TEXT, NUMERIC, NUMERIC, TEXT);

-- Drop get_product_by_id function
DROP FUNCTION IF EXISTS get_product_by_id(TEXT);

-- Drop get_products_by_category function
DROP FUNCTION IF EXISTS get_products_by_category(TEXT, INTEGER);

-- Drop search_products_by_image function
DROP FUNCTION IF EXISTS search_products_by_image(VECTOR, DOUBLE PRECISION, INTEGER, TEXT, TEXT, NUMERIC, NUMERIC, TEXT);
DROP FUNCTION IF EXISTS search_products_by_image(VECTOR, FLOAT, INTEGER, TEXT, TEXT, DECIMAL, DECIMAL, TEXT);

-- Drop hybrid_search_products function (if exists)
DROP FUNCTION IF EXISTS hybrid_search_products(VECTOR, TEXT, DOUBLE PRECISION, INTEGER, TEXT, TEXT, NUMERIC, NUMERIC, TEXT);
DROP FUNCTION IF EXISTS hybrid_search_products(VECTOR, TEXT, FLOAT, INTEGER, TEXT, TEXT, DECIMAL, DECIMAL, TEXT);

-- =====================================================
-- STEP 2: RECREATE ALL FUNCTIONS WITH CORRECT SIGNATURES
-- =====================================================

-- Function 1: search_products (Semantic search with vector embeddings)
CREATE OR REPLACE FUNCTION search_products(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.6,
    match_count INT DEFAULT 5,
    filter_category TEXT DEFAULT NULL,
    filter_size_range TEXT DEFAULT NULL,
    min_price DECIMAL DEFAULT NULL,
    max_price DECIMAL DEFAULT NULL,
    filter_stock_status TEXT DEFAULT 'in_stock'
)
RETURNS TABLE (
    product_id TEXT,
    title TEXT,
    category TEXT,
    description TEXT,
    size_range TEXT,
    colors JSONB,
    specifications JSONB,
    images JSONB,
    price DECIMAL,
    discount_price DECIMAL,
    stock_status TEXT,
    warranty TEXT,
    similarity FLOAT
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
        p.size_range,
        p.colors,
        p.specifications,
        p.images,
        p.price,
        p.discount_price,
        p.stock_status,
        p.warranty,
        (p.embedding <=> query_embedding) * -1 + 1 AS similarity
    FROM products p
    WHERE 
        (p.embedding <=> query_embedding) * -1 + 1 > match_threshold
        AND (filter_category IS NULL OR p.category = filter_category)
        AND (filter_size_range IS NULL OR p.size_range = filter_size_range)
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        AND (filter_stock_status IS NULL OR p.stock_status = filter_stock_status)
    ORDER BY p.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function 2: keyword_search_products (Fixed type mismatch)
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
    size_range TEXT,
    colors JSONB,
    specifications JSONB,
    images JSONB,
    price DECIMAL,
    discount_price DECIMAL,
    stock_status TEXT,
    warranty TEXT,
    similarity FLOAT,  -- Changed from DOUBLE PRECISION to FLOAT
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
        p.size_range,
        p.colors,
        p.specifications,
        p.images,
        p.price,
        p.discount_price,
        p.stock_status,
        p.warranty,
        CASE 
            WHEN LOWER(p.product_id) = LOWER(search_term) THEN 1.0
            WHEN LOWER(p.title) = LOWER(search_term) THEN 1.0
            WHEN LOWER(p.product_id) LIKE LOWER(search_term) || '%' THEN 0.95
            WHEN LOWER(p.title) LIKE LOWER(search_term) || '%' THEN 0.95
            WHEN LOWER(p.product_id) LIKE '%' || LOWER(search_term) || '%' THEN 0.85
            WHEN LOWER(p.title) LIKE '%' || LOWER(search_term) || '%' THEN 0.85
            WHEN LOWER(p.description) LIKE '%' || LOWER(search_term) || '%' THEN 0.75
            ELSE 0.5
        END AS similarity,
        CASE 
            WHEN LOWER(p.product_id) = LOWER(search_term) THEN 'exact_id'
            WHEN LOWER(p.title) = LOWER(search_term) THEN 'exact_title'
            WHEN LOWER(p.product_id) LIKE LOWER(search_term) || '%' THEN 'starts_with_id'
            WHEN LOWER(p.title) LIKE LOWER(search_term) || '%' THEN 'starts_with_title'
            WHEN LOWER(p.product_id) LIKE '%' || LOWER(search_term) || '%' THEN 'contains_id'
            WHEN LOWER(p.title) LIKE '%' || LOWER(search_term) || '%' THEN 'contains_title'
            WHEN LOWER(p.description) LIKE '%' || LOWER(search_term) || '%' THEN 'contains_description'
            ELSE 'no_match'
        END AS match_type
    FROM products p
    WHERE 
        (
            LOWER(p.product_id) LIKE '%' || LOWER(search_term) || '%'
            OR LOWER(p.title) LIKE '%' || LOWER(search_term) || '%'
            OR LOWER(p.description) LIKE '%' || LOWER(search_term) || '%'
        )
        AND (filter_category IS NULL OR p.category = filter_category)
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        AND (filter_stock_status IS NULL OR p.stock_status = filter_stock_status)
    ORDER BY 
        CASE 
            WHEN LOWER(p.product_id) = LOWER(search_term) THEN 1
            WHEN LOWER(p.title) = LOWER(search_term) THEN 1
            WHEN LOWER(p.product_id) LIKE LOWER(search_term) || '%' THEN 2
            WHEN LOWER(p.title) LIKE LOWER(search_term) || '%' THEN 2
            WHEN LOWER(p.product_id) LIKE '%' || LOWER(search_term) || '%' THEN 3
            WHEN LOWER(p.title) LIKE '%' || LOWER(search_term) || '%' THEN 3
            WHEN LOWER(p.description) LIKE '%' || LOWER(search_term) || '%' THEN 4
            ELSE 5
        END,
        p.price ASC
    LIMIT match_count;
END;
$$;

-- Function 3: get_product_by_id
CREATE OR REPLACE FUNCTION get_product_by_id(p_product_id TEXT)
RETURNS TABLE (
    product_id TEXT,
    title TEXT,
    category TEXT,
    description TEXT,
    size_range TEXT,
    colors JSONB,
    specifications JSONB,
    images JSONB,
    price DECIMAL,
    discount_price DECIMAL,
    stock_status TEXT,
    warranty TEXT
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
        p.size_range,
        p.colors,
        p.specifications,
        p.images,
        p.price,
        p.discount_price,
        p.stock_status,
        p.warranty
    FROM products p
    WHERE p.product_id = p_product_id;
END;
$$;

-- Function 4: get_products_by_category
CREATE OR REPLACE FUNCTION get_products_by_category(p_category TEXT, p_limit INT DEFAULT 10)
RETURNS TABLE (
    product_id TEXT,
    title TEXT,
    category TEXT,
    description TEXT,
    size_range TEXT,
    price DECIMAL,
    discount_price DECIMAL,
    stock_status TEXT
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
        p.size_range,
        p.price,
        p.discount_price,
        p.stock_status
    FROM products p
    WHERE p.category = p_category
    AND p.stock_status = 'in_stock'
    ORDER BY p.created_at DESC
    LIMIT p_limit;
END;
$$;

-- Function 5: search_products_by_image
CREATE OR REPLACE FUNCTION search_products_by_image(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.65,
    match_count INT DEFAULT 10,
    filter_category TEXT DEFAULT NULL,
    filter_size_range TEXT DEFAULT NULL,
    min_price DECIMAL DEFAULT NULL,
    max_price DECIMAL DEFAULT NULL,
    filter_stock_status TEXT DEFAULT 'in_stock'
)
RETURNS TABLE (
    product_id TEXT,
    title TEXT,
    category TEXT,
    description TEXT,
    ai_image_description TEXT,
    ai_image_metadata JSONB,
    size_range TEXT,
    colors JSONB,
    specifications JSONB,
    images JSONB,
    price DECIMAL,
    discount_price DECIMAL,
    stock_status TEXT,
    warranty TEXT,
    similarity FLOAT
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
        p.ai_image_description,
        p.ai_image_metadata,
        p.size_range,
        p.colors,
        p.specifications,
        p.images,
        p.price,
        p.discount_price,
        p.stock_status,
        p.warranty,
        (p.image_embedding <=> query_embedding) * -1 + 1 AS similarity
    FROM products p
    WHERE 
        p.image_embedding IS NOT NULL
        AND (p.image_embedding <=> query_embedding) * -1 + 1 > match_threshold
        AND (filter_category IS NULL OR p.category = filter_category)
        AND (filter_size_range IS NULL OR p.size_range = filter_size_range)
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        AND (filter_stock_status IS NULL OR p.stock_status = filter_stock_status)
    ORDER BY p.image_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function 6: hybrid_search_products (NEW - Combines keyword + semantic search)
CREATE OR REPLACE FUNCTION hybrid_search_products(
    query_embedding VECTOR(768),
    search_term TEXT,
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 10,
    filter_category TEXT DEFAULT NULL,
    filter_size_range TEXT DEFAULT NULL,
    min_price DECIMAL DEFAULT NULL,
    max_price DECIMAL DEFAULT NULL,
    filter_stock_status TEXT DEFAULT 'in_stock'
)
RETURNS TABLE (
    product_id TEXT,
    title TEXT,
    category TEXT,
    description TEXT,
    size_range TEXT,
    colors JSONB,
    specifications JSONB,
    images JSONB,
    price DECIMAL,
    discount_price DECIMAL,
    stock_status TEXT,
    warranty TEXT,
    similarity FLOAT,
    search_method TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    -- First try keyword search for exact matches
    SELECT 
        p.product_id,
        p.title,
        p.category,
        p.description,
        p.size_range,
        p.colors,
        p.specifications,
        p.images,
        p.price,
        p.discount_price,
        p.stock_status,
        p.warranty,
        CASE 
            WHEN LOWER(p.product_id) = LOWER(search_term) THEN 1.0
            WHEN LOWER(p.title) = LOWER(search_term) THEN 1.0
            WHEN LOWER(p.product_id) LIKE LOWER(search_term) || '%' THEN 0.95
            WHEN LOWER(p.title) LIKE LOWER(search_term) || '%' THEN 0.95
            ELSE 0.85
        END AS similarity,
        'keyword' AS search_method
    FROM products p
    WHERE 
        (
            LOWER(p.product_id) LIKE '%' || LOWER(search_term) || '%'
            OR LOWER(p.title) LIKE '%' || LOWER(search_term) || '%'
        )
        AND (filter_category IS NULL OR p.category = filter_category)
        AND (filter_size_range IS NULL OR p.size_range = filter_size_range)
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        AND (filter_stock_status IS NULL OR p.stock_status = filter_stock_status)
    
    UNION ALL
    
    -- Then add semantic search results
    SELECT 
        p.product_id,
        p.title,
        p.category,
        p.description,
        p.size_range,
        p.colors,
        p.specifications,
        p.images,
        p.price,
        p.discount_price,
        p.stock_status,
        p.warranty,
        (p.embedding <=> query_embedding) * -1 + 1 AS similarity,
        'semantic' AS search_method
    FROM products p
    WHERE 
        (p.embedding <=> query_embedding) * -1 + 1 > match_threshold
        AND (filter_category IS NULL OR p.category = filter_category)
        AND (filter_size_range IS NULL OR p.size_range = filter_size_range)
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        AND (filter_stock_status IS NULL OR p.stock_status = filter_stock_status)
        -- Exclude products already found by keyword search
        AND p.product_id NOT IN (
            SELECT p2.product_id FROM products p2
            WHERE LOWER(p2.product_id) LIKE '%' || LOWER(search_term) || '%'
            OR LOWER(p2.title) LIKE '%' || LOWER(search_term) || '%'
        )
    
    ORDER BY similarity DESC, search_method
    LIMIT match_count;
END;
$$;

-- =====================================================
-- STEP 3: UPDATE COMMENTS AND DOCUMENTATION
-- =====================================================

-- Update column comments
COMMENT ON COLUMN products.size_range IS 'Available sizes for fashion items (S, M, L, XL, etc.)';

-- Update function comments
COMMENT ON FUNCTION search_products IS 'Semantic search for fashion products with optional filters (text-based)';
COMMENT ON FUNCTION keyword_search_products IS 'Keyword-based search for exact product names, IDs, or descriptions (fixed type mismatch)';
COMMENT ON FUNCTION search_products_by_image IS 'Search fashion products using image-based embeddings with optional filters';
COMMENT ON FUNCTION get_product_by_id IS 'Get detailed fashion product information by product ID';
COMMENT ON FUNCTION get_products_by_category IS 'Get fashion products filtered by category';
COMMENT ON FUNCTION hybrid_search_products IS 'Combines keyword and semantic search for optimal fashion product discovery';

-- =====================================================
-- STEP 4: VERIFICATION QUERIES
-- =====================================================

-- Test that all functions exist and work
-- Uncomment these to test after running the migration:

/*
-- Test search_products
SELECT * FROM search_products(
    ARRAY[0.1]::VECTOR(768), 
    0.3, 3, 'Cardigan', 'S, M, L, XL', NULL, NULL, 'in_stock'
) LIMIT 1;

-- Test keyword_search_products  
SELECT * FROM keyword_search_products('cardigan', 3, NULL, NULL, NULL, 'in_stock') LIMIT 1;

-- Test get_product_by_id
SELECT * FROM get_product_by_id('1101') LIMIT 1;

-- Test get_products_by_category
SELECT * FROM get_products_by_category('Cardigan', 3) LIMIT 1;

-- Test search_products_by_image
SELECT * FROM search_products_by_image(
    ARRAY[0.1]::VECTOR(768), 
    0.3, 3, 'Cardigan', 'S, M, L, XL', NULL, NULL, 'in_stock'
) LIMIT 1;

-- Test hybrid_search_products
SELECT * FROM hybrid_search_products(
    ARRAY[0.1]::VECTOR(768), 'cardigan', 
    0.3, 3, 'Cardigan', 'S, M, L, XL', NULL, NULL, 'in_stock'
) LIMIT 1;
*/

-- =====================================================
-- MIGRATION COMPLETE
-- =====================================================
-- All database functions have been updated for Fashion Mart
-- Functions now use size_range instead of age_range
-- Type mismatches have been fixed
-- Hybrid search function has been added
-- All functions are ready for Phase 3 implementation
