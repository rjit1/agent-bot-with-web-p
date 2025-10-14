// Test script to verify Supabase connection
// Run this in your browser console after setting up the environment

async function testSupabaseConnection() {
  try {
    console.log('Testing Supabase connection...')
    
    // Test basic connection
    const { data, error } = await supabase
      .from('products')
      .select('product_id, title')
      .limit(1)
    
    if (error) {
      console.error('Supabase connection error:', error)
      return false
    }
    
    console.log('✅ Supabase connection successful!')
    console.log('Sample data:', data)
    
    // Test storage bucket access
    const { data: buckets, error: bucketError } = await supabase.storage.listBuckets()
    
    if (bucketError) {
      console.error('Storage bucket error:', bucketError)
      return false
    }
    
    console.log('✅ Storage access successful!')
    console.log('Available buckets:', buckets)
    
    return true
  } catch (err) {
    console.error('Test failed:', err)
    return false
  }
}

// Run the test
testSupabaseConnection()
