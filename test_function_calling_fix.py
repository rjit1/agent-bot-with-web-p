#!/usr/bin/env python3
"""
Quick Test Script for AI Function Calling Fix
Tests that the AI now properly calls search_products for "g63 jeep" query.
"""
import os
import asyncio
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_ai_function_calling():
    """Test that AI calls search_products function for specific queries."""
    
    print("🧪 Testing AI Function Calling Fix")
    print("=" * 50)
    
    try:
        # Import after setting up environment
        from gurtoy_bot import GurtoyAI
        
        # Initialize AI
        ai = GurtoyAI()
        print("✅ AI initialized successfully")
        
        # Test the specific query that was failing
        test_query = "g63 jeep"
        print(f"\n🔍 Testing query: '{test_query}'")
        
        # Create minimal user context
        user_context = {
            "user_id": 1,
            "telegram_id": 123456789,
            "recent_messages": [],
            "session_data": {}
        }
        
        # Generate AI response
        print("🤖 Generating AI response...")
        response, products = await ai.generate_response(test_query, user_context)
        
        print(f"📝 AI Response: {response}")
        print(f"📦 Products found: {len(products) if products else 0}")
        
        # Check if AI called search function (indicated by SHOW_PRODUCTS or products)
        if response == "SHOW_PRODUCTS" or products:
            print("✅ SUCCESS: AI called search_products function!")
            print("🎉 The fix is working - AI now searches for specific products!")
        else:
            print("❌ FAILED: AI still not calling search_products function")
            print("🔍 AI Response suggests it's not calling the function")
        
        print(f"\n📊 Test Results:")
        print(f"   Query: {test_query}")
        print(f"   Response: {response}")
        print(f"   Products: {len(products) if products else 0}")
        print(f"   Function Called: {'✅ YES' if (response == 'SHOW_PRODUCTS' or products) else '❌ NO'}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run the test."""
    
    print("🚀 Gurtoy Bot - AI Function Calling Test")
    print("=" * 50)
    
    # Test AI function calling
    await test_ai_function_calling()
    
    print("\n" + "=" * 50)
    print("🎉 Test completed!")
    print("\n📋 Next steps:")
    print("1. If test shows SUCCESS → Restart bot and test in Telegram")
    print("2. If test shows FAILED → Check tool format and system instruction")
    print("3. Send 'g63 jeep' to bot in Telegram to verify fix")

if __name__ == "__main__":
    asyncio.run(main())
