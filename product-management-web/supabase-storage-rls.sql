-- RLS Policies for product-images Storage Bucket
-- Run these SQL commands in your Supabase SQL Editor

-- Enable RLS on storage.objects table (if not already enabled)
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Policy 1: Allow authenticated users to upload images
CREATE POLICY "Allow authenticated users to upload images" ON storage.objects
FOR INSERT 
TO authenticated
WITH CHECK (bucket_id = 'product-images');

-- Policy 2: Allow public read access to images
CREATE POLICY "Allow public read access to images" ON storage.objects
FOR SELECT 
TO public
USING (bucket_id = 'product-images');

-- Policy 3: Allow authenticated users to update their own images
CREATE POLICY "Allow authenticated users to update images" ON storage.objects
FOR UPDATE 
TO authenticated
USING (bucket_id = 'product-images')
WITH CHECK (bucket_id = 'product-images');

-- Policy 4: Allow authenticated users to delete images
CREATE POLICY "Allow authenticated users to delete images" ON storage.objects
FOR DELETE 
TO authenticated
USING (bucket_id = 'product-images');

-- Policy 5: Allow service role full access (for server-side operations)
CREATE POLICY "Allow service role full access to images" ON storage.objects
FOR ALL 
TO service_role
USING (bucket_id = 'product-images')
WITH CHECK (bucket_id = 'product-images');

-- Additional policy for anonymous users (if needed for public access)
-- Uncomment the following if you want to allow anonymous uploads
-- CREATE POLICY "Allow anonymous uploads" ON storage.objects
-- FOR INSERT 
-- TO anon
-- WITH CHECK (bucket_id = 'product-images');

-- Verify the policies were created
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies 
WHERE tablename = 'objects' AND schemaname = 'storage';
