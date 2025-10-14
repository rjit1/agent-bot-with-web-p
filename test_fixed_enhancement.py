"""
Quick Test for Fixed Visual Verification Enhancement
Tests the fixed _enhance_products_with_visual_verification method.
"""
import os
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_fixed_enhancement():
    """Test the fixed product enhancement method."""
    try:
        logger.info("🧪 Testing Fixed Visual Verification Enhancement...")
        
        # Test imports
        logger.info("📦 Testing imports...")
        from gurtoy_bot import GurtoyAI
        
        logger.info("✅ All imports successful")
        
        # Create mock data
        mock_products = [
            {
                'product_id': 'TEST-001',
                'title': 'Test Product 1',
                'price': 1000,
                'description': 'Test description'
            }
        ]
        
        # Create mock smart response with correct structure
        class MockSmartResponse:
            def __init__(self):
                self.primary_message = "Test primary message"
                self.secondary_message = "Test secondary message"
                self.match_summary = "Test match summary"
                self.response_type = type('ResponseType', (), {'value': 'exact_match_found'})()
                self.confidence_level = "high"  # This is a string, not an enum
        
        mock_smart_response = MockSmartResponse()
        
        # Test enhancement
        try:
            # Create instance to test method
            ai_instance = GurtoyAI.__new__(GurtoyAI)  # Create without __init__
            
            enhanced_products = ai_instance._enhance_products_with_visual_verification(
                mock_products, mock_smart_response, "exact_match"
            )
            
            if len(enhanced_products) == 1:
                logger.info("✅ Product enhancement returned correct number of products")
            else:
                logger.error(f"❌ Product enhancement returned {len(enhanced_products)} products, expected 1")
                return False
            
            # Check if visual verification data was added correctly
            first_product = enhanced_products[0]
            if 'visual_verification' in first_product:
                visual_data = first_product['visual_verification']
                if visual_data['confidence'] == "high":
                    logger.info("✅ Confidence level handled correctly as string")
                else:
                    logger.error(f"❌ Confidence level incorrect: {visual_data['confidence']}")
                    return False
                
                logger.info("✅ Visual verification data added to products")
            else:
                logger.error("❌ Visual verification data not added to products")
                return False
            
            logger.info("🎉 Fixed visual verification enhancement test completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error testing product enhancement: {e}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False

async def main():
    """Main test function."""
    logger.info("🚀 Starting Fixed Visual Verification Enhancement Test")
    
    success = await test_fixed_enhancement()
    
    if success:
        logger.info("🎉 ALL TESTS PASSED! The fix is working correctly!")
        logger.info("🚀 The system now handles confidence_level as a string properly!")
    else:
        logger.error("❌ TESTS FAILED! Please check the issues above.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
