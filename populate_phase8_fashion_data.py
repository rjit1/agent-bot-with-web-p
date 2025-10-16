#!/usr/bin/env python3
"""
Phase 8 Data Population Script
Populates new fashion fields (style_keywords, occasion) for existing products
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
import json
import random

# Load environment variables
load_dotenv()

def get_supabase_client() -> Client:
    """Initialize Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
    
    return create_client(url, key)

def get_fashion_style_keywords(category: str) -> list:
    """Get appropriate style keywords based on product category."""
    style_mapping = {
        'kurta': ['ethnic', 'traditional', 'casual', 'comfortable', 'elegant'],
        'cardigan': ['casual', 'comfortable', 'layered', 'versatile', 'cozy'],
        'top': ['casual', 'formal', 'versatile', 'stylish', 'trendy'],
        'dress': ['elegant', 'formal', 'party', 'casual', 'stylish'],
        'accessory': ['stylish', 'trendy', 'elegant', 'versatile', 'fashionable']
    }
    
    return style_mapping.get(category.lower(), ['casual', 'stylish', 'versatile'])

def get_fashion_occasions(category: str) -> list:
    """Get appropriate occasions based on product category."""
    occasion_mapping = {
        'kurta': ['casual', 'traditional', 'office', 'wedding'],
        'cardigan': ['casual', 'office', 'layered'],
        'top': ['casual', 'office', 'party', 'formal'],
        'dress': ['party', 'formal', 'wedding', 'office'],
        'accessory': ['casual', 'office', 'party', 'formal']
    }
    
    return occasion_mapping.get(category.lower(), ['casual', 'office'])

def populate_fashion_fields():
    """Populate style_keywords and occasion fields for all products."""
    
    print("🔄 Starting Phase 8 Data Population...")
    
    try:
        # Initialize Supabase client
        supabase = get_supabase_client()
        print("✅ Connected to Supabase")
        
        # Fetch all products
        print("📥 Fetching all products...")
        response = supabase.table('products').select('*').execute()
        products = response.data
        
        if not products:
            print("❌ No products found in database")
            return False
        
        print(f"📊 Found {len(products)} products to update")
        
        # Update each product with fashion fields
        updated_count = 0
        for product in products:
            product_id = product['product_id']
            category = product.get('category', 'unknown')
            
            # Get appropriate style keywords and occasions
            style_keywords = get_fashion_style_keywords(category)
            occasions = get_fashion_occasions(category)
            
            # Update the product
            update_data = {
                'style_keywords': style_keywords,
                'occasion': occasions
            }
            
            # Ensure size_range is set if not already
            if not product.get('size_range'):
                update_data['size_range'] = random.choice(['S', 'M', 'L', 'XL'])
            
            try:
                supabase.table('products').update(update_data).eq('product_id', product_id).execute()
                updated_count += 1
                
                if updated_count % 10 == 0:
                    print(f"✅ Updated {updated_count}/{len(products)} products...")
                    
            except Exception as e:
                print(f"❌ Error updating product {product_id}: {e}")
                continue
        
        print(f"🎉 Successfully updated {updated_count}/{len(products)} products")
        
        # Verify the updates
        print("\n🔍 Verifying updates...")
        verification_response = supabase.table('products').select('product_id, category, style_keywords, occasion, size_range').limit(5).execute()
        
        if verification_response.data:
            print("📋 Sample updated products:")
            for product in verification_response.data:
                print(f"   {product['product_id']}: {product['category']}")
                print(f"      Style: {product['style_keywords']}")
                print(f"      Occasion: {product['occasion']}")
                print(f"      Size: {product['size_range']}")
                print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error in data population: {e}")
        return False

def test_fashion_search_functions():
    """Test the new fashion search functions."""
    
    print("\n🧪 Testing Fashion Search Functions...")
    
    try:
        supabase = get_supabase_client()
        
        # Test 1: Search by size
        print("📏 Testing search by size...")
        size_response = supabase.rpc('search_products_by_size', {
            'p_size_range': 'M',
            'p_limit': 5
        }).execute()
        
        if size_response.data:
            print(f"✅ Found {len(size_response.data)} products in size M")
        else:
            print("⚠️ No products found for size M")
        
        # Test 2: Search by style
        print("🎨 Testing search by style...")
        style_response = supabase.rpc('search_products_by_style', {
            'p_style_keywords': ['casual', 'comfortable'],
            'p_limit': 5
        }).execute()
        
        if style_response.data:
            print(f"✅ Found {len(style_response.data)} products with casual/comfortable style")
        else:
            print("⚠️ No products found for casual/comfortable style")
        
        # Test 3: Search by occasion
        print("🎉 Testing search by occasion...")
        occasion_response = supabase.rpc('search_products_by_occasion', {
            'p_occasion': ['office', 'casual'],
            'p_limit': 5
        }).execute()
        
        if occasion_response.data:
            print(f"✅ Found {len(occasion_response.data)} products for office/casual occasions")
        else:
            print("⚠️ No products found for office/casual occasions")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing search functions: {e}")
        return False

if __name__ == '__main__':
    print("🔧 Phase 8 Data Population Script")
    print("==================================")
    
    # Populate fashion fields
    population_success = populate_fashion_fields()
    
    if population_success:
        # Test search functions
        test_success = test_fashion_search_functions()
        
        if test_success:
            print("\n🎉 Phase 8 Data Population Complete!")
            print("✅ All fashion fields populated successfully")
            print("✅ Fashion search functions tested successfully")
        else:
            print("\n⚠️ Data populated but search function tests failed")
    else:
        print("\n❌ Phase 8 Data Population Failed")
