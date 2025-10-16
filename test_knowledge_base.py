#!/usr/bin/env python3
"""
Test Fashion Mart Knowledge Base
"""

import os
import json
from supabase import create_client
from dotenv import load_dotenv

def test_knowledge_base():
    """Test the updated knowledge base."""
    
    load_dotenv()
    
    # Initialize Supabase client
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print('❌ Missing Supabase credentials')
        return False
    
    supabase = create_client(supabase_url, supabase_key)
    
    print('🔍 Testing Fashion Mart Knowledge Base...')
    try:
        # Check knowledge base
        result = supabase.table('gurtoy_knowledge').select('chunk_id, title, category, content').execute()
        
        if result.data:
            print(f'✅ Found {len(result.data)} knowledge chunks')
            
            # Check for fashion content
            fashion_chunks = [chunk for chunk in result.data if 'fashion' in chunk.get('content', '').lower()]
            toy_chunks = [chunk for chunk in result.data if 'toy' in chunk.get('content', '').lower()]
            
            print(f'📊 Fashion-related chunks: {len(fashion_chunks)}')
            print(f'📊 Toy-related chunks: {len(toy_chunks)}')
            
            # Group by category
            categories = {}
            for item in result.data:
                category = item.get('category', 'Unknown')
                categories[category] = categories.get(category, 0) + 1
            
            print('\n📊 Knowledge Categories:')
            for category, count in sorted(categories.items()):
                print(f'  - {category}: {count} chunks')
            
            # Show sample chunks
            print('\n📋 Sample Knowledge Chunks:')
            for i, chunk in enumerate(result.data[:3]):
                title = chunk.get('title', 'Unknown')
                content = chunk.get('content', '')[:100] + '...' if len(chunk.get('content', '')) > 100 else chunk.get('content', '')
                print(f'\n{i+1}. {title}')
                print(f'   Content: {content}')
            
            # Test if fashion content is present
            if len(fashion_chunks) > 0:
                print('\n✅ Fashion Mart knowledge base is active!')
                return True
            else:
                print('\n⚠️ Fashion content not found - may need to run setup_database.py')
                return False
                
        else:
            print('❌ No knowledge chunks found')
            return False
            
    except Exception as e:
        print(f'❌ Error testing knowledge base: {e}')
        return False

if __name__ == '__main__':
    test_knowledge_base()
