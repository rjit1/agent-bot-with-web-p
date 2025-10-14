#!/usr/bin/env python3
"""
Test Script for Search Functionality Fixes
Tests the new hybrid search functionality to ensure it works correctly.
"""
import os
import asyncio
import json
from dotenv import load_dotenv
from gurtoy_bot import GurtoyAI

# Load environment variables
load_dotenv()

async def test_search_functionality():
    """Test the new search functionality."""
    
    print("🧪 Testing Search Functionality Fixes")
    print("=" * 60)
    
    try:
        # Initialize AI
        ai = GurtoyAI()
        print("✅ AI initialized successfully")
        
        # Test cases
        test_cases = [
            {
                "query": "2188",
                "description": "Product ID search",
                "expected": "Should find exact product with ID 2188"
            },
            {
                "query": "g63",
                "description": "Model name search", 
                "expected": "Should find G63 products"
            },
            {
                "query": "red bike for 8 year old",
                "description": "Age-specific search",
                "expected": "Should find red bikes suitable for 8-year-olds"
            },
            {
                "query": "jeep",
                "description": "Category search",
                "expected": "Should find all jeep products"
            },
            {
                "query": "bike",
                "description": "General product search",
                "expected": "Should find all bike products"
            }
        ]
        
        print(f"\n📋 Running {len(test_cases)} test cases...")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] Testing: {test_case['description']}")
            print(f"Query: '{test_case['query']}'")
            print(f"Expected: {test_case['expected']}")
            
            try:
                # Test the search
                results = await ai.search_products(test_case['query'])
                
                if results:
                    print(f"✅ SUCCESS: Found {len(results)} products")
                    
                    # Show first result
                    first_result = results[0]
                    print(f"   First result: {first_result['title']}")
                    print(f"   Similarity: {first_result['similarity']:.3f}")
                    print(f"   Search method: {first_result.get('search_method', 'unknown')}")
                    
                    # Show age range if available
                    if first_result.get('age_range'):
                        print(f"   Age range: {first_result['age_range']}")
                        
                else:
                    print(f"❌ FAILED: No products found")
                    
            except Exception as e:
                print(f"❌ ERROR: {e}")
        
        print(f"\n🎉 Search functionality testing completed!")
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")

async def test_intelligent_search():
    """Test the intelligent search functionality."""
    
    print("\n🧠 Testing Intelligent Search")
    print("=" * 40)
    
    try:
        ai = GurtoyAI()
        
        # Test intelligent search
        test_queries = [
            "red bike for 8 year old boy",
            "g63 jeep for my son",
            "something for my daughter",
            "dirt bike"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing intelligent search: '{query}'")
            
            try:
                results = await ai.intelligent_search(query)
                
                if results:
                    print(f"✅ Found {len(results)} products")
                    print(f"   First result: {results[0]['title']}")
                else:
                    print(f"❌ No products found")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except Exception as e:
        print(f"❌ Intelligent search test failed: {e}")

def test_product_name_detection():
    """Test the product name detection logic."""
    
    print("\n🎯 Testing Product Name Detection")
    print("=" * 40)
    
    try:
        ai = GurtoyAI()
        
        test_cases = [
            ("2188", True, "Product ID"),
            ("g63", True, "Model name"),
            ("red jeep", True, "Color + product"),
            ("bike", True, "Product type"),
            ("red bike for 8 year old", False, "Descriptive query"),
            ("something for my daughter", False, "General query"),
            ("what do you recommend", False, "Question"),
        ]
        
        for query, expected, description in test_cases:
            result = ai._is_product_name_query(query)
            status = "✅" if result == expected else "❌"
            print(f"{status} '{query}' → {result} ({description})")
            
    except Exception as e:
        print(f"❌ Product name detection test failed: {e}")

async def main():
    """Run all tests."""
    
    print("🚀 Gurtoy Bot - Search Functionality Test Suite")
    print("=" * 60)
    
    # Test product name detection
    test_product_name_detection()
    
    # Test basic search functionality
    await test_search_functionality()
    
    # Test intelligent search
    await test_intelligent_search()
    
    print("\n" + "=" * 60)
    print("🎉 All tests completed!")
    print("\n📋 Next steps:")
    print("1. Deploy database changes: python deploy_search_fixes.py")
    print("2. Restart the bot: python run_bot.py")
    print("3. Test with real user queries in Telegram")

if __name__ == "__main__":
    asyncio.run(main())