-- ============================================================================
-- COMPREHENSIVE SEARCH FUNCTIONALITY FIX
-- ============================================================================
-- 
-- PROBLEMS FIXED:
-- 1. Age filtering uses exact string matching (fails for ranges like "3-8 years")
-- 2. Product name searches ("2188", "g63") return 0 results
-- 3. Intelligent search applies age filtering incorrectly
--
-- SOLUTIONS:
-- 1. Intelligent age range matching in database function
-- 2. Hybrid search strategy (keyword + semantic)
-- 3. Smart age filtering with fallback logic
-- ============================================================================

-- 1. UPDATE search_products function with intelligent age range matching
CREATE OR REPLACE FUNCTION search_products(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.5,
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
DECLARE
    requested_age INTEGER;
BEGIN
    -- Extract single age from filter_age_range if provided
    -- Handles formats: '8', '8 years', '8years'
    IF filter_age_range IS NOT NULL THEN
        requested_age := (regexp_match(filter_age_range, '(\d+)'))[1]::INTEGER;
    END IF;

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
        -- Similarity threshold
        (p.embedding <=> query_embedding) * -1 + 1 > match_threshold
        
        -- Category filter
        AND (filter_category IS NULL OR p.category = filter_category)
        
        -- Stock status filter
        AND (filter_stock_status IS NULL OR p.stock_status = filter_stock_status)
        
        -- Price filters
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        
        -- INTELLIGENT AGE RANGE FILTERING
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
                            requested_age >= (regexp_match(p.age_range, '^(\d+)-'))[1]::INTEGER
                            AND requested_age <= (regexp_match(p.age_range, '-(\d+)'))[1]::INTEGER
                        -- Handle single age format: '3+ years', '5 years', etc.
                        WHEN p.age_range ~ '^\d+\+' THEN
                            requested_age >= (regexp_match(p.age_range, '^(\d+)\+'))[1]::INTEGER
                        -- Handle exact age: '5 years'
                        WHEN p.age_range ~ '^\d+\s*(years?|saal)?' THEN
                            requested_age = (regexp_match(p.age_range, '^(\d+)'))[1]::INTEGER
                        ELSE
                            true  -- If format doesn't match, include it
                    END
                )
            )
            OR
            -- Fallback: exact string match for backward compatibility
            p.age_range = filter_age_range
        )
    ORDER BY (p.embedding <=> query_embedding) * -1 + 1 DESC
    LIMIT match_count;
END;
$$;

-- 2. ENHANCE keyword_search_products function for better exact matching
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
            -- Exact matches (highest priority)
            WHEN LOWER(p.product_id) = LOWER(search_term) THEN 1.0
            WHEN LOWER(p.title) = LOWER(search_term) THEN 1.0
            
            -- Starts with search term (high priority)
            WHEN LOWER(p.product_id) LIKE LOWER(search_term) || '%' THEN 0.95
            WHEN LOWER(p.title) LIKE LOWER(search_term) || '%' THEN 0.95
            
            -- Contains search term (medium priority)
            WHEN LOWER(p.product_id) LIKE '%' || LOWER(search_term) || '%' THEN 0.85
            WHEN LOWER(p.title) LIKE '%' || LOWER(search_term) || '%' THEN 0.85
            
            -- Description contains (lower priority)
            WHEN LOWER(p.description) LIKE '%' || LOWER(search_term) || '%' THEN 0.7
            
            -- Category contains (lowest priority)
            WHEN LOWER(p.category) LIKE '%' || LOWER(search_term) || '%' THEN 0.6
            
            ELSE 0.0
        END AS similarity,
        CASE 
            WHEN LOWER(p.product_id) = LOWER(search_term) THEN 'exact_product_id'
            WHEN LOWER(p.title) = LOWER(search_term) THEN 'exact_title'
            WHEN LOWER(p.product_id) LIKE LOWER(search_term) || '%' THEN 'product_id_prefix'
            WHEN LOWER(p.title) LIKE LOWER(search_term) || '%' THEN 'title_prefix'
            WHEN LOWER(p.product_id) LIKE '%' || LOWER(search_term) || '%' THEN 'product_id_contains'
            WHEN LOWER(p.title) LIKE '%' || LOWER(search_term) || '%' THEN 'title_contains'
            WHEN LOWER(p.description) LIKE '%' || LOWER(search_term) || '%' THEN 'description_contains'
            WHEN LOWER(p.category) LIKE '%' || LOWER(search_term) || '%' THEN 'category_contains'
            ELSE 'no_match'
        END AS match_type
    FROM products p
    WHERE 
        -- Only return products that have some similarity
        (
            LOWER(p.product_id) LIKE '%' || LOWER(search_term) || '%'
            OR LOWER(p.title) LIKE '%' || LOWER(search_term) || '%'
            OR LOWER(p.description) LIKE '%' || LOWER(search_term) || '%'
            OR LOWER(p.category) LIKE '%' || LOWER(search_term) || '%'
        )
        
        -- Apply filters
        AND (filter_category IS NULL OR p.category = filter_category)
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        AND (filter_stock_status IS NULL OR p.stock_status = filter_stock_status)
    ORDER BY similarity DESC, p.title ASC
    LIMIT match_count;
END;
$$;

-- 3. CREATE hybrid search function that combines keyword + semantic search
CREATE OR REPLACE FUNCTION hybrid_search_products(
    query_embedding VECTOR(768),
    search_term TEXT,
    match_threshold FLOAT DEFAULT 0.5,
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
    age_range TEXT,
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
DECLARE
    requested_age INTEGER;
    keyword_results RECORD;
    semantic_results RECORD;
    combined_results RECORD;
BEGIN
    -- Extract age from filter if provided
    IF filter_age_range IS NOT NULL THEN
        requested_age := (regexp_match(filter_age_range, '(\d+)'))[1]::INTEGER;
    END IF;

    -- Create temporary table to store combined results
    CREATE TEMP TABLE temp_search_results (
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
        similarity FLOAT,
        search_method TEXT
    );

    -- STEP 1: Try keyword search first (for exact product names/IDs)
    INSERT INTO temp_search_results
    SELECT 
        k.product_id,
        k.title,
        k.category,
        k.description,
        k.age_range,
        k.colors,
        k.specifications,
        k.images,
        k.price,
        k.discount_price,
        k.stock_status,
        k.warranty,
        k.similarity::FLOAT,
        'keyword'::TEXT
    FROM keyword_search_products(
        search_term,
        match_count,
        filter_category,
        min_price,
        max_price,
        filter_stock_status
    ) k
    WHERE k.similarity >= 0.85;  -- Only high-confidence keyword matches

    -- STEP 2: If no good keyword matches, try semantic search
    IF NOT EXISTS (SELECT 1 FROM temp_search_results WHERE search_method = 'keyword') THEN
        INSERT INTO temp_search_results
        SELECT 
            s.product_id,
            s.title,
            s.category,
            s.description,
            s.age_range,
            s.colors,
            s.specifications,
            s.images,
            s.price,
            s.discount_price,
            s.stock_status,
            s.warranty,
            s.similarity,
            'semantic'::TEXT
        FROM search_products(
            query_embedding,
            match_threshold,
            match_count,
            filter_category,
            filter_age_range,
            min_price,
            max_price,
            filter_stock_status
        ) s;
    END IF;

    -- STEP 3: If still no results, try semantic search without age filtering
    IF NOT EXISTS (SELECT 1 FROM temp_search_results) THEN
        INSERT INTO temp_search_results
        SELECT 
            s.product_id,
            s.title,
            s.category,
            s.description,
            s.age_range,
            s.colors,
            s.specifications,
            s.images,
            s.price,
            s.discount_price,
            s.stock_status,
            s.warranty,
            s.similarity,
            'semantic_no_age_filter'::TEXT
        FROM search_products(
            query_embedding,
            match_threshold,
            match_count,
            filter_category,
            NULL,  -- No age filter
            min_price,
            max_price,
            filter_stock_status
        ) s;
    END IF;

    -- Return combined results
    RETURN QUERY
    SELECT * FROM temp_search_results
    ORDER BY similarity DESC, search_method ASC
    LIMIT match_count;

    -- Clean up
    DROP TABLE temp_search_results;
END;
$$;

-- Add comments for documentation
COMMENT ON FUNCTION search_products IS 'Enhanced semantic search with intelligent age range matching (handles ranges like "3-8 years" for specific ages)';
COMMENT ON FUNCTION keyword_search_products IS 'Keyword-based search for exact product names, IDs, or descriptions (for product name searches like "2188", "G63")';
COMMENT ON FUNCTION hybrid_search_products IS 'Hybrid search combining keyword and semantic search with intelligent fallback logic';

-- ============================================================================
-- USAGE EXAMPLES:
-- ============================================================================
--
-- 1. Age Range Matching:
--    - User asks for "8 year old" → finds products with age_range "3-8 years", "5-10 years", etc.
--    - User asks for "5 year old" → finds products with age_range "3-8 years", "5+ years", etc.
--
-- 2. Product Name Search:
--    - "2188" → finds product with product_id "2188" (exact match)
--    - "g63" → finds products with "G63" in title (case-insensitive)
--    - "red jeep" → finds products with "red" and "jeep" in title/description
--
-- 3. Hybrid Search Strategy:
--    - First tries keyword search for exact matches
--    - Falls back to semantic search if no keyword matches
--    - Removes age filtering if no results found
--    - Ensures user always gets some results
-- ============================================================================
