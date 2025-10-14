"""
Get Payment Links for Current Database Orders
This generates/fetches payment links for unpaid orders in the database
"""

import os
from dotenv import load_dotenv
import razorpay
from supabase import create_client

load_dotenv()

# Initialize clients
razorpay_client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

print("=" * 80)
print("🔗 PAYMENT LINKS FOR CURRENT DATABASE ORDERS")
print("=" * 80)

# Get unpaid orders from database
result = supabase.table("orders").select("*").eq("status", "pending_payment").order("created_at", desc=True).limit(10).execute()
orders = result.data

if not orders:
    print("\n✅ No unpaid orders found!")
    print("All orders have been paid or there are no orders in the database.")
    exit(0)

print(f"\n📦 Found {len(orders)} unpaid orders\n")
print("=" * 80)

for idx, order in enumerate(orders, 1):
    order_id = order['order_id']
    razorpay_order_id = order.get('razorpay_order_id')
    amount = order['total_amount']
    created_at = order['created_at']
    user_id = order.get('user_id')
    
    print(f"\n📦 ORDER #{idx}: {order_id}")
    print(f"   Amount: ₹{amount}")
    print(f"   Created: {created_at}")
    print(f"   User ID: {user_id}")
    
    if not razorpay_order_id:
        print(f"   ⚠️  No Razorpay Order ID - Order not synced with Razorpay")
        continue
    
    print(f"   Razorpay ID: {razorpay_order_id}")
    
    # Check if payment link exists for this order
    try:
        # Try to get existing payment links for this order
        links = razorpay_client.invoice.all({"order_id": razorpay_order_id})
        
        if links.get('items') and len(links['items']) > 0:
            link = links['items'][0]
            short_url = link.get('short_url')
            print(f"   🔗 Payment Link: {short_url}")
        else:
            # No payment link found, try to get order details and create one
            order_details = razorpay_client.order.fetch(razorpay_order_id)
            
            # Check if order already has a payment
            payments = razorpay_client.order.payments(razorpay_order_id)
            if payments.get('items'):
                payment = payments['items'][0]
                print(f"   💳 Payment Status: {payment['status']}")
                if payment['status'] == 'captured':
                    print(f"   ✅ ALREADY PAID! Payment ID: {payment['id']}")
                    continue
            
            print(f"   ⚠️  No payment link available")
            print(f"   💡 To pay manually:")
            print(f"      1. Go to Razorpay Dashboard")
            print(f"      2. Search for: {razorpay_order_id}")
            print(f"      3. Create a test payment")
            print(f"\n   🎯 OR create a new order through Telegram bot")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

print("\n" + "=" * 80)
print("📝 HOW TO PAY:")
print("=" * 80)
print("""
1. **Find the payment link in your Telegram chat** with the bot
2. The bot sends a payment link when you confirm an order
3. Look for messages like: "Please complete payment: https://rzp.io/l/..."
4. Click the link and pay with TEST credentials

**TEST CREDENTIALS:**
- Card: 4111 1111 1111 1111
- CVV: 123
- Expiry: 12/25
- UPI: success@razorpay

⏱️  **After payment, wait 60-90 seconds for bot to detect it**
""")
print("=" * 80)