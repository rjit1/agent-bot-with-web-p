"""Example: Telegram bot webhook stub integrating Gemini 2.5 Flash.

This module sketches how to connect Telegram updates to Gemini and Supabase.
- Uses FastAPI for webhook endpoint.
- Reuses the function calling example to dispatch actions.

NOTE: This is a simplified reference; production code should handle retries,
security, rate limits, and concurrency considerations.
"""
from __future__ import annotations

import os
from typing import Any, Dict

import google.generativeai as genai
import httpx
from fastapi import FastAPI, HTTPException, Request
from supabase import create_client

app = FastAPI()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


def init_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Supabase credentials are not configured")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


SUPABASE_CLIENT = init_supabase()


def send_telegram_message(chat_id: int, text: str, reply_markup: Dict[str, Any] | None = None) -> None:
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    with httpx.Client(timeout=10) as client:
        response = client.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)
        response.raise_for_status()


def get_gemini_model() -> genai.GenerativeModel:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash-latest",
        tools=[{"function": {
            "name": "get_user_profile",
            "description": "Fetch user preferences and history from Supabase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telegram_id": {"type": "string"},
                },
                "required": ["telegram_id"],
            },
        }}],
        system_instruction="You are a helpful commerce assistant for Indian shoppers.",
    )


def handle_gemini_function_call(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "get_user_profile":
        telegram_id = args.get("telegram_id")
        response = SUPABASE_CLIENT.table("users").select("*").eq("telegram_id", telegram_id).single().execute()
        return response.data or {"preferences": {}, "history": []}
    return {"error": "Function not implemented"}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    update = await request.json()
    if "message" not in update:
        raise HTTPException(status_code=200, detail="No message to process")

    chat_id = update["message"]["chat"]["id"]
    user_text = update["message"].get("text", "")
    if not user_text:
        send_telegram_message(chat_id, "Please send a text message to get started ✨")
        return {"status": "ignored"}

    model = get_gemini_model()
    chat = model.start_chat(history=[])
    response = chat.send_message({"role": "user", "parts": [user_text]})

    candidate = response.candidates[0]
    part = candidate.content.parts[0]

    if hasattr(part, "function_call") and part.function_call:
        call = part.function_call
        tool_result = handle_gemini_function_call(call.name, call.args)
        response = chat.send_message(
            {
                "function_call": {
                    "name": call.name,
                    "args": call.args,
                    "result": tool_result,
                }
            }
        )

    send_telegram_message(chat_id, response.text or "Sorry, I could not understand that.")
    return {"status": "ok"}