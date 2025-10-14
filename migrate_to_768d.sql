-- Migration script to update existing database from 1536 to 768 dimensions
-- Run this if you already have data in your database

-- Step 1: Drop the existing embedding index
DROP INDEX IF EXISTS idx_gurtoy_knowledge_embedding;

-- Step 2: Alter the embedding column to use 768 dimensions
ALTER TABLE gurtoy_knowledge ALTER COLUMN embedding TYPE VECTOR(768);

-- Step 3: Update the search function to use 768 dimensions
CREATE OR REPLACE FUNCTION search_knowledge(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5,
    filter_category TEXT DEFAULT NULL,
    min_priority INT DEFAULT 5
)
RETURNS TABLE (
    chunk_id TEXT,
    title TEXT,
    content TEXT,
    category TEXT,
    keywords TEXT[],
    priority INT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gk.chunk_id,
        gk.title,
        gk.content,
        gk.category,
        gk.keywords,
        gk.priority,
        (gk.embedding <=> query_embedding) * -1 + 1 AS similarity
    FROM gurtoy_knowledge gk
    WHERE 
        (gk.embedding <=> query_embedding) * -1 + 1 > match_threshold
        AND (filter_category IS NULL OR gk.category = filter_category)
        AND gk.priority <= min_priority
    ORDER BY gk.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Step 4: Clear existing embeddings (they need to be regenerated with new model)
UPDATE gurtoy_knowledge SET embedding = NULL;

-- Step 5: Recreate the embedding index for 768 dimensions
CREATE INDEX IF NOT EXISTS idx_gurtoy_knowledge_embedding ON gurtoy_knowledge USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Step 6: Update table comment
COMMENT ON TABLE gurtoy_knowledge IS 'Stores company knowledge chunks with embeddings for vector search (768-dimensional, text-embedding-004)';