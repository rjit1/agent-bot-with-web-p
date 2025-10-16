#!/usr/bin/env python3
"""
Generate Text Embeddings for Fashion Mart Products
This script generates text embeddings for all products in the database
by combining their existing text fields.
"""

import os
import logging
from typing import Dict, Any, List
from supabase import create_client, Client
from dotenv import load_dotenv
import google.generativeai as genai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def generate_text_embedding(text: str) -> List[float]:
    """Generate embedding for text using Gemini embedding model."""
    try:
        embedding_model = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
        
        result = genai.embed_content(
            content=text,
            task_type="retrieval_document",
            model=embedding_model
        )
        
        return result['embedding']
    
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None

def generate_product_embedding(product: Dict[str, Any]) -> List[float]:
    """Generate embedding for a product by combining multiple fields."""
    
    # Combine multiple fields for better semantic search
    embedding_text_parts = [
        f"Title: {product['title']}",
        f"Category: {product['category']}",
        f"Description: {product['description']}"
    ]
    
    # Add size range if available
    if product.get('size_range'):
        embedding_text_parts.append(f"Size Range: {product['size_range']}")
    
    # Add colors if available
    if product.get('colors') and product['colors']:
        if isinstance(product['colors'], list):
            colors_str = ', '.join(product['colors'])
        else:
            colors_str = str(product['colors'])
        embedding_text_parts.append(f"Colors: {colors_str}")
    
    # Add specifications if available
    if product.get('specifications') and product['specifications']:
        specs = product['specifications']
        if isinstance(specs, dict):
            if 'material' in specs:
                embedding_text_parts.append(f"Material: {specs['material']}")
            if 'care_instructions' in specs:
                embedding_text_parts.append(f"Care Instructions: {specs['care_instructions']}")
            if 'features' in specs:
                if isinstance(specs['features'], list):
                    features_str = ', '.join(specs['features'])
                else:
                    features_str = str(specs['features'])
                embedding_text_parts.append(f"Features: {features_str}")
    
    embedding_text = " | ".join(embedding_text_parts)
    
    logger.debug(f"Generating embedding for: {product['product_id']} - {product['title']}")
    logger.debug(f"Embedding text: {embedding_text[:100]}...")
    
    return generate_text_embedding(embedding_text)

def generate_embeddings_for_all_products():
    """Generate text embeddings for all products in the database."""
    
    # Supabase setup
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("❌ Missing Supabase credentials in environment variables")
        return
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Gemini setup
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.error("❌ Missing GEMINI_API_KEY in environment variables")
        return
    
    genai.configure(api_key=gemini_api_key)
    
    try:
        logger.info("🔍 Checking database connection...")
        
        # Fetch all products that don't have embeddings yet
        response = supabase.table("products").select(
            "product_id, title, category, description, size_range, colors, specifications"
        ).is_("embedding", "null").execute()
        
        products = response.data
        logger.info(f"✅ Found {len(products)} products without text embeddings")
        
        if not products:
            logger.info("✅ All products already have text embeddings!")
            return
        
        # Process each product
        successful = 0
        failed = 0
        
        for i, product in enumerate(products, 1):
            logger.info(f"📝 Processing product {i}/{len(products)}: {product['product_id']} - {product['title']}")
            
            try:
                # Generate embedding
                embedding = generate_product_embedding(product)
                
                if embedding:
                    # Update product with embedding
                    update_response = supabase.table("products").update({
                        "embedding": embedding
                    }).eq("product_id", product["product_id"]).execute()
                    
                    if update_response.data:
                        logger.info(f"   ✅ Successfully updated embedding for {product['product_id']}")
                        successful += 1
                    else:
                        logger.error(f"   ❌ Failed to update database for {product['product_id']}")
                        failed += 1
                else:
                    logger.error(f"   ❌ Failed to generate embedding for {product['product_id']}")
                    failed += 1
                    
            except Exception as e:
                logger.error(f"   ❌ Error processing {product['product_id']}: {e}")
                failed += 1
        
        # Summary
        logger.info(f"\n📊 EMBEDDING GENERATION SUMMARY:")
        logger.info(f"Total Products: {len(products)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Success Rate: {(successful/len(products)*100):.1f}%")
        
        if successful > 0:
            logger.info("✅ Text embeddings generation completed!")
        else:
            logger.error("❌ No embeddings were generated successfully")
        
    except Exception as e:
        logger.error(f"❌ Error generating embeddings: {e}")

if __name__ == "__main__":
    generate_embeddings_for_all_products()
