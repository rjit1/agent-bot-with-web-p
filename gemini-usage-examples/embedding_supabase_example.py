"""Example: Generating embeddings with gemini-embedding-001 and storing them in Supabase.

Prerequisites:
- Install google-generativeai and supabase libraries:
  `pip install google-generativeai supabase`
- Set GEMINI_API_KEY and SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY environment variables.
- Supabase table setup (simplified):
    create table product_embeddings (
        product_id text primary key,
        description text,
        embedding vector(3072)
    );
"""
from __future__ import annotations

import os
from typing import List

import google.generativeai as genai
from supabase import create_client


PRODUCTS = [
    {
        "product_id": "kurta-001",
        "description": "Festive silk kurta with zari embroidery and mandarin collar",
    },
    {
        "product_id": "saree-101",
        "description": "Lightweight georgette saree with floral print, perfect for evening events",
    },
]


def generate_embedding(text: str) -> List[float]:
    """Call gemini-embedding-001 to get a 3072-dimensional vector."""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    embedding = genai.embed_content(
        model="models/embedding-001",
        content=text,
    )
    return embedding["embedding"]


def store_embeddings():
    """Generate and persist embeddings in Supabase."""
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

    upserts = []
    for product in PRODUCTS:
        vector = generate_embedding(product["description"])
        upserts.append({
            "product_id": product["product_id"],
            "description": product["description"],
            "embedding": vector,
        })

    response = supabase.table("product_embeddings").upsert(upserts).execute()
    print("Upsert response:", response)


if __name__ == "__main__":
    store_embeddings()