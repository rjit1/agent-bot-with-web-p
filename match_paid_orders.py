"""
Match paid Razorpay orders with database orders
Find out why payments aren't being detected
"""
import os
from dotenv import load_dotenv
import razorpay
from supabase import create_client, Client

load_dotenv()

# Initialize clients
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

razorpay_client = razorpay.Client(auth=(
    os.getenv("RAZORPAY_KEY_ID"),
    os.getenv("RAZORPAY_KEY_SECRET")
))

def match_paid_orders():
    """Match paid orders from Razorpay with database"""
    
    print("\n" + "="*70)
    print("🔍 MATCHING PAID ORDERS: Razorpay vs Database")
    print("="*70)
    
    # Get all orders from database
    db_orders = supabase.table("orders").select("""
        order_id,
        razorpay_order_id,
        status,
        total_amount,
        user_id,
        users!inner(telegram_id, first_name)
    """).execute()
    
    print(f"\n📊 Database has {len(db_orders.data)} orders")
    
    # Get paid orders from Razorpay
    razorpay_orders = razorpay_client.order.all({"count": 20})
    
    paid_razorpay_orders = []
    for order in razorpay_orders['items']:
        if order.get('status') == 'paid':
            paid_razorpay_orders.append(order)
    
    print(f"💳 Razorpay has {len(paid_razorpay_orders)} PAID orders")
    
    # Create lookup dictionaries
    db_razorpay_ids = {order['razorpay_order_id']: order for order in db_orders.data if order.get('razorpay_order_id')}
    
    print(f"\n{'='*70}")
    print("🔍 ANALYZING PAID ORDERS")
    print("="*70)
    
    matched = []
    unmatched = []
    
    for razorpay_order in paid_razorpay_orders:
        razorpay_order_id = razorpay_order['id']
        
        print(f"\n📦 Razorpay Order: {razorpay_order_id}")
        print(f"   Amount: ₹{razorpay_order['amount'] / 100}")
        print(f"   Status: {razorpay_order['status']}")
        print(f"   Amount Paid: ₹{razorpay_order.get('amount_paid', 0) / 100}")
        
        # Check if in database
        if razorpay_order_id in db_razorpay_ids:
            db_order = db_razorpay_ids[razorpay_order_id]
            print(f"   ✅ FOUND IN DATABASE")
            print(f"      DB Order ID: {db_order['order_id']}")
            print(f"      DB Status: {db_order['status']}")
            print(f"      User Telegram ID: {db_order['users']['telegram_id']}")
            
            if db_order['status'] != 'paid':
                print(f"      🚨 MISMATCH: Razorpay says PAID but DB says {db_order['status'].upper()}")
                matched.append({
                    'razorpay_order_id': razorpay_order_id,
                    'db_order_id': db_order['order_id'],
                    'db_status': db_order['status'],
                    'telegram_id': db_order['users']['telegram_id'],
                    'user_id': db_order['user_id'],
                    'amount': razorpay_order['amount'] / 100
                })
            else:
                print(f"      ✅ Status matches - all good")
        else:
            print(f"   ❌ NOT FOUND IN DATABASE")
            print(f"      This order was deleted or never created in DB")
            unmatched.append(razorpay_order_id)
    
    # Summary
    print(f"\n\n{'='*70}")
    print("📊 SUMMARY")
    print("="*70)
    
    print(f"\n✅ Matched (in both DB and Razorpay): {len(matched)}")
    print(f"❌ Unmatched (paid in Razorpay but not in DB): {len(unmatched)}")
    
    if matched:
        print(f"\n\n{'='*70}")
        print("🚨 CRITICAL ISSUE FOUND!")
        print("="*70)
        print(f"\n{len(matched)} order(s) are PAID in Razorpay but NOT updated in database!")
        print("\nThese orders need to be updated:\n")
        
        for order in matched:
            print(f"   Order ID: {order['db_order_id']}")
            print(f"   Razorpay Order ID: {order['razorpay_order_id']}")
            print(f"   User Telegram ID: {order['telegram_id']}")
            print(f"   Amount: ₹{order['amount']}")
            print(f"   Current DB Status: {order['db_status']}")
            print(f"   Should be: paid")
            print()
        
        print("="*70)
        print("💡 SOLUTION")
        print("="*70)
        print("""
The payment detection polling is NOT working correctly!

POSSIBLE CAUSES:
1. Payment was made BEFORE bot started polling
2. Bot was offline when payment was made
3. Payment detection has a bug in the logic
4. handle_payment_success() is not being called

IMMEDIATE FIX:
We need to manually trigger payment detection for these orders.
        """)
        
        # Offer to fix
        print("\n🔧 Do you want to manually update these orders? (y/n)")
        response = input("> ").strip().lower()
        
        if response == 'y':
            print("\nUpdating orders...")
            for order in matched:
                # Update order status
                supabase.table("orders").update({
                    "status": "paid"
                }).eq("order_id", order['db_order_id']).execute()
                
                print(f"✅ Updated {order['db_order_id']} to 'paid'")
            
            print("\n✅ All orders updated!")
            print("\nNOTE: Users were NOT notified. You may want to send manual notifications.")
    
    if unmatched:
        print(f"\n\n{'='*70}")
        print("ℹ️ UNMATCHED ORDERS (Not a Problem)")
        print("="*70)
        print(f"\n{len(unmatched)} paid order(s) are in Razorpay but not in database.")
        print("This is normal if the database was reset after these orders.")
        print("\nUnmatched Razorpay Order IDs:")
        for order_id in unmatched:
            print(f"   - {order_id}")

if __name__ == "__main__":
    match_paid_orders()