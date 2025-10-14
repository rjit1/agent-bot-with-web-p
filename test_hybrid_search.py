#!/usr/bin/env python3
"""
Test script to verify hybrid search function is working
"""
import os
import asyncio
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

async def test_hybrid_search():
    """Test the hybrid search function."""
    print("🔍 Testing Hybrid Search Function...")
    
    # Initialize Supabase
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    
    # Test 1: Search for "2188"
    print("\n📋 Test 1: Searching for '2188'")
    try:
        result = supabase.rpc(
            "hybrid_search_products",
            {
                "query_embedding": [0.1] * 768,  # Dummy embedding
                "search_term": "2188",
                "match_threshold": 0.3,
                "match_count": 5,
                "filter_category": None,
                "filter_age_range": None,
                "min_price": None,
                "max_price": None,
                "filter_stock_status": "in_stock"
            }
        ).execute()
        
        print(f"✅ Hybrid search successful! Found {len(result.data)} products")
        for product in result.data:
            print(f"   - {product.get('title', 'N/A')} (ID: {product.get('product_id', 'N/A')})")
            
    except Exception as e:
        print(f"❌ Hybrid search failed: {e}")
    
    # Test 2: Search for "jeep"
    print("\n📋 Test 2: Searching for 'jeep'")
    try:
        result = supabase.rpc(
            "hybrid_search_products",
            {
                "query_embedding": [0.1] * 768,  # Dummy embedding
                "search_term": "jeep",
                "match_threshold": 0.3,
                "match_count": 5,
                "filter_category": None,
                "filter_age_range": None,
                "min_price": None,
                "max_price": None,
                "filter_stock_status": "in_stock"
            }
        ).execute()
        
        print(f"✅ Hybrid search successful! Found {len(result.data)} products")
        for product in result.data:
            print(f"   - {product.get('title', 'N/A')} (ID: {product.get('product_id', 'N/A')})")
            
    except Exception as e:
        print(f"❌ Hybrid search failed: {e}")
    
    # Test 3: Check if function exists
    print("\n📋 Test 3: Checking if hybrid_search_products function exists")
    try:
        # Try to call with minimal parameters
        result = supabase.rpc("hybrid_search_products", {}).execute()
        print("✅ Function exists and is callable")
    except Exception as e:
        print(f"❌ Function doesn't exist or has issues: {e}")

if __name__ == "__main__":
    asyncio.run(test_hybrid_search())
