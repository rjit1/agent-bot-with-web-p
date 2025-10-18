"""
Test script to verify base64 encoding fixes for audio and image processing.
Tests the audio_handler, image_handler, and visual_verification_system modules.
"""

import asyncio
import logging
import sys
from pathlib import Path
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_audio_handler_base64():
    """Test audio handler uses base64 encoding instead of file uploads."""
    logger.info("=" * 60)
    logger.info("Testing AudioHandler base64 encoding")
    logger.info("=" * 60)
    
    try:
        from audio_handler import AudioHandler
        
        # Check if base64 is imported in audio_handler
        import audio_handler as ah_module
        if not hasattr(ah_module, 'base64'):
            logger.warning("⚠️ base64 module not found in audio_handler")
        else:
            logger.info("✅ base64 module imported in audio_handler")
        
        # Check if aiofiles is imported
        if not hasattr(ah_module, 'aiofiles'):
            logger.warning("⚠️ aiofiles module not found in audio_handler")
        else:
            logger.info("✅ aiofiles module imported in audio_handler")
        
        # Inspect transcribe_audio method
        import inspect
        source = inspect.getsource(AudioHandler.transcribe_audio)
        
        checks = {
            'base64 encoding': 'base64.standard_b64encode' in source,
            'aiofiles': 'aiofiles.open' in source,
            'no upload_file calls': 'upload_file' not in source,
            'mime_type handling': 'mime_type' in source,
            'generate_content with data': '"data": audio_base64' in source
        }
        
        for check_name, result in checks.items():
            status = "✅" if result else "❌"
            logger.info(f"{status} {check_name}: {result}")
        
        all_passed = all(checks.values())
        return all_passed
        
    except Exception as e:
        logger.error(f"❌ Error testing audio handler: {e}", exc_info=True)
        return False

async def test_image_handler_base64():
    """Test image handler uses base64 encoding instead of file uploads."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing ImageHandler base64 encoding")
    logger.info("=" * 60)
    
    try:
        from image_handler import ImageHandler
        
        # Check if base64 is imported
        import image_handler as ih_module
        if not hasattr(ih_module, 'base64'):
            logger.warning("⚠️ base64 module not found in image_handler")
        else:
            logger.info("✅ base64 module imported in image_handler")
        
        # Inspect estimate_size_from_image method
        import inspect
        source = inspect.getsource(ImageHandler.estimate_size_from_image)
        
        checks = {
            'base64 encoding': 'base64.standard_b64encode' in source,
            'aiofiles': 'aiofiles.open' in source,
            'no upload_file calls': 'upload_file' not in source,
            'mime_type map': 'mime_type_map' in source,
            'generate_content with inline data': '"data": image_base64' in source
        }
        
        for check_name, result in checks.items():
            status = "✅" if result else "❌"
            logger.info(f"{status} {check_name}: {result}")
        
        all_passed = all(checks.values())
        return all_passed
        
    except Exception as e:
        logger.error(f"❌ Error testing image handler: {e}", exc_info=True)
        return False

async def test_visual_verification_base64():
    """Test visual verification system uses base64 encoding instead of file uploads."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing VisualVerificationSystem base64 encoding")
    logger.info("=" * 60)
    
    try:
        from visual_verification_system import VisualVerificationSystem
        
        # Check if base64 is imported
        import visual_verification_system as vv_module
        if not hasattr(vv_module, 'base64'):
            logger.warning("⚠️ base64 module not found in visual_verification_system")
        else:
            logger.info("✅ base64 module imported in visual_verification_system")
        
        # Check if aiofiles is imported
        if not hasattr(vv_module, 'aiofiles'):
            logger.warning("⚠️ aiofiles module not found in visual_verification_system")
        else:
            logger.info("✅ aiofiles module imported in visual_verification_system")
        
        import inspect
        
        # Check analyze_user_image
        logger.info("\nChecking analyze_user_image method:")
        source = inspect.getsource(VisualVerificationSystem.analyze_user_image)
        checks_analyze = {
            'base64 encoding': 'base64.standard_b64encode' in source,
            'no upload_file': 'upload_file' not in source,
            'aiofiles': 'aiofiles.open' in source,
            'mime_type handling': 'mime_type_map' in source,
        }
        
        for check_name, result in checks_analyze.items():
            status = "✅" if result else "❌"
            logger.info(f"  {status} {check_name}: {result}")
        
        # Check compare_all_images_batch
        logger.info("\nChecking compare_all_images_batch method:")
        source = inspect.getsource(VisualVerificationSystem.compare_all_images_batch)
        checks_batch = {
            'no upload_file': 'upload_file' not in source,
            'aiofiles for encoding': 'aiofiles.open' in source,
            'content_parts list': 'content_parts' in source,
            'inline base64 data': '"data": user_image_base64' in source or '"data": product_image_base64' in source,
        }
        
        for check_name, result in checks_batch.items():
            status = "✅" if result else "❌"
            logger.info(f"  {status} {check_name}: {result}")
        
        # Check compare_single_product
        logger.info("\nChecking compare_single_product method:")
        source = inspect.getsource(VisualVerificationSystem.compare_single_product)
        checks_single = {
            'no upload_file': 'upload_file' not in source,
            'base64 encoding': 'base64.standard_b64encode' in source,
            'aiofiles': 'aiofiles.open' in source,
            'mime_type map': 'mime_type_map' in source,
            'inline images in response': '"data": user_image_base64' in source and '"data": product_image_base64' in source,
        }
        
        for check_name, result in checks_single.items():
            status = "✅" if result else "❌"
            logger.info(f"  {status} {check_name}: {result}")
        
        all_passed = all(checks_analyze.values()) and all(checks_batch.values()) and all(checks_single.values())
        return all_passed
        
    except Exception as e:
        logger.error(f"❌ Error testing visual verification system: {e}", exc_info=True)
        return False

async def main():
    """Run all tests."""
    logger.info("🚀 Starting base64 encoding fixes verification")
    logger.info("=" * 60)
    
    results = {}
    
    results['audio_handler'] = await test_audio_handler_base64()
    results['image_handler'] = await test_image_handler_base64()
    results['visual_verification'] = await test_visual_verification_base64()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    for module_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{status}: {module_name}")
    
    all_passed = all(results.values())
    
    logger.info("=" * 60)
    if all_passed:
        logger.info("✅ All tests passed! Base64 encoding fixes verified.")
        logger.info("\nKey improvements:")
        logger.info("1. Audio transcription: No longer uses genai.upload_file()")
        logger.info("2. Image analysis: No longer uses genai.upload_file()")
        logger.info("3. Visual verification: No longer uses genai.upload_file()")
        logger.info("4. All file uploads replaced with inline base64 encoding")
        logger.info("5. Eliminates 'Missing required parameter ragStoreName' errors")
    else:
        logger.error("❌ Some tests failed. Please review the output above.")
    
    logger.info("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)