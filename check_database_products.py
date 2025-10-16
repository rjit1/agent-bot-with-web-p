#!/usr/bin/env python3
"""
Database Product Checker
Check current products in Supabase database
"""

import os
import json
from supabase import create_client
from dotenv import load_dotenv

def check_database_products():
    """Check current products in the database"""
    
    # Load environment variables
    load_dotenv()
    
    # Initialize Supabase client
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print('❌ Missing Supabase credentials in .env file')
        return
    
    supabase = create_client(supabase_url, supabase_key)
    
    print('🔍 Checking database connection...')
    try:
        # Test connection
        result = supabase.table('products').select('count').limit(1).execute()
        print('✅ Database connection successful')
        
        # Get all products
        print('\n📦 Fetching all products from database...')
        products_result = supabase.table('products').select('*').execute()
        
        if products_result.data:
            print(f'✅ Found {len(products_result.data)} products in database')
            
            # Group by category
            categories = {}
            for product in products_result.data:
                category = product.get('category', 'Unknown')
                categories[category] = categories.get(category, 0) + 1
            
            print('\n📊 Products by Category:')
            for category, count in sorted(categories.items()):
                print(f'  - {category}: {count} products')
            
            # Show all products with details
            print('\n📋 Complete Product List:')
            for i, product in enumerate(products_result.data, 1):
                title = product.get('title', 'Unknown')
                product_id = product.get('product_id', 'N/A')
                category = product.get('category', 'N/A')
                price = product.get('price', 0)
                stock = product.get('stock_status', 'N/A')
                images = product.get('images', [])
                description = product.get('description', '')
                
                print(f'\n{i:2d}. {title}')
                print(f'     ID: {product_id}')
                print(f'     Category: {category}')
                print(f'     Price: ₹{price}')
                print(f'     Stock: {stock}')
                print(f'     Images: {len(images)} available')
                
                if images and len(images) > 0:
                    first_image = str(images[0]) if images[0] else 'No URL'
                    print(f'     First Image URL: {first_image}')
                
                if description:
                    print(f'     Description: {description[:100]}...')
            
            # Check for website pages or external URLs
            print('\n🌐 Checking for website pages...')
            website_products = []
            for product in products_result.data:
                images = product.get('images', [])
                if images:
                    for img_url in images:
                        if img_url and ('website' in str(img_url).lower() or 'page' in str(img_url).lower()):
                            website_products.append(product)
                            break
            
            if website_products:
                print(f'Found {len(website_products)} products with website references:')
                for product in website_products:
                    title = product.get('title', 'Unknown')
                    product_id = product.get('product_id', 'N/A')
                    print(f'  - {title} (ID: {product_id})')
            else:
                print('No products found with website page references')
                
            # Save detailed report
            print('\n💾 Saving detailed report...')
            report = {
                'total_products': len(products_result.data),
                'categories': categories,
                'products': products_result.data
            }
            
            with open('database_products_report.json', 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print('✅ Report saved to database_products_report.json')
                
        else:
            print('❌ No products found in database')
            
    except Exception as e:
        print(f'❌ Database error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_database_products()
