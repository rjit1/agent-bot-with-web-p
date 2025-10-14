"""
Deploy Keyword Search Function to Supabase
This script adds the keyword_search_products function to the database.
"""
import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def deploy_keyword_search():
    """Deploy the keyword search function to Supabase."""
    
    print("🚀 Deploying keyword search function to Supabase...")
    
    # Initialize Supabase client
    supabase = create_client(
        os.getenv("SUPABASE_URL"), 
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    
    # Read the SQL function from products_schema.sql
    with open("products_schema.sql", "r", encoding="utf-8") as f:
        sql_content = f.read()
    
    # Extract just the keyword_search_products function
    # Find the function definition
    start_marker = "-- Function to search products using keyword matching"
    end_marker = "-- Function to search products using image embeddings"
    
    start_idx = sql_content.find(start_marker)
    end_idx = sql_content.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        print("❌ Could not find keyword search function in SQL file")
        return False
    
    keyword_search_sql = sql_content[start_idx:end_idx].strip()
    
    # Execute the SQL
    try:
        print("📝 Executing SQL to create keyword_search_products function...")
        
        # Use raw SQL execution via RPC
        # Note: Supabase Python client doesn't have direct SQL execution
        # We'll need to use the REST API or execute via psycopg2
        
        print("⚠️  Manual deployment required:")
        print("\n" + "="*80)
        print("Please execute the following SQL in your Supabase SQL Editor:")
        print("="*80)
        print(keyword_search_sql)
        print("="*80)
        print("\nSteps:")
        print("1. Go to your Supabase Dashboard")
        print("2. Navigate to SQL Editor")
        print("3. Copy and paste the SQL above")
        print("4. Click 'Run'")
        print("\n✅ After running the SQL, the keyword search will be available!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error deploying function: {e}")
        return False

if __name__ == "__main__":
    deploy_keyword_search()