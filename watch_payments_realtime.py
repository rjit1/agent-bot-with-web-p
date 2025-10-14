"""
Real-time payment watcher - monitors for new payments every 5 seconds
"""
import os
import time
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import razorpay

load_dotenv()

async def watch_payments():
    # Initialize clients
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    
    razorpay_client = razorpay.Client(auth=(
        os.getenv("RAZORPAY_KEY_ID"),
        os.getenv("RAZORPAY_KEY_SECRET")
    ))
    
    print("=" * 80)
    print("🔍 REAL-TIME PAYMENT WATCHER")
    print("=" * 80)
    print("Monitoring for payments every 5 seconds...")
    print("Press Ctrl+C to stop")
    print("=" * 80)
    print()
    
    seen_orders = set()
    
    try:
        while True:
            # Get pending orders
            orders = supabase.table("orders").select("""
                order_id,
                razorpay_order_id,
                status,
                total_amount,
                created_at
            """).eq("status", "pending_payment").order("created_at", desc=True).limit(5).execute()
            
            if orders.data:
                for order in orders.data:
                    order_id = order["order_id"]
                    razorpay_order_id = order.get("razorpay_order_id")
                    
                    if not razorpay_order_id:
                        continue
                    
                    # Only show each order once when first seen
                    if order_id not in seen_orders:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📦 Watching order: {order_id}")
                        seen_orders.add(order_id)
                    
                    try:
                        # Check Razorpay
                        payments = razorpay_client.order.payments(razorpay_order_id)
                        
                        if payments["items"]:
                            for payment in payments["items"]:
                                print(f"\n{'='*80}")
                                print(f"🎉 PAYMENT DETECTED!")
                                print(f"{'='*80}")
                                print(f"Order ID: {order_id}")
                                print(f"Payment ID: {payment['id']}")
                                print(f"Status: {payment['status']}")
                                print(f"Amount: ₹{payment['amount'] / 100}")
                                print(f"Method: {payment.get('method', 'N/A')}")
                                
                                if payment['status'] == 'captured':
                                    print(f"\n✅ PAYMENT SUCCESSFUL!")
                                    print(f"The bot should send confirmation within 90 seconds...")
                                elif payment['status'] == 'failed':
                                    print(f"\n❌ PAYMENT FAILED: {payment.get('error_description', 'Unknown')}")
                                else:
                                    print(f"\n⏳ Payment status: {payment['status']}")
                                
                                print(f"{'='*80}\n")
                    
                    except Exception as e:
                        pass  # Silently skip errors
            
            # Wait 5 seconds
            await asyncio.sleep(5)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Checking... (watching {len(seen_orders)} orders)", end='\r')
    
    except KeyboardInterrupt:
        print("\n\n✅ Watcher stopped")

if __name__ == "__main__":
    asyncio.run(watch_payments())