-- =====================================================
-- PHASE 8 DATABASE MIGRATION: FASHION MART SCHEMA UPDATES
-- =====================================================
-- This script adds new fashion-specific fields and updates search functions
-- for Fashion Mart women's fashion store

-- =====================================================
-- STEP 1: ADD NEW FASHION-SPECIFIC FIELDS
-- =====================================================

-- Add style_keywords field for fashion style classification
ALTER TABLE products ADD COLUMN IF NOT EXISTS style_keywords TEXT[] DEFAULT '{}';

-- Add occasion field for event-based filtering
ALTER TABLE products ADD COLUMN IF NOT EXISTS occasion TEXT[] DEFAULT '{}';

-- Ensure size_range field exists (should already be there from Phase 2)
ALTER TABLE products ADD COLUMN IF NOT EXISTS size_range TEXT;

-- =====================================================
-- STEP 2: CREATE NEW INDEXES FOR FASHION FIELDS
-- =====================================================

-- Index for style_keywords array
CREATE INDEX IF NOT EXISTS idx_products_style_keywords ON products 
USING gin(style_keywords);

-- Index for occasion array
CREATE INDEX IF NOT EXISTS idx_products_occasion ON products 
USING gin(occasion);

-- Index for size_range (if not already exists)
CREATE INDEX IF NOT EXISTS idx_products_size_range ON products(size_range);

-- =====================================================
-- STEP 3: DROP EXISTING FUNCTIONS TO AVOID CONFLICTS
-- =====================================================

-- Drop all existing search functions
DROP FUNCTION IF EXISTS search_products(VECTOR, FLOAT, INTEGER, TEXT, TEXT, DECIMAL, DECIMAL, TEXT);
DROP FUNCTION IF EXISTS keyword_search_products(TEXT, INTEGER, TEXT, DECIMAL, DECIMAL, TEXT);
DROP FUNCTION IF EXISTS get_product_by_id(TEXT);
DROP FUNCTION IF EXISTS get_products_by_category(TEXT, INTEGER);
DROP FUNCTION IF EXISTS search_products_by_image(VECTOR, FLOAT, INTEGER, TEXT, TEXT, DECIMAL, DECIMAL, TEXT);
DROP FUNCTION IF EXISTS hybrid_search_products(VECTOR, TEXT, FLOAT, INTEGER, TEXT, TEXT, DECIMAL, DECIMAL, TEXT);

-- =====================================================
-- STEP 4: CREATE ENHANCED SEARCH FUNCTIONS WITH FASHION FIELDS
-- =====================================================

-- Function 1: Enhanced search_products with fashion fields
CREATE OR REPLACE FUNCTION search_products(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.6,
    match_count INT DEFAULT 5,
    filter_category TEXT DEFAULT NULL,
    filter_size_range TEXT DEFAULT NULL,
    filter_style_keywords TEXT[] DEFAULT NULL,
    filter_occasion TEXT[] DEFAULT NULL,
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
    style_keywords TEXT[],
    occasion TEXT[],
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
        p.style_keywords,
        p.occasion,
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
        AND (filter_style_keywords IS NULL OR p.style_keywords && filter_style_keywords)
        AND (filter_occasion IS NULL OR p.occasion && filter_occasion)
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        AND (filter_stock_status IS NULL OR p.stock_status = filter_stock_status)
    ORDER BY p.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function 2: Enhanced keyword_search_products with fashion fields
CREATE OR REPLACE FUNCTION keyword_search_products(
    search_term TEXT,
    match_count INT DEFAULT 10,
    filter_category TEXT DEFAULT NULL,
    filter_size_range TEXT DEFAULT NULL,
    filter_style_keywords TEXT[] DEFAULT NULL,
    filter_occasion TEXT[] DEFAULT NULL,
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
    style_keywords TEXT[],
    occasion TEXT[],
    colors JSONB,
    specifications JSONB,
    images JSONB,
    price DECIMAL,
    discount_price DECIMAL,
    stock_status TEXT,
    warranty TEXT,
    similarity FLOAT,
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
        p.style_keywords,
        p.occasion,
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
        AND (filter_size_range IS NULL OR p.size_range = filter_size_range)
        AND (filter_style_keywords IS NULL OR p.style_keywords && filter_style_keywords)
        AND (filter_occasion IS NULL OR p.occasion && filter_occasion)
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

-- Function 3: Enhanced get_product_by_id with fashion fields
CREATE OR REPLACE FUNCTION get_product_by_id(p_product_id TEXT)
RETURNS TABLE (
    product_id TEXT,
    title TEXT,
    category TEXT,
    description TEXT,
    size_range TEXT,
    style_keywords TEXT[],
    occasion TEXT[],
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
        p.style_keywords,
        p.occasion,
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

-- Function 4: Enhanced get_products_by_category with fashion fields
CREATE OR REPLACE FUNCTION get_products_by_category(p_category TEXT, p_limit INT DEFAULT 10)
RETURNS TABLE (
    product_id TEXT,
    title TEXT,
    category TEXT,
    description TEXT,
    size_range TEXT,
    style_keywords TEXT[],
    occasion TEXT[],
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
        p.style_keywords,
        p.occasion,
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

-- Function 5: Enhanced search_products_by_image with fashion fields
CREATE OR REPLACE FUNCTION search_products_by_image(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.65,
    match_count INT DEFAULT 10,
    filter_category TEXT DEFAULT NULL,
    filter_size_range TEXT DEFAULT NULL,
    filter_style_keywords TEXT[] DEFAULT NULL,
    filter_occasion TEXT[] DEFAULT NULL,
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
    style_keywords TEXT[],
    occasion TEXT[],
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
        p.style_keywords,
        p.occasion,
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
        AND (filter_style_keywords IS NULL OR p.style_keywords && filter_style_keywords)
        AND (filter_occasion IS NULL OR p.occasion && filter_occasion)
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        AND (filter_stock_status IS NULL OR p.stock_status = filter_stock_status)
    ORDER BY p.image_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function 6: Enhanced hybrid_search_products with fashion fields
CREATE OR REPLACE FUNCTION hybrid_search_products(
    query_embedding VECTOR(768),
    search_term TEXT,
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 10,
    filter_category TEXT DEFAULT NULL,
    filter_size_range TEXT DEFAULT NULL,
    filter_style_keywords TEXT[] DEFAULT NULL,
    filter_occasion TEXT[] DEFAULT NULL,
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
    style_keywords TEXT[],
    occasion TEXT[],
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
        p.style_keywords,
        p.occasion,
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
        AND (filter_style_keywords IS NULL OR p.style_keywords && filter_style_keywords)
        AND (filter_occasion IS NULL OR p.occasion && filter_occasion)
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
        p.style_keywords,
        p.occasion,
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
        AND (filter_style_keywords IS NULL OR p.style_keywords && filter_style_keywords)
        AND (filter_occasion IS NULL OR p.occasion && filter_occasion)
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
-- STEP 5: CREATE NEW FASHION-SPECIFIC SEARCH FUNCTIONS
-- =====================================================

-- Function 7: Search products by size range
CREATE OR REPLACE FUNCTION search_products_by_size(
    p_size_range TEXT,
    p_limit INT DEFAULT 20,
    filter_category TEXT DEFAULT NULL,
    filter_style_keywords TEXT[] DEFAULT NULL,
    filter_occasion TEXT[] DEFAULT NULL,
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
    style_keywords TEXT[],
    occasion TEXT[],
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
        p.style_keywords,
        p.occasion,
        p.colors,
        p.specifications,
        p.images,
        p.price,
        p.discount_price,
        p.stock_status,
        p.warranty
    FROM products p
    WHERE 
        p.size_range = p_size_range
        AND (filter_category IS NULL OR p.category = filter_category)
        AND (filter_style_keywords IS NULL OR p.style_keywords && filter_style_keywords)
        AND (filter_occasion IS NULL OR p.occasion && filter_occasion)
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        AND (filter_stock_status IS NULL OR p.stock_status = filter_stock_status)
    ORDER BY p.price ASC, p.created_at DESC
    LIMIT p_limit;
END;
$$;

-- Function 8: Search products by style keywords
CREATE OR REPLACE FUNCTION search_products_by_style(
    p_style_keywords TEXT[],
    p_limit INT DEFAULT 20,
    filter_category TEXT DEFAULT NULL,
    filter_size_range TEXT DEFAULT NULL,
    filter_occasion TEXT[] DEFAULT NULL,
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
    style_keywords TEXT[],
    occasion TEXT[],
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
        p.style_keywords,
        p.occasion,
        p.colors,
        p.specifications,
        p.images,
        p.price,
        p.discount_price,
        p.stock_status,
        p.warranty
    FROM products p
    WHERE 
        p.style_keywords && p_style_keywords
        AND (filter_category IS NULL OR p.category = filter_category)
        AND (filter_size_range IS NULL OR p.size_range = filter_size_range)
        AND (filter_occasion IS NULL OR p.occasion && filter_occasion)
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        AND (filter_stock_status IS NULL OR p.stock_status = filter_stock_status)
    ORDER BY p.price ASC, p.created_at DESC
    LIMIT p_limit;
END;
$$;

-- Function 9: Search products by occasion
CREATE OR REPLACE FUNCTION search_products_by_occasion(
    p_occasion TEXT[],
    p_limit INT DEFAULT 20,
    filter_category TEXT DEFAULT NULL,
    filter_size_range TEXT DEFAULT NULL,
    filter_style_keywords TEXT[] DEFAULT NULL,
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
    style_keywords TEXT[],
    occasion TEXT[],
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
        p.style_keywords,
        p.occasion,
        p.colors,
        p.specifications,
        p.images,
        p.price,
        p.discount_price,
        p.stock_status,
        p.warranty
    FROM products p
    WHERE 
        p.occasion && p_occasion
        AND (filter_category IS NULL OR p.category = filter_category)
        AND (filter_size_range IS NULL OR p.size_range = filter_size_range)
        AND (filter_style_keywords IS NULL OR p.style_keywords && filter_style_keywords)
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        AND (filter_stock_status IS NULL OR p.stock_status = filter_stock_status)
    ORDER BY p.price ASC, p.created_at DESC
    LIMIT p_limit;
END;
$$;

-- =====================================================
-- STEP 6: VERIFICATION QUERIES
-- =====================================================

-- Verify new columns exist
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'products' 
AND column_name IN ('size_range', 'style_keywords', 'occasion')
ORDER BY column_name;

-- Verify new indexes exist
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'products' 
AND indexname LIKE '%style_keywords%' OR indexname LIKE '%occasion%' OR indexname LIKE '%size_range%'
ORDER BY indexname;

-- Verify functions exist
SELECT routine_name, routine_type 
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_name LIKE '%search_products%' OR routine_name LIKE '%get_product%'
ORDER BY routine_name;

-- =====================================================
-- PHASE 8 MIGRATION COMPLETE
-- =====================================================
