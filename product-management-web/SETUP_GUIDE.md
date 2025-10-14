# 🚀 **Complete Setup Guide - Product Management Web App**

## ✅ **Step 1: Run RLS Policies**

Copy and paste this SQL into your **Supabase SQL Editor**:

```sql
-- RLS Policies for product-images Storage Bucket
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
```

## ✅ **Step 2: Update Environment Variables**

Your `.env.local` file should look exactly like this:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://uejyfpzabmlrgkdayfrn.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVlanlmcHphYm1scmdrZGF5ZnJuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAyOTE2NTgsImV4cCI6MjA3NTg2NzY1OH0.9sTzwDUdxVVF_KJUjN7RxTnukSr-NdLpfuRThGn_O6Q
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVlanlmcHphYm1scmdrZGF5ZnJuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MDI5MTY1OCwiZXhwIjoyMDc1ODY3NjU4fQ.0tRcC0yYKRY2kRO9BjJglWfL7MnyplrLuhUo7jmeQzw

# Authentication
ADMIN_PASSWORD=121233
JWT_SECRET=your_jwt_secret_here

# App Configuration
NEXT_PUBLIC_APP_NAME=Gurtoy Product Management
NEXT_PUBLIC_CONTACT_TELEGRAM=@Sarvesh_101
```

**⚠️ IMPORTANT**: Replace `your_jwt_secret_here` with a strong secret key (e.g., `my-super-secret-jwt-key-2024`)

## ✅ **Step 3: Install Dependencies**

```bash
cd product-management-web
npm install
```

## ✅ **Step 4: Start Development Server**

```bash
npm run dev
```

## ✅ **Step 5: Test the Application**

1. **Open**: http://localhost:3000
2. **Login**: Use password `121233`
3. **Test Features**:
   - Add a new product
   - Upload images
   - Search products
   - Edit/Delete products

## 🔧 **Troubleshooting**

### **Issue 1: "supabaseKey is required" Error**
**Solution**: The environment variables are not being loaded properly. Make sure:
- `.env.local` file exists in the root directory
- File is named exactly `.env.local` (not `.env`)
- Restart the development server after changes

### **Issue 2: Image Upload Not Working**
**Solution**: 
1. Verify RLS policies are applied
2. Check that `product-images` bucket exists
3. Ensure bucket is set to public

### **Issue 3: Authentication Issues**
**Solution**:
1. Check JWT_SECRET is set
2. Verify password is exactly `121233`
3. Clear browser cache/localStorage

## 🧪 **Test Connection**

Run this in your browser console to test Supabase connection:

```javascript
// Test Supabase connection
async function testConnection() {
  try {
    const { data, error } = await supabase
      .from('products')
      .select('product_id, title')
      .limit(1)
    
    if (error) {
      console.error('Error:', error)
    } else {
      console.log('✅ Connection successful!', data)
    }
  } catch (err) {
    console.error('Test failed:', err)
  }
}

testConnection()
```

## 📱 **Mobile Testing**

1. **Desktop**: Test on http://localhost:3000
2. **Mobile**: Use your computer's IP address (e.g., http://192.168.1.100:3000)
3. **Features to test**:
   - Touch interactions
   - Image upload on mobile
   - Responsive design
   - Search functionality

## 🚀 **Production Deployment**

### **Option 1: Vercel (Recommended)**
1. Push code to GitHub
2. Connect to Vercel
3. Add environment variables
4. Deploy

### **Option 2: Manual Server**
```bash
npm run build
npm start
```

## 📞 **Support**

- **Password Issues**: Contact @Sarvesh_101 on Telegram
- **Technical Issues**: Check browser console for errors
- **Database Issues**: Verify Supabase connection and RLS policies

---

**🎉 Your web application should now be fully functional!**
