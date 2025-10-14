#!/usr/bin/env python3
"""
Complete workflow test for image-based search functionality
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_complete_workflow():
    try:
        print("Testing Complete Image-Based Search Workflow...")
        print("=" * 50)
        
        from gurtoy_bot import GurtoyAI
        from image_handler import ImageHandler
        
        # Initialize components
        print("1. Initializing components...")
        gurtoy_ai = GurtoyAI()
        image_handler = ImageHandler(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            gemini_api_key=os.getenv("GEMINI_API_KEY")
        )
        print("   SUCCESS: Components initialized")
        
        # Test 1: Image analysis (simulated)
        print("\n2. Testing image analysis workflow...")
        
        # Simulate image analysis result
        mock_analysis = {
            "product_type": "electric ride-on jeep",
            "detailed_description": "Electric ride-on jeep with red exterior, LED headlights, rubber wheels, realistic styling, remote control capability, suitable for children aged 3-8 years",
            "colors": ["red", "black"],
            "primary_color": "red",
            "key_features": ["LED lights", "rubber wheels", "realistic styling", "remote control"],
            "age_range": "3-8 years",
            "size_category": "large",
            "style_keywords": ["realistic", "electric", "ride-on", "jeep"],
            "confidence": "high"
        }
        
        print(f"   Mock analysis: {mock_analysis['product_type']}")
        
        # Test 2: Embedding generation
        print("\n3. Testing embedding generation...")
        embedding = await gurtoy_ai._generate_image_embedding(mock_analysis['detailed_description'])
        
        if embedding:
            print(f"   SUCCESS: Generated {len(embedding)}D embedding")
        else:
            print("   ERROR: Failed to generate embedding")
            return False
        
        # Test 3: Database search
        print("\n4. Testing database search...")
        products = await gurtoy_ai._search_products_by_image_embedding(
            embedding, match_threshold=0.70, max_results=5
        )
        
        if products:
            print(f"   SUCCESS: Found {len(products)} products")
            for i, product in enumerate(products[:3], 1):
                print(f"      {i}. {product['title']} (Similarity: {product['similarity']:.3f})")
        else:
            print("   WARNING: No products found")
        
        # Test 4: Complete image-based search function
        print("\n5. Testing complete search_products_by_image function...")
        search_results = await gurtoy_ai.search_products_by_image(
            image_description=mock_analysis['detailed_description'],
            product_type=mock_analysis['product_type'],
            image_features=mock_analysis['key_features'],
            desired_colors=mock_analysis['colors'],
            primary_color=mock_analysis['primary_color'],
            age_range=mock_analysis['age_range'],
            match_threshold=0.70,
            max_results=5
        )
        
        if search_results:
            print(f"   SUCCESS: Complete search returned {len(search_results)} products")
        else:
            print("   WARNING: Complete search returned no results")
        
        # Test 5: Different similarity thresholds
        print("\n6. Testing different similarity thresholds...")
        thresholds = [0.65, 0.70, 0.75]
        
        for threshold in thresholds:
            results = await gurtoy_ai.search_products_by_image(
                image_description=mock_analysis['detailed_description'],
                product_type=mock_analysis['product_type'],
                match_threshold=threshold,
                max_results=3
            )
            print(f"   Threshold {threshold}: {len(results)} products")
        
        print("\nSUCCESS: Complete workflow test passed!")
        return True
        
    except Exception as e:
        print(f"ERROR: Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_function_calling():
    try:
        print("\nTesting Function Calling Integration...")
        print("=" * 50)
        
        from gurtoy_bot import GurtoyAI
        gurtoy_ai = GurtoyAI()
        
        # Test if the tool is properly registered
        tools = gurtoy_ai.model.tools
        print(f"Total tools registered: {len(tools)}")
        
        # Check if our image search tool is in the tools
        image_tool_found = False
        for tool_group in tools:
            if 'function_declarations' in tool_group:
                for func_decl in tool_group['function_declarations']:
                    if func_decl.get('name') == 'search_products_by_image':
                        image_tool_found = True
                        print("SUCCESS: search_products_by_image tool is registered")
                        break
        
        if not image_tool_found:
            print("ERROR: search_products_by_image tool not found in registered tools")
            return False
        
        print("SUCCESS: Function calling integration test passed!")
        return True
        
    except Exception as e:
        print(f"ERROR: Function calling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("Starting Complete Workflow Tests")
    print("=" * 60)
    
    workflow_result = await test_complete_workflow()
    function_result = await test_function_calling()
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    print(f"Complete Workflow: {'PASS' if workflow_result else 'FAIL'}")
    print(f"Function Calling: {'PASS' if function_result else 'FAIL'}")
    
    if workflow_result and function_result:
        print("\n🎉 ALL TESTS PASSED! Image-based search is ready for production!")
    else:
        print("\n⚠️ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())
