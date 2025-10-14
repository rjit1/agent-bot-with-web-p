-- ============================================================================
-- FIX: Update search_products function to handle age range matching properly
-- ============================================================================
-- 
-- PROBLEM: Current function does exact string matching on age_range
--          e.g., WHERE age_range = '5 years' (fails for '3-8 years')
--
-- SOLUTION: Parse age ranges and check if requested age falls within range
--           e.g., Check if 5 is between 3 and 8
-- ============================================================================

CREATE OR REPLACE FUNCTION search_products(
    query_embedding vector(768),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5,
    filter_category text DEFAULT NULL,
    filter_age_range text DEFAULT NULL,
    min_price numeric DEFAULT NULL,
    max_price numeric DEFAULT NULL,
    filter_stock_status text DEFAULT 'in_stock'
)
RETURNS TABLE (
    product_id bigint,
    title text,
    category text,
    description text,
    age_range text,
    price numeric,
    discount_price numeric,
    colors jsonb,
    specifications jsonb,
    images jsonb,
    stock_status text,
    warranty text,
    similarity float
)
LANGUAGE plpgsql
AS $$
DECLARE
    requested_age int;
    age_min int;
    age_max int;
BEGIN
    -- Extract single age from filter_age_range if provided
    -- Handles formats: '5', '5 years', '5years'
    IF filter_age_range IS NOT NULL THEN
        requested_age := (regexp_match(filter_age_range, '(\d+)'))[1]::int;
    END IF;

    RETURN QUERY
    SELECT
        p.product_id,
        p.title,
        p.category,
        p.description,
        p.age_range,
        p.price,
        p.discount_price,
        p.colors,
        p.specifications,
        p.images,
        p.stock_status,
        p.warranty,
        1 - (p.embedding <=> query_embedding) AS similarity
    FROM products p
    WHERE 
        -- Similarity threshold
        1 - (p.embedding <=> query_embedding) > match_threshold
        
        -- Category filter
        AND (filter_category IS NULL OR p.category = filter_category)
        
        -- Stock status filter
        AND (filter_stock_status IS NULL OR p.stock_status = filter_stock_status)
        
        -- Price filters
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        
        -- Age range filter with intelligent matching
        AND (
            filter_age_range IS NULL 
            OR 
            -- If requested_age is extracted, check if it falls within product's age range
            (
                requested_age IS NOT NULL
                AND
                -- Extract min and max from product age_range (e.g., '3-8 years' → 3 and 8)
                (
                    -- Handle range format: '3-8 years', '1-4 years', etc.
                    CASE 
                        WHEN p.age_range ~ '^\d+-\d+' THEN
                            requested_age >= (regexp_match(p.age_range, '^(\d+)-'))[1]::int
                            AND requested_age <= (regexp_match(p.age_range, '-(\d+)'))[1]::int
                        -- Handle single age format: '3+ years', '5 years', etc.
                        WHEN p.age_range ~ '^\d+\+' THEN
                            requested_age >= (regexp_match(p.age_range, '^(\d+)\+'))[1]::int
                        -- Handle exact age: '5 years'
                        WHEN p.age_range ~ '^\d+\s*(years?|saal)?' THEN
                            requested_age = (regexp_match(p.age_range, '^(\d+)'))[1]::int
                        ELSE
                            true  -- If format doesn't match, include it
                    END
                )
            )
            OR
            -- Fallback: exact string match for backward compatibility
            p.age_range = filter_age_range
        )
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

-- ============================================================================
-- EXPLANATION:
-- ============================================================================
-- 
-- Age Range Matching Logic:
-- 
-- 1. Extract requested age from filter (e.g., '5 years' → 5)
-- 
-- 2. For each product, check if requested age falls within product's range:
--    - '3-8 years': Check if 5 >= 3 AND 5 <= 8 ✅
--    - '3+ years': Check if 5 >= 3 ✅
--    - '5 years': Check if 5 = 5 ✅
-- 
-- 3. Examples:
--    User asks for '5 year old':
--      ✅ Matches '1-8 years' (5 is between 1 and 8)
--      ✅ Matches '3-7 years' (5 is between 3 and 7)
--      ✅ Matches '3+ years' (5 is >= 3)
--      ❌ Doesn't match '1-4 years' (5 is > 4)
--      ❌ Doesn't match '6-10 years' (5 is < 6)
-- 
-- ============================================================================

-- Test the function
SELECT 
    title,
    age_range,
    '5 years' as search_for,
    CASE 
        WHEN age_range ~ '^\d+-\d+' THEN
            5 >= (regexp_match(age_range, '^(\d+)-'))[1]::int
            AND 5 <= (regexp_match(age_range, '-(\d+)'))[1]::int
        WHEN age_range ~ '^\d+\+' THEN
            5 >= (regexp_match(age_range, '^(\d+)\+'))[1]::int
        WHEN age_range ~ '^\d+\s*(years?|saal)?' THEN
            5 = (regexp_match(age_range, '^(\d+)'))[1]::int
        ELSE
            false
    END as matches
FROM products
WHERE category LIKE '%Jeep%'
ORDER BY matches DESC, title;