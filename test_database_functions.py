#!/usr/bin/env python3
"""
Database Function Test for Fashion Mart
This script tests if the database functions are working correctly after migration.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_database_functions():
    """Test database functions to ensure they're working correctly."""
    
    logger.info("=" * 80)
    logger.info("🔧 DATABASE FUNCTION TESTING")
    logger.info("=" * 80)
    
    try:
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            logger.error("❌ Missing Supabase credentials")
            return False
        
        supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("✅ Supabase client initialized")
        
        # Test 1: Check if products table has the correct columns
        logger.info("\n" + "="*50)
        logger.info("📊 TEST 1: TABLE SCHEMA CHECK")
        logger.info("="*50)
        
        try:
            # Get a sample product to check columns
            result = supabase.table("products").select("product_id, title, size_range, style_keywords, occasion").limit(1).execute()
            
            if result.data:
                product = result.data[0]
                logger.info("✅ Products table accessible")
                logger.info(f"📦 Sample product: {product.get('title', 'N/A')}")
                logger.info(f"📏 Size range: {product.get('size_range', 'N/A')}")
                logger.info(f"🎨 Style keywords: {product.get('style_keywords', 'N/A')}")
                logger.info(f"🎉 Occasion: {product.get('occasion', 'N/A')}")
            else:
                logger.error("❌ No products found in database")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error accessing products table: {e}")
            return False
        
        # Test 2: Test search_products function
        logger.info("\n" + "="*50)
        logger.info("🔍 TEST 2: SEARCH_PRODUCTS FUNCTION")
        logger.info("="*50)
        
        try:
            # Test with a simple query
            result = supabase.rpc(
                "search_products",
                {
                    "query_embedding": [0.1] * 768,  # Dummy embedding
                    "match_threshold": 0.1,
                    "match_count": 5,
                    "filter_category": "all",
                    "filter_size_range": "M",
                    "min_price": None,
                    "max_price": None,
                    "filter_stock_status": "in_stock"
                }
            ).execute()
            
            logger.info(f"✅ search_products function working - found {len(result.data)} results")
            
        except Exception as e:
            logger.error(f"❌ search_products function failed: {e}")
            return False
        
        # Test 3: Test hybrid_search_products function
        logger.info("\n" + "="*50)
        logger.info("🔗 TEST 3: HYBRID_SEARCH_PRODUCTS FUNCTION")
        logger.info("="*50)
        
        try:
            result = supabase.rpc(
                "hybrid_search_products",
                {
                    "query_embedding": [0.1] * 768,  # Dummy embedding
                    "search_term": "cardigan",
                    "match_threshold": 0.1,
                    "match_count": 5,
                    "filter_category": "all",
                    "filter_size_range": "M",
                    "min_price": None,
                    "max_price": None,
                    "filter_stock_status": "in_stock"
                }
            ).execute()
            
            logger.info(f"✅ hybrid_search_products function working - found {len(result.data)} results")
            
        except Exception as e:
            logger.error(f"❌ hybrid_search_products function failed: {e}")
            return False
        
        # Test 4: Test keyword_search_products function
        logger.info("\n" + "="*50)
        logger.info("🔤 TEST 4: KEYWORD_SEARCH_PRODUCTS FUNCTION")
        logger.info("="*50)
        
        try:
            result = supabase.rpc(
                "keyword_search_products",
                {
                    "search_term": "cardigan",
                    "match_count": 5,
                    "filter_category": "all",
                    "min_price": None,
                    "max_price": None,
                    "filter_size_range": "M"
                }
            ).execute()
            
            logger.info(f"✅ keyword_search_products function working - found {len(result.data)} results")
            
        except Exception as e:
            logger.error(f"❌ keyword_search_products function failed: {e}")
            return False
        
        # Final Results
        logger.info("\n" + "="*80)
        logger.info("🎉 DATABASE FUNCTION TEST RESULTS")
        logger.info("="*80)
        logger.info("✅ Products table schema: WORKING")
        logger.info("✅ search_products function: WORKING")
        logger.info("✅ hybrid_search_products function: WORKING")
        logger.info("✅ keyword_search_products function: WORKING")
        logger.info("="*80)
        logger.info("🎯 ALL DATABASE FUNCTIONS ARE WORKING CORRECTLY!")
        logger.info("="*80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed with error: {e}", exc_info=True)
        return False

async def main():
    """Main test function."""
    logger.info("🚀 Starting database function testing...")
    
    success = await test_database_functions()
    
    if success:
        logger.info("🎉 ALL DATABASE TESTS PASSED!")
        logger.info("✅ Database functions are ready for production")
    else:
        logger.error("❌ DATABASE TESTS FAILED")
        logger.error("⚠️ Please run the Phase 8 migration script")

if __name__ == "__main__":
    asyncio.run(main())
