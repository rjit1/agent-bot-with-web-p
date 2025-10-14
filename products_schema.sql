-- Products Schema for Gurtoy Telegram Bot
-- Phase 2: Product System with Semantic Search
-- This schema adds product catalog with vector embeddings

-- Products Table
CREATE TABLE IF NOT EXISTS products (
    id BIGSERIAL PRIMARY KEY,
    product_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    age_range TEXT,
    colors JSONB DEFAULT '[]',
    specifications JSONB DEFAULT '{}',
    images JSONB DEFAULT '[]',
    price DECIMAL(10, 2) NOT NULL,
    discount_price DECIMAL(10, 2),
    stock_status TEXT DEFAULT 'in_stock' CHECK (stock_status IN ('in_stock', 'out_of_stock', 'pre_order')),
    warranty TEXT,
    embedding VECTOR(768), -- Using 768 dimensions for consistency (text-based search)
    ai_image_description TEXT, -- AI-generated description from product image
    ai_image_metadata JSONB DEFAULT '{}', -- AI-extracted metadata (colors, features, etc.)
    image_embedding VECTOR(768), -- Embedding from AI image description (image-based search)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_products_product_id ON products(product_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_stock_status ON products(stock_status);
CREATE INDEX IF NOT EXISTS idx_products_age_range ON products(age_range);

-- Use HNSW index for optimal vector search performance with 768 dimensions
CREATE INDEX IF NOT EXISTS idx_products_embedding ON products 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- Index for AI image description (full-text search)
CREATE INDEX IF NOT EXISTS idx_products_ai_image_description ON products 
USING gin(to_tsvector('english', ai_image_description));

-- HNSW index for image-based vector search
CREATE INDEX IF NOT EXISTS idx_products_image_embedding ON products 
USING hnsw (image_embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- Function to search products using vector similarity with filters
CREATE OR REPLACE FUNCTION search_products(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.6,
    match_count INT DEFAULT 5,
    filter_category TEXT DEFAULT NULL,
    filter_age_range TEXT DEFAULT NULL,
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
        p.age_range,
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
        AND (filter_age_range IS NULL OR p.age_range = filter_age_range)
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
    age_range TEXT,
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
        p.age_range,
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
    age_range TEXT,
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
        p.age_range,
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

-- Function to search products using keyword matching (for exact product names/IDs)
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

-- Function to search products using image embeddings (Phase 4: Image-Based Product Matching)
CREATE OR REPLACE FUNCTION search_products_by_image(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.65,
    match_count INT DEFAULT 10,
    filter_category TEXT DEFAULT NULL,
    filter_age_range TEXT DEFAULT NULL,
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
    age_range TEXT,
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
        p.age_range,
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
        AND (filter_age_range IS NULL OR p.age_range = filter_age_range)
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        AND (filter_stock_status IS NULL OR p.stock_status = filter_stock_status)
    ORDER BY p.image_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to update product image data
CREATE OR REPLACE FUNCTION update_product_image_data(
    p_product_id TEXT,
    p_ai_image_description TEXT,
    p_ai_image_metadata JSONB,
    p_image_embedding VECTOR(768)
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE products
    SET 
        ai_image_description = p_ai_image_description,
        ai_image_metadata = p_ai_image_metadata,
        image_embedding = p_image_embedding,
        updated_at = NOW()
    WHERE product_id = p_product_id;
    
    RETURN FOUND;
END;
$$;

-- Trigger to automatically update updated_at timestamp
CREATE TRIGGER update_products_updated_at 
BEFORE UPDATE ON products 
FOR EACH ROW 
EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) policies
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

-- Products are publicly readable (for bot operations)
CREATE POLICY "Products readable" ON products FOR SELECT USING (true);

-- Service role can manage products
CREATE POLICY "Service role full access products" ON products FOR ALL USING (auth.role() = 'service_role');

-- Add comments for documentation
COMMENT ON TABLE products IS 'Product catalog with embeddings for semantic search (text and image-based)';
COMMENT ON COLUMN products.embedding IS 'Vector embedding (768D) for semantic product search (text-based)';
COMMENT ON COLUMN products.ai_image_description IS 'AI-generated detailed product description from product image analysis (used for image-based search)';
COMMENT ON COLUMN products.ai_image_metadata IS 'JSON object containing AI-extracted metadata: colors, features, style_keywords, age_range, size_category, confidence';
COMMENT ON COLUMN products.image_embedding IS 'Vector embedding (768D) generated from AI image description for image-based product matching';
COMMENT ON COLUMN products.specifications IS 'JSON object containing battery, features, etc.';
COMMENT ON COLUMN products.colors IS 'JSON array of available colors';
COMMENT ON COLUMN products.images IS 'JSON array of product image URLs';
COMMENT ON FUNCTION search_products IS 'Semantic search for products with optional filters (text-based)';
COMMENT ON FUNCTION keyword_search_products IS 'Keyword-based search for exact product names, IDs, or descriptions (for product name searches like "2188", "G63")';
COMMENT ON FUNCTION search_products_by_image IS 'Search products using image-based embeddings with optional filters (lower threshold 0.65 for image search)';
COMMENT ON FUNCTION update_product_image_data IS 'Update product with AI-generated image description, metadata, and embedding';
COMMENT ON FUNCTION get_product_by_id IS 'Get detailed product information by product ID';
COMMENT ON FUNCTION get_products_by_category IS 'Get products filtered by category';