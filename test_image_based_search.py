#!/usr/bin/env python3
"""
Test script for image-based product search functionality.
This script tests the complete workflow:
1. Image analysis using Gemini
2. Embedding generation
3. Database search using image embeddings
4. Product matching and results
"""

import asyncio
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_image_based_search():
    """Test the complete image-based search workflow."""
    try:
        logger.info("🧪 Testing Image-Based Product Search Functionality")
        logger.info("=" * 60)
        
        # Import the main bot components
        from gurtoy_bot import GurtoyAI
        from image_handler import ImageHandler
        
        # Initialize components
        logger.info("📦 Initializing components...")
        gurtoy_ai = GurtoyAI()
        image_handler = ImageHandler(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            gemini_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        # Test with a sample image (you'll need to provide a real image path)
        test_image_path = "test_image.jpg"  # Replace with actual image path
        
        if not os.path.exists(test_image_path):
            logger.warning(f"⚠️ Test image not found: {test_image_path}")
            logger.info("Please provide a test image to continue testing")
            return
        
        logger.info(f"🖼️ Testing with image: {test_image_path}")
        
        # Step 1: Generate product search description
        logger.info("\n📝 Step 1: Generating product search description...")
        analysis_result = await image_handler.generate_product_search_description(
            [test_image_path], 
            caption="Looking for this product"
        )
        
        if not analysis_result:
            logger.error("❌ Failed to generate product search description")
            return
        
        logger.info(f"✅ Analysis Result:")
        logger.info(f"   Product Type: {analysis_result.get('product_type')}")
        logger.info(f"   Description: {analysis_result.get('detailed_description')[:100]}...")
        logger.info(f"   Colors: {analysis_result.get('colors')}")
        logger.info(f"   Features: {analysis_result.get('key_features')}")
        logger.info(f"   Age Range: {analysis_result.get('age_range')}")
        
        # Step 2: Test image-based search
        logger.info("\n🔍 Step 2: Testing image-based product search...")
        products = await gurtoy_ai.search_products_by_image(
            image_description=analysis_result.get('detailed_description'),
            product_type=analysis_result.get('product_type'),
            image_features=analysis_result.get('key_features', []),
            desired_colors=analysis_result.get('colors', []),
            primary_color=analysis_result.get('primary_color'),
            age_range=analysis_result.get('age_range'),
            match_threshold=0.70,
            max_results=5
        )
        
        if products:
            logger.info(f"✅ Found {len(products)} matching products:")
            for i, product in enumerate(products, 1):
                logger.info(f"   {i}. {product['title']} (Similarity: {product['similarity']:.3f})")
                logger.info(f"      Price: ₹{product['price']}")
                logger.info(f"      Colors: {product['colors']}")
        else:
            logger.info("❌ No matching products found")
        
        # Step 3: Test with different thresholds
        logger.info("\n🎯 Step 3: Testing with different similarity thresholds...")
        
        for threshold in [0.65, 0.70, 0.75]:
            products_thresh = await gurtoy_ai.search_products_by_image(
                image_description=analysis_result.get('detailed_description'),
                product_type=analysis_result.get('product_type'),
                image_features=analysis_result.get('key_features', []),
                desired_colors=analysis_result.get('colors', []),
                primary_color=analysis_result.get('primary_color'),
                age_range=analysis_result.get('age_range'),
                match_threshold=threshold,
                max_results=3
            )
            
            logger.info(f"   Threshold {threshold}: {len(products_thresh)} products")
        
        logger.info("\n✅ Image-based search test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)

async def test_database_connection():
    """Test database connection and image search function."""
    try:
        logger.info("\n🗄️ Testing database connection...")
        
        from gurtoy_bot import GurtoyAI
        gurtoy_ai = GurtoyAI()
        
        # Test embedding generation
        test_description = "Electric ride-on jeep with red exterior, LED lights, rubber wheels, remote control"
        embedding = await gurtoy_ai._generate_image_embedding(test_description)
        
        if embedding:
            logger.info(f"✅ Generated embedding: {len(embedding)} dimensions")
            
            # Test database search
            products = await gurtoy_ai._search_products_by_image_embedding(
                embedding, match_threshold=0.70, max_results=5
            )
            
            if products:
                logger.info(f"✅ Database search returned {len(products)} products")
            else:
                logger.info("⚠️ No products found in database search")
        else:
            logger.error("❌ Failed to generate embedding")
            
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}", exc_info=True)

async def main():
    """Main test function."""
    logger.info("🚀 Starting Image-Based Product Search Tests")
    logger.info("=" * 60)
    
    # Test database connection first
    await test_database_connection()
    
    # Test full workflow (requires test image)
    await test_image_based_search()
    
    logger.info("\n🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
