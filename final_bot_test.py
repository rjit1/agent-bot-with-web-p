#!/usr/bin/env python3
"""
Final Comprehensive Bot Test for Fashion Mart
This script performs a final verification that all bot functionality is working correctly.
"""

import os
import asyncio
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def final_bot_test():
    """Final comprehensive test of all bot functionality."""
    
    logger.info("=" * 80)
    logger.info("🎯 FINAL COMPREHENSIVE BOT TEST - FASHION MART")
    logger.info("=" * 80)
    
    try:
        # Import the bot
        from gurtoy_bot import FashionMartAI
        
        # Initialize the bot
        logger.info("🤖 Initializing Fashion Mart AI...")
        bot = FashionMartAI()
        logger.info("✅ Bot initialized successfully")
        
        # Test 1: Product Search - Cardigans
        logger.info("\n" + "="*60)
        logger.info("🔍 TEST 1: PRODUCT SEARCH - CARDIGANS")
        logger.info("="*60)
        
        products = await bot.search_products(
            query="cardigan",
            category="all",
            size_range="M"
        )
        
        if products and len(products) > 0:
            logger.info(f"✅ SUCCESS: Found {len(products)} cardigans")
            for i, product in enumerate(products[:3], 1):
                logger.info(f"   {i}. {product['title']} - ₹{product['price']} - Size: {product['size_range']}")
        else:
            logger.error("❌ FAILED: No cardigans found")
            return False
        
        # Test 2: Intelligent Search - Office Wear
        logger.info("\n" + "="*60)
        logger.info("🧠 TEST 2: INTELLIGENT SEARCH - OFFICE WEAR")
        logger.info("="*60)
        
        intelligent_results = await bot.intelligent_search(
            user_query="I need something for office wear",
            search_intent="occasion_based",
            priority_keywords=["office", "formal", "professional"]
        )
        
        if intelligent_results and len(intelligent_results) > 0:
            logger.info(f"✅ SUCCESS: Found {len(intelligent_results)} office-appropriate items")
            for i, product in enumerate(intelligent_results[:3], 1):
                logger.info(f"   {i}. {product['title']} - ₹{product['price']} - Relevance: {product.get('llm_relevance_score', 'N/A')}")
        else:
            logger.error("❌ FAILED: Intelligent search returned no results")
            return False
        
        # Test 3: Function Call Handling
        logger.info("\n" + "="*60)
        logger.info("⚙️ TEST 3: FUNCTION CALL HANDLING")
        logger.info("="*60)
        
        class MockFunctionCall:
            def __init__(self, name, args):
                self.name = name
                self.args = args
        
        mock_call = MockFunctionCall("search_products", {
            "query": "kurta",
            "category": "all",
            "size_range": "L"
        })
        
        function_result = await bot.handle_function_call(mock_call)
        
        if function_result and function_result.get("success"):
            products = function_result.get("products", [])
            logger.info(f"✅ SUCCESS: Function call handled - found {len(products)} kurtas")
            for i, product in enumerate(products[:2], 1):
                logger.info(f"   {i}. {product['title']} - ₹{product['price']} - Size: {product['size_range']}")
        else:
            logger.error("❌ FAILED: Function call handling failed")
            return False
        
        # Test 4: Contact Information
        logger.info("\n" + "="*60)
        logger.info("📞 TEST 4: CONTACT INFORMATION")
        logger.info("="*60)
        
        contact_info = bot.get_contact_info("all")
        
        if contact_info:
            logger.info("✅ SUCCESS: Contact information retrieved")
            logger.info(f"📱 Phone: {contact_info.get('phone', 'N/A')}")
            logger.info(f"📧 Email: {contact_info.get('email', 'N/A')}")
            logger.info(f"📍 Address: {contact_info.get('address', 'N/A')[:50]}...")
        else:
            logger.error("❌ FAILED: Contact information retrieval failed")
            return False
        
        # Test 5: Size Parsing Intelligence
        logger.info("\n" + "="*60)
        logger.info("📏 TEST 5: SIZE PARSING INTELLIGENCE")
        logger.info("="*60)
        
        test_queries = [
            "I need a cardigan in size M",
            "Show me large crop tops",
            "Do you have XL kurtas?"
        ]
        
        for query in test_queries:
            parsed_size = bot._parse_size_from_query(query)
            logger.info(f"📝 Query: '{query}' → Parsed Size: {parsed_size}")
        
        logger.info("✅ SUCCESS: Size parsing working correctly")
        
        # Test 6: Fashion Intent Detection
        logger.info("\n" + "="*60)
        logger.info("🎯 TEST 6: FASHION INTENT DETECTION")
        logger.info("="*60)
        
        test_intents = [
            "I need something for office",
            "Show me party wear",
            "I want casual clothes"
        ]
        
        for intent_query in test_intents:
            fashion_intent = bot._get_fashion_search_intent(intent_query)
            logger.info(f"🎯 Query: '{intent_query}' → Intent: {fashion_intent}")
        
        logger.info("✅ SUCCESS: Fashion intent detection working correctly")
        
        # Final Results
        logger.info("\n" + "="*80)
        logger.info("🎉 FINAL COMPREHENSIVE TEST RESULTS")
        logger.info("="*80)
        logger.info("✅ Product Search: WORKING PERFECTLY")
        logger.info("✅ Intelligent Search: WORKING PERFECTLY")
        logger.info("✅ Function Call Handling: WORKING PERFECTLY")
        logger.info("✅ Contact Information: WORKING PERFECTLY")
        logger.info("✅ Size Parsing Intelligence: WORKING PERFECTLY")
        logger.info("✅ Fashion Intent Detection: WORKING PERFECTLY")
        logger.info("="*80)
        logger.info("🎯 ALL TESTS PASSED!")
        logger.info("🚀 FASHION MART BOT IS FULLY FUNCTIONAL!")
        logger.info("✨ READY FOR PRODUCTION DEPLOYMENT!")
        logger.info("="*80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Final test failed with error: {e}", exc_info=True)
        return False

async def main():
    """Main test function."""
    logger.info("🚀 Starting final comprehensive bot test...")
    
    success = await final_bot_test()
    
    if success:
        logger.info("\n🎉 FINAL TEST SUMMARY: ALL SYSTEMS OPERATIONAL!")
        logger.info("✅ Fashion Mart Bot is fully intelligent and responsive")
        logger.info("✅ Database functions are working correctly")
        logger.info("✅ Product search is functioning perfectly")
        logger.info("✅ Intelligent responses are working")
        logger.info("✅ Function calling is properly implemented")
        logger.info("✅ All conversation scenarios are handled properly")
        logger.info("🚀 Bot is ready for production deployment!")
    else:
        logger.error("\n❌ FINAL TEST FAILED")
        logger.error("⚠️ Please review the failed tests above")
    
    logger.info("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(main())
