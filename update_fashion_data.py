#!/usr/bin/env python3
"""
Phase 2: Update Product Data for Fashion Mart
This script updates all products with fashion-specific data
"""

import os
import json
from supabase import create_client
from dotenv import load_dotenv

def get_fashion_sizes_and_colors():
    """Get size and color mappings for different fashion categories."""
    return {
        "Cardigan": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Navy", "Gray", "Brown", "Pink", "Red", "Blue"]
        },
        "Long cardigan": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Navy", "Gray", "Brown", "Pink", "Red", "Blue"]
        },
        "Crop top": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Pink", "Red", "Blue", "Green", "Yellow", "Purple"]
        },
        "Shrug": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Navy", "Gray", "Brown", "Pink", "Red", "Blue"]
        },
        "Cardigan ": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Navy", "Gray", "Brown", "Pink", "Red", "Blue"]
        },
        "High neck top": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Pink", "Red", "Blue", "Green", "Yellow", "Purple"]
        },
        "Tunic": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Navy", "Gray", "Brown", "Pink", "Red", "Blue", "Green"]
        },
        "High neck crop": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Pink", "Red", "Blue", "Green", "Yellow", "Purple"]
        },
        "Court set": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Navy", "Gray", "Brown", "Pink", "Red", "Blue"]
        },
        "V neck crop top": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Pink", "Red", "Blue", "Green", "Yellow", "Purple"]
        },
        "SL cardigan": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Navy", "Gray", "Brown", "Pink", "Red", "Blue"]
        },
        "SL Cardigan": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Navy", "Gray", "Brown", "Pink", "Red", "Blue"]
        },
        "SL Cardigan ": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Navy", "Gray", "Brown", "Pink", "Red", "Blue"]
        },
        "Kot": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Navy", "Gray", "Brown", "Pink", "Red", "Blue", "Green", "Yellow"]
        },
        "Extra long kot": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Navy", "Gray", "Brown", "Pink", "Red", "Blue", "Green", "Yellow"]
        },
        "Cardigan crop": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Navy", "Gray", "Brown", "Pink", "Red", "Blue"]
        },
        "Self cardigan ": {
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "White", "Navy", "Gray", "Brown", "Pink", "Red", "Blue"]
        }
    }

def update_fashion_data():
    """Update all products with fashion-specific data."""
    
    load_dotenv()
    
    # Initialize Supabase client
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print('❌ Missing Supabase credentials')
        return False
    
    supabase = create_client(supabase_url, supabase_key)
    
    print('🚀 Starting Fashion Product Data Update...')
    
    # Get size and color mappings
    fashion_data = get_fashion_sizes_and_colors()
    
    try:
        # Get all products
        result = supabase.table('products').select('id, product_id, title, category, colors, specifications, age_range').execute()
        
        if not result.data:
            print('❌ No products found')
            return False
        
        print(f'📊 Found {len(result.data)} products to update')
        
        updated_count = 0
        
        for product in result.data:
            product_id = product['product_id']
            category = product['category']
            current_colors = product.get('colors', [])
            current_specs = product.get('specifications', {})
            current_age_range = product.get('age_range', '')
            
            # Get category-specific data
            category_data = fashion_data.get(category, {
                "sizes": ["S", "M", "L", "XL"],
                "colors": ["Black", "White", "Navy", "Gray", "Brown", "Pink", "Red", "Blue"]
            })
            
            # Update colors if empty
            if not current_colors:
                colors = category_data["colors"][:4]  # Take first 4 colors
            else:
                colors = current_colors
            
            # Update specifications with sizes and material info
            updated_specs = current_specs.copy()
            updated_specs["sizes"] = category_data["sizes"]
            
            # Add material information based on category
            if "cardigan" in category.lower():
                updated_specs["material"] = "Wool/Cotton blend"
                updated_specs["care"] = "Machine wash cold, lay flat to dry"
            elif "top" in category.lower() or "crop" in category.lower():
                updated_specs["material"] = "Cotton/Polyester blend"
                updated_specs["care"] = "Machine wash warm, tumble dry low"
            elif "kot" in category.lower():
                updated_specs["material"] = "Cotton/Synthetic blend"
                updated_specs["care"] = "Machine wash cold, gentle cycle"
            else:
                updated_specs["material"] = "Mixed materials"
                updated_specs["care"] = "Check individual product label"
            
            # Update age_range with sizes (we'll rename the column later)
            size_range = ', '.join(category_data["sizes"])
            
            # Update the product
            update_result = supabase.table('products').update({
                'colors': colors,
                'specifications': updated_specs,
                'age_range': size_range  # Temporarily use age_range for sizes
            }).eq('product_id', product_id).execute()
            
            if update_result.data:
                updated_count += 1
                print(f'✅ Updated {product_id}: {product["title"]} - Sizes: {category_data["sizes"]}, Colors: {colors[:3]}...')
            else:
                print(f'⚠️ Failed to update {product_id}: {product["title"]}')
        
        print(f'\n🎉 Successfully updated {updated_count}/{len(result.data)} products')
        
        # Verify the updates
        print('\n🔍 Verifying updates...')
        verify_result = supabase.table('products').select('product_id, title, category, age_range, colors, specifications').execute()
        
        if verify_result.data:
            print(f'📊 Verification: {len(verify_result.data)} products verified')
            
            # Show sample updated products
            print('\n📋 Sample Updated Products:')
            for i, product in enumerate(verify_result.data[:5]):
                print(f'\n{i+1}. {product["title"]} ({product["product_id"]})')
                print(f'   Category: {product["category"]}')
                print(f'   Sizes: {product.get("age_range", "N/A")}')
                print(f'   Colors: {product.get("colors", [])}')
                specs = product.get("specifications", {})
                if "material" in specs:
                    print(f'   Material: {specs["material"]}')
        
        return True
        
    except Exception as e:
        print(f'❌ Error updating products: {e}')
        return False

if __name__ == '__main__':
    update_fashion_data()
