#!/usr/bin/env python3
"""
Check Product Data Status - Embeddings and Image Descriptions
This script checks the current status of:
1. Text embeddings (embedding column)
2. Image descriptions (ai_image_description column)
3. Image embeddings (image_embedding column)
4. Image metadata (ai_image_metadata column)
"""

import os
import logging
from typing import Dict, Any, List
from supabase import create_client, Client
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def check_product_data_status():
    """Check the status of embeddings and image descriptions for all products."""
    
    # Supabase setup
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("❌ Missing Supabase credentials in environment variables")
        return
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    try:
        logger.info("🔍 Checking database connection...")
        
        # Fetch all products with their embedding and image data
        response = supabase.table("products").select(
            "product_id, title, category, description, images, "
            "embedding, ai_image_description, ai_image_metadata, image_embedding"
        ).execute()
        
        products = response.data
        logger.info(f"✅ Found {len(products)} products in database")
        
        # Analyze the data
        total_products = len(products)
        products_with_images = 0
        products_with_text_embeddings = 0
        products_with_image_descriptions = 0
        products_with_image_embeddings = 0
        products_with_image_metadata = 0
        
        missing_text_embeddings = []
        missing_image_descriptions = []
        missing_image_embeddings = []
        
        logger.info("\n📊 Analyzing product data status...")
        
        for product in products:
            # Check if product has images
            if product.get('images') and len(product['images']) > 0:
                products_with_images += 1
            
            # Check text embeddings
            if product.get('embedding') is not None:
                products_with_text_embeddings += 1
            else:
                missing_text_embeddings.append({
                    'id': product['product_id'],
                    'title': product['title'],
                    'category': product['category']
                })
            
            # Check image descriptions
            if product.get('ai_image_description') and product['ai_image_description'].strip():
                products_with_image_descriptions += 1
            else:
                if product.get('images') and len(product['images']) > 0:
                    missing_image_descriptions.append({
                        'id': product['product_id'],
                        'title': product['title'],
                        'category': product['category'],
                        'has_images': True
                    })
            
            # Check image embeddings
            if product.get('image_embedding') is not None:
                products_with_image_embeddings += 1
            else:
                if product.get('images') and len(product['images']) > 0:
                    missing_image_embeddings.append({
                        'id': product['product_id'],
                        'title': product['title'],
                        'category': product['category'],
                        'has_images': True
                    })
            
            # Check image metadata
            if product.get('ai_image_metadata') and product['ai_image_metadata'] != {}:
                products_with_image_metadata += 1
        
        # Print summary
        logger.info(f"\n📈 PRODUCT DATA STATUS SUMMARY:")
        logger.info(f"Total Products: {total_products}")
        logger.info(f"Products with Images: {products_with_images}")
        logger.info(f"Products with Text Embeddings: {products_with_text_embeddings}")
        logger.info(f"Products with Image Descriptions: {products_with_image_descriptions}")
        logger.info(f"Products with Image Embeddings: {products_with_image_embeddings}")
        logger.info(f"Products with Image Metadata: {products_with_image_metadata}")
        
        # Calculate percentages
        text_embedding_percentage = (products_with_text_embeddings / total_products) * 100
        image_desc_percentage = (products_with_image_descriptions / products_with_images) * 100 if products_with_images > 0 else 0
        image_embedding_percentage = (products_with_image_embeddings / products_with_images) * 100 if products_with_images > 0 else 0
        
        logger.info(f"\n📊 COMPLETION PERCENTAGES:")
        logger.info(f"Text Embeddings: {text_embedding_percentage:.1f}% ({products_with_text_embeddings}/{total_products})")
        logger.info(f"Image Descriptions: {image_desc_percentage:.1f}% ({products_with_image_descriptions}/{products_with_images})")
        logger.info(f"Image Embeddings: {image_embedding_percentage:.1f}% ({products_with_image_embeddings}/{products_with_images})")
        
        # Show missing data
        if missing_text_embeddings:
            logger.info(f"\n❌ MISSING TEXT EMBEDDINGS ({len(missing_text_embeddings)} products):")
            for product in missing_text_embeddings[:10]:  # Show first 10
                logger.info(f"  - {product['id']}: {product['title']} ({product['category']})")
            if len(missing_text_embeddings) > 10:
                logger.info(f"  ... and {len(missing_text_embeddings) - 10} more")
        
        if missing_image_descriptions:
            logger.info(f"\n❌ MISSING IMAGE DESCRIPTIONS ({len(missing_image_descriptions)} products):")
            for product in missing_image_descriptions[:10]:  # Show first 10
                logger.info(f"  - {product['id']}: {product['title']} ({product['category']})")
            if len(missing_image_descriptions) > 10:
                logger.info(f"  ... and {len(missing_image_descriptions) - 10} more")
        
        if missing_image_embeddings:
            logger.info(f"\n❌ MISSING IMAGE EMBEDDINGS ({len(missing_image_embeddings)} products):")
            for product in missing_image_embeddings[:10]:  # Show first 10
                logger.info(f"  - {product['id']}: {product['title']} ({product['category']})")
            if len(missing_image_embeddings) > 10:
                logger.info(f"  ... and {len(missing_image_embeddings) - 10} more")
        
        # Recommendations
        logger.info(f"\n🎯 RECOMMENDATIONS:")
        if missing_text_embeddings:
            logger.info("1. Run import_products.py to generate text embeddings for all products")
        if missing_image_descriptions:
            logger.info("2. Run generate_product_image_descriptions.py to generate image descriptions")
        if missing_image_embeddings:
            logger.info("3. Image embeddings will be generated automatically with image descriptions")
        
        # Overall status
        if products_with_text_embeddings == total_products and products_with_image_descriptions == products_with_images:
            logger.info("\n✅ ALL PRODUCT DATA IS COMPLETE!")
        else:
            logger.info(f"\n⚠️  PRODUCT DATA NEEDS COMPLETION")
        
        return {
            'total_products': total_products,
            'products_with_images': products_with_images,
            'products_with_text_embeddings': products_with_text_embeddings,
            'products_with_image_descriptions': products_with_image_descriptions,
            'products_with_image_embeddings': products_with_image_embeddings,
            'missing_text_embeddings': missing_text_embeddings,
            'missing_image_descriptions': missing_image_descriptions,
            'missing_image_embeddings': missing_image_embeddings
        }
        
    except Exception as e:
        logger.error(f"❌ Error checking product data: {e}")
        return None

if __name__ == "__main__":
    check_product_data_status()
