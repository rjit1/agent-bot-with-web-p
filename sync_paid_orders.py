"""
Sync Paid Razorpay Orders to Database
This script finds all paid orders on Razorpay and syncs them to the database
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
print("🔄 SYNCING PAID RAZORPAY ORDERS TO DATABASE")
print("=" * 80)

# Fetch recent payments from Razorpay
payments = razorpay_client.payment.all({"count": 20})
print(f"\n✅ Found {payments['count']} recent payments on Razorpay\n")

synced = 0
already_synced = 0
errors = 0

for payment in payments['items']:
    if payment['status'] != 'captured':
        continue
    
    order_id = payment.get('order_id')
    if not order_id:
        continue
    
    payment_id = payment['id']
    amount = payment['amount'] / 100
    
    print(f"💳 Payment: {payment_id}")
    print(f"   Order ID: {order_id}")
    print(f"   Amount: ₹{amount}")
    print(f"   Status: {payment['status']}")
    
    # Check if this order exists in database
    try:
        result = supabase.table("orders").select("*").eq("razorpay_order_id", order_id).execute()
        
        if result.data and len(result.data) > 0:
            order = result.data[0]
            db_order_id = order['id']
            current_status = order['status']
            
            print(f"   📦 Found in DB: {db_order_id}")
            print(f"   Current DB status: {current_status}")
            
            # Update if not already paid
            if current_status != 'paid':
                update_result = supabase.table("orders").update({
                    "status": "paid",
                    "razorpay_payment_id": payment_id,
                    "paid_at": datetime.fromtimestamp(payment['created_at']).isoformat()
                }).eq("id", db_order_id).execute()
                
                print(f"   ✅ SYNCED - Updated order to 'paid' status")
                synced += 1
            else:
                print(f"   ℹ️  Already marked as paid")
                already_synced += 1
        else:
            print(f"   ❌ NOT IN DATABASE - This order doesn't exist in your DB")
            errors += 1
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        errors += 1
    
    print()

print("=" * 80)
print(f"📊 SYNC SUMMARY:")
print(f"   ✅ Newly synced: {synced}")
print(f"   ℹ️  Already synced: {already_synced}")
print(f"   ❌ Not in database: {errors}")
print("=" * 80)