#!/usr/bin/env python3
"""
Phase 2 Database Migration Script
Handles the migration from toy store to fashion store schema
"""

import os
import psycopg2
from dotenv import load_dotenv

def run_migration():
    """Run the database migration."""
    
    load_dotenv()
    
    # Get database connection details from Supabase URL
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print('❌ Missing Supabase credentials')
        return False
    
    # Extract connection details from Supabase URL
    # Format: https://project-ref.supabase.co
    db_host = supabase_url.replace('https://', '').replace('http://', '')
    db_name = 'postgres'
    db_user = 'postgres'
    db_password = supabase_key
    
    print('🚀 Starting Phase 2 Database Migration...')
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=5432,
            sslmode='require'
        )
        
        cursor = conn.cursor()
        
        # Step 1: Rename age_range column to size_range
        print('📝 Step 1: Renaming age_range column to size_range...')
        cursor.execute("ALTER TABLE products RENAME COLUMN age_range TO size_range;")
        print('✅ Column renamed successfully')
        
        # Step 2: Update the index name
        print('📝 Step 2: Updating index...')
        cursor.execute("DROP INDEX IF EXISTS idx_products_age_range;")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_size_range ON products(size_range);")
        print('✅ Index updated successfully')
        
        # Step 3: Drop existing functions
        print('📝 Step 3: Dropping existing functions...')
        functions_to_drop = [
            "DROP FUNCTION IF EXISTS search_products(VECTOR, DOUBLE PRECISION, INTEGER, TEXT, TEXT, NUMERIC, NUMERIC, TEXT);",
            "DROP FUNCTION IF EXISTS get_product_by_id(TEXT);",
            "DROP FUNCTION IF EXISTS get_products_by_category(TEXT, INTEGER);",
            "DROP FUNCTION IF EXISTS keyword_search_products(TEXT, INTEGER, TEXT, NUMERIC, NUMERIC, TEXT);",
            "DROP FUNCTION IF EXISTS search_products_by_image(VECTOR, DOUBLE PRECISION, INTEGER, TEXT, TEXT, NUMERIC, NUMERIC, TEXT);"
        ]
        
        for func_drop in functions_to_drop:
            try:
                cursor.execute(func_drop)
                print(f'✅ Dropped function: {func_drop.split()[4]}')
            except Exception as e:
                print(f'⚠️ Function drop warning: {e}')
        
        # Step 4: Create new functions
        print('📝 Step 4: Creating new functions with size_range...')
        
        # Read the migration SQL file
        with open('phase2_database_migration_fixed.sql', 'r') as f:
            migration_sql = f.read()
        
        # Extract function definitions (skip the DROP statements we already executed)
        sql_lines = migration_sql.split('\n')
        function_sql = []
        in_function = False
        
        for line in sql_lines:
            if line.strip().startswith('CREATE OR REPLACE FUNCTION'):
                in_function = True
                function_sql.append(line)
            elif in_function:
                function_sql.append(line)
                if line.strip().endswith('$$;'):
                    in_function = False
        
        # Execute function creation
        function_sql_text = '\n'.join(function_sql)
        if function_sql_text.strip():
            cursor.execute(function_sql_text)
            print('✅ Functions created successfully')
        
        # Commit all changes
        conn.commit()
        print('✅ All changes committed to database')
        
        # Verify the migration
        print('🔍 Verifying migration...')
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'products' AND column_name = 'size_range';")
        result = cursor.fetchone()
        
        if result:
            print('✅ Migration verified: size_range column exists')
        else:
            print('❌ Migration verification failed')
            return False
        
        cursor.close()
        conn.close()
        
        print('🎉 Phase 2 Database Migration Completed Successfully!')
        return True
        
    except Exception as e:
        print(f'❌ Migration failed: {e}')
        return False

if __name__ == '__main__':
    run_migration()
