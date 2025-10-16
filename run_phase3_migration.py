#!/usr/bin/env python3
"""
Phase 3 Database Migration Executor
Executes the complete database migration for Fashion Mart
"""

import os
import sys
from supabase import create_client
from dotenv import load_dotenv

def execute_phase3_migration():
    """Execute the Phase 3 database migration."""
    
    print('🚀 Starting Phase 3 Database Migration...')
    
    # Load environment variables
    load_dotenv()
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env file")
        return False
    
    # Initialize Supabase client
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    
    try:
        # Read the SQL migration file
        with open('phase3_database_migration_complete.sql', 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print('📄 SQL migration file loaded successfully')
        
        # Split SQL into individual statements (basic approach)
        # Note: This is a simplified approach. For production, use proper SQL parsing
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
        
        print(f'📊 Found {len(statements)} SQL statements to execute')
        
        # Execute each statement
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements, 1):
            if not statement:
                continue
                
            try:
                print(f'🔄 Executing statement {i}/{len(statements)}...')
                
                # Use Supabase RPC to execute SQL
                result = supabase.rpc('exec_sql', {'sql': statement}).execute()
                
                if result.data:
                    print(f'✅ Statement {i} executed successfully')
                    success_count += 1
                else:
                    print(f'⚠️ Statement {i} executed but returned no data')
                    success_count += 1
                    
            except Exception as e:
                error_msg = str(e)
                if 'function exec_sql' in error_msg:
                    print(f'❌ Statement {i} failed: exec_sql function not available')
                    print(f'   SQL: {statement[:100]}...')
                    error_count += 1
                else:
                    print(f'❌ Statement {i} failed: {error_msg}')
                    error_count += 1
        
        print(f'\n📊 Migration Summary:')
        print(f'✅ Successful statements: {success_count}')
        print(f'❌ Failed statements: {error_count}')
        
        if error_count == 0:
            print('\n🎉 Phase 3 Database Migration completed successfully!')
            return True
        else:
            print(f'\n⚠️ Migration completed with {error_count} errors')
            return False
            
    except Exception as e:
        print(f'❌ Migration failed: {e}')
        return False

def test_migration_results():
    """Test that the migration was successful."""
    
    print('\n🔍 Testing migration results...')
    
    load_dotenv()
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    
    # Test functions
    functions_to_test = [
        ('search_products', {
            'query_embedding': [0.1] * 768,
            'match_threshold': 0.3,
            'match_count': 1,
            'filter_category': 'Cardigan',
            'filter_size_range': 'S, M, L, XL',
            'min_price': None,
            'max_price': None,
            'filter_stock_status': 'in_stock'
        }),
        ('keyword_search_products', {
            'search_term': 'cardigan',
            'match_count': 1,
            'filter_category': None,
            'min_price': None,
            'max_price': None,
            'filter_stock_status': 'in_stock'
        }),
        ('get_product_by_id', {'p_product_id': '1101'}),
        ('get_products_by_category', {'p_category': 'Cardigan', 'p_limit': 1}),
        ('hybrid_search_products', {
            'query_embedding': [0.1] * 768,
            'search_term': 'cardigan',
            'match_threshold': 0.3,
            'match_count': 1,
            'filter_category': 'Cardigan',
            'filter_size_range': 'S, M, L, XL',
            'min_price': None,
            'max_price': None,
            'filter_stock_status': 'in_stock'
        })
    ]
    
    success_count = 0
    
    for func_name, params in functions_to_test:
        try:
            result = supabase.rpc(func_name, params).execute()
            if result.data is not None:
                print(f'✅ {func_name}: Working correctly')
                success_count += 1
            else:
                print(f'⚠️ {func_name}: No data returned (may be normal)')
                success_count += 1
        except Exception as e:
            print(f'❌ {func_name}: Error - {str(e)[:100]}...')
    
    print(f'\n📊 Test Results: {success_count}/{len(functions_to_test)} functions working')
    
    if success_count == len(functions_to_test):
        print('🎉 All database functions are working correctly!')
        return True
    else:
        print('⚠️ Some functions may need manual fixing')
        return False

if __name__ == '__main__':
    print('🔧 Phase 3 Database Migration Tool')
    print('=====================================')
    
    # Execute migration
    migration_success = execute_phase3_migration()
    
    if migration_success:
        # Test results
        test_success = test_migration_results()
        
        if test_success:
            print('\n🎉 PHASE 3 DATABASE MIGRATION COMPLETE!')
            print('All database functions are now ready for Fashion Mart.')
        else:
            print('\n⚠️ Migration completed but some functions need manual verification.')
    else:
        print('\n❌ Migration failed. Please check the errors above.')
