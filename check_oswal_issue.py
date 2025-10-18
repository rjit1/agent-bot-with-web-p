#!/usr/bin/env python3
"""
Check if oswal products exist in the database and debug the fuzzy matching issue
"""
import os
from dotenv import load_dotenv
import supabase
from difflib import SequenceMatcher

load_dotenv()
client = supabase.create_client(
    os.getenv('SUPABASE_URL'), 
    os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

print("="*70)
print("CHECKING FOR OSWAL PRODUCTS IN DATABASE")
print("="*70)

# Check for oswal products
response = client.table('products').select('*').ilike('title', '%oswal%').execute()
print(f'\nOSWAL Products: Found {len(response.data)} products')
for p in response.data:
    print(f'  - {p.get("title", "N/A")}')

print('\n' + '='*70)
print('ALL UNIQUE BRANDS IN DATABASE:')
print('='*70)
response = client.table('products').select('title').execute()
brands = set()
for p in response.data:
    title = p['title'].strip()
    brands.add(title)

brands_list = sorted(brands)
print(f'Total unique brands: {len(brands_list)}\n')
for brand in brands_list:
    print(f'  - {brand}')

print('\n' + '='*70)
print('FUZZY MATCHING TEST: "oswal" vs ALL BRANDS')
print('='*70)

def fuzzy_match(query_word, brand, threshold=0.65):
    """Calculate similarity between query and brand"""
    query_lower = query_word.lower()
    brand_lower = brand.lower()
    matcher = SequenceMatcher(None, query_lower, brand_lower)
    confidence = matcher.ratio()
    return confidence

query = "oswal"
print(f'\nQuery: "{query}"')
print(f'Threshold for matching: 65%\n')

matches = []
for brand in brands_list:
    confidence = fuzzy_match(query, brand)
    matches.append((brand, confidence))
    status = "✓ MATCH" if confidence >= 0.65 else "✗ NO MATCH"
    print(f'{status}: "{query}" vs "{brand}" = {confidence*100:.2f}%')

print('\n' + '='*70)
print('MATCHES >= 65%:')
print('='*70)
high_matches = [m for m in matches if m[1] >= 0.65]
if high_matches:
    for brand, conf in sorted(high_matches, key=lambda x: x[1], reverse=True):
        print(f'  • {brand}: {conf*100:.2f}%')
else:
    print('  ⚠️  NO MATCHES FOUND!')
    print('\n  Closest matches:')
    for brand, conf in sorted(matches, key=lambda x: x[1], reverse=True)[:5]:
        print(f'    • {brand}: {conf*100:.2f}%')