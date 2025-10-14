-- CORRECTED RLS Policies for product-images Storage Bucket
-- IMPORTANT: Run this SQL using the SERVICE ROLE key, not the anon key
-- You can run this in Supabase SQL Editor with service role permissions

-- First, check if RLS is enabled (this should already be enabled)
-- ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Drop any existing policies to avoid conflicts
DROP POLICY IF EXISTS "Allow anonymous uploads" ON storage.objects;
DROP POLICY IF EXISTS "Allow public read access to images" ON storage.objects;
DROP POLICY IF EXISTS "Allow authenticated users to upload images" ON storage.objects;
DROP POLICY IF EXISTS "Allow authenticated users to update images" ON storage.objects;
DROP POLICY IF EXISTS "Allow authenticated users to delete images" ON storage.objects;
DROP POLICY IF EXISTS "Allow service role full access to images" ON storage.objects;

-- Policy 1: Allow anonymous users to upload images (for web app)
CREATE POLICY "Allow anonymous uploads to product-images"
ON storage.objects
FOR INSERT
TO public
WITH CHECK (bucket_id = 'product-images');

-- Policy 2: Allow public read access to images
CREATE POLICY "Allow public read access to product-images"
ON storage.objects
FOR SELECT
TO public
USING (bucket_id = 'product-images');

-- Policy 3: Allow authenticated users to upload images
CREATE POLICY "Allow authenticated users to upload to product-images"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'product-images');

-- Policy 4: Allow authenticated users to update images
CREATE POLICY "Allow authenticated users to update product-images"
ON storage.objects
FOR UPDATE
TO authenticated
USING (bucket_id = 'product-images')
WITH CHECK (bucket_id = 'product-images');

-- Policy 5: Allow authenticated users to delete images
CREATE POLICY "Allow authenticated users to delete product-images"
ON storage.objects
FOR DELETE
TO authenticated
USING (bucket_id = 'product-images');

-- Policy 6: Allow service role full access (for server-side operations)
CREATE POLICY "Allow service role full access to product-images"
ON storage.objects
FOR ALL
TO service_role
USING (bucket_id = 'product-images')
WITH CHECK (bucket_id = 'product-images');

-- Verify the policies were created successfully
SELECT 
    schemaname, 
    tablename, 
    policyname, 
    permissive, 
    roles, 
    cmd, 
    qual, 
    with_check
FROM pg_policies 
WHERE tablename = 'objects' 
    AND schemaname = 'storage'
    AND policyname LIKE '%product-images%'
ORDER BY policyname;
