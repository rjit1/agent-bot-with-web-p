// Test script to verify Material-UI imports are working
// Run this in your browser console after the app loads

function testMaterialUIComponents() {
  console.log('Testing Material-UI components...')
  
  // Check if Material-UI is loaded
  if (typeof window !== 'undefined' && window.MaterialUI) {
    console.log('✅ Material-UI is loaded')
  } else {
    console.log('⚠️ Material-UI not found in window object')
  }
  
  // Check if React is working
  if (typeof React !== 'undefined') {
    console.log('✅ React is loaded')
  } else {
    console.log('⚠️ React not found')
  }
  
  console.log('Test completed')
}

// Run the test
testMaterialUIComponents()
