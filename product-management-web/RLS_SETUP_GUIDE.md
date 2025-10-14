# 🔧 **Fixed: Supabase Storage RLS Policy Setup**

## ❌ **The Problem**
You're getting `ERROR: 42501: must be owner of table objects` because:
1. You're using the **anon key** instead of **service role key**
2. The storage.objects table requires **service role permissions** to create policies

## ✅ **The Solution**

### **Method 1: Use Service Role Key (Recommended)**

#### **Step 1: Get Your Service Role Key**
1. Go to your Supabase Dashboard
2. Navigate to **Settings** → **API**
3. Copy the **service_role** key (not the anon key)

#### **Step 2: Run SQL with Service Role**
1. Go to **SQL Editor** in Supabase Dashboard
2. **IMPORTANT**: Make sure you're using the **service_role** key
3. Copy and paste this SQL:

```sql
-- CORRECTED RLS Policies for product-images Storage Bucket
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
```

#### **Step 3: Verify Policies Created**
Run this to check if policies were created:
```sql
SELECT policyname, cmd, roles 
FROM pg_policies 
WHERE tablename = 'objects' 
    AND schemaname = 'storage'
    AND policyname LIKE '%product-images%';
```

---

### **Method 2: Simple Approach (Alternative)**

If Method 1 doesn't work, try this simpler approach:

#### **Step 1: Make Bucket Public**
1. Go to **Storage** in Supabase Dashboard
2. Click on your **product-images** bucket
3. Go to **Settings**
4. Set **Access Level** to **Public**

#### **Step 2: Run Simple Policies**
```sql
-- Simple RLS Policies
DROP POLICY IF EXISTS "Public Access" ON storage.objects;
DROP POLICY IF EXISTS "Allow uploads" ON storage.objects;

-- Public read access
CREATE POLICY "Public Access"
ON storage.objects
FOR SELECT
TO public
USING (bucket_id = 'product-images');

-- Allow uploads
CREATE POLICY "Allow uploads"
ON storage.objects
FOR INSERT
TO public
WITH CHECK (bucket_id = 'product-images');
```

---

### **Method 3: Dashboard Method (Easiest)**

#### **Step 1: Use Supabase Dashboard**
1. Go to **Authentication** → **Policies**
2. Find **storage.objects** table
3. Click **New Policy**
4. Create these policies manually:

**Policy 1: Public Upload**
- **Policy Name**: `Allow public uploads`
- **Operation**: `INSERT`
- **Target Roles**: `public`
- **Check Expression**: `bucket_id = 'product-images'`

**Policy 2: Public Read**
- **Policy Name**: `Allow public read`
- **Operation**: `SELECT`
- **Target Roles**: `public`
- **Check Expression**: `bucket_id = 'product-images'`

---

## 🧪 **Testing Your Setup**

### **Test 1: Check Policies**
```sql
SELECT policyname, cmd, roles 
FROM pg_policies 
WHERE tablename = 'objects' 
    AND schemaname = 'storage';
```

### **Test 2: Test Upload**
1. Start your web app: `npm run dev`
2. Go to http://localhost:3000
3. Login with password: `121233`
4. Try to add a product and upload an image
5. Should work without RLS errors!

---

## 🔍 **Troubleshooting**

### **Still Getting "must be owner" Error?**
1. **Check your key**: Make sure you're using **service_role** key, not **anon** key
2. **Check permissions**: Your Supabase account needs admin permissions
3. **Try dashboard method**: Use Method 3 above instead of SQL

### **Upload Still Failing?**
1. **Check bucket name**: Make sure it's exactly `product-images`
2. **Check bucket exists**: Verify the bucket exists in Storage
3. **Check file size**: Make sure images are under 20MB
4. **Check file type**: Only JPG, PNG, GIF, WebP allowed

### **Images Not Showing?**
1. **Make bucket public**: Set access level to Public
2. **Check URLs**: Verify image URLs are accessible
3. **Check CORS**: Make sure CORS is configured properly

---

## ✅ **Success Indicators**

You'll know it's working when:
- ✅ No "must be owner" errors
- ✅ Image uploads work in the web app
- ✅ Images display properly
- ✅ No RLS policy violations in logs

---

**🎉 Once you run the corrected SQL with the service role key, your image uploads should work perfectly!**
