"""
Send manual payment confirmation messages for orders that were fixed
"""
import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client
import httpx

load_dotenv()

# Initialize clients
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

async def send_telegram_message(chat_id: int, message: str):
    """Send a message via Telegram API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message
            }
        )
        return response.json()

async def send_payment_confirmation(order_id: str, telegram_id: int, amount: float, payment_id: str):
    """Send payment success confirmation message"""
    success_message = f"""🎉 Payment Successful!

✅ Order ID: {order_id}
💰 Amount Paid: Rs {amount}
🆔 Payment ID: {payment_id}

What's Next:
📦 Your order is being processed
🚚 You'll receive shipping updates via SMS
📞 Contact us at 8300000086 for any queries

Thank you for choosing Gurtoy! 😊

Note: This confirmation was delayed due to a technical issue that has now been resolved."""
    
    try:
        result = await send_telegram_message(telegram_id, success_message)
        if result.get('ok'):
            print(f"✅ Confirmation sent for order {order_id} to user {telegram_id}")
            return True
        else:
            print(f"❌ Failed to send confirmation for order {order_id}: {result.get('description')}")
            return False
    except Exception as e:
        print(f"❌ Error sending confirmation for order {order_id}: {e}")
        return False

async def main():
    print("="*80)
    print("📤 SENDING MANUAL PAYMENT CONFIRMATIONS")
    print("="*80)
    
    # Find all orders that were recently updated to 'paid' status
    # but don't have a confirmation sent log
    recently_paid_orders = supabase.table("orders").select("""
        order_id,
        total_amount,
        razorpay_order_id,
        user_id,
        users!inner(telegram_id, first_name)
    """).eq("status", "paid").execute()
    
    print(f"\nFound {len(recently_paid_orders.data)} paid orders")
    
    # Filter to only recently fixed ones (the 3 we just fixed)
    target_orders = ["GUR20251006000055", "GUR20251006000057", "GUR20251006000059"]
    
    sent_count = 0
    failed_count = 0
    
    for order in recently_paid_orders.data:
        order_id = order['order_id']
        
        if order_id in target_orders:
            print(f"\n{'='*60}")
            print(f"Processing: {order_id}")
            print(f"User: {order['users']['first_name']} (ID: {order['users']['telegram_id']})")
            print(f"Amount: ₹{order['total_amount']}")
            print(f"{'='*60}")
            
            # Send confirmation message
            print(f"\n📤 Sending confirmation to {order['users']['first_name']}...")
            
            success = await send_payment_confirmation(
                order_id=order_id,
                telegram_id=order['users']['telegram_id'],
                amount=order['total_amount'],
                payment_id=order.get('razorpay_order_id', 'N/A')
            )
            
            if success:
                sent_count += 1
            else:
                failed_count += 1
            
            # Small delay between messages
            await asyncio.sleep(1)
    
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"\nTotal Orders Processed: {len(target_orders)}")
    print(f"✅ Confirmations Sent: {sent_count}")
    print(f"❌ Failed: {failed_count}")
    
    if sent_count > 0:
        print(f"\n🎉 Success! {sent_count} payment confirmation(s) sent!")
    
    if failed_count > 0:
        print(f"\n⚠️  Warning: {failed_count} confirmation(s) failed to send")
        print(f"   Check Telegram bot token and user IDs")

if __name__ == "__main__":
    asyncio.run(main())