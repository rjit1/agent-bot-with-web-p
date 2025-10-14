"""
Simple script to generate knowledge JSON file without dependencies
"""
import json
from knowledge_data import get_knowledge_chunks

def main():
    """Generate the knowledge JSON file."""
    print("📚 Generating knowledge data JSON...")
    
    # Get knowledge chunks
    chunks = get_knowledge_chunks()
    
    # Convert knowledge chunks to JSON format
    knowledge_data = []
    for chunk in chunks:
        knowledge_data.append({
            "chunk_id": chunk["chunk_id"],
            "title": chunk["title"],
            "content": chunk["content"],
            "category": chunk["category"],
            "keywords": chunk["keywords"],
            "priority": chunk["priority"],
            "language": chunk.get("language", "en"),
            "metadata": {
                "word_count": len(chunk["content"].split()),
                "char_count": len(chunk["content"])
            }
        })
    
    # Save to JSON file
    with open("gurtoy_knowledge_data.json", "w", encoding="utf-8") as f:
        json.dump(knowledge_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Generated gurtoy_knowledge_data.json with {len(knowledge_data)} chunks")
    print("\nNext step: Run 'python setup_database.py' to load into Supabase")

if __name__ == "__main__":
    main()