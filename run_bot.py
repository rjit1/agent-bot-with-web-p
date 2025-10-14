#!/usr/bin/env python3
"""
Gurtoy Telegram Bot Launcher
Simple script to run the bot in polling mode (no webhook required)
"""
import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_environment():
    """Check if required environment variables are set."""
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        "TELEGRAM_BOT_TOKEN",
        "GEMINI_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file")
        return False
    
    print("✅ Environment variables configured")
    return True


def print_banner():
    """Print startup banner."""
    print("\n" + "=" * 60)
    print("GURTOY TELEGRAM BOT")
    print("=" * 60)
    print("Mode: POLLING (No webhook required)")
    print("Perfect for local development and testing!")
    print("=" * 60 + "\n")


async def run_polling_bot():
    """Run the bot in polling mode."""
    from gurtoy_bot_polling import TelegramPollingBot
    
    bot = TelegramPollingBot()
    await bot.start_polling()


def main():
    """Main entry point."""
    print_banner()
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    print("🚀 Starting bot in polling mode...")
    print("💡 Tip: This mode doesn't require ngrok or public URL\n")
    
    try:
        # Run the polling bot
        asyncio.run(run_polling_bot())
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()