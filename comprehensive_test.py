#!/usr/bin/env python3
"""
Enhanced test script for image-based search functionality with proper Unicode handling
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Fix Unicode issues on Windows
if sys.platform == "win32":
    import colorama
    colorama.init()

load_dotenv()

async def test_database_connection():
    try:
        print("🧪 Testing Database Connection...")
        from gurtoy_bot import GurtoyAI
        gurtoy_ai = GurtoyAI()
        
        # Test embedding generation
        test_description = 'Electric ride-on jeep with red exterior, LED lights, rubber wheels, remote control'
        print(f"📝 Testing embedding generation for: {test_description[:50]}...")
        
        embedding = await gurtoy_ai._generate_image_embedding(test_description)
        
        if embedding:
            print(f"✅ Generated embedding: {len(embedding)} dimensions")
            print(f"   First 5 values: {embedding[:5]}")
            
            # Test database search
            print("🔍 Testing database search...")
            products = await gurtoy_ai._search_products_by_image_embedding(
                embedding, match_threshold=0.70, max_results=5
            )
            
            if products:
                print(f"✅ Database search returned {len(products)} products")
                for i, product in enumerate(products[:3], 1):
                    print(f"   {i}. {product['title']} (Similarity: {product['similarity']:.3f})")
            else:
                print("⚠️ No products found in database search")
        else:
            print("❌ Failed to generate embedding")
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_image_handler():
    try:
        print("\n🖼️ Testing Image Handler...")
        from image_handler import ImageHandler
        
        image_handler = ImageHandler(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            gemini_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        print("✅ Image handler initialized successfully")
        
        # Test if we can create the product search description method
        if hasattr(image_handler, 'generate_product_search_description'):
            print("✅ Product search description method available")
        else:
            print("❌ Product search description method not found")
            
    except Exception as e:
        print(f"❌ Image handler test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_tool_availability():
    try:
        print("\n🔧 Testing Tool Availability...")
        from gurtoy_bot import GurtoyAI
        gurtoy_ai = GurtoyAI()
        
        # Check if the new tool method exists
        if hasattr(gurtoy_ai, '_create_search_products_by_image_tool'):
            print("✅ Image search tool method available")
        else:
            print("❌ Image search tool method not found")
            
        if hasattr(gurtoy_ai, 'search_products_by_image'):
            print("✅ Image search function available")
        else:
            print("❌ Image search function not found")
            
    except Exception as e:
        print(f"❌ Tool availability test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_environment_variables():
    try:
        print("\n🔑 Testing Environment Variables...")
        
        required_vars = [
            "GEMINI_API_KEY",
            "SUPABASE_URL", 
            "SUPABASE_SERVICE_ROLE_KEY",
            "TELEGRAM_BOT_TOKEN"
        ]
        
        missing_vars = []
        for var in required_vars:
            if os.getenv(var):
                print(f"✅ {var}: Available")
            else:
                print(f"❌ {var}: Missing")
                missing_vars.append(var)
        
        if missing_vars:
            print(f"\n⚠️ Missing environment variables: {', '.join(missing_vars)}")
        else:
            print("\n✅ All required environment variables are available")
            
    except Exception as e:
        print(f"❌ Environment variables test failed: {e}")

async def test_supabase_connection():
    try:
        print("\n🗄️ Testing Supabase Connection...")
        from supabase import create_client, Client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            print("❌ Supabase credentials not found")
            return
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Test basic connection
        result = supabase.table("products").select("product_id").limit(1).execute()
        
        if result.data:
            print("✅ Supabase connection successful")
            print(f"   Found {len(result.data)} product(s) in database")
        else:
            print("⚠️ Supabase connected but no products found")
            
    except Exception as e:
        print(f"❌ Supabase connection test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    print("🚀 Starting Comprehensive Tests for Image-Based Search")
    print("=" * 60)
    
    await test_environment_variables()
    await test_supabase_connection()
    await test_database_connection()
    await test_image_handler()
    await test_tool_availability()
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
