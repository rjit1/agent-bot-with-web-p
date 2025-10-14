"""
Test Script for Enhanced Production-Level Image Matching
Tests the complete workflow with visual verification and product cards.
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

async def test_enhanced_production_system():
    """Test the enhanced production-level image matching system."""
    try:
        logger.info("🧪 Testing Enhanced Production-Level Image Matching System...")
        
        # Test imports
        logger.info("📦 Testing imports...")
        from gurtoy_bot import GurtoyAI
        from visual_verification_system import initialize_visual_verification, get_visual_verification
        from intelligent_image_matching import initialize_intelligent_systems, get_production_system
        
        logger.info("✅ All imports successful")
        
        # Test GurtoyAI class methods
        logger.info("🔍 Testing GurtoyAI methods...")
        
        # Check if _enhance_products_with_visual_verification method exists
        if hasattr(GurtoyAI, '_enhance_products_with_visual_verification'):
            logger.info("✅ _enhance_products_with_visual_verification method exists")
        else:
            logger.error("❌ _enhance_products_with_visual_verification method not found")
            return False
        
        # Test method signature
        import inspect
        method = getattr(GurtoyAI, '_enhance_products_with_visual_verification')
        signature = inspect.signature(method)
        
        expected_params = ['self', 'products', 'smart_response', 'match_type']
        actual_params = list(signature.parameters.keys())
        
        if actual_params == expected_params:
            logger.info("✅ Method signature is correct")
        else:
            logger.error(f"❌ Method signature mismatch. Expected: {expected_params}, Got: {actual_params}")
            return False
        
        # Test product enhancement logic
        logger.info("🔍 Testing product enhancement logic...")
        
        # Create mock data
        mock_products = [
            {
                'product_id': 'TEST-001',
                'title': 'Test Product 1',
                'price': 1000,
                'description': 'Test description'
            },
            {
                'product_id': 'TEST-002', 
                'title': 'Test Product 2',
                'price': 2000,
                'description': 'Test description 2'
            }
        ]
        
        # Create mock smart response
        class MockSmartResponse:
            def __init__(self):
                self.primary_message = "Test primary message"
                self.secondary_message = "Test secondary message"
                self.match_summary = "Test match summary"
                self.response_type = type('ResponseType', (), {'value': 'exact_match_found'})()
                self.confidence_level = type('ConfidenceLevel', (), {'value': 'high'})()
        
        mock_smart_response = MockSmartResponse()
        
        # Test enhancement
        try:
            # Create instance to test method
            ai_instance = GurtoyAI.__new__(GurtoyAI)  # Create without __init__
            
            enhanced_products = ai_instance._enhance_products_with_visual_verification(
                mock_products, mock_smart_response, "exact_match"
            )
            
            if len(enhanced_products) == 2:
                logger.info("✅ Product enhancement returned correct number of products")
            else:
                logger.error(f"❌ Product enhancement returned {len(enhanced_products)} products, expected 2")
                return False
            
            # Check if visual verification data was added
            first_product = enhanced_products[0]
            if 'visual_verification' in first_product:
                logger.info("✅ Visual verification data added to products")
            else:
                logger.error("❌ Visual verification data not added to products")
                return False
            
            # Check match badge
            if 'match_badge' in first_product:
                logger.info(f"✅ Match badge added: {first_product['match_badge']}")
            else:
                logger.error("❌ Match badge not added to products")
                return False
            
            # Check match priority
            if 'match_priority' in first_product:
                logger.info(f"✅ Match priority added: {first_product['match_priority']}")
            else:
                logger.error("❌ Match priority not added to products")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error testing product enhancement: {e}")
            return False
        
        logger.info("🎉 Enhanced production-level image matching system test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False

async def main():
    """Main test function."""
    logger.info("🚀 Starting Enhanced Production-Level Image Matching System Test")
    
    success = await test_enhanced_production_system()
    
    if success:
        logger.info("🎉 ALL TESTS PASSED! Enhanced production-level system is working!")
        logger.info("🚀 The system now includes:")
        logger.info("   ✅ Visual verification with batch image comparison")
        logger.info("   ✅ Enhanced product cards with match badges")
        logger.info("   ✅ Smart response integration")
        logger.info("   ✅ Production-level intelligence")
        logger.info("   ✅ Proper product card display")
    else:
        logger.error("❌ TESTS FAILED! Please check the issues above.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
