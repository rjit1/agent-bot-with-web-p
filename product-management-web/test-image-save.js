// Quick test script to verify the image save fix
// Run this in browser console on the product management page

async function testImageSave() {
  console.log('🧪 Testing Image Save Fix...')
  
  try {
    // Test 1: Check if we can create a product with images
    const testProduct = {
      product_id: 'TEST_' + Date.now(),
      title: 'Test Product for Image Save',
      category: 'Test Category',
      description: 'Testing image save functionality',
      specifications: {},
      images: [
        {
          url: 'https://example.com/test-image.jpg',
          name: 'test-image.jpg',
          path: 'products/test-image.jpg',
          uploaded_at: new Date().toISOString()
        }
      ],
      price: 99.99,
      stock_status: 'in_stock'
    }
    
    const token = localStorage.getItem('auth_token')
    const response = await fetch('/api/products', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(testProduct)
    })
    
    const result = await response.json()
    
    if (result.success) {
      console.log('✅ Product created successfully with images!')
      console.log('📊 Product data:', result.product)
      
      // Test 2: Verify images are in the database
      if (result.product.images && result.product.images.length > 0) {
        console.log('✅ Images successfully saved to database!')
        console.log('🖼️ Saved images:', result.product.images)
      } else {
        console.log('❌ Images not found in database response')
      }
      
      // Clean up test product
      await fetch(`/api/products/${testProduct.product_id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      console.log('🧹 Test product cleaned up')
      
    } else {
      console.log('❌ Product creation failed:', result.error)
    }
    
  } catch (error) {
    console.log('❌ Test failed:', error)
  }
}

// Run the test
testImageSave()
