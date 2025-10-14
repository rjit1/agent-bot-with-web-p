#!/usr/bin/env python3
"""
Comprehensive Test Script for Gemini Function Calling Fix
Tests that the AI now properly calls search_products for specific queries.
"""
import os
import asyncio
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_gemini_function_calling():
    """Test that Gemini properly calls search_products function."""
    
    print("🧪 Testing Gemini Function Calling Fix")
    print("=" * 60)
    
    try:
        # Import after setting up environment
        from gurtoy_bot import GurtoyAI
        
        # Initialize AI
        print("🔧 Initializing AI with corrected tool format...")
        ai = GurtoyAI()
        print("✅ AI initialized successfully")
        
        # Test the specific query that was failing
        test_queries = [
            "g63 jeep",
            "2188", 
            "red bike",
            "police car",
            "electric scooter"
        ]
        
        print(f"\n🔍 Testing {len(test_queries)} specific product queries:")
        print("-" * 40)
        
        # Create minimal user context
        user_context = {
            "user_id": 1,
            "telegram_id": 123456789,
            "recent_messages": [],
            "session_data": {}
        }
        
        success_count = 0
        total_tests = len(test_queries)
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📝 Test {i}/{total_tests}: '{query}'")
            
            try:
                # Generate AI response
                response, products = await ai.generate_response(query, user_context)
                
                print(f"   🤖 AI Response: {response[:100]}{'...' if len(response) > 100 else ''}")
                print(f"   📦 Products found: {len(products) if products else 0}")
                
                # Check if AI called search function
                if response == "SHOW_PRODUCTS" or products:
                    print(f"   ✅ SUCCESS: AI called search_products function!")
                    success_count += 1
                else:
                    print(f"   ❌ FAILED: AI did not call search_products function")
                    print(f"   🔍 Response suggests AI is not calling the function")
                
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
        
        print(f"\n📊 Test Results Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Successful: {success_count}")
        print(f"   Failed: {total_tests - success_count}")
        print(f"   Success Rate: {(success_count/total_tests)*100:.1f}%")
        
        if success_count == total_tests:
            print(f"\n🎉 ALL TESTS PASSED! The fix is working perfectly!")
            print(f"✅ AI now properly calls search_products for specific product queries")
        elif success_count > 0:
            print(f"\n⚠️  PARTIAL SUCCESS: {success_count}/{total_tests} tests passed")
            print(f"🔧 Some queries are working, but others may need attention")
        else:
            print(f"\n❌ ALL TESTS FAILED: The fix needs more work")
            print(f"🔍 Check tool format and system instruction")
        
        return success_count == total_tests
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_tool_format():
    """Test that tools are in correct format."""
    
    print("\n🔧 Testing Tool Format")
    print("=" * 30)
    
    try:
        from gurtoy_bot import GurtoyAI
        
        # Initialize AI to check tool format
        ai = GurtoyAI()
        
        # Check if model has tools
        if hasattr(ai.model, 'tools') and ai.model.tools:
            print(f"✅ Model has {len(ai.model.tools)} tools configured")
            
            # Check tool format
            for i, tool in enumerate(ai.model.tools):
                if isinstance(tool, dict) and 'function_declarations' in tool:
                    print(f"✅ Tool {i+1}: Correct 'function_declarations' format")
                else:
                    print(f"❌ Tool {i+1}: Incorrect format - {type(tool)}")
                    return False
            
            print("✅ All tools are in correct Gemini function calling format!")
            return True
        else:
            print("❌ Model has no tools configured")
            return False
            
    except Exception as e:
        print(f"❌ Tool format test failed: {e}")
        return False

async def main():
    """Run comprehensive tests."""
    
    print("🚀 Gurtoy Bot - Comprehensive Function Calling Test")
    print("=" * 60)
    
    # Test 1: Tool Format
    format_success = await test_tool_format()
    
    # Test 2: Function Calling
    calling_success = await test_gemini_function_calling()
    
    print("\n" + "=" * 60)
    print("🎯 FINAL RESULTS")
    print("=" * 60)
    
    print(f"Tool Format Test: {'✅ PASSED' if format_success else '❌ FAILED'}")
    print(f"Function Calling Test: {'✅ PASSED' if calling_success else '❌ FAILED'}")
    
    if format_success and calling_success:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"✅ The Gemini function calling fix is working correctly!")
        print(f"🚀 Ready to restart bot and test in Telegram!")
    else:
        print(f"\n⚠️  SOME TESTS FAILED")
        print(f"🔧 Additional fixes may be needed")
    
    print(f"\n📋 Next Steps:")
    print(f"1. If all tests passed → Restart bot: python run_bot.py")
    print(f"2. Test in Telegram: Send 'g63 jeep' to bot")
    print(f"3. Verify: Bot should show G63 jeep products")
    print(f"4. If issues persist → Check logs for function call errors")

if __name__ == "__main__":
    asyncio.run(main())
