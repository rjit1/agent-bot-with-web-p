-- ALTERNATIVE: Simple RLS Policies for product-images Storage Bucket
-- This is a simpler approach that should work without ownership issues

-- Step 1: Make sure your bucket is set to PUBLIC in Supabase Dashboard
-- Go to Storage > product-images bucket > Settings > Make it PUBLIC

-- Step 2: Run these policies (use SERVICE ROLE key in SQL Editor)

-- Drop existing policies
DROP POLICY IF EXISTS "Public Access" ON storage.objects;
DROP POLICY IF EXISTS "Allow uploads" ON storage.objects;

-- Simple policy for public access (read)
CREATE POLICY "Public Access"
ON storage.objects
FOR SELECT
TO public
USING (bucket_id = 'product-images');

-- Simple policy for uploads (insert)
CREATE POLICY "Allow uploads"
ON storage.objects
FOR INSERT
TO public
WITH CHECK (bucket_id = 'product-images');

-- Verify policies
SELECT policyname, cmd, roles 
FROM pg_policies 
WHERE tablename = 'objects' 
    AND schemaname = 'storage';
