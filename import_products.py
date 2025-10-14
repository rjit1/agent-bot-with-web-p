"""
Product Import Script for Gurtoy Telegram Bot
This script imports product data with embeddings into Supabase.
"""
from __future__ import annotations

import os
import csv
import json
import time
from typing import List, Dict, Any

import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def load_product_data(csv_file: str = "product_data_transformed.csv") -> List[Dict[str, Any]]:
    """Load product data from CSV file."""
    products = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse JSON fields
                try:
                    colors = json.loads(row['colors']) if row['colors'] else []
                except json.JSONDecodeError:
                    colors = []
                
                try:
                    specifications = json.loads(row['specifications']) if row['specifications'] else {}
                except json.JSONDecodeError:
                    specifications = {}
                
                try:
                    images = json.loads(row['images']) if row['images'] else []
                except json.JSONDecodeError:
                    images = []
                
                product = {
                    'product_id': row['product_id'],
                    'title': row['title'],
                    'category': row['category'],
                    'description': row['description'],
                    'age_range': row['age_range'],
                    'colors': colors,
                    'specifications': specifications,
                    'images': images,
                    'price': float(row['price']),
                    'discount_price': float(row['discount_price']),
                    'stock_status': row['stock_status'],
                    'warranty': row['warranty']
                }
                products.append(product)
        
        return products
    
    except FileNotFoundError:
        print(f"❌ Error: {csv_file} not found")
        return []
    except Exception as e:
        print(f"❌ Error loading product data: {e}")
        return []

def generate_product_embedding(product: Dict[str, Any]) -> List[float]:
    """Generate embedding for a product by combining multiple fields."""
    
    # Combine multiple fields for better semantic search
    embedding_text_parts = [
        f"Title: {product['title']}",
        f"Category: {product['category']}",
        f"Description: {product['description']}",
        f"Age Range: {product['age_range']}"
    ]
    
    # Add colors if available
    if product['colors']:
        colors_str = ', '.join(product['colors'])
        embedding_text_parts.append(f"Colors: {colors_str}")
    
    # Add specifications if available
    if product['specifications']:
        specs = product['specifications']
        if 'battery' in specs:
            embedding_text_parts.append(f"Battery: {specs['battery']}")
        if 'features' in specs:
            features_str = ', '.join(specs['features'])
            embedding_text_parts.append(f"Features: {features_str}")
    
    embedding_text = " | ".join(embedding_text_parts)
    
    # Generate embedding
    embedding_model = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
    embedding_dimensionality = int(os.getenv("EMBEDDING_DIMENSIONALITY", "768"))
    
    embed_params = {
        "model": embedding_model,
        "content": embedding_text,
        "task_type": "retrieval_document"
    }
    
    # Add dimensional reduction for both embedding-001 and text-embedding-004
    if embedding_model == "models/embedding-001" and embedding_dimensionality != 3072:
        embed_params["output_dimensionality"] = embedding_dimensionality
    elif embedding_model == "models/text-embedding-004":
        # text-embedding-004 supports output_dimensionality parameter
        embed_params["output_dimensionality"] = embedding_dimensionality
    
    result = genai.embed_content(**embed_params)
    return result["embedding"]

def import_products():
    """Import products with embeddings into Supabase."""
    
    print("🚀 Gurtoy Product Import Script")
    print("=" * 50)
    
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
        # Test Gemini
        embedding_model = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
        embedding_dimensionality = int(os.getenv("EMBEDDING_DIMENSIONALITY", "768"))
        embed_params = {
            "model": embedding_model,
            "content": "test",
            "task_type": "retrieval_document"
        }
        
        if embedding_model == "models/embedding-001" and embedding_dimensionality != 3072:
            embed_params["output_dimensionality"] = embedding_dimensionality
        elif embedding_model == "models/text-embedding-004":
            embed_params["output_dimensionality"] = embedding_dimensionality
            
        test_embedding = genai.embed_content(**embed_params)
        print(f"✅ Gemini API connection successful (Model: {embedding_model}, Dimensions: {len(test_embedding['embedding'])})")
        
        # Test Supabase
        result = supabase.table("products").select("count").limit(1).execute()
        print("✅ Supabase connection successful")
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False
    
    # Load product data
    print("\n📦 Loading product data...")
    products = load_product_data()
    
    if not products:
        print("❌ No products to import")
        return False
    
    print(f"✅ Loaded {len(products)} products")
    
    # Count products by category
    categories = {}
    for product in products:
        category = product['category']
        categories[category] = categories.get(category, 0) + 1
    
    print("\n📊 Products by category:")
    for category, count in categories.items():
        print(f"  - {category}: {count} products")
    
    # Generate embeddings and prepare data
    print("\n🧠 Generating embeddings...")
    import_data = []
    
    for i, product in enumerate(products):
        try:
            print(f"  [{i+1}/{len(products)}] Processing: {product['title']}")
            
            # Generate embedding
            embedding = generate_product_embedding(product)
            
            # Prepare data for import
            import_data.append({
                "product_id": product['product_id'],
                "title": product['title'],
                "category": product['category'],
                "description": product['description'],
                "age_range": product['age_range'],
                "colors": json.dumps(product['colors']),
                "specifications": json.dumps(product['specifications']),
                "images": json.dumps(product['images']),
                "price": product['price'],
                "discount_price": product['discount_price'],
                "stock_status": product['stock_status'],
                "warranty": product['warranty'],
                "embedding": embedding
            })
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"❌ Error processing product {product['product_id']}: {e}")
            continue
    
    if not import_data:
        print("❌ No data to import")
        return False
    
    print(f"\n✅ Generated embeddings for {len(import_data)} products")
    
    # Import data into Supabase
    print("\n💾 Importing products into Supabase...")
    try:
        # Clear existing products (optional)
        print("  Clearing existing products...")
        supabase.table("products").delete().neq("product_id", "").execute()
        
        # Insert new products
        print(f"  Inserting {len(import_data)} products...")
        response = supabase.table("products").insert(import_data).execute()
        
        print(f"✅ Successfully imported {len(response.data)} products")
        
    except Exception as e:
        print(f"❌ Error importing products: {e}")
        return False
    
    # Test vector search
    print("\n🔍 Testing product search...")
    try:
        test_queries = [
            "red jeep for 4 year old",
            "bike with lights and music",
            "police style toys"
        ]
        
        for query in test_queries:
            print(f"\n  Query: '{query}'")
            
            # Generate query embedding
            embed_params = {
                "model": embedding_model,
                "content": query
            }
            
            if embedding_model == "models/embedding-001" and embedding_dimensionality != 3072:
                embed_params["output_dimensionality"] = embedding_dimensionality
                
            query_embedding = genai.embed_content(**embed_params)
            
            # Search products
            search_result = supabase.rpc(
                "search_products",
                {
                    "query_embedding": query_embedding["embedding"],
                    "match_threshold": 0.5,
                    "match_count": 3
                }
            ).execute()
            
            if search_result.data:
                print(f"  ✅ Found {len(search_result.data)} results:")
                for i, product in enumerate(search_result.data[:3]):
                    print(f"    {i+1}. {product['title']} (Similarity: {product['similarity']:.2f})")
            else:
                print("  ⚠️ No results found")
        
    except Exception as e:
        print(f"❌ Error testing search: {e}")
        return False
    
    print("\n🎉 Product import completed successfully!")
    print("\n📊 Summary:")
    print(f"  - Total products: {len(import_data)}")
    print(f"  - Categories: {len(categories)}")
    print(f"  - Embedding model: {embedding_model}")
    print(f"  - Embedding dimensions: {embedding_dimensionality}")
    
    print("\n✅ Next steps:")
    print("  1. Update gurtoy_bot.py to add product search function")
    print("  2. Test product search in Telegram bot")
    print("  3. Monitor search quality and adjust thresholds")
    
    return True

def verify_import():
    """Verify the product import."""
    print("🔍 Verifying product import...")
    
    try:
        supabase = create_client(
            os.getenv("SUPABASE_URL"), 
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )
        
        # Check products
        result = supabase.table("products").select("product_id, title, category, price, stock_status").execute()
        product_count = len(result.data)
        
        print(f"📦 Products: {product_count} total")
        
        # Group by category
        categories = {}
        for item in result.data:
            category = item["category"]
            categories[category] = categories.get(category, 0) + 1
        
        print("\n📊 Products by category:")
        for category, count in categories.items():
            print(f"  - {category}: {count} products")
        
        # Check stock status
        stock_counts = {}
        for item in result.data:
            status = item["stock_status"]
            stock_counts[status] = stock_counts.get(status, 0) + 1
        
        print("\n📦 Stock status:")
        for status, count in stock_counts.items():
            print(f"  - {status}: {count} products")
        
        # Show sample products
        print("\n📋 Sample products:")
        for i, product in enumerate(result.data[:5]):
            print(f"  {i+1}. {product['title']}")
            print(f"     ID: {product['product_id']}")
            print(f"     Category: {product['category']}")
            print(f"     Price: ₹{product['price']}")
            print()
        
        print("✅ Product verification completed")
        return True
        
    except Exception as e:
        print(f"❌ Product verification failed: {e}")
        return False

def main():
    """Main function."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        verify_import()
    else:
        success = import_products()
        if success:
            print("\n" + "=" * 50)
            verify_import()

if __name__ == "__main__":
    main()