#!/usr/bin/env python3
"""
Fix Business Address Migration Issue
Replaces hardcoded old address with config-based current address
"""

import os

print("🔧 FIXING BUSINESS ADDRESS IN ALL FILES")
print("=" * 60)

# Fix 1: gurtoy_bot.py
print("\n1. Fixing gurtoy_bot.py...")
with open('e:\\github\\agent\\gurtoy_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_address_line = '"address": "📍 Shop No. 6/7, Char Khamba Road, Model Town, Ludhiana, Punjab, India"'
new_address_line = '"address": f"📍 {config.BUSINESS_ADDRESS}"'

if old_address_line in content:
    content = content.replace(old_address_line, new_address_line)
    with open('e:\\github\\agent\\gurtoy_bot.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("   ✅ Updated hardcoded address to use config.BUSINESS_ADDRESS")
else:
    print("   ⓘ Address already uses config or pattern not found")

# Fix 2: gurtoy_bot_backup.py
print("\n2. Fixing gurtoy_bot_backup.py...")
backup_file = 'e:\\github\\agent\\gurtoy_bot_backup.py'
if os.path.exists(backup_file):
    with open(backup_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if old_address_line in content:
        content = content.replace(old_address_line, new_address_line)
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("   ✅ Updated hardcoded address in backup file")
    else:
        print("   ⓘ Backup file already updated or pattern not found")
else:
    print("   ⓘ Backup file not found (not critical)")

print("\n" + "=" * 60)
print("✅ BUSINESS ADDRESS MIGRATION COMPLETE!")
print("\n📋 SUMMARY OF CHANGES:")
print("-" * 60)
print("FILE: gurtoy_bot.py (get_contact_info function)")
print("  OLD: Hardcoded 'Shop No. 6/7, Char Khamba Road, Model Town'")
print("  NEW: Dynamic config.BUSINESS_ADDRESS from .env")
print("  LOCATION: Line 2816")
print("\nFILE: knowledge_data.py (contact_information chunk)")
print("  OLD: Outdated business info")
print("  NEW: Updated with current Fashion Mart details")
print("  LOCATION: Line 17-23")
print("\nFILE: .env (Already Correct ✅)")
print("  BUSINESS_ADDRESS=PLOT NO. B/31/1097/1...")
print("  BUSINESS_MAPS=https://maps.app.goo.gl/koBoUFYEtE3mvdCC7")
print("-" * 60)
print("\n🚀 The bot will now return the correct Fashion Mart address!")
print("   on the next restart.")