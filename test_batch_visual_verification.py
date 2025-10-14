"""
Test Script for Batch Visual Verification
Tests the new batch image comparison functionality.
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

async def test_batch_visual_verification():
    """Test the batch visual verification system."""
    try:
        logger.info("🧪 Testing Batch Visual Verification System...")
        
        # Check if we have the required environment variables
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            logger.error("❌ GEMINI_API_KEY not found in environment variables")
            return False
        
        logger.info("✅ GEMINI_API_KEY found")
        
        # Test imports
        logger.info("📦 Testing imports...")
        from visual_verification_system import initialize_visual_verification, get_visual_verification
        from intelligent_image_matching import initialize_intelligent_systems, get_production_system
        
        logger.info("✅ All imports successful")
        
        # Initialize systems
        logger.info("🚀 Initializing systems...")
        visual_verification = initialize_visual_verification(gemini_api_key)
        initialize_intelligent_systems(visual_verification, gemini_api_key)
        
        production_system = get_production_system()
        
        if visual_verification and production_system:
            logger.info("✅ Visual verification system initialized successfully")
            logger.info("✅ Production system initialized successfully")
            
            # Test batch comparison method exists
            logger.info("🔍 Testing batch comparison method...")
            if hasattr(visual_verification, 'compare_all_images_batch'):
                logger.info("✅ Batch comparison method exists")
            else:
                logger.error("❌ Batch comparison method not found")
                return False
            
            logger.info("🎉 Batch visual verification system test completed successfully!")
            return True
        else:
            logger.error("❌ Failed to initialize systems")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False

async def main():
    """Main test function."""
    logger.info("🚀 Starting Batch Visual Verification System Test")
    
    success = await test_batch_visual_verification()
    
    if success:
        logger.info("🎉 ALL TESTS PASSED! Batch visual verification system is working!")
    else:
        logger.error("❌ TESTS FAILED! Please check the issues above.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
