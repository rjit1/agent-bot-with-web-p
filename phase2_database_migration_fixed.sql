-- Phase 2 Database Migration: Fashion Mart Schema Updates (CORRECTED)
-- This script migrates the database from toy store to fashion store

-- Step 1: Rename age_range column to size_range
ALTER TABLE products RENAME COLUMN age_range TO size_range;

-- Step 2: Update the index name
DROP INDEX IF EXISTS idx_products_age_range;
CREATE INDEX IF NOT EXISTS idx_products_size_range ON products(size_range);

-- Step 3: Drop existing functions first (to avoid return type conflicts)
DROP FUNCTION IF EXISTS search_products(VECTOR, DOUBLE PRECISION, INTEGER, TEXT, TEXT, NUMERIC, NUMERIC, TEXT);
DROP FUNCTION IF EXISTS get_product_by_id(TEXT);
DROP FUNCTION IF EXISTS get_products_by_category(TEXT, INTEGER);
DROP FUNCTION IF EXISTS keyword_search_products(TEXT, INTEGER, TEXT, NUMERIC, NUMERIC, TEXT);
DROP FUNCTION IF EXISTS search_products_by_image(VECTOR, DOUBLE PRECISION, INTEGER, TEXT, TEXT, NUMERIC, NUMERIC, TEXT);

-- Step 4: Recreate all functions with size_range instead of age_range
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

-- Function to get product by ID
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

-- Function to get products by category
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

-- Function to search products using keyword matching
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

-- Function to search products using image embeddings
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

-- Update comments
COMMENT ON COLUMN products.size_range IS 'Available sizes for fashion items (S, M, L, XL, etc.)';
COMMENT ON FUNCTION search_products IS 'Semantic search for fashion products with optional filters (text-based)';
COMMENT ON FUNCTION keyword_search_products IS 'Keyword-based search for exact product names, IDs, or descriptions';
COMMENT ON FUNCTION search_products_by_image IS 'Search fashion products using image-based embeddings with optional filters';
COMMENT ON FUNCTION get_product_by_id IS 'Get detailed fashion product information by product ID';
COMMENT ON FUNCTION get_products_by_category IS 'Get fashion products filtered by category';
