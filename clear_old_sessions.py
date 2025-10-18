"""
Clear Old Toy Store Session Data from Database
This script removes toy-related context from user sessions
"""

import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def clear_toy_session_data():
    """Clear toy-related session data from database"""
    
    print("🧹 Starting session cleanup...")
    print("=" * 60)
    
    # Get all sessions
    try:
        response = supabase.table("sessions").select("*").execute()
        sessions = response.data
        
        print(f"📊 Total sessions found: {len(sessions)}")
        print()
        
        toy_keywords = ['jeep', 'bike', 'car', 'scooter', 'toy', 'doll', 'puzzle', 'battery', 'wheels']
        cleaned_count = 0
        
        for session in sessions:
            session_id = session['id']
            telegram_id = session['telegram_id']
            session_data = session.get('session_data', {})
            
            needs_cleaning = False
            
            # Check product_type
            product_type = session_data.get('product_type', '')
            if product_type in toy_keywords:
                print(f"🔍 Session {session_id} (User {telegram_id}): product_type='{product_type}'")
                session_data['product_type'] = 'unknown'
                needs_cleaning = True
            
            # Check conversation_summary
            summary = session_data.get('conversation_summary', '')
            if any(keyword in summary.lower() for keyword in toy_keywords):
                print(f"🔍 Session {session_id} (User {telegram_id}): summary contains toy keywords")
                session_data['conversation_summary'] = ''
                needs_cleaning = True
            
            # Clear recent_products
            if 'recent_products' in session_data and session_data['recent_products']:
                print(f"🔍 Session {session_id} (User {telegram_id}): clearing recent_products")
                session_data['recent_products'] = []
                needs_cleaning = True
            
            # Update if needed
            if needs_cleaning:
                try:
                    supabase.table("sessions").update({
                        "session_data": session_data
                    }).eq("id", session_id).execute()
                    
                    print(f"✅ Cleaned session {session_id}")
                    cleaned_count += 1
                except Exception as e:
                    print(f"❌ Error cleaning session {session_id}: {e}")
            
        print()
        print("=" * 60)
        print(f"✅ Cleanup complete!")
        print(f"📊 Sessions cleaned: {cleaned_count}/{len(sessions)}")
        
        # Verify
        print()
        print("🔍 Verifying cleanup...")
        response = supabase.table("sessions").select("*").execute()
        remaining_toy_sessions = 0
        
        for session in response.data:
            session_data = session.get('session_data', {})
            product_type = session_data.get('product_type', '')
            summary = session_data.get('conversation_summary', '')
            
            if product_type in toy_keywords or any(keyword in summary.lower() for keyword in toy_keywords):
                remaining_toy_sessions += 1
        
        if remaining_toy_sessions == 0:
            print("✅ No toy-related sessions remaining!")
        else:
            print(f"⚠️ Warning: {remaining_toy_sessions} sessions still contain toy keywords")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧹 Fashion Mart Session Cleanup Tool")
    print("=" * 60)
    print("This will remove toy-related context from user sessions")
    print()
    
    response = input("Continue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        clear_toy_session_data()
    else:
        print("❌ Cleanup cancelled")