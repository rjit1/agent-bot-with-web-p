"""Example: Using Gemini 2.5 Flash with function calling to route user intents.

Prerequisites:
- Install google-generativeai: `pip install google-generativeai`
- Set the GEMINI_API_KEY environment variable.

This script demonstrates how to register tool schemas (functions) and
let Gemini decide which function to invoke when handling a Telegram user query.
"""
from __future__ import annotations

import os
import json
from typing import Any, Dict

import google.generativeai as genai


def create_product_search_tool() -> Dict[str, Any]:
    """Return the JSON schema describing a product search function."""
    return {
        "name": "search_products",
        "description": "Search the catalog for products that match a user query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Raw natural-language description of the desired product.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of products to fetch.",
                    "default": 5,
                },
                "language": {
                    "type": "string",
                    "enum": ["en", "hi"],
                    "description": "Language to prefer for product copy (English or Hindi).",
                },
            },
            "required": ["query"],
        },
    }


def mock_product_search(query: str, max_results: int = 5, language: str = "en") -> Dict[str, Any]:
    """Simulate a product search result payload returned to Gemini."""
    # In production you would call Supabase edge functions or Postgres directly.
    sample_products = [
        {
            "id": "kurta-001",
            "title": "Festive Silk Kurta",
            "price": 2499,
            "currency": "INR",
            "image_url": "https://example.com/images/kurta-001.jpg",
        },
        {
            "id": "kurta-002",
            "title": "Casual Cotton Kurta",
            "price": 1499,
            "currency": "INR",
            "image_url": "https://example.com/images/kurta-002.jpg",
        },
    ]
    return {
        "query": query,
        "language": language,
        "results": sample_products[:max_results],
    }


def generate_response(user_message: str) -> str:
    """Send a message to Gemini and let it decide whether to call functions.

    Returns the final assistant message ready to send back to Telegram.
    """
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-latest",
        tools=[{"function": create_product_search_tool()}],
        system_instruction=(
            "You are a friendly shopping assistant for Indian customers."
            "Detect intent, call tools when product data is needed,"
            " and reply in the user language with engaging formatting."
        ),
    )

    chat = model.start_chat(history=[])
    response = chat.send_message(user_message)

    if response.candidates[0].content.parts[0].function_call:
        call = response.candidates[0].content.parts[0].function_call
        print(f"Gemini decided to call function: {call.name}")
        args = {k: json.loads(v) if isinstance(v, str) else v for k, v in call.args.items()}
        tool_output = mock_product_search(**args)
        response = chat.send_message(
            {
                "function_call": {
                    "name": call.name,
                    "args": call.args,
                    "result": tool_output,
                }
            }
        )

    return response.text


if __name__ == "__main__":
    user_query = "Show me festive kurtas under 3000 rupees with some emoji"
    reply = generate_response(user_query)
    print("Assistant:", reply)