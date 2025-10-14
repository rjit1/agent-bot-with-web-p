"""
Database Setup Script for Gurtoy Telegram Bot
This script sets up the Supabase database and loads knowledge data with embeddings.
"""
from __future__ import annotations

import os
import json
import asyncio
from typing import List, Dict, Any

import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_database():
    """Set up the database with knowledge data and embeddings."""
    
    # Check environment variables
    required_vars = ["GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please create a .env file based on .env.example and fill in the values.")
        return False
    
    # Initialize clients
    print("🔧 Initializing clients...")
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    supabase = create_client(
        os.getenv("SUPABASE_URL"), 
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    
    # Test connections
    print("🔍 Testing connections...")
    try:
        # Test Gemini with configured embedding model
        embedding_model = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
        embedding_dimensionality = int(os.getenv("EMBEDDING_DIMENSIONALITY", "768"))
        embed_params = {
            "model": embedding_model,
            "content": "test"
        }
        
        # Add dimensional reduction if needed (only for embedding-001)
        if embedding_model == "models/embedding-001" and embedding_dimensionality != 3072:
            embed_params["output_dimensionality"] = embedding_dimensionality
            
        test_embedding = genai.embed_content(**embed_params)
        print("✅ Gemini API connection successful")
        
        # Test Supabase
        result = supabase.table("gurtoy_knowledge").select("count").limit(1).execute()
        print("✅ Supabase connection successful")
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False
    
    # Load knowledge data
    print("📚 Loading knowledge data...")
    try:
        with open("gurtoy_knowledge_data.json", "r", encoding="utf-8") as f:
            knowledge_data = json.load(f)
        print(f"✅ Loaded {len(knowledge_data)} knowledge chunks")
    except FileNotFoundError:
        print("❌ Knowledge data file not found. Please run knowledge_preparation.py first.")
        return False
    except Exception as e:
        print(f"❌ Error loading knowledge data: {e}")
        return False
    
    # Generate embeddings and prepare data
    print("🧠 Generating embeddings...")
    upsert_data = []
    
    for i, chunk in enumerate(knowledge_data):
        try:
            print(f"  Processing chunk {i+1}/{len(knowledge_data)}: {chunk['title']}")
            
            # Generate embedding with configured model
            embedding_model = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
            embedding_dimensionality = int(os.getenv("EMBEDDING_DIMENSIONALITY", "768"))
            embed_params = {
                "model": embedding_model,
                "content": chunk["content"]
            }
            
            # Add dimensional reduction if needed (only for embedding-001)
            if embedding_model == "models/embedding-001" and embedding_dimensionality != 3072:
                embed_params["output_dimensionality"] = embedding_dimensionality
                
            embedding = genai.embed_content(**embed_params)
            
            # Prepare data for upsert
            upsert_data.append({
                "chunk_id": chunk["chunk_id"],
                "title": chunk["title"],
                "content": chunk["content"],
                "category": chunk["category"],
                "keywords": chunk["keywords"],
                "priority": chunk["priority"],
                "language": chunk["language"],
                "metadata": chunk["metadata"],
                "embedding": embedding["embedding"]
            })
            
        except Exception as e:
            print(f"❌ Error processing chunk {chunk['chunk_id']}: {e}")
            continue
    
    if not upsert_data:
        print("❌ No data to insert")
        return False
    
    # Insert data into Supabase
    print("💾 Storing data in Supabase...")
    try:
        # Clear existing data (optional)
        print("  Clearing existing knowledge data...")
        supabase.table("gurtoy_knowledge").delete().neq("chunk_id", "").execute()
        
        # Insert new data
        print(f"  Inserting {len(upsert_data)} chunks...")
        response = supabase.table("gurtoy_knowledge").insert(upsert_data).execute()
        
        print(f"✅ Successfully stored {len(response.data)} knowledge chunks")
        
    except Exception as e:
        print(f"❌ Error storing data in Supabase: {e}")
        return False
    
    # Test vector search
    print("🔍 Testing vector search...")
    try:
        test_query = "What toys do you sell?"
        embedding_model = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
        embedding_dimensionality = int(os.getenv("EMBEDDING_DIMENSIONALITY", "768"))
        embed_params = {
            "model": embedding_model,
            "content": test_query
        }
        
        # Add dimensional reduction if needed (only for embedding-001)
        if embedding_model == "models/embedding-001" and embedding_dimensionality != 3072:
            embed_params["output_dimensionality"] = embedding_dimensionality
            
        test_embedding = genai.embed_content(**embed_params)
        
        search_result = supabase.rpc(
            "search_knowledge",
            {
                "query_embedding": test_embedding["embedding"],
                "match_threshold": 0.5,
                "match_count": 3
            }
        ).execute()
        
        if search_result.data:
            print(f"✅ Vector search working! Found {len(search_result.data)} results for test query")
            print(f"  Top result: {search_result.data[0]['title']}")
        else:
            print("⚠️ Vector search returned no results")
            
    except Exception as e:
        print(f"❌ Error testing vector search: {e}")
        return False
    
    print("\n🎉 Database setup completed successfully!")
    print("\nNext steps:")
    print("1. Set up your Telegram bot token in the .env file")
    print("2. Run the bot: python gurtoy_bot.py")
    print("3. Set up webhook URL for production deployment")
    
    return True

def verify_setup():
    """Verify the database setup."""
    print("🔍 Verifying database setup...")
    
    try:
        supabase = create_client(
            os.getenv("SUPABASE_URL"), 
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )
        
        # Check knowledge base
        result = supabase.table("gurtoy_knowledge").select("chunk_id, title, category").execute()
        knowledge_count = len(result.data)
        
        print(f"📚 Knowledge base: {knowledge_count} chunks")
        
        # Group by category
        categories = {}
        for item in result.data:
            category = item["category"]
            categories[category] = categories.get(category, 0) + 1
        
        for category, count in categories.items():
            print(f"  - {category}: {count} chunks")
        
        # Check tables exist
        tables_to_check = ["users", "sessions", "conversation_logs", "sentiment_tags", "handoff_requests"]
        
        for table in tables_to_check:
            try:
                supabase.table(table).select("count").limit(1).execute()
                print(f"✅ Table '{table}' exists")
            except Exception as e:
                print(f"❌ Table '{table}' missing or inaccessible: {e}")
        
        print("✅ Database verification completed")
        return True
        
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False

def main():
    """Main function."""
    print("🚀 Gurtoy Bot Database Setup")
    print("=" * 40)
    
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        verify_setup()
    else:
        success = setup_database()
        if success:
            verify_setup()

if __name__ == "__main__":
    main()