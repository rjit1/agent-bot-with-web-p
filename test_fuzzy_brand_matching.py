#!/usr/bin/env python3
"""
Test script to verify fuzzy brand matching functionality.
Tests the intelligent brand recognition system.
"""

import os
import sys
import asyncio
from difflib import SequenceMatcher

# Add the repo to path
sys.path.insert(0, '/e/github/agent')

# Mock brands for testing
MOCK_BRANDS = ['teacher', 'teachar', 'oster', 'imported', 'nice girl', 'richeez', 'g f o', 'compinent']

def fuzzy_match_brand(query_word: str, brands: list, threshold: float = 0.65) -> tuple:
    """
    Use fuzzy matching to find similar brand names.
    """
    best_match = None
    best_ratio = 0.0
    
    for brand in brands:
        ratio = SequenceMatcher(None, query_word.lower(), brand.lower()).ratio()
        
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = brand
    
    if best_ratio >= threshold:
        return (best_match, best_ratio)
    
    return None

def test_fuzzy_matching():
    """Test various fuzzy matching scenarios."""
    print("=" * 70)
    print("TESTING INTELLIGENT BRAND FUZZY MATCHING")
    print("=" * 70)
    
    test_cases = [
        ("oswal", "Checking if 'oswal' matches with 'oster'"),
        ("oster", "Exact match for 'oster'"),
        ("teachar", "Checking if 'teachar' matches with 'teacher'"),
        ("teacher", "Exact match for 'teacher'"),
        ("techer", "Misspelled 'teacher'"),
        ("richeez", "Exact match for 'richeez'"),
        ("richees", "Misspelled 'richeez'"),
        ("imported", "Exact match for 'imported'"),
        ("impoted", "Misspelled 'imported'"),
        ("nice girl", "Exact match for 'nice girl'"),
        ("niceGirl", "Variant of 'nice girl'"),
        ("g f o", "Exact match for 'g f o'"),
        ("gfo", "Compact form of 'g f o'"),
        ("compinent", "Exact match for 'compinent'"),
        ("component", "Similar to 'compinent'"),
        ("unknown", "Unknown brand - should not match"),
        ("xyz", "Random string - should not match"),
    ]
    
    results = []
    print(f"\nAvailable brands: {MOCK_BRANDS}")
    print("\n" + "-" * 70)
    
    for query, description in test_cases:
        result = fuzzy_match_brand(query, MOCK_BRANDS, threshold=0.60)
        
        if result:
            matched_brand, confidence = result
            status = "✅ MATCH" if confidence >= 0.70 else "⚠️  POSSIBLE"
            print(f"\n{status}: {description}")
            print(f"  Query: '{query}' → Matched: '{matched_brand}' (confidence: {confidence:.2%})")
            results.append((query, matched_brand, confidence, "MATCH"))
        else:
            print(f"\n❌ NO MATCH: {description}")
            print(f"  Query: '{query}' → No suitable brand found")
            results.append((query, None, 0.0, "NO MATCH"))
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    matches = [r for r in results if r[3] == "MATCH"]
    no_matches = [r for r in results if r[3] == "NO MATCH"]
    
    print(f"\n✅ Successful matches: {len(matches)}/{len(results)}")
    for query, brand, conf, _ in matches:
        print(f"   • '{query}' → '{brand}' ({conf:.2%})")
    
    print(f"\n❌ No matches: {len(no_matches)}/{len(results)}")
    for query, _, _, _ in no_matches:
        print(f"   • '{query}'")
    
    print("\n" + "=" * 70)
    print("KEY FINDINGS:")
    print("=" * 70)
    
    # Test the specific case from the issue
    oswal_result = fuzzy_match_brand("oswal", MOCK_BRANDS, threshold=0.60)
    print("\n🔍 ISSUE CASE: User asked for 'oswal products'")
    if oswal_result:
        matched, conf = oswal_result
        print(f"✅ System now recognizes: 'oswal' → '{matched}' ({conf:.2%})")
        if conf >= 0.70:
            print(f"   → This would be AUTO-CORRECTED in the search!")
        else:
            print(f"   → This would be LOGGED as POSSIBLE MATCH")
    else:
        print("❌ No match found for 'oswal'")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    test_fuzzy_matching()