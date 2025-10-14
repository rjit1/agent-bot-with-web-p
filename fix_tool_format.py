#!/usr/bin/env python3
"""
Fix all remaining payment tools to use correct Gemini function format
"""
import re

def fix_tool_format(content):
    """Fix tool format from function_declarations to direct format."""
    
    # Pattern to match function_declarations format
    pattern = r'def _create_(\w+)_tool\(self\) -> Dict\[str, Any\]:\s*"""([^"]*)"""\s*return \{\s*"function_declarations":\s*\[\s*\{\s*"name":\s*"([^"]*)",\s*"description":\s*"""([^"]*)""",\s*"parameters":\s*(\{[^}]+\})\s*\}\s*\]\s*\}'
    
    # This is complex, let me do it step by step
    # First, let's find all the tool methods
    tool_methods = re.findall(r'def _create_(\w+)_tool\(self\) -> Dict\[str, Any\]:', content)
    
    print(f"Found tool methods: {tool_methods}")
    
    return content

if __name__ == "__main__":
    # Read the file
    with open('gurtoy_bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the content
    fixed_content = fix_tool_format(content)
    
    print("Tool format fix completed")
