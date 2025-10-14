"""
Match the paid order to a user in database
"""
import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

async def match_user():
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    
    # From the Razorpay payment
    payment_email = "skb83208@gmail.com"
    payment_phone = "+918568199188"
    
    print("=" * 80)
    print(f"🔍 MATCHING PAYMENT TO USER")
    print("=" * 80)
    print(f"\nPayment Details from Razorpay:")
    print(f"   Email: {payment_email}")
    print(f"   Phone: {payment_phone}")
    
    # Search for user with this email or phone
    print(f"\n📋 Searching for matching user in database...")
    
    # Search by email
    users = supabase.table("users").select("*").execute()
    
    if users.data:
        print(f"\n✅ Found {len(users.data)} users in database:")
        for user in users.data:
            print(f"\n   User: {user.get('first_name', 'Unknown')}")
            print(f"   Telegram ID: {user.get('telegram_id')}")
            print(f"   Email: {user.get('email', 'N/A')}")
            
            # Check if this user has orders
            orders = supabase.table("orders").select("order_id, razorpay_order_id, status").eq("user_id", user['id']).order("created_at", desc=True).limit(3).execute()
            
            if orders.data:
                print(f"   Orders:")
                for order in orders.data:
                    print(f"      - {order['order_id']}: Razorpay={order.get('razorpay_order_id')} Status={order['status']}")

if __name__ == "__main__":
    asyncio.run(match_user())