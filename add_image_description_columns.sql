-- Migration: Add Image Description Columns to Products Table
-- Phase 4: Image-Based Product Matching
-- This migration adds columns to store AI-generated product descriptions and embeddings from product images

-- Add new columns to products table
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS ai_image_description TEXT,
ADD COLUMN IF NOT EXISTS ai_image_metadata JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS image_embedding VECTOR(768);

-- Add indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_products_ai_image_description ON products USING gin(to_tsvector('english', ai_image_description));
CREATE INDEX IF NOT EXISTS idx_products_image_embedding ON products 
USING hnsw (image_embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- Add comments for documentation
COMMENT ON COLUMN products.ai_image_description IS 'AI-generated detailed product description from product image analysis (used for image-based search)';
COMMENT ON COLUMN products.ai_image_metadata IS 'JSON object containing AI-extracted metadata: colors, features, style_keywords, age_range, size_category, confidence';
COMMENT ON COLUMN products.image_embedding IS 'Vector embedding (768D) generated from AI image description for image-based product matching';

-- Create function to search products using image embeddings
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

COMMENT ON FUNCTION search_products_by_image IS 'Search products using image-based embeddings with optional filters (lower threshold 0.65 for image search)';

-- Create function to get products with image descriptions
CREATE OR REPLACE FUNCTION get_products_with_image_descriptions(
    p_limit INT DEFAULT 100,
    p_offset INT DEFAULT 0
)
RETURNS TABLE (
    product_id TEXT,
    title TEXT,
    ai_image_description TEXT,
    ai_image_metadata JSONB,
    has_image_embedding BOOLEAN
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.product_id,
        p.title,
        p.ai_image_description,
        p.ai_image_metadata,
        (p.image_embedding IS NOT NULL) AS has_image_embedding
    FROM products p
    ORDER BY p.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$;

COMMENT ON FUNCTION get_products_with_image_descriptions IS 'Get products with their AI-generated image descriptions and metadata';

-- Create function to update product image description and embedding
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

COMMENT ON FUNCTION update_product_image_data IS 'Update product with AI-generated image description, metadata, and embedding';

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION search_products_by_image TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION get_products_with_image_descriptions TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION update_product_image_data TO service_role;

-- Migration complete
SELECT 'Migration completed: Image description columns added to products table' AS status;