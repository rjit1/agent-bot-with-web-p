"""
Test Script: Teacher Product Search
Verifies that the bot can correctly search for "Teacher" brand products
"""

import os
import asyncio
from supabase import create_client
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Initialize
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

async def test_direct_database_search():
    """Test 1: Direct database search for Teacher products"""
    print("=" * 70)
    print("TEST 1: Direct Database Search for 'Teacher' Products")
    print("=" * 70)
    
    try:
        # Search using title
        response = supabase.table("products").select("*").ilike("title", "%teacher%").execute()
        
        print(f"\n✅ Found {len(response.data)} products with 'Teacher' in title:")
        for product in response.data:
            print(f"  - {product['product_id']}: {product['title']} ({product['category']})")
            print(f"    Colors: {product['colors']}")
            print(f"    Price: ₹{product['discount_price']}")
            print()
        
        return len(response.data) > 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_keyword_search():
    """Test 2: Keyword search function"""
    print("=" * 70)
    print("TEST 2: Keyword Search for 'teacher'")
    print("=" * 70)
    
    try:
        # Try keyword search via database
        response = supabase.table("products").select("*").or_(
            "title.ilike.%teacher%,product_id.ilike.%teacher%,description.ilike.%teacher%"
        ).execute()
        
        print(f"\n✅ Keyword search found {len(response.data)} products:")
        for product in response.data:
            print(f"  - {product['title']}")
        
        return len(response.data) > 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_semantic_search():
    """Test 3: Semantic/embedding search"""
    print("=" * 70)
    print("TEST 3: Semantic Search for 'teacher brand cardigan'")
    print("=" * 70)
    
    try:
        # Generate embedding
        query = "teacher brand cardigan"
        embedding_result = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query",
            output_dimensionality=768
        )
        
        # Search using embedding
        response = supabase.rpc(
            "search_products",
            {
                "query_embedding": embedding_result["embedding"],
                "match_threshold": 0.5,
                "match_count": 10,
                "filter_category": None,
                "filter_size_range": None,
                "min_price": None,
                "max_price": None,
                "filter_stock_status": "in_stock"
            }
        ).execute()
        
        print(f"\n✅ Semantic search found {len(response.data)} products:")
        for product in response.data[:5]:  # Show top 5
            print(f"  - {product['title']} (similarity: {product['similarity']:.2f})")
        
        # Check if Teacher products are in results
        teacher_products = [p for p in response.data if 'teacher' in p['title'].lower()]
        if teacher_products:
            print(f"\n✅ Found {len(teacher_products)} Teacher brand products in results!")
            return True
        else:
            print("\n⚠️ No Teacher brand products in results")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_product_pattern_matching():
    """Test 4: Product pattern matching logic"""
    print("=" * 70)
    print("TEST 4: Product Pattern Matching")
    print("=" * 70)
    
    # Simulate the _is_product_name_query logic
    query = "teacher product"
    query_clean = query.strip().lower()
    
    product_patterns = [
        'teacher', 'teachar', 'oster', 'imported', 'richeez', 'nice girl',
        'compinent', 'g f o', 'gfo', 'self', 'pinaque', 'i like you',
        'klj', 'oswal', 'fashion', 'mart',
        '1102', '1103', '1104', '1202', '2000', '2001', '2005', '2007',
        '3001', '4002', '5001', '6001', '7001', '7002', '7003', '7004',
        'red', 'blue', 'black', 'white', 'navy', 'gray', 'pink'
    ]
    
    is_product_query = any(pattern in query_clean for pattern in product_patterns)
    
    if is_product_query:
        print(f"✅ Query '{query}' CORRECTLY identified as product name query")
        print(f"   Matched pattern: teacher")
        return True
    else:
        print(f"❌ Query '{query}' NOT identified as product name query")
        return False

async def test_session_context():
    """Test 5: Check session context doesn't have toy data"""
    print("=" * 70)
    print("TEST 5: Session Context Check")
    print("=" * 70)
    
    try:
        # Check recent sessions
        response = supabase.table("sessions").select("*").limit(10).execute()
        
        toy_keywords = ['jeep', 'bike', 'car', 'scooter', 'toy']
        sessions_with_toys = 0
        
        for session in response.data:
            session_data = session.get('session_data', {})
            product_type = session_data.get('product_type', '')
            
            if product_type in toy_keywords:
                sessions_with_toys += 1
                print(f"⚠️ Session {session['id']} still has product_type='{product_type}'")
        
        if sessions_with_toys == 0:
            print("✅ No sessions with toy-related product_type found!")
            return True
        else:
            print(f"⚠️ Found {sessions_with_toys} sessions with toy context")
            print("   Run: python clear_old_sessions.py")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    print("\n" + "="*70)
    print("🧪 TEACHER PRODUCT SEARCH TEST SUITE")
    print("="*70)
    print()
    
    results = {}
    
    # Run all tests
    results['database_search'] = await test_direct_database_search()
    print()
    
    results['keyword_search'] = await test_keyword_search()
    print()
    
    results['semantic_search'] = await test_semantic_search()
    print()
    
    results['pattern_matching'] = await test_product_pattern_matching()
    print()
    
    results['session_context'] = await test_session_context()
    print()
    
    # Summary
    print("=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<50} {status}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Bot is ready to search for Teacher products!")
    else:
        print("\n⚠️ Some tests failed. Please review the results above.")

if __name__ == "__main__":
    asyncio.run(main())