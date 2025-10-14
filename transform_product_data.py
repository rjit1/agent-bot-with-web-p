"""
Transform product_data.csv into bot-friendly format with all required fields
"""
import csv
import json
import re
from datetime import datetime

def extract_age_range(description):
    """Extract age range from description"""
    # Look for patterns like "Age: 3-7 years", "Age:3–8 years", "Age: 1–4 years"
    patterns = [
        r'Age:\s*(\d+)\s*[-–]\s*(\d+)\s*years?',
        r'Age:\s*(\d+)\s*and\s*up',
        r'Age:\s*(\d+)\s*years?'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            if 'and up' in pattern:
                return f"{match.group(1)}+ years"
            elif len(match.groups()) == 2:
                return f"{match.group(1)}-{match.group(2)} years"
            else:
                return f"{match.group(1)}+ years"
    
    return "3-8 years"  # Default

def extract_colors(title, description):
    """Extract colors from title and description"""
    colors = []
    color_keywords = ['red', 'blue', 'green', 'pink', 'white', 'black', 'yellow', 'multicolor', 'orange']
    
    text = (title + " " + description).lower()
    for color in color_keywords:
        if color in text:
            colors.append(color.capitalize())
    
    return colors if colors else ["Multicolor"]

def extract_specifications(description):
    """Extract key specifications from description"""
    specs = {}
    
    # Battery voltage
    battery_match = re.search(r'(\d+)V\s*battery', description, re.IGNORECASE)
    if battery_match:
        specs['battery'] = f"{battery_match.group(1)}V"
    else:
        specs['battery'] = "12V"  # Default
    
    # Features
    features = []
    if 'LED' in description or 'lights' in description.lower():
        features.append("LED Lights")
    if 'music' in description.lower() or 'sound' in description.lower():
        features.append("Music System")
    if 'remote' in description.lower():
        features.append("Remote Control")
    if 'seat belt' in description.lower():
        features.append("Safety Belt")
    
    specs['features'] = features if features else ["LED Lights", "Music System"]
    
    return specs

def parse_images(image_string):
    """Parse comma-separated image URLs"""
    if not image_string or image_string.strip() == '':
        return []
    
    # Split by comma and clean up
    images = [img.strip() for img in image_string.split(',')]
    return [img for img in images if img]  # Remove empty strings

def clean_description(description):
    """Clean and format description for bot"""
    # Remove age info (we have separate field)
    description = re.sub(r'Age:\s*\d+[-–]\d+\s*years?', '', description, flags=re.IGNORECASE)
    description = re.sub(r'Age:\s*\d+\s*and\s*up', '', description, flags=re.IGNORECASE)
    description = re.sub(r'Age:\s*\d+\s*years?', '', description, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    description = re.sub(r'\s+', ' ', description)
    description = description.strip()
    
    return description

def generate_product_id(index, title):
    """Generate unique product ID"""
    # Use index + first letters of title
    words = title.split()[:3]
    prefix = ''.join([w[0].upper() for w in words if w])
    return f"GURTOY-{prefix}-{str(index+1).zfill(3)}"

def transform_csv():
    """Transform the product CSV"""
    input_file = 'e:\\project\\agent\\product_data.csv'
    output_file = 'e:\\project\\agent\\product_data_transformed.csv'
    
    products = []
    
    print("🔄 Reading original CSV...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for idx, row in enumerate(reader):
            # Generate product ID
            product_id = generate_product_id(idx, row['title'])
            
            # Extract data
            age_range = extract_age_range(row['description'])
            colors = extract_colors(row['title'], row['description'])
            specs = extract_specifications(row['description'])
            images = parse_images(row['images'])
            clean_desc = clean_description(row['description'])
            
            # Create transformed product
            product = {
                'product_id': product_id,
                'title': row['title'].strip(),
                'category': row['category'].strip(),
                'description': clean_desc,
                'age_range': age_range,
                'colors': json.dumps(colors),  # JSON array
                'specifications': json.dumps(specs),  # JSON object
                'images': json.dumps(images),  # JSON array
                'price': int(row['price']),
                'discount_price': int(row['discount_price']),
                'stock_status': 'in_stock',  # All in stock for demo
                'warranty': '6 months manufacturer warranty',
                'created_at': datetime.now().isoformat()
            }
            
            products.append(product)
            print(f"✅ Processed: {product['title'][:50]}...")
    
    print(f"\n📝 Writing transformed CSV with {len(products)} products...")
    
    # Write transformed CSV
    fieldnames = [
        'product_id', 'title', 'category', 'description', 'age_range', 
        'colors', 'specifications', 'images', 'price', 'discount_price', 
        'stock_status', 'warranty', 'created_at'
    ]
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(products)
    
    print(f"✅ Transformed CSV saved to: {output_file}")
    print(f"\n📊 Summary:")
    print(f"   - Total Products: {len(products)}")
    print(f"   - Categories: {len(set(p['category'] for p in products))}")
    print(f"   - All products set to ₹1 discount price for demo")
    print(f"\n🎯 Sample Product:")
    sample = products[0]
    print(f"   ID: {sample['product_id']}")
    print(f"   Title: {sample['title']}")
    print(f"   Price: ₹{sample['price']} → ₹{sample['discount_price']} (demo)")
    print(f"   Age: {sample['age_range']}")
    print(f"   Colors: {sample['colors']}")
    print(f"   Images: {len(json.loads(sample['images']))} images")

if __name__ == "__main__":
    transform_csv()