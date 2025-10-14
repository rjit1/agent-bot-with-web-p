"""
Investigate Order ID Mismatch
This investigates why database orders don't match Razorpay orders
"""

import os
from dotenv import load_dotenv
import razorpay
from supabase import create_client
from datetime import datetime

load_dotenv()

# Initialize clients
razorpay_client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

print("=" * 80)
print("🔍 INVESTIGATING ORDER ID MISMATCH")
print("=" * 80)

# Get all orders from database
print("\n📊 Fetching database orders...")
db_result = supabase.table("orders").select("*").order("created_at", desc=True).limit(20).execute()
db_orders = db_result.data

print(f"✅ Found {len(db_orders)} orders in database\n")

# Get all orders from Razorpay  
print("📊 Fetching Razorpay orders...")
rzp_orders = razorpay_client.order.all({"count": 20})
print(f"✅ Found {rzp_orders['count']} orders on Razorpay\n")

# Create sets of Razorpay order IDs
db_razorpay_ids = set()
for order in db_orders:
    rzp_id = order.get("razorpay_order_id")
    if rzp_id:
        db_razorpay_ids.add(rzp_id)

razorpay_order_ids = set()
for order in rzp_orders['items']:
    razorpay_order_ids.add(order['id'])

# Find matches and mismatches
matched = db_razorpay_ids & razorpay_order_ids
in_db_not_razorpay = db_razorpay_ids - razorpay_order_ids
in_razorpay_not_db = razorpay_order_ids - db_razorpay_ids

print("=" * 80)
print("📊 ANALYSIS RESULTS:")
print("=" * 80)
print(f"✅ Matched (in both): {len(matched)}")
print(f"⚠️  In DB but not in Razorpay (last 20): {len(in_db_not_razorpay)}")
print(f"❌ In Razorpay but NOT in DB: {len(in_razorpay_not_db)}")

if matched:
    print("\n✅ MATCHED ORDERS:")
    for order_id in list(matched)[:5]:
        print(f"   - {order_id}")

if in_razorpay_not_db:
    print(f"\n❌ ORDERS IN RAZORPAY BUT NOT IN DATABASE ({len(in_razorpay_not_db)}):")
    for order_id in list(in_razorpay_not_db)[:10]:
        # Get order details
        order = razorpay_client.order.fetch(order_id)
        status = order.get('status', 'unknown')
        amount = order.get('amount', 0) / 100
        created = datetime.fromtimestamp(order['created_at']).strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"   - {order_id}")
        print(f"     Status: {status} | Amount: ₹{amount} | Created: {created}")
        
        # Check if it has payments
        try:
            payments = razorpay_client.order.payments(order_id)
            if payments.get('items'):
                payment_status = payments['items'][0]['status']
                print(f"     💳 Payment Status: {payment_status}")
        except:
            pass

print("\n" + "=" * 80)

# Check database order creation dates
print("\n📅 DATABASE ORDER CREATION TIMELINE:")
print("=" * 80)
for order in db_orders[:10]:
    order_id = order.get('order_id', 'N/A')
    rzp_id = order.get('razorpay_order_id', 'N/A')
    status = order.get('status', 'N/A')
    created = order.get('created_at', 'N/A')
    
    print(f"{created} | {order_id}")
    print(f"   Razorpay ID: {rzp_id}")
    print(f"   Status: {status}")
    print()

print("=" * 80)
print("✅ Investigation complete")
print("=" * 80)

print("\n🔍 HYPOTHESIS:")
print("If orders were created on Razorpay but are missing from the database,")
print("this suggests one of the following:")
print("  1. Database was cleared/reset after orders were created")
print("  2. Orders created through a different mechanism (not through bot)")
print("  3. Order creation succeeded on Razorpay but failed to save to database")
print("  4. You're using old payment links from previous test sessions")