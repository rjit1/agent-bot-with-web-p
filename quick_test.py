#!/usr/bin/env python3
"""
Quick test script for image-based search functionality
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_database_connection():
    try:
        print('Testing Database Connection...')
        from gurtoy_bot import GurtoyAI
        gurtoy_ai = GurtoyAI()
        
        # Test embedding generation
        test_description = 'Electric ride-on jeep with red exterior, LED lights, rubber wheels, remote control'
        print(f'Testing embedding generation for: {test_description[:50]}...')
        
        embedding = await gurtoy_ai._generate_image_embedding(test_description)
        
        if embedding:
            print(f'SUCCESS: Generated embedding: {len(embedding)} dimensions')
            print(f'   First 5 values: {embedding[:5]}')
            
            # Test database search
            print('Testing database search...')
            products = await gurtoy_ai._search_products_by_image_embedding(
                embedding, match_threshold=0.70, max_results=5
            )
            
            if products:
                print(f'SUCCESS: Database search returned {len(products)} products')
                for i, product in enumerate(products[:3], 1):
                    print(f'   {i}. {product["title"]} (Similarity: {product["similarity"]:.3f})')
            else:
                print('WARNING: No products found in database search')
        else:
            print('ERROR: Failed to generate embedding')
            
    except Exception as e:
        print(f'ERROR: Database test failed: {e}')
        import traceback
        traceback.print_exc()

async def test_image_handler():
    try:
        print('\nTesting Image Handler...')
        from image_handler import ImageHandler
        
        image_handler = ImageHandler(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            gemini_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        print('SUCCESS: Image handler initialized successfully')
        
        # Test if we can create the product search description method
        if hasattr(image_handler, 'generate_product_search_description'):
            print('SUCCESS: Product search description method available')
        else:
            print('ERROR: Product search description method not found')
            
    except Exception as e:
        print(f'ERROR: Image handler test failed: {e}')
        import traceback
        traceback.print_exc()

async def test_tool_availability():
    try:
        print('\nTesting Tool Availability...')
        from gurtoy_bot import GurtoyAI
        gurtoy_ai = GurtoyAI()
        
        # Check if the new tool method exists
        if hasattr(gurtoy_ai, '_create_search_products_by_image_tool'):
            print('SUCCESS: Image search tool method available')
        else:
            print('ERROR: Image search tool method not found')
            
        if hasattr(gurtoy_ai, 'search_products_by_image'):
            print('SUCCESS: Image search function available')
        else:
            print('ERROR: Image search function not found')
            
    except Exception as e:
        print(f'ERROR: Tool availability test failed: {e}')
        import traceback
        traceback.print_exc()

async def main():
    print('Starting Quick Tests for Image-Based Search')
    print('=' * 60)
    
    await test_database_connection()
    await test_image_handler()
    await test_tool_availability()
    
    print('\nQuick tests completed!')

if __name__ == "__main__":
    asyncio.run(main())