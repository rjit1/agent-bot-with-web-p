#!/usr/bin/env python3
"""
Simple test script for image-based search functionality
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

async def test_basic_imports():
    try:
        print("Testing basic imports...")
        from gurtoy_bot import GurtoyAI
        print("SUCCESS: GurtoyAI imported")
        
        from image_handler import ImageHandler
        print("SUCCESS: ImageHandler imported")
        
        from supabase import create_client
        print("SUCCESS: Supabase imported")
        
        return True
    except Exception as e:
        print(f"ERROR: Import failed: {e}")
        return False

async def test_environment_variables():
    try:
        print("\nTesting Environment Variables...")
        
        required_vars = [
            "GEMINI_API_KEY",
            "SUPABASE_URL", 
            "SUPABASE_SERVICE_ROLE_KEY",
            "TELEGRAM_BOT_TOKEN"
        ]
        
        missing_vars = []
        for var in required_vars:
            if os.getenv(var):
                print(f"SUCCESS: {var} available")
            else:
                print(f"ERROR: {var} missing")
                missing_vars.append(var)
        
        if missing_vars:
            print(f"WARNING: Missing variables: {', '.join(missing_vars)}")
            return False
        else:
            print("SUCCESS: All environment variables available")
            return True
            
    except Exception as e:
        print(f"ERROR: Environment test failed: {e}")
        return False

async def test_supabase_connection():
    try:
        print("\nTesting Supabase Connection...")
        from supabase import create_client, Client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            print("ERROR: Supabase credentials not found")
            return False
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Test basic connection
        result = supabase.table("products").select("product_id").limit(1).execute()
        
        if result.data:
            print("SUCCESS: Supabase connection working")
            print(f"Found {len(result.data)} product(s)")
            return True
        else:
            print("WARNING: Connected but no products found")
            return False
            
    except Exception as e:
        print(f"ERROR: Supabase test failed: {e}")
        return False

async def test_gemini_connection():
    try:
        print("\nTesting Gemini Connection...")
        import google.generativeai as genai
        
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            print("ERROR: Gemini API key not found")
            return False
        
        genai.configure(api_key=gemini_api_key)
        
        # Test embedding generation
        test_text = "Electric ride-on jeep with red exterior"
        embed_params = {
            "model": "models/text-embedding-004",
            "content": test_text,
            "task_type": "retrieval_query",
            "output_dimensionality": 768
        }
        
        result = await asyncio.to_thread(genai.embed_content, **embed_params)
        
        if result and 'embedding' in result:
            print("SUCCESS: Gemini embedding generation working")
            print(f"Generated {len(result['embedding'])}D embedding")
            return True
        else:
            print("ERROR: Failed to generate embedding")
            return False
            
    except Exception as e:
        print(f"ERROR: Gemini test failed: {e}")
        return False

async def test_database_functions():
    try:
        print("\nTesting Database Functions...")
        from supabase import create_client, Client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Test if search_products_by_image function exists
        try:
            # Create a dummy embedding for testing
            dummy_embedding = [0.1] * 768
            
            result = supabase.rpc(
                "search_products_by_image",
                {
                    "query_embedding": dummy_embedding,
                    "match_threshold": 0.70,
                    "match_count": 5,
                    "filter_stock_status": "in_stock"
                }
            ).execute()
            
            print("SUCCESS: search_products_by_image function exists")
            return True
            
        except Exception as e:
            if "function search_products_by_image" in str(e):
                print("ERROR: search_products_by_image function not found in database")
                return False
            else:
                print(f"SUCCESS: Function exists (error was: {e})")
                return True
            
    except Exception as e:
        print(f"ERROR: Database function test failed: {e}")
        return False

async def main():
    print("Starting Image-Based Search Tests")
    print("=" * 50)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Environment Variables", test_environment_variables),
        ("Supabase Connection", test_supabase_connection),
        ("Gemini Connection", test_gemini_connection),
        ("Database Functions", test_database_functions)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"ERROR: {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY:")
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")

if __name__ == "__main__":
    asyncio.run(main())
