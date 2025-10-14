#!/usr/bin/env python3
"""
Test Script for AI Search Function Fix
Tests that the AI now properly calls search_products for specific product queries.
"""
import os
import asyncio
import json
from dotenv import load_dotenv
from gurtoy_bot import GurtoyAI

# Load environment variables
load_dotenv()

async def test_ai_search_behavior():
    """Test that AI properly calls search_products for specific queries."""
    
    print("🧪 Testing AI Search Behavior Fix")
    print("=" * 60)
    
    try:
        # Initialize AI
        ai = GurtoyAI()
        print("✅ AI initialized successfully")
        
        # Test cases that should trigger IMMEDIATE search
        specific_queries = [
            "g63 jeep",
            "2188", 
            "red bike",
            "police car",
            "electric scooter"
        ]
        
        # Test cases that should ask questions first
        vague_queries = [
            "show me toys",
            "kuch dikhao",
            "bikes chahiye",
            "something for my child"
        ]
        
        print(f"\n📋 Testing {len(specific_queries)} specific queries (should search immediately)...")
        
        for query in specific_queries:
            print(f"\n🔍 Testing: '{query}'")
            
            try:
                # Create minimal user context
                user_context = {
                    "user_id": 1,
                    "telegram_id": 123456789,
                    "recent_messages": [],
                    "session_data": {}
                }
                
                # Generate AI response
                response, products = await ai.generate_response(query, user_context)
                
                print(f"   Response: {response[:100]}...")
                print(f"   Products found: {len(products) if products else 0}")
                
                # Check if AI called search function (indicated by SHOW_PRODUCTS or products)
                if response == "SHOW_PRODUCTS" or products:
                    print(f"   ✅ SUCCESS: AI called search function")
                else:
                    print(f"   ❌ FAILED: AI did not call search function")
                    
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
        
        print(f"\n📋 Testing {len(vague_queries)} vague queries (should ask questions first)...")
        
        for query in vague_queries:
            print(f"\n🔍 Testing: '{query}'")
            
            try:
                # Create minimal user context
                user_context = {
                    "user_id": 1,
                    "telegram_id": 123456789,
                    "recent_messages": [],
                    "session_data": {}
                }
                
                # Generate AI response
                response, products = await ai.generate_response(query, user_context)
                
                print(f"   Response: {response[:100]}...")
                print(f"   Products found: {len(products) if products else 0}")
                
                # Check if AI asked questions instead of searching
                if "?" in response and response != "SHOW_PRODUCTS":
                    print(f"   ✅ SUCCESS: AI asked questions instead of searching")
                else:
                    print(f"   ⚠️  CHECK: AI may have searched instead of asking questions")
                    
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
        
        print(f"\n🎉 AI Search Behavior Test Completed!")
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")

async def main():
    """Run the test."""
    
    print("🚀 Gurtoy Bot - AI Search Behavior Test")
    print("=" * 60)
    
    # Test AI search behavior
    await test_ai_search_behavior()
    
    print("\n" + "=" * 60)
    print("🎉 Test completed!")
    print("\n📋 Next steps:")
    print("1. Restart the bot: python run_bot.py")
    print("2. Test with real user queries in Telegram")
    print("3. Verify that 'g63 jeep' now triggers search_products function")

if __name__ == "__main__":
    asyncio.run(main())
