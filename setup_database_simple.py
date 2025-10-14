#!/usr/bin/env python3
"""
Simplified database setup using REST API and direct SQL execution
"""
import os
import json
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from knowledge_data import get_knowledge_chunks

# Load environment variables
load_dotenv()

def setup_supabase_client():
    """Setup Supabase connection details."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials")
    
    return supabase_url, supabase_key

def setup_gemini():
    """Setup Gemini AI client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing Gemini API key")
    
    genai.configure(api_key=api_key)
    return api_key

def generate_embedding(text, model_name):
    """Generate embedding for text using Gemini."""
    try:
        # Use the configured embedding model
        embedding_response = genai.embed_content(
            model=model_name,
            content=text
        )
        
        embedding = embedding_response['embedding']
        
        # Apply dimensional reduction only for the old embedding-001 model
        if model_name == "models/embedding-001":
            # Reduce from 768 to target dimensions if needed
            target_dim = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
            if len(embedding) > target_dim:
                embedding = embedding[:target_dim]
        
        return embedding
        
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def insert_knowledge_chunk(supabase_url, supabase_key, chunk_data):
    """Insert or update a knowledge chunk in the database."""
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal"
    }
    
    # Try to update first
    chunk_id = chunk_data["chunk_id"]
    update_response = requests.patch(
        f"{supabase_url}/rest/v1/gurtoy_knowledge?chunk_id=eq.{chunk_id}",
        headers=headers,
        json=chunk_data
    )
    
    if update_response.status_code in [200, 201, 204]:
        return True
    
    # If update fails, try insert
    response = requests.post(
        f"{supabase_url}/rest/v1/gurtoy_knowledge",
        headers=headers,
        json=chunk_data
    )
    
    if response.status_code not in [200, 201]:
        print(f"   Error: {response.status_code} - {response.text[:200]}")
    
    return response.status_code in [200, 201]

def main():
    """Main setup function."""
    print("🚀 Setting up Gurtoy Knowledge Database")
    print("=" * 60)
    
    try:
        # Setup clients
        supabase_url, supabase_key = setup_supabase_client()
        setup_gemini()
        
        # Get configuration
        embedding_model = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
        print(f"📊 Using embedding model: {embedding_model}")
        
        # Load knowledge data
        print("📚 Loading knowledge data...")
        knowledge_chunks = get_knowledge_chunks()
        print(f"✅ Loaded {len(knowledge_chunks)} knowledge chunks")
        
        # Process and insert chunks
        print("🔄 Processing and inserting chunks...")
        success_count = 0
        
        for i, chunk in enumerate(knowledge_chunks, 1):
            print(f"Processing chunk {i}/{len(knowledge_chunks)}: {chunk['title'][:50]}...")
            
            # Generate embedding
            content_for_embedding = f"{chunk['title']} {chunk['content']}"
            embedding = generate_embedding(content_for_embedding, embedding_model)
            
            if embedding is None:
                print(f"❌ Failed to generate embedding for chunk {i}")
                continue
            
            # Prepare chunk data
            chunk_data = {
                "chunk_id": chunk["chunk_id"],
                "title": chunk["title"],
                "content": chunk["content"],
                "category": chunk["category"],
                "keywords": chunk["keywords"],
                "priority": chunk["priority"],
                "embedding": embedding
            }
            
            # Insert into database
            if insert_knowledge_chunk(supabase_url, supabase_key, chunk_data):
                success_count += 1
                print(f"✅ Inserted chunk {i}")
            else:
                print(f"❌ Failed to insert chunk {i}")
        
        print("\n" + "=" * 60)
        print(f"🎉 Database setup complete!")
        print(f"✅ Successfully inserted {success_count}/{len(knowledge_chunks)} chunks")
        
        if success_count == len(knowledge_chunks):
            print("🚀 Ready to start the Telegram bot!")
        else:
            print("⚠️  Some chunks failed to insert. Check the logs above.")
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()