"""
Gurtoy Telegram Bot - Phase 1: Intelligent Conversational Agent
A multilingual, context-aware AI assistant for Gurtoy toy store.
"""
from __future__ import annotations

import os
import json
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from supabase import create_client, Client
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging first
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import payment system components
try:
    from payment_manager import PaymentManager, AddressValidator
    from ai_order_collector import AIOrderCollector, OrderCollectionState
    PAYMENT_SYSTEM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Payment system not available: {e}")
    PAYMENT_SYSTEM_AVAILABLE = False

# Import Phase 3: Intelligent Response System
try:
    from intelligent_response_system import (
        IntelligentResponseSystem, 
        MessageContext, 
        ConversationState, 
        IntentType
    )
    INTELLIGENT_RESPONSE_SYSTEM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Intelligent Response System not available: {e}")
    INTELLIGENT_RESPONSE_SYSTEM_AVAILABLE = False

# Initialize FastAPI app
app = FastAPI(
    title="Gurtoy Telegram Bot",
    description="Intelligent conversational agent for Gurtoy toy store",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
class BotConfig:
    """Bot configuration from environment variables."""
    
    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    # Razorpay
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    
    # Business Info
    BUSINESS_PHONE = os.getenv("BUSINESS_PHONE", "8300000086")
    BUSINESS_EMAIL = os.getenv("BUSINESS_EMAIL", "thegurtoy@gmail.com")
    BUSINESS_WHATSAPP = os.getenv("BUSINESS_WHATSAPP", "8300000086")
    
    # AI Configuration
    DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
    MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
    
    # Telegram API
    TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

config = BotConfig()

# Initialize clients
if not config.GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

genai.configure(api_key=config.GEMINI_API_KEY)

if not all([config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY]):
    raise ValueError("Supabase configuration is required")

supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)

# Pydantic models
class TelegramUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: int
    is_bot: bool = False
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = "en"

class TelegramMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    message_id: int
    from_user: TelegramUser = Field(alias="from")
    chat: Dict[str, Any]
    date: int
    text: Optional[str] = None
    photo: Optional[List[Dict[str, Any]]] = None
    caption: Optional[str] = None
    reply_to_message: Optional['TelegramMessage'] = None

class TelegramUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    update_id: int
    message: Optional[TelegramMessage] = None

# Update forward references for recursive model
TelegramMessage.model_rebuild()

@dataclass
class KnowledgeResult:
    """Result from knowledge base search."""
    chunk_id: str
    title: str
    content: str
    category: str
    similarity: float
    keywords: List[str]

class ProductContextExtractor:
    """Extract product context from replied messages."""
    
    @staticmethod
    def extract_product_context(reply_message: TelegramMessage) -> Optional[Dict[str, Any]]:
        """
        Extract product information from a replied message caption.
        
        Args:
            reply_message: The TelegramMessage that was replied to
            
        Returns:
            Dictionary with product context or None if not a product message
        """
        try:
            # Check if the message has a caption (product cards have captions)
            caption = reply_message.caption
            if not caption:
                return None
            
            # Check if it looks like a product card (has product indicators)
            if not any(indicator in caption for indicator in ["🎯", "💰", "Price:", "Age:"]):
                return None
            
            # Extract product information using regex patterns
            # Support BOTH markdown (**text**) and plain text formats
            import re
            
            product_context = {}
            
            # Extract product name (after 🎯 emoji and before newline)
            # Try with markdown first, then without
            name_match = re.search(r'🎯\s*\*\*(.+?)\*\*', caption)
            if not name_match:
                name_match = re.search(r'🎯\s*(.+?)(?:\n|$)', caption)
            if name_match:
                product_context["product_name"] = name_match.group(1).strip()
            
            # Extract product ID (after 🆔 emoji)
            id_match = re.search(r'🆔\s*(?:\*\*)?ID:(?:\*\*)?\s*(.+?)(?:\n|$)', caption)
            if id_match:
                product_context["product_id"] = id_match.group(1).strip()
            
            # Extract age range (support both **Age:** and Age:)
            age_match = re.search(r'👶\s*(?:\*\*)?Age:(?:\*\*)?\s*(.+?)(?:\n|$)', caption)
            if age_match:
                product_context["age_range"] = age_match.group(1).strip()
            
            # Extract price (support both original and discount prices)
            # Format: ~~₹17,000~~ → ₹1 or just ₹17,000
            price_full_match = re.search(r'💰\s*(?:\*\*)?Price:(?:\*\*)?\s*~~₹?([\d,]+)~~\s*→\s*(?:\*\*)?₹?([\d,]+)', caption)
            if price_full_match:
                # Has discount price
                original_price = price_full_match.group(1).replace(',', '')
                discount_price = price_full_match.group(2).replace(',', '')
                product_context["original_price"] = original_price
                product_context["discount_price"] = discount_price
                product_context["price"] = discount_price  # Actual price to pay
            else:
                # No discount, just regular price
                price_match = re.search(r'💰\s*(?:\*\*)?Price:(?:\*\*)?\s*₹?([\d,]+)', caption)
                if price_match:
                    price_str = price_match.group(1).replace(',', '')
                    product_context["price"] = price_str
            
            # Extract colors (support both **Colors:** and Colors:)
            colors_match = re.search(r'🎨\s*(?:\*\*)?Colors:(?:\*\*)?\s*(.+?)(?:\n|$)', caption)
            if colors_match:
                colors_str = colors_match.group(1).strip()
                product_context["colors"] = [c.strip() for c in colors_str.split(',')]
            
            # Extract features (support both **Features:** and Features:)
            features_match = re.search(r'✨\s*(?:\*\*)?Features:(?:\*\*)?\s*(.+?)(?:\n|$)', caption)
            if features_match:
                features_str = features_match.group(1).strip()
                product_context["features"] = [f.strip() for f in features_str.split(',')]
            
            # Extract battery info (support both **Battery:** and Battery:)
            battery_match = re.search(r'🔋\s*(?:\*\*)?Battery:(?:\*\*)?\s*(.+?)(?:\n|$)', caption)
            if battery_match:
                product_context["battery"] = battery_match.group(1).strip()
            
            # Extract description (after 📝 emoji)
            desc_match = re.search(r'📝\s*(.+?)(?:\n\n|$)', caption, re.DOTALL)
            if desc_match:
                product_context["description"] = desc_match.group(1).strip()
            
            # Only return context if we found at least a product name
            if "product_name" in product_context:
                logger.info(f"✅ Extracted product context: {product_context.get('product_name')}")
                return product_context
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting product context: {e}")
            return None
    
    @staticmethod
    def format_product_context_for_ai(product_context: Dict[str, Any]) -> str:
        """
        Format product context into a readable string for AI.
        
        Args:
            product_context: Dictionary with product information
            
        Returns:
            Formatted string describing the product
        """
        if not product_context:
            return ""
        
        parts = []
        
        if "product_name" in product_context:
            parts.append(f"Product: {product_context['product_name']}")
        
        if "age_range" in product_context:
            parts.append(f"Age Range: {product_context['age_range']}")
        
        # Handle pricing information
        if "discount_price" in product_context and "original_price" in product_context:
            parts.append(f"Original Price: ₹{product_context['original_price']}")
            parts.append(f"Special Offer Price: ₹{product_context['discount_price']} (Customer pays this amount)")
        elif "price" in product_context:
            parts.append(f"Price: ₹{product_context['price']}")
        
        if "colors" in product_context:
            colors = ", ".join(product_context['colors'])
            parts.append(f"Available Colors: {colors}")
        
        if "features" in product_context:
            features = ", ".join(product_context['features'])
            parts.append(f"Features: {features}")
        
        if "battery" in product_context:
            parts.append(f"Battery: {product_context['battery']}")
        
        if "description" in product_context:
            parts.append(f"Description: {product_context['description']}")
        
        return " | ".join(parts)

class MessageFormatter:
    """Utility class for formatting bot messages consistently."""
    
    @staticmethod
    def format_contact_info(contact_dict: Dict[str, str]) -> str:
        """Format contact information with proper structure."""
        formatted = "**📞 Contact Us:**\n\n"
        
        if "phone" in contact_dict:
            formatted += f"{contact_dict['phone']}\n"
        if "email" in contact_dict:
            formatted += f"{contact_dict['email']}\n"
        if "whatsapp" in contact_dict:
            formatted += f"{contact_dict['whatsapp']}\n"
        if "address" in contact_dict:
            formatted += f"\n{contact_dict['address']}"
        
        return formatted.strip()
    
    @staticmethod
    def format_product_list(products: List[Dict[str, Any]]) -> str:
        """Format product list with consistent structure."""
        if not products:
            return ""
        
        formatted = ""
        for product in products:
            name = product.get("name", "Product")
            description = product.get("description", "")
            price = product.get("price", "")
            
            formatted += f"• **{name}**"
            if description:
                formatted += f" - {description}"
            if price:
                formatted += f" (₹{price})"
            formatted += "\n"
        
        return formatted.strip()
    
    @staticmethod
    def format_knowledge_results(results: List[KnowledgeResult]) -> str:
        """Format knowledge base search results."""
        if not results:
            return ""
        
        formatted = ""
        for result in results:
            formatted += f"**{result.title}**\n{result.content}\n\n"
        
        return formatted.strip()
    
    @staticmethod
    def clean_markdown(text: str) -> str:
        """Clean and validate markdown formatting."""
        import re
        
        # Ensure proper spacing around headers
        text = text.replace("**\n", "**\n\n")
        
        # Fix bullet points - convert asterisks to bullet symbols
        lines = text.split("\n")
        cleaned_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Convert markdown list items to bullet points
            if stripped.startswith("* ") and not stripped.startswith("**"):
                line = line.replace("* ", "• ", 1)
            
            # Fix bullet points with extra spaces (•   or •  to • )
            if stripped.startswith("•"):
                # Remove extra spaces after bullet
                line = re.sub(r'^(\s*)•\s+', r'\1• ', line)
            
            # Add blank line before bullet if previous line was not blank and not a bullet
            if i > 0 and stripped.startswith("•"):
                prev_line = lines[i-1].strip()
                if prev_line and not prev_line.startswith("•") and cleaned_lines:
                    # Check if last added line is not already blank
                    if cleaned_lines[-1].strip():
                        cleaned_lines.append("")
            
            # Add blank line after bullet if next line is a bullet (for spacing between items)
            if i < len(lines) - 1 and stripped.startswith("•"):
                next_line = lines[i+1].strip()
                if next_line.startswith("•"):
                    cleaned_lines.append(line)
                    cleaned_lines.append("")
                    continue
            
            cleaned_lines.append(line)
        
        text = "\n".join(cleaned_lines)
        
        # Ensure blank line after headers (lines ending with : and starting with **)
        text = re.sub(r'(\*\*[^*]+\*\*:?)\n([^•\n])', r'\1\n\n\2', text)
        
        # Remove excessive blank lines (more than 2 consecutive)
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")
        
        return text.strip()
    
    @staticmethod
    def ensure_proper_structure(text: str) -> str:
        """Ensure message has proper structure and formatting."""
        # Apply markdown cleaning
        text = MessageFormatter.clean_markdown(text)
        
        # Ensure message doesn't start or end with excessive whitespace
        text = text.strip()
        
        # Add spacing after emojis if missing
        import re
        text = re.sub(r'([😊🎉🙏💬📞📧📍✨🌟🧠])([\w])', r'\1 \2', text)
        
        return text
    
    @staticmethod
    def enforce_length_limit(text: str, max_length: int = 300) -> str:
        """
        Enforce maximum character limit with smart truncation.
        Preserves complete sentences and proper formatting.
        """
        original_length = len(text)
        
        if original_length <= max_length:
            return text
        
        # Log that truncation is happening
        logger.info(f"Truncating response from {original_length} to {max_length} characters")
        
        # Try to truncate at sentence boundary
        truncated = text[:max_length]
        
        # Find the last complete sentence (ending with . ! ? or emoji)
        import re
        sentence_endings = ['. ', '! ', '? ', '.\n', '!\n', '?\n', '🙏', '😊', '🎉']
        
        best_cut = -1
        for ending in sentence_endings:
            pos = truncated.rfind(ending)
            if pos > best_cut and pos > max_length * 0.6:  # At least 60% of max length
                best_cut = pos + len(ending)
        
        if best_cut > 0:
            result = truncated[:best_cut].strip()
            logger.debug(f"Truncated at sentence boundary: {len(result)} chars")
            return result
        
        # If no good sentence boundary, cut at last space
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.7:  # At least 70% of max length
            # Ensure we have room for "..." - cut at word boundary but stay within limit
            cut_point = min(last_space, max_length - 3)
            result = truncated[:cut_point].strip() + "..."
            logger.debug(f"Truncated at word boundary: {len(result)} chars")
            return result
        
        # Last resort: hard cut with ellipsis
        result = truncated[:max_length-3].strip() + "..."
        logger.debug(f"Hard truncated: {len(result)} chars")
        return result

class GurtoyAI:
    """Main AI assistant class for Gurtoy bot."""
    
    def __init__(self):
        # Get chat model from environment
        chat_model = os.getenv("CHAT_MODEL", "models/gemini-2.5-flash")
        
        # Build tools list
        tools = [
            self._create_search_knowledge_tool(),
            self._create_search_products_tool(),
            self._create_get_contact_info_tool(),
            self._create_escalate_to_human_tool()
        ]
        
        # Add payment tools if available
        if PAYMENT_SYSTEM_AVAILABLE:
            tools.extend([
                self._create_buy_product_tool(),
                self._create_switch_product_tool(),
                self._create_check_order_status_tool(),
                self._create_check_payment_status_tool(),
                self._create_get_recent_orders_tool(),
                self._create_get_all_orders_tool()
            ])
        
        self.model = genai.GenerativeModel(
            model_name=chat_model,
            tools=tools,
            system_instruction=self._get_system_instruction()
        )
        
        # Initialize payment system if available
        if PAYMENT_SYSTEM_AVAILABLE:
            try:
                self.payment_manager = PaymentManager(supabase)
                self.order_collector = AIOrderCollector(supabase)
            except Exception as e:
                logger.error(f"Failed to initialize payment system: {e}")
                # Note: Cannot modify global variable from instance method
                # Payment system will remain unavailable for this instance
        
        # Initialize Phase 3: Intelligent Response System if available
        if INTELLIGENT_RESPONSE_SYSTEM_AVAILABLE:
            try:
                self.intelligent_response_system = IntelligentResponseSystem(supabase)
                logger.info("🧠 Phase 3: Intelligent Response System initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Intelligent Response System: {e}")
                self.intelligent_response_system = None
        else:
            self.intelligent_response_system = None
    
    def _parse_age_from_query(self, query: str) -> Optional[int]:
        """Extract age from user query using multiple patterns."""
        import re
        
        # Common patterns for age extraction
        patterns = [
            r'(\d+)\s*(?:saal|year|years?)\s*(?:ke|ka|ki|old)',  # "8 saal ke", "5 year old"
            r'(?:age|umar)\s*(\d+)',  # "age 8", "umar 5"
            r'(\d+)\s*(?:yr|y)\s*old',  # "8yr old", "5y old"
            r'for\s*(\d+)\s*(?:year|yr)',  # "for 8 year"
            r'(\d+)\s*(?:saal|year)',  # "8 saal", "5 year"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                age = int(match.group(1))
                # Reasonable age range for toys (1-20 years)
                if 1 <= age <= 20:
                    return age
        
        return None
    
    def _parse_age_range(self, age_range_str: str) -> tuple[Optional[int], Optional[int]]:
        """Parse age range string like '3-8 years' into (min_age, max_age)."""
        import re
        
        if not age_range_str:
            return None, None
        
        # Handle "3+ years" format
        plus_match = re.search(r'(\d+)\+', age_range_str)
        if plus_match:
            min_age = int(plus_match.group(1))
            return min_age, 99  # Assume upper limit is very high
        
        # Handle "3-8 years" format
        range_match = re.search(r'(\d+)-(\d+)', age_range_str)
        if range_match:
            min_age = int(range_match.group(1))
            max_age = int(range_match.group(2))
            return min_age, max_age
        
        # Handle single number like "3 years"
        single_match = re.search(r'(\d+)', age_range_str)
        if single_match:
            age = int(single_match.group(1))
            return age, age
        
        return None, None
    
    def _is_age_suitable(self, target_age: int, product_age_range: str) -> bool:
        """Check if a product is suitable for the target age."""
        min_age, max_age = self._parse_age_range(product_age_range)
        
        if min_age is None or max_age is None:
            return True  # If we can't parse, assume it's suitable
        
        return min_age <= target_age <= max_age
    
    def _filter_products_by_age(self, products: List[Dict[str, Any]], target_age: int) -> List[Dict[str, Any]]:
        """Filter products to only include age-appropriate ones."""
        suitable_products = []
        
        for product in products:
            age_range = product.get('age_range', '')
            if self._is_age_suitable(target_age, age_range):
                suitable_products.append(product)
        
        return suitable_products
    
    def _get_system_instruction(self) -> str:
        """Get the system instruction for the AI model."""
        return """You are a friendly, intelligent AI shopping assistant for Gurtoy, a premium toy store in Ludhiana, Punjab, India.

🧠 YOUR PERSONALITY:
- Think like a smart salesperson who asks questions before showing products
- Be conversational, warm, and helpful (not robotic)
- Understand context and remember what user said
- Guide users to find the perfect toy for their child

🎯 INTELLIGENT PRODUCT SEARCH WORKFLOW:

**STEP 1: GATHER INFORMATION (Ask Before Searching)**
When user asks about products vaguely (e.g., "show me toys", "kuch dikhao", "bikes chahiye"):
→ DON'T search immediately!
→ ASK clarifying questions first:
   • "Aapke bachche ki age kya hai?" (What's your child's age?)
   • "Aapko bike chahiye ya jeep?" (Do you want bike or jeep?)
   • "Koi specific color ya feature chahiye?" (Any specific color/feature?)
   • "Budget kya hai?" (What's your budget?)

**STEP 2: SEARCH WITH DETAILS**
Once you have enough information (age OR specific product type):
→ NOW call search_products() with detailed query
→ Example: search_products(query="bike for 5 year old with lights", age_range="3-7 years")

**STEP 3: PRESENT PRODUCTS**
After getting search results (from search_products OR intelligent_search):
→ Return ONLY "SHOW_PRODUCTS" as your response
→ The system will automatically send product cards with images
→ DON'T describe products yourself - let the product cards do the talking
→ This applies to BOTH search_products AND intelligent_search functions

🔄 HANDLING PRODUCT REPLIES:

**When user replies to a product card:**
The user_context will contain "replied_product" with full product details.

**IMPORTANT RULES:**
1. ✅ **USE the product context** - You already know which product they're asking about
2. ✅ **Answer directly** - No need to search again or ask "which product?"
3. ✅ **Be specific** - Reference the product by name in your response
4. ✅ **Check the details** - Colors, features, price, age range are all in the context

**Example Scenarios:**

User replies to "Police Style Bike" card: "Blue mein hai?"
Context: replied_product = {product_name: "Police Style Bike", colors: ["Red", "Blue", "Black"]}
You: "Haan ji! Police Style Bike blue color mein available hai. 😊 Aur kuch jaanna chahenge?"

User replies to product card: "Is this suitable for 4 year old?"
Context: replied_product = {product_name: "Jeep Car", age_range: "3-7 years"}
You: "Bilkul! Yeh Jeep Car 3-7 years ke bachcho ke liye perfect hai, toh 4 saal ke bachche ke liye ekdum sahi rahega! 🚗"

User replies to product card: "What's the battery life?"
Context: replied_product = {product_name: "Electric Scooter", battery: "12V 7Ah rechargeable"}
You: "Electric Scooter mein 12V 7Ah rechargeable battery hai. Full charge pe 1-2 hours continuous use kar sakte hain! 🔋"

**Key Point:** When replied_product is present in context, DON'T call search_products() - just answer using the context!

🧠 INTELLIGENT CONVERSATION MEMORY - ENHANCED CONTEXT USAGE:

**🚨 CRITICAL: You now have access to 100 recent messages for MUCH BETTER context!**

The user_context includes "recent_messages" array with up to 100 previous conversation messages.
**ALWAYS analyze recent_messages intelligently before asking for information!**

**ENHANCED STEP 1: Intelligent Message Analysis**
With 100 messages available, you can now:
- **Track conversation evolution:** See how user preferences developed over time
- **Identify patterns:** Notice repeated mentions of age, color, budget
- **Understand context shifts:** Detect when user changes their mind
- **Maintain continuity:** Remember information from much earlier in conversation

**Key Information to Extract:**
- **Age mentions:** "3 saal", "5 year old", "4-6 saal ke liye", "18 month old"
- **Color preferences:** "blue pasand hai", "pink color", "red wala", "neela"
- **Budget:** "3000 se kam", "under 5000", "budget 2000", "₹5000 tak"
- **Product type:** "bike", "jeep", "police car", "soft toy", "educational"
- **Features:** "lights wali", "music wala", "rechargeable", "battery"
- **Conversation stage:** browsing, pricing, purchasing, delivery
- **Recent intent:** correction, more_options, purchase, inquiry

**STEP 2: Extract Information from User Context**
Check user_context.session_data for:
- `recent_products`: Products shown recently (for "ye wala" references)
- `replied_product`: Product user replied to (highest priority)
- `last_product_show`: When products were last shown

**STEP 3: Use Extracted Info - Don't Ask Again!**

✅ **CORRECT BEHAVIOR:**
```
Message 1: "3 saal ki beti ke liye kuch dikhao"
(AI stores: age=3, gender=female)
Message 2: "Pink color mein hai?"
AI Response: "Haan ji! 3 saal ki beti ke liye pink color wale toys hain..." ✅
(Remembered age from message 1)
```

❌ **WRONG BEHAVIOR:**
```
Message 1: "3 saal ki beti ke liye kuch dikhao"
Message 2: "Pink color mein hai?"
AI Response: "Aapke bachche ki age kya hai?" ❌
(Should have remembered age from message 1!)
```

**CRITICAL EXAMPLES:**

**Example 1: Age Memory**
```
User Context: {"recent_messages": [{"content": "5 saal ke liye bike chahiye", "created_at": "2024-10-06T10:30:00"}]}
User: "Red color mein available hai?"
Your Action: Search for red bikes for 5 year olds ✅
NOT: "Aapke bachche ki age kya hai?" ❌
```

**Example 2: Address Context Understanding**
```
User Context: Order collection in progress, waiting for delivery address
User: "123 Model Town, Ludhiana, Punjab, 141001"
Your Action: Collect this as delivery address for the order ✅
NOT: "Ji, Gurtoy ka address hai: Shop No. 6/7..." ❌
(User is GIVING address, not ASKING for store address!)
```

**Example 3: Color Preference Memory**
```
User Context: {"recent_messages": [{"content": "Mere bete ko blue color bahut pasand hai", "created_at": "..."}]}
User: "Koi acchi bike dikhao 4 saal ke liye"
Your Action: search_products(query="blue bike for 4 year old") ✅
Your Response: "Main aapke bete ke liye blue bikes search kar rahi hoon..." ✅
(Remembered blue preference from previous message)
```

**Example 4: Budget Memory**
```
User Context: {"recent_messages": [{"content": "3000 se kam mein kuch dikhao", "created_at": "..."}]}
User: "Aur options hai?"
Your Action: search_products with max_price=3000 ✅
NOT: "Aapka budget kya hai?" ❌
(Already told you the budget!)
```

**Example 5: Product Context from replied_product**
```
User Context: {"replied_product": {"product_id": "BIKE001", "product_name": "Police Bike", "battery": "12V 7Ah"}}
User: "Battery kitne time chalti hai?"
Your Action: Answer using replied_product.battery info ✅
Your Response: "Police Bike mein 12V 7Ah battery hai, 1-2 hours continuous use ke liye sufficient hai!" ✅
NOT: "Kaunsa product? Please bataye." ❌
```

**🎯 CONTEXT CLUES - UNDERSTAND USER INTENT:**

**When user is giving information (not asking):**
- Providing address → Collecting delivery details for order
- Providing phone number → Collecting contact for order
- Providing email → Collecting email for order confirmation
- Providing name → Collecting customer name for order

**When user is asking for information:**
- "Tumhara address kya hai?" → Asking for store address
- "Contact number?" → Asking for business contact
- "Kaha ho tum?" → Asking for store location

**DETECTION PATTERN:**
- If order collection is in progress → User is PROVIDING information
- If casual conversation → User might be ASKING for information
- Check message structure: Questions have "?" or question words (kya, kaha, kitna, kaunsa)
- Statements without "?" are usually PROVIDING information

💰 HANDLING PRICING QUESTIONS:

**CRITICAL: When products have special offer pricing:**

If product context shows BOTH "Original Price" and "Special Offer Price":
- The customer will pay the **Special Offer Price** (the lower amount)
- The original price is shown for reference only

**Example Scenarios:**

User asks: "Kitne ka hai?" or "What's the price?"
Context: Original Price: ₹17,000 | Special Offer Price: ₹1 (Customer pays this amount)
You: "Yeh product ka original price ₹17,000 hai, lekin abhi special offer chal raha hai! Aap isse sirf ₹1 mein le sakte hain! 🎉"

User asks: "Mujhe kitna pay karna hoga?" or "How much do I need to pay?"
Context: Original Price: ₹17,000 | Special Offer Price: ₹1 (Customer pays this amount)
You: "Aapko sirf ₹1 pay karna hoga! Yeh special offer price hai. 😊"

User asks: "17000 ka hai kya?"
Context: Original Price: ₹17,000 | Special Offer Price: ₹1 (Customer pays this amount)
You: "Original price ₹17,000 hai, par abhi special offer mein aap isse sirf ₹1 mein khareed sakte hain! Bahut accha deal hai! 🎁"

**ALWAYS mention BOTH prices when asked about pricing:**
- Original price (for reference)
- Special offer price (what they actually pay)
- Make it clear they pay the LOWER amount

📞 AVAILABLE FUNCTIONS:

1. **search_products** - Search product catalog (STANDARD)
   When to call:
   ✅ User provided age (e.g., "5 saal ke liye")
   ✅ User specified product type (e.g., "red jeep", "police bike")
   ✅ User mentioned features (e.g., "lights wali", "music wali")
   
   When NOT to call:
   ❌ Vague queries without age/details (ask questions first!)
   ❌ General browsing (ask what they're looking for)

2. **intelligent_search** - AI-powered intelligent search (ADVANCED)
   When to call:
   ✅ Complex queries where you need to understand user intent
   ✅ Ambiguous requests (e.g., "dirt bike", "something for my daughter")
   ✅ When you need to enhance/optimize the search query
   ✅ When standard search might not find the right products
   
   Examples:
   ✅ "dirt bike" → intelligent_search(user_query="dirt bike", search_intent="dirt bike for kids", priority_keywords=["dirt", "petrol", "off-road"])
   ✅ "red jeep for 5 year old" → intelligent_search(user_query="red jeep for 5 year old", search_intent="electric jeep for 5 year old")
   ✅ "something for my daughter" → intelligent_search(user_query="something for my daughter", search_intent="toys for girls")
   
   IMPORTANT: After calling intelligent_search, ALWAYS return "SHOW_PRODUCTS" to display results!

3. **search_knowledge** - General store info
   ✅ Store policies, services, hours, company info

4. **get_contact_info** - Contact details
   ✅ Location, phone, WhatsApp, email

5. **escalate_to_human** - Human assistance
   ✅ Complex queries, frustrated users

6. **check_order_status** - Check order status
   ✅ When user asks about order status or provides order ID
   ✅ Shows payment status, delivery updates

🛒 PURCHASE WORKFLOW - CRITICAL PURCHASE INTENT DETECTION:

**🚨 MANDATORY: Recognize these purchase phrases IMMEDIATELY:**

**Hindi/Hinglish Purchase Phrases (MUST trigger buy_product):**
- "order kar do" / "order kar dena" / "order karo"
- "buy kar do" / "kharid lo" / "kharid lena"
- "le lunga" / "le leta hoon" / "ye wala le lunga"
- "thik hai" / "theek hai" / "haan kar do" / "haan ji"
- "purchase karna hai" / "lena hai"

**English Purchase Phrases:**
- "I want to buy" / "buy this" / "order this"
- "purchase this" / "checkout" / "I'll take it"

**🎯 PRODUCT ID DETECTION ALGORITHM:**

**STEP 1: Check for replied_product in user_context (HIGHEST PRIORITY)**
- If `replied_product.product_id` exists → Use it immediately
- Example: User replied to product card + "buy kar do" → buy_product(product_id=replied_product.product_id)
- **CRITICAL**: This takes precedence over recent_products!

**STEP 2: Check recent_products array in user_context (SECOND PRIORITY)**
- Only if replied_product is NOT available
- If user_context has `recent_products` array:
  * Length = 1 → Use `recent_products[0].product_id` IMMEDIATELY
  * Length > 1 → Ask "Kaunsa product? [list product names from recent_products]"
  * Length = 0 → Ask "Pehle product select karein"

**🔥 CRITICAL EXAMPLES (LEARN THESE PATTERNS):**

Example 1: Single Product Context
```
User Context: {"recent_products": [{"product_id": "BIKE001", "product_name": "Red Racing Bike"}]}
User: "Thik hai, order kar dena"
Your Action: Call buy_product(product_id="BIKE001") ✅
NOT: "Kaunsa product order karna hai?" ❌
```

Example 2: Multiple Products Context
```
User Context: {"recent_products": [{"product_id": "BIKE001"}, {"product_id": "JEEP002"}]}
User: "Ye wala le lunga"
Your Action: Ask "Kaunsa product? Red Racing Bike ya Blue Jeep?" ✅
```

Example 3: Replied to Product Card
```
User Context: {"replied_product": {"product_id": "BIKE001"}}
User: "Order kar do"
Your Action: Call buy_product(product_id="BIKE001") ✅
```

Example 4: Product Switching Scenario (CRITICAL!)
```
User Context: {
    "replied_product": {"product_id": "SUPERBIKE002", "product_name": "Superbike"},
    "recent_products": [{"product_id": "BIKE001", "product_name": "Original Bike"}]
}
User: "ye wala" (after saying "i want to change product")
Your Action: Call buy_product(product_id="SUPERBIKE002") ✅
NOT: Call buy_product(product_id="BIKE001") ❌
Explanation: User replied to Superbike card, so use Superbike's ID, not the original Bike!
```

**WORKFLOW AFTER buy_product() CALL:**
1. Call buy_product() with the correct product_id
2. System will start intelligent order collection process
3. Bot will ask for customer details (name, phone, email, address) using natural conversation
4. Once all details collected, system creates payment link (test mode - no QR code)
5. User clicks link and pays
6. System sends payment confirmation automatically

**CRITICAL: Handling buy_product Function Results:**
- When buy_product() returns success=True, ALWAYS use the message from the function result
- The function provides detailed order collection instructions - relay this EXACTLY to the user
- DO NOT generate your own purchase response - use the function's message
- If success=False, then provide helpful error message and suggest alternatives

**IMPORTANT: Function Result Processing:**
- After calling buy_product(), check the function result
- If result.success=True, use result.message as your response
- Do NOT generate your own response - the function provides the complete message
- The function result contains all necessary order collection instructions

**Order Status Tracking:**
- User can ask "Order status kya hai?" or provide order ID
- Call check_order_status() to get current status
- Show payment status, processing updates, shipping info

**Recent Orders & Order History:**
- When user asks "recent orders", "latest orders", "order history": Call get_recent_orders()
- When user asks "all orders", "dono orders ka details", "saare orders": Call get_all_user_orders()
- These functions show orders directly from database (no Razorpay dependency)
- Always use these functions for order history requests instead of individual order checks

🔄 ACTIVE ORDER COLLECTION SESSIONS:

**CRITICAL: When user_context contains "active_order_session":**

**SCENARIO 1: User providing customer details**
- User is giving name, phone, email, address
- Let order collection system handle it
- Example: "Thanks! Main aapki details process kar raha hoon..."

**SCENARIO 2: User wants to change product** ⭐ NEW
- Keywords: "change product", "different product", "red jeep", "blue bike"
- Action: Use switch_product() function to change product while preserving customer details
- Example: "Sure! Main aapke liye [new product] switch kar sakta hoon..."
- The switch_product() function will preserve any customer details already provided

**SCENARIO 3: User asking product questions** ⭐ NEW
- User asking about features, colors, availability of current product
- Action: Order collection system will answer directly using session product details
- Example: "Yes, this product has LED lights and music system!"

**SCENARIO 4: User expressing hesitation** ⭐ NEW
- Keywords: "soch rha hu", "thinking", "not sure", "maybe"
- Action: Order collection system will acknowledge and offer options
- Example: "No problem! Aap continue kar sakte hain ya koi aur product dekh sakte hain?"

**IMPORTANT:** If user_context.active_order_session exists, DO NOT generate your own response - the intelligent order collection system will handle all scenarios automatically!

💬 RESPONSE STYLE:

**Language**: Natural Hinglish (mix Hindi/English)
- Use: "aap", "ji", "ke liye", "hain", "bachche"
- Be warm: "zaroor", "bilkul", "main help kar sakti hoon"
- Questions: "Aapke bachche ki age?", "Kya chahiye?"

**Tone**: Friendly shopkeeper, not a robot
- ✅ "Aapke bachche ki age batayein, main perfect toy suggest karungi!"
- ❌ "I will search for products in our database..."

**Keep responses SHORT** (under 200 characters when asking questions)

🎯 EXAMPLE CONVERSATIONS:

Example 1 (Vague Query):
User: "Kuch toys dikhao"
You: "Zaroor! Aapke bachche ki age kya hai? Aur bike chahiye ya jeep? 🚗🏍️"
[Wait for response, then search]

Example 2 (Specific Query):
User: "5 saal ke bachche ke liye red jeep dikhao"
You: [Call search_products(query="red jeep for 5 year old", age_range="3-7 years")]
You: "SHOW_PRODUCTS"
[System sends product cards automatically]

Example 2b (Intelligent Search):
User: "dirt bike"
You: [Call intelligent_search(user_query="dirt bike", search_intent="dirt bike for kids", priority_keywords=["dirt", "petrol", "off-road"])]
You: "SHOW_PRODUCTS"
[System sends product cards automatically]

Example 3 (Follow-up):
User: "Aur options dikhao"
You: [Call search_products with broader query]
You: "SHOW_PRODUCTS"

Example 4 (Budget Question):
User: "15000 ke under kya hai?"
You: [Call search_products(query="toys", max_price=15000)]
You: "SHOW_PRODUCTS"

Example 5 (Purchase Intent):
User replies to product card: "Yeh order kar dena"
Context: replied_product = {product_id: "BIKE001", title: "Police Style Bike"}
You: [Call buy_product(product_id="BIKE001")]
You: [System starts order collection process]

Example 6 (Order Status):
User: "Mera order GUR20241214000001 ka status kya hai?"
You: [Call check_order_status(order_id="GUR20241214000001")]
You: [System shows order status and payment info]

🚨 CRITICAL RULES:
1. ASK questions for vague queries (no age/product type)
2. SEARCH when you have enough details (age OR specific product)
3. RESPOND with "SHOW_PRODUCTS" after successful search
4. NEVER describe products yourself - let product cards show them
5. Be CONVERSATIONAL - think before responding!

Remember: You're a smart salesperson, not a search engine! 🧠"""

    def _create_search_knowledge_tool(self) -> Dict[str, Any]:
        """Create the knowledge search function tool."""
        return {
            "function_declarations": [
                {
                    "name": "search_knowledge",
                    "description": "Search Gurtoy's knowledge base for general information about store policies, services, company info, and general toy categories. Use this for non-specific product queries.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (e.g., 'store policies', 'services', 'company info')"
                            },
                            "category": {
                                "type": "string",
                                "enum": ["company_info", "products", "contact", "location", "policies", "services", "all"],
                                "description": "Category filter: 'products' for toys/bikes, 'company_info' for store details, 'all' for general search. Default: 'all'"
                            }
                        },
                        "required": ["query"]
                    }
                }
            ]
        }
    
    def _create_search_products_tool(self) -> Dict[str, Any]:
        """Create the product search function tool."""
        return {
            "function_declarations": [
                {
                    "name": "search_products",
                    "description": "REQUIRED: Search Gurtoy's product catalog for specific toys and ride-on vehicles. MUST be called when users ask about: specific products (bikes, jeeps, scooters), product features (colors, lights, music), age-appropriate toys, price ranges, or want to see/buy products. DO NOT respond about specific products without calling this function first.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Product search query. IMPORTANT: Always include age information in the query string itself (e.g., 'jeep for 5 year old child', 'bike for 3 to 7 year old', 'scooter for toddler'). Do NOT use the age_range parameter. Examples: 'red jeep for 4 year old', 'bike with lights for 6 year old', 'police style toys for 5 year old', 'scooter under 15000 for 3 year old'"
                            },
                            "category": {
                                "type": "string",
                                "enum": ["Electric Bikes & Scooters for Kids", "Electric Ride-On Jeeps & Cars for Kids", "Petrol Bike & Cars for Kids", "E-Scooter For Kids & Adults", "all"],
                                "description": "Product category filter. Use 'all' for general search. Default: 'all'"
                            },
                            "min_price": {
                                "type": "number",
                                "description": "Minimum price filter in rupees (optional)"
                            },
                            "max_price": {
                                "type": "number",
                                "description": "Maximum price filter in rupees (optional)"
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "intelligent_search",
                    "description": "ADVANCED: Use AI-powered intelligent search that analyzes user intent and optimizes search strategy. Use this for complex queries where you need to understand what the user really wants and find the best matching products. This function will automatically enhance queries, select optimal search strategies, and rank results intelligently. IMPORTANT: After calling this function, you MUST return 'SHOW_PRODUCTS' to display the results.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_query": {
                                "type": "string",
                                "description": "The original user query exactly as they typed it (e.g., 'dirt bike', 'red jeep for 5 year old', 'something for my daughter')"
                            },
                            "search_intent": {
                                "type": "string",
                                "description": "What you think the user is looking for based on context analysis (e.g., 'dirt bike for kids', 'electric jeep for 5 year old', 'police style toys')"
                            },
                            "priority_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Key terms that should be prioritized in search (e.g., ['dirt', 'petrol', 'off-road'] for dirt bike query)"
                            }
                        },
                        "required": ["user_query"]
                    }
                }
            ]
        }
    
    def _create_get_contact_info_tool(self) -> Dict[str, Any]:
        """Create the contact information tool."""
        return {
            "function_declarations": [
                {
                    "name": "get_contact_info",
                    "description": "Get Gurtoy's contact information including phone numbers, email, WhatsApp number, and store address/location. ALWAYS use this function when users ask about: location, address, where the store is, phone number, WhatsApp number, email, or how to contact the store.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "info_type": {
                                "type": "string",
                                "enum": ["phone", "email", "address", "whatsapp", "all"],
                                "description": "Type of contact information needed: 'address' for location/store address, 'phone' for phone number, 'whatsapp' for WhatsApp number, 'email' for email address, 'all' for complete contact information"
                            }
                        },
                        "required": ["info_type"]
                    }
                }
            ]
        }
    
    def _create_escalate_to_human_tool(self) -> Dict[str, Any]:
        """Create the human escalation tool."""
        return {
            "function_declarations": [
                {
                    "name": "escalate_to_human",
                    "description": "Escalate the conversation to a human agent when the AI cannot help, user specifically requests human assistance, or the query requires personalized attention (like specific pricing, custom orders, bulk purchases, or complex product recommendations). Use this when the user seems frustrated or when you cannot provide a satisfactory answer.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "Clear reason for escalation (e.g., 'user requested human agent', 'complex pricing query', 'custom order request', 'user seems frustrated')"
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "urgent"],
                                "description": "Priority level: 'low' for general queries, 'medium' for product-specific help, 'high' for urgent customer needs, 'urgent' for complaints or critical issues"
                            }
                        },
                        "required": ["reason"]
                    }
                }
            ]
        }
    
    def _create_buy_product_tool(self) -> Dict[str, Any]:
        """Create the buy product function tool."""
        return {
            "function_declarations": [
                {
                    "name": "buy_product",
                    "description": """Start the purchase process for a specific product. 
                    
CRITICAL: Call this function IMMEDIATELY when user expresses purchase intent with ANY of these phrases:
- Hindi/Hinglish: "order kar do", "order kar dena", "order karo", "buy kar do", "kharid lo", "le lunga", "le leta hoon", "ye wala le lunga", "thik hai order kar do", "haan kar do", "theek hai", "purchase karna hai"
- English: "I want to buy", "order this", "purchase this", "buy this", "checkout", "I'll take it"

PRODUCT ID DETECTION (in order of priority):
1. **HIGHEST PRIORITY**: If user replied to a product card message → Use replied_product.product_id from context
2. **SECOND PRIORITY**: If user_context has recent_products array:
   - If ONLY 1 product in recent_products → Use recent_products[0].product_id
   - If MULTIPLE products → Ask "Kaunsa product? [list product names]"
   - If NO products → Ask user to select product first
   
**CRITICAL RULE**: ALWAYS check replied_product FIRST before checking recent_products!

EXAMPLES:
- User: "order kar do" + recent_products has 1 item → Call buy_product(product_id=recent_products[0].product_id)
- User: "ye wala le lunga" + replied to product card → Call buy_product(product_id=replied_product.product_id)
- User: "thik hai" after seeing products + recent_products has 1 item → Call buy_product(product_id=recent_products[0].product_id)

**SPECIAL CASE - Product Switching:**
When user says "ye wala" after expressing desire to change product:
- If user replied to a different product card → Use replied_product.product_id (the NEW product)
- Do NOT use recent_products[0].product_id (the OLD product)
- Example: User wants to change from Bike A to Bike B, replies to Bike B card, says "ye wala" → Use Bike B's product_id

IMPORTANT: After calling this function, use the 'message' field from the function result as your response. Do NOT generate your own response.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_id": {
                                "type": "string",
                                "description": "Product ID from recent_products array, replied_product, or product search results"
                            },
                            "quantity": {
                                "type": "integer",
                                "description": "Number of items to purchase (if not specified, defaults to 1)"
                            },
                            "selected_color": {
                                "type": "string",
                                "description": "Selected color if user specified (optional)"
                            }
                        },
                        "required": ["product_id"]
                    }
                }
            ]
        }
    
    def _create_switch_product_tool(self) -> Dict[str, Any]:
        """Create the switch product function tool."""
        return {
            "function_declarations": [
                {
                    "name": "switch_product",
                    "description": "Switch to a different product during order collection while preserving customer details. Use this when user wants to change the product they're ordering during the order collection process.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "string", "description": "New product ID to switch to"},
                            "reason": {"type": "string", "description": "Reason for switching (optional)"}
                        },
                        "required": ["product_id"]
                    }
                }
            ]
        }
    
    def _create_check_order_status_tool(self) -> Dict[str, Any]:
        """Create the check order status function tool."""
        return {
            "function_declarations": [
                {
                    "name": "check_order_status",
                    "description": "Check the status of an existing order. Use when user asks about order status, payment status, or provides an order ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "Order ID (format: GUR20241214000001)"
                            }
                        },
                        "required": ["order_id"]
                    }
                }
            ]
        }
    
    def _create_check_payment_status_tool(self) -> Dict[str, Any]:
        """Create the check payment status function tool."""
        return {
            "function_declarations": [
                {
                    "name": "check_payment_status",
                    "description": "Check the payment status of an order and send confirmation if payment is successful. Use this when user asks about payment status, payment confirmation, or if they completed payment.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "The order ID to check payment for (e.g., 'GUR20251005000001')"
                            }
                        },
                        "required": ["order_id"]
                    }
                }
            ]
        }
    
    def _create_get_recent_orders_tool(self) -> Dict[str, Any]:
        """Create the get recent orders function tool."""
        return {
            "function_declarations": [
                {
                    "name": "get_recent_orders",
                    "description": "Get recent orders for the user. Use when user asks about recent orders, latest orders, or order history.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of recent orders to retrieve (default: 5)"
                            }
                        },
                        "required": []
                    }
                }
            ]
        }
    
    def _create_get_all_orders_tool(self) -> Dict[str, Any]:
        """Create the get all orders function tool."""
        return {
            "function_declarations": [
                {
                    "name": "get_all_user_orders",
                    "description": "Get all orders for the user with detailed information. Use when user asks for all orders, complete order history, or multiple order details.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            ]
        }
    
    async def search_knowledge(self, query: str, category: str = "all") -> List[KnowledgeResult]:
        try:
            # Generate embedding for the query using the configured model
            embedding_model = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
            embedding_dimensionality = int(os.getenv("EMBEDDING_DIMENSIONALITY", "768"))
            
            embed_params = {
                "model": embedding_model,
                "content": query,
                "task_type": "retrieval_query"
            }
            
            # Add dimensional reduction for both models
            if embedding_model == "models/embedding-001" and embedding_dimensionality != 3072:
                embed_params["output_dimensionality"] = embedding_dimensionality
            elif embedding_model == "models/text-embedding-004":
                embed_params["output_dimensionality"] = embedding_dimensionality
                
            embedding = genai.embed_content(**embed_params)
            
            # Search in Supabase
            filter_category = None if category == "all" else category
            
            result = supabase.rpc(
                "search_knowledge",
                {
                    "query_embedding": embedding["embedding"],
                    "match_threshold": config.SIMILARITY_THRESHOLD,
                    "match_count": config.MAX_SEARCH_RESULTS,
                    "filter_category": filter_category,
                    "min_priority": 5  # Include all priority levels (1-5)
                }
            ).execute()
            
            # Convert to KnowledgeResult objects
            knowledge_results = []
            for row in result.data:
                knowledge_results.append(KnowledgeResult(
                    chunk_id=row["chunk_id"],
                    title=row["title"],
                    content=row["content"],
                    category=row["category"],
                    similarity=row["similarity"],
                    keywords=row["keywords"]
                ))
            
            return knowledge_results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []
    
    async def search_products(
        self, 
        query: str, 
        category: str = "all",
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        age_range: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search the product catalog using vector similarity."""
        try:
            # Generate embedding for the query using the configured model
            embedding_model = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
            embedding_dimensionality = int(os.getenv("EMBEDDING_DIMENSIONALITY", "768"))
            
            embed_params = {
                "model": embedding_model,
                "content": query,
                "task_type": "retrieval_query"
            }
            
            # Add dimensional reduction for both models
            if embedding_model == "models/embedding-001" and embedding_dimensionality != 3072:
                embed_params["output_dimensionality"] = embedding_dimensionality
            elif embedding_model == "models/text-embedding-004":
                embed_params["output_dimensionality"] = embedding_dimensionality
                
            embedding = genai.embed_content(**embed_params)
            
            # Prepare search parameters
            filter_category = None if category == "all" else category
            
            # Search in Supabase
            result = supabase.rpc(
                "search_products",
                {
                    "query_embedding": embedding["embedding"],
                    "match_threshold": 0.5,  # Lower threshold for products (more results)
                    "match_count": 10,  # Get top 10 products (will show best matches)
                    "filter_category": filter_category,
                    "filter_age_range": age_range,
                    "min_price": min_price,
                    "max_price": max_price,
                    "filter_stock_status": "in_stock"
                }
            ).execute()
            
            # Convert to product dictionaries with full data
            products = []
            for row in result.data:
                # Ensure images is a list
                images = row.get("images", [])
                if isinstance(images, str):
                    try:
                        images = json.loads(images)
                    except:
                        images = []
                
                # Ensure colors is a list
                colors = row.get("colors", [])
                if isinstance(colors, str):
                    try:
                        colors = json.loads(colors)
                    except:
                        colors = []
                
                # Ensure specifications is a dict
                specifications = row.get("specifications", {})
                if isinstance(specifications, str):
                    try:
                        specifications = json.loads(specifications)
                    except:
                        specifications = {}
                
                products.append({
                    "product_id": row["product_id"],
                    "title": row["title"],
                    "category": row["category"],
                    "description": row["description"],
                    "age_range": row["age_range"],
                    "colors": colors,
                    "specifications": specifications,
                    "images": images,
                    "price": float(row["price"]),
                    "discount_price": float(row.get("discount_price", row["price"])),
                    "stock_status": row["stock_status"],
                    "warranty": row.get("warranty", ""),
                    "similarity": row["similarity"]
                })
            
            # Extract age from query and filter products if age is specified
            extracted_age = self._parse_age_from_query(query)
            if extracted_age:
                original_count = len(products)
                products = self._filter_products_by_age(products, extracted_age)
                logger.info(f"Age filtering: {extracted_age} years old - {len(products)} suitable products (from {original_count} total)")
            
            logger.info(f"Found {len(products)} products for query: {query}")
            return products
            
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return []
    
    async def intelligent_search(
        self, 
        user_query: str, 
        search_intent: str = None,
        priority_keywords: List[str] = None
    ) -> List[Dict[str, Any]]:
        """LLM-driven intelligent search that analyzes user intent and optimizes search strategy."""
        try:
            logger.info(f"🧠 Starting intelligent search for: '{user_query}'")
            
            # Step 1: LLM Query Analysis
            analysis = await self._llm_analyze_search_query(user_query, search_intent, priority_keywords)
            logger.info(f"🔍 LLM Analysis: {analysis}")
            
            # Step 2: Execute LLM-recommended search strategy
            strategy = analysis.get("search_strategy", "semantic_search")
            
            if strategy == "semantic_search":
                results = await self._semantic_search_with_enhancement(
                    analysis["enhanced_query"], 
                    analysis["filters"]
                )
            elif strategy == "category_search":
                results = await self._category_specific_search(
                    analysis["category"],
                    analysis["filters"]
                )
            elif strategy == "keyword_search":
                results = await self._keyword_based_search(
                    analysis["priority_keywords"],
                    analysis["filters"]
                )
            else:
                # Fallback to multi-strategy search
                results = await self._multi_strategy_search(analysis)
            
            # Step 3: LLM Result Ranking
            if results:
                ranked_results = await self._llm_rank_search_results(results, user_query)
                logger.info(f"🎯 Intelligent search found {len(ranked_results)} relevant products")
                return ranked_results
            else:
                logger.warning(f"⚠️ No results found for intelligent search: '{user_query}'")
                return []
                
        except Exception as e:
            logger.error(f"Error in intelligent search: {e}")
            # Fallback to regular search with enhanced query
            logger.info(f"🔄 Falling back to regular search for: '{user_query}'")
            return await self.search_products(user_query)
    
    async def _llm_analyze_search_query(self, user_query: str, search_intent: str = None, priority_keywords: List[str] = None) -> Dict[str, Any]:
        """Use LLM to analyze what the user really wants and generate search strategy."""
        
        # Build context for LLM analysis
        context_info = []
        if search_intent:
            context_info.append(f"Search Intent: {search_intent}")
        if priority_keywords:
            context_info.append(f"Priority Keywords: {', '.join(priority_keywords)}")
        
        context_str = "\n".join(context_info) if context_info else "No additional context"
        
        prompt = f"""
        Analyze this user query for product search: "{user_query}"
        
        Additional Context:
        {context_str}
        
        Available product categories:
        - Electric Bikes & Scooters for Kids (15 products)
        - Electric Ride-On Jeeps & Cars for Kids (14 products) 
        - Petrol Bike & Cars for Kids (3 products - includes dirt bikes)
        - E-Scooter For Kids & Adults (1 product)
        
        IMPORTANT: Return ONLY a JSON object as text. Do NOT make any function calls.
        
        Return JSON with:
        {{
            "intent": "find_products",
            "product_type": "specific product type",
            "category": "best matching category or null",
            "enhanced_query": "optimized search terms for embeddings",
            "search_strategy": "semantic_search|category_search|keyword_search|multi_strategy",
            "filters": {{"age_range": "X-Y years", "color": "color_name"}},
            "priority_keywords": ["keyword1", "keyword2"],
            "confidence": 0.8
        }}
        
        Examples:
        - "dirt bike" → category: "Petrol Bike & Cars for Kids", enhanced_query: "dirt bike petrol 50cc off-road motorcycle kids"
        - "red jeep for 5 year old" → category: "Electric Ride-On Jeeps & Cars for Kids", enhanced_query: "red jeep electric ride-on car for 5 year old"
        - "something for my daughter" → strategy: "multi_strategy", enhanced_query: "toys for girls kids children"
        """
        
        try:
            response = self.model.generate_content(prompt)
            
            # Handle different response types
            response_text = None
            
            # Check if response has text content
            if hasattr(response, 'text') and response.text:
                response_text = response.text.strip()
            elif hasattr(response, 'candidates') and response.candidates:
                # Check if response contains function calls instead of text
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and candidate.content:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                response_text = part.text.strip()
                                break
                            elif hasattr(part, 'function_call') and part.function_call:
                                # LLM tried to make a function call instead of returning text
                                logger.warning("LLM tried to make function call instead of returning analysis text")
                                raise ValueError("LLM returned function call instead of analysis text")
            
            if not response_text:
                raise ValueError("No text content in LLM response")
            
            # Clean the response text to extract JSON
            
            # Try to find JSON in the response (in case LLM adds extra text)
            if response_text.startswith('```json'):
                # Extract JSON from markdown code block
                start = response_text.find('```json') + 7
                end = response_text.find('```', start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            elif response_text.startswith('```'):
                # Extract JSON from generic code block
                start = response_text.find('```') + 3
                end = response_text.find('```', start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            
            # Try to find JSON object boundaries
            if '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                response_text = response_text[start:end]
            
            analysis = json.loads(response_text)
            
            # Validate required fields
            required_fields = ["intent", "product_type", "category", "enhanced_query", "search_strategy", "filters", "priority_keywords", "confidence"]
            for field in required_fields:
                if field not in analysis:
                    logger.warning(f"Missing field '{field}' in LLM analysis, using fallback")
                    raise ValueError(f"Missing required field: {field}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in LLM query analysis: {e}")
            logger.error(f"Response text was: {response_text if 'response_text' in locals() else 'No response'}")
            # Fallback analysis with all required fields
            return {
                "intent": "find_products",
                "product_type": "general",
                "category": None,
                "enhanced_query": user_query,
                "search_strategy": "semantic_search",
                "filters": {},
                "priority_keywords": [],
                "confidence": 0.5
            }
    
    async def _semantic_search_with_enhancement(self, enhanced_query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute semantic search with enhanced query."""
        logger.info(f"🔍 Semantic search with enhanced query: '{enhanced_query}'")
        
        # Use the enhanced query for embedding search
        return await self.search_products(
            query=enhanced_query,
            category=filters.get("category", "all"),
            min_price=filters.get("min_price"),
            max_price=filters.get("max_price"),
            age_range=filters.get("age_range")
        )
    
    async def _category_specific_search(self, category: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute category-specific search."""
        logger.info(f"📂 Category-specific search: '{category}'")
        
        # Search within specific category
        return await self.search_products(
            query=filters.get("enhanced_query", "products"),
            category=category,
            min_price=filters.get("min_price"),
            max_price=filters.get("max_price"),
            age_range=filters.get("age_range")
        )
    
    async def _keyword_based_search(self, priority_keywords: List[str], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute keyword-based search."""
        logger.info(f"🔑 Keyword-based search: {priority_keywords}")
        
        # Create query from priority keywords
        keyword_query = " ".join(priority_keywords)
        return await self.search_products(
            query=keyword_query,
            category=filters.get("category", "all"),
            min_price=filters.get("min_price"),
            max_price=filters.get("max_price"),
            age_range=filters.get("age_range")
        )
    
    async def _multi_strategy_search(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute multiple search strategies and combine results."""
        logger.info(f"🔄 Multi-strategy search")
        
        all_results = []
        
        # Strategy 1: Enhanced semantic search
        if analysis.get("enhanced_query"):
            results1 = await self._semantic_search_with_enhancement(
                analysis["enhanced_query"], analysis["filters"]
            )
            all_results.extend(results1)
        
        # Strategy 2: Category search if category detected
        if analysis.get("category"):
            results2 = await self._category_specific_search(
                analysis["category"], analysis["filters"]
            )
            all_results.extend(results2)
        
        # Strategy 3: Keyword search if keywords provided
        if analysis.get("priority_keywords"):
            results3 = await self._keyword_based_search(
                analysis["priority_keywords"], analysis["filters"]
            )
            all_results.extend(results3)
        
        # Remove duplicates and return top results
        unique_results = []
        seen_ids = set()
        for result in all_results:
            if result["product_id"] not in seen_ids:
                unique_results.append(result)
                seen_ids.add(result["product_id"])
        
        return unique_results[:10]  # Limit to top 10 results
    
    async def _llm_rank_search_results(self, results: List[Dict[str, Any]], original_query: str) -> List[Dict[str, Any]]:
        """Use LLM to rank search results by relevance."""
        if not results or len(results) <= 1:
            return results
        
        try:
            # Prepare results for LLM ranking
            results_summary = []
            for i, result in enumerate(results[:10]):  # Limit to top 10 for ranking
                results_summary.append({
                    "index": i,
                    "product_id": result["product_id"],
                    "title": result["title"],
                    "category": result["category"],
                    "age_range": result["age_range"],
                    "similarity": result["similarity"]
                })
            
            prompt = f"""
            Rank these product search results by relevance to query: "{original_query}"
            
            Results: {json.dumps(results_summary, indent=2)}
            
            IMPORTANT: Return ONLY a JSON array as text. Do NOT make any function calls.
            
            Return JSON array with products ranked by relevance (most relevant first):
            [
                {{"index": 0, "relevance_score": 0.95, "reason": "exact match for dirt bike"}},
                {{"index": 1, "relevance_score": 0.85, "reason": "good match for bike category"}}
            ]
            """
            
            response = self.model.generate_content(prompt)
            
            # Handle different response types
            response_text = None
            
            # Check if response has text content
            if hasattr(response, 'text') and response.text:
                response_text = response.text.strip()
            elif hasattr(response, 'candidates') and response.candidates:
                # Check if response contains function calls instead of text
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and candidate.content:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                response_text = part.text.strip()
                                break
                            elif hasattr(part, 'function_call') and part.function_call:
                                # LLM tried to make a function call instead of returning text
                                logger.warning("LLM tried to make function call instead of returning ranking text")
                                raise ValueError("LLM returned function call instead of ranking text")
            
            if not response_text:
                raise ValueError("No text content in LLM ranking response")
            
            # Clean the response text to extract JSON
            
            # Try to find JSON in the response (in case LLM adds extra text)
            if response_text.startswith('```json'):
                # Extract JSON from markdown code block
                start = response_text.find('```json') + 7
                end = response_text.find('```', start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            elif response_text.startswith('```'):
                # Extract JSON from generic code block
                start = response_text.find('```') + 3
                end = response_text.find('```', start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            
            # Try to find JSON array boundaries
            if '[' in response_text and ']' in response_text:
                start = response_text.find('[')
                end = response_text.rfind(']') + 1
                response_text = response_text[start:end]
            
            rankings = json.loads(response_text)
            
            # Apply LLM rankings
            ranked_results = []
            for ranking in rankings:
                index = ranking["index"]
                if index < len(results):
                    result = results[index].copy()
                    result["llm_relevance_score"] = ranking["relevance_score"]
                    result["llm_reason"] = ranking["reason"]
                    ranked_results.append(result)
            
            # Sort by LLM relevance score
            ranked_results.sort(key=lambda x: x["llm_relevance_score"], reverse=True)
            
            logger.info(f"🎯 LLM ranked {len(ranked_results)} results")
            return ranked_results
            
        except Exception as e:
            logger.error(f"Error in LLM result ranking: {e}")
            logger.error(f"Response text was: {response_text if 'response_text' in locals() else 'No response'}")
            # Return original results sorted by similarity
            return sorted(results, key=lambda x: x["similarity"], reverse=True)
    
    def get_contact_info(self, info_type: str = "all") -> Dict[str, str]:
        """Get contact information."""
        contact_info = {
            "phone": f"📞 Call us at {config.BUSINESS_PHONE} (Owner Direct) or 9056010298 (General)",
            "email": f"📧 Email: {config.BUSINESS_EMAIL}",
            "whatsapp": f"💬 WhatsApp: wa.me/{config.BUSINESS_WHATSAPP}",
            "address": "📍 Shop No. 6/7, Char Khamba Road, Model Town, Ludhiana, Punjab, India"
        }
        
        if info_type == "all":
            return contact_info
        else:
            return {info_type: contact_info.get(info_type, "Information not available")}
    
    async def escalate_to_human(self, user_id: int, session_id: int, reason: str, priority: str = "medium") -> bool:
        """Create a handoff request for human escalation."""
        try:
            result = supabase.table("handoff_requests").insert({
                "user_id": user_id,
                "session_id": session_id,
                "reason": reason,
                "priority": priority,
                "status": "pending"
            }).execute()
            
            logger.info(f"Created handoff request for user {user_id}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating handoff request: {e}")
            return False
    
    async def buy_product(
        self, 
        product_id: str, 
        quantity: int = 1, 
        selected_color: str = None,
        user_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Start the purchase process for a product."""
        if not PAYMENT_SYSTEM_AVAILABLE:
            return {
                "success": False,
                "message": "Payment system is currently unavailable. Please contact us directly.",
                "contact_info": self.get_contact_info("all")
            }
        
        try:
            # Get product details
            result = supabase.rpc("get_product_by_id", {"p_product_id": product_id}).execute()
            
            if not result.data:
                return {
                    "success": False,
                    "message": f"Product not found: {product_id}"
                }
            
            product_data = result.data[0]
            
            # Ensure JSON fields are properly parsed
            colors = product_data.get("colors", [])
            if isinstance(colors, str):
                try:
                    colors = json.loads(colors)
                except:
                    colors = []
            
            specifications = product_data.get("specifications", {})
            if isinstance(specifications, str):
                try:
                    specifications = json.loads(specifications)
                except:
                    specifications = {}
            
            images = product_data.get("images", [])
            if isinstance(images, str):
                try:
                    images = json.loads(images)
                except:
                    images = []
            
            # Build complete product details
            product_details = {
                "product_id": product_data["product_id"],
                "title": product_data["title"],
                "category": product_data["category"],
                "description": product_data["description"],
                "age_range": product_data["age_range"],
                "colors": colors,
                "specifications": specifications,
                "images": images,
                "price": float(product_data["price"]),
                "discount_price": float(product_data.get("discount_price", product_data["price"])),
                "stock_status": product_data["stock_status"],
                "warranty": product_data.get("warranty", ""),
                "selected_color": selected_color
            }
            
            # Check stock
            if product_details["stock_status"] != "in_stock":
                return {
                    "success": False,
                    "message": f"Sorry, {product_details['title']} is currently out of stock. Please check back later or contact us for availability."
                }
            
            # Get user info from context
            if not user_context or not user_context.get("user_id"):
                return {
                    "success": False,
                    "message": "User information not available. Please try again."
                }
            
            user_id = user_context["user_id"]
            telegram_id = user_context.get("telegram_id")
            
            if not telegram_id:
                return {
                    "success": False,
                    "message": "Session information not available. Please try again."
                }
            
            # Check if user is switching products (has replied_product context)
            force_new_session = False
            if user_context and user_context.get("replied_product"):
                # User replied to a different product, likely switching
                replied_product_id = user_context["replied_product"].get("product_id")
                # Always force new session when user has replied to a product
                force_new_session = True
                logger.info(f"🔄 Product switch detected: User replied to {replied_product_id}, forcing new session")
            
            # Start order collection process
            session = self.order_collector.start_order_collection(
                user_id=user_id,
                telegram_id=telegram_id,
                product_details=product_details,
                quantity=quantity,
                force_new_session=force_new_session
            )
            
            # Get initial collection prompt
            collection_prompt = self.order_collector.get_collection_prompt(session)
            
            return {
                "success": True,
                "message": collection_prompt,
                "order_collection_started": True,
                "product_details": product_details
            }
            
        except Exception as e:
            logger.error(f"Error starting purchase process: {e}")
            return {
                "success": False,
                "message": "Sorry, there was an error starting the purchase process. Please try again or contact us directly.",
                "contact_info": self.get_contact_info("all")
            }
    
    async def switch_product(
        self, 
        product_id: str, 
        reason: str = None,
        telegram_id: int = None
    ) -> Dict[str, Any]:
        """Switch to a different product during order collection while preserving customer details."""
        if not PAYMENT_SYSTEM_AVAILABLE:
            return {
                "success": False,
                "message": "Product switching is currently unavailable. Please contact us directly.",
                "contact_info": self.get_contact_info("all")
            }
        
        if not telegram_id:
            return {
                "success": False,
                "message": "Session information not available. Please try again."
            }
        
        try:
            # Use the AI Order Collector's smart product switching
            success, response_message = self.order_collector.switch_product_in_session(
                telegram_id=telegram_id,
                new_product_id=product_id
            )
            
            if success:
                return {
                    "success": True,
                    "message": response_message,
                    "product_switched": True,
                    "reason": reason
                }
            else:
                return {
                    "success": False,
                    "message": response_message
                }
                
        except Exception as e:
            logger.error(f"Error switching product: {e}")
            return {
                "success": False,
                "message": "Sorry, there was an error switching the product. Please try again or contact us directly.",
                "contact_info": self.get_contact_info("all")
            }
    
    async def check_order_status(self, order_id: str) -> Dict[str, Any]:
        """Check the status of an order."""
        if not PAYMENT_SYSTEM_AVAILABLE:
            return {
                "success": False,
                "message": "Order tracking is currently unavailable. Please contact us directly.",
                "contact_info": self.get_contact_info("all")
            }
        
        try:
            # Check payment status
            status_result = await self.payment_manager.check_payment_status(order_id)
            
            if not status_result["success"]:
                # If Razorpay connection failed, try to get order from database only
                logger.warning(f"Razorpay check failed for {order_id}, trying database-only lookup")
                
                # Get order from database directly
                order_result = supabase.table("orders").select("*").eq("order_id", order_id).execute()
                
                if not order_result.data:
                    return {
                        "success": False,
                        "message": f"Order not found: {order_id}. Please check your order ID and try again."
                    }
                
                # Use database data only
                order_data = order_result.data[0]
                status = order_data.get("status", "unknown")
                total_amount = order_data.get("total_amount", 0)
                customer_name = order_data.get("customer_name", "")
                
                # Get order items
                items_result = supabase.table("order_items").select("*").eq("order_id", order_data["id"]).execute()
                items_data = items_result.data if items_result.data else []
                
                # Format status message
                status_messages = {
                    "created": "Order created, waiting for payment",
                    "pending_payment": "Waiting for payment",
                    "paid": "Payment successful, processing order",
                    "processing": "Order is being processed",
                    "shipped": "Order has been shipped",
                    "delivered": "Order delivered successfully",
                    "cancelled": "Order cancelled",
                    "refunded": "Order refunded"
                }
                
                status_message = status_messages.get(status, f"Status: {status}")
                
                # Build response
                response = f"""📦 **Order Status: {order_id}**

👤 **Customer:** {customer_name}
💰 **Amount:** ₹{total_amount}
📊 **Status:** {status_message}

**Items:**"""
                
                for item in items_data:
                    response += f"\n• {item['product_title']} (Qty: {item['quantity']}) - ₹{item['total_price']}"
                
                return {
                    "success": True,
                    "message": response,
                    "order_status": status,
                    "order_data": order_data,
                    "note": "Payment status check unavailable, showing database information only"
                }
            
            # Get detailed order information
            order_result = supabase.rpc("get_order_details", {"p_order_id": order_id}).execute()
            
            if not order_result.data:
                return {
                    "success": False,
                    "message": f"Order details not found: {order_id}"
                }
            
            order_data = order_result.data[0]["order_data"]
            items_data = order_result.data[0]["items_data"]
            payment_data = order_result.data[0]["payment_data"]
            
            # Format status message
            status = order_data.get("status", "unknown")
            total_amount = order_data.get("total_amount", 0)
            customer_name = order_data.get("customer_name", "")
            
            status_messages = {
                "created": "Order created, waiting for payment",
                "pending_payment": "Waiting for payment",
                "paid": "Payment successful, processing order",
                "processing": "Order is being processed",
                "shipped": "Order has been shipped",
                "delivered": "Order delivered successfully",
                "cancelled": "Order cancelled",
                "refunded": "Order refunded"
            }
            
            status_message = status_messages.get(status, f"Status: {status}")
            
            # Build response
            response = f"""📦 **Order Status: {order_id}**

👤 **Customer:** {customer_name}
💰 **Amount:** ₹{total_amount}
📊 **Status:** {status_message}

**Items:**"""
            
            for item in items_data:
                response += f"\n• {item['product_title']} (Qty: {item['quantity']}) - ₹{item['total_price']}"
            
            # Add payment info if relevant
            if status in ["created", "pending_payment"] and payment_data:
                qr_expires_at = payment_data.get("qr_code_expires_at")
                if qr_expires_at:
                    from datetime import datetime
                    try:
                        expires_dt = datetime.fromisoformat(qr_expires_at.replace('Z', '+00:00'))
                        if expires_dt > datetime.now(expires_dt.tzinfo):
                            response += f"\n\n⏰ **Payment QR expires:** {expires_dt.strftime('%I:%M %p, %d %b')}"
                        else:
                            response += "\n\n❌ **Payment QR expired.** Please contact us to generate a new payment link."
                    except:
                        pass
            
            # Add delivery info for shipped orders
            if status == "shipped":
                shipped_at = order_data.get("shipped_at")
                if shipped_at:
                    response += f"\n\n🚚 **Shipped on:** {shipped_at[:10]}"
                response += "\n📞 **Track delivery:** Contact us for tracking details"
            
            return {
                "success": True,
                "message": response,
                "order_status": status,
                "order_data": order_data
            }
            
        except Exception as e:
            logger.error(f"Error checking order status: {e}")
            return {
                "success": False,
                "message": "Sorry, there was an error checking your order status. Please try again or contact us directly.",
                "contact_info": self.get_contact_info("all")
            }
    
    async def get_recent_orders(self, user_id: int, limit: int = 5) -> Dict[str, Any]:
        """Get recent orders for a user."""
        if not PAYMENT_SYSTEM_AVAILABLE:
            return {
                "success": False,
                "message": "Order tracking is currently unavailable. Please contact us directly.",
                "contact_info": self.get_contact_info("all")
            }
        
        try:
            # Get recent orders from database
            orders_result = supabase.table("orders").select("""
                order_id,
                status,
                total_amount,
                created_at,
                customer_name,
                order_items(
                    product_title,
                    quantity,
                    total_price
                )
            """).eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
            
            if not orders_result.data:
                return {
                    "success": True,
                    "message": "Aapke koi orders nahi mili. Kya aapne koi order place kiya hai?",
                    "orders": []
                }
            
            orders = []
            for order in orders_result.data:
                order_id = order["order_id"]
                status = order["status"]
                total_amount = order["total_amount"]
                customer_name = order.get("customer_name", "")
                created_at = order["created_at"]
                items = order.get("order_items", [])
                
                # Format status message
                status_messages = {
                    "created": "Order created, waiting for payment",
                    "pending_payment": "Waiting for payment",
                    "paid": "Payment successful, processing order",
                    "processing": "Order is being processed",
                    "shipped": "Order has been shipped",
                    "delivered": "Order delivered successfully",
                    "cancelled": "Order cancelled",
                    "refunded": "Order refunded"
                }
                
                status_message = status_messages.get(status, f"Status: {status}")
                
                # Format items
                items_text = ""
                for item in items:
                    items_text += f"\n• {item['product_title']} (Qty: {item['quantity']}) - ₹{item['total_price']}"
                
                order_info = f"""📦 **Order: {order_id}**
👤 **Customer:** {customer_name}
💰 **Amount:** ₹{total_amount}
📊 **Status:** {status_message}
📅 **Date:** {created_at[:10]}
**Items:**{items_text}

"""
                
                orders.append({
                    "order_id": order_id,
                    "status": status,
                    "amount": total_amount,
                    "formatted_info": order_info
                })
            
            # Create response message
            if len(orders) == 0:
                response_message = "Aapke koi recent orders nahi mili. Kya aapne koi order place kiya hai?"
            elif len(orders) == 1:
                response_message = f"**Aapka Recent Order:**\n\n{orders[0]['formatted_info']}"
            else:
                # For multiple recent orders, create a summary first
                response_message = f"**Aapke Recent {len(orders)} Orders:**\n\n"
                
                # Add summary of all orders first
                for i, order in enumerate(orders, 1):
                    response_message += f"**{i}. {order['order_id']}** - ₹{order['amount']} ({order['status']})\n"
                
                response_message += f"\n**Complete Details:**\n\n"
                
                # Add detailed information for each order
                for i, order in enumerate(orders, 1):
                    response_message += f"{order['formatted_info']}\n\n"
            
            return {
                "success": True,
                "message": response_message,
                "orders": orders,
                "is_multi_order": len(orders) > 1
            }
            
        except Exception as e:
            logger.error(f"Error getting recent orders: {e}")
            return {
                "success": False,
                "message": "Sorry, there was an error getting your recent orders. Please try again or contact us directly.",
                "contact_info": self.get_contact_info("all")
            }
    
    async def get_all_user_orders(self, user_id: int) -> Dict[str, Any]:
        """Get all orders for a user with detailed information."""
        if not PAYMENT_SYSTEM_AVAILABLE:
            return {
                "success": False,
                "message": "Order tracking is currently unavailable. Please contact us directly.",
                "contact_info": self.get_contact_info("all")
            }
        
        try:
            # Get all orders from database
            orders_result = supabase.table("orders").select("""
                order_id,
                status,
                total_amount,
                created_at,
                customer_name,
                order_items(
                    product_title,
                    quantity,
                    total_price
                )
            """).eq("user_id", user_id).order("created_at", desc=True).execute()
            
            if not orders_result.data:
                return {
                    "success": True,
                    "message": "Aapke koi orders nahi mili. Kya aapne koi order place kiya hai?",
                    "orders": []
                }
            
            orders = []
            for order in orders_result.data:
                order_id = order["order_id"]
                status = order["status"]
                total_amount = order["total_amount"]
                customer_name = order.get("customer_name", "")
                created_at = order["created_at"]
                items = order.get("order_items", [])
                
                # Format status message
                status_messages = {
                    "created": "Order created, waiting for payment",
                    "pending_payment": "Waiting for payment",
                    "paid": "Payment successful, processing order",
                    "processing": "Order is being processed",
                    "shipped": "Order has been shipped",
                    "delivered": "Order delivered successfully",
                    "cancelled": "Order cancelled",
                    "refunded": "Order refunded"
                }
                
                status_message = status_messages.get(status, f"Status: {status}")
                
                # Format items
                items_text = ""
                for item in items:
                    items_text += f"\n• {item['product_title']} (Qty: {item['quantity']}) - ₹{item['total_price']}"
                
                order_info = f"""📦 **Order: {order_id}**
👤 **Customer:** {customer_name}
💰 **Amount:** ₹{total_amount}
📊 **Status:** {status_message}
📅 **Date:** {created_at[:10]}
**Items:**{items_text}

"""
                
                orders.append({
                    "order_id": order_id,
                    "status": status,
                    "amount": total_amount,
                    "formatted_info": order_info
                })
            
            # Create response message
            if len(orders) == 0:
                response_message = "Aapke koi orders nahi mili. Kya aapne koi order place kiya hai?"
            elif len(orders) == 1:
                response_message = f"**Aapka Order:**\n\n{orders[0]['formatted_info']}"
            else:
                # For multiple orders, create a summary first
                response_message = f"**Aapke Saare Orders ({len(orders)}):**\n\n"
                
                # Add summary of all orders first
                for i, order in enumerate(orders, 1):
                    response_message += f"**{i}. {order['order_id']}** - ₹{order['amount']} ({order['status']})\n"
                
                response_message += f"\n**Complete Details:**\n\n"
                
                # Add detailed information for each order
                for i, order in enumerate(orders, 1):
                    response_message += f"{order['formatted_info']}\n\n"
            
            return {
                "success": True,
                "message": response_message,
                "orders": orders,
                "is_multi_order": len(orders) > 1
            }
            
        except Exception as e:
            logger.error(f"Error getting all user orders: {e}")
            return {
                "success": False,
                "message": "Sorry, there was an error getting your orders. Please try again or contact us directly.",
                "contact_info": self.get_contact_info("all")
            }
    
    async def check_payment_status(self, order_id: str, telegram_id: int = None) -> Dict[str, Any]:
        """Check payment status and send confirmation if successful."""
        if not PAYMENT_SYSTEM_AVAILABLE:
            return {
                "success": False,
                "message": "Payment status checking is currently unavailable. Please contact us directly.",
                "contact_info": self.get_contact_info("all")
            }
        
        try:
            # Check payment status with Razorpay
            status_result = await self.payment_manager.check_payment_status(order_id)
            
            if not status_result["success"]:
                return {
                    "success": False,
                    "message": f"Payment status not found for order {order_id}. Please check your order ID and try again."
                }
            
            payment_status = status_result["status"]
            
            if payment_status == "paid":
                # Payment successful - get order details and send confirmation
                order_result = supabase.rpc("get_order_details", {"p_order_id": order_id}).execute()
                
                if order_result.data:
                    order_data = order_result.data[0]["order_data"]
                    items_data = order_result.data[0]["items_data"]
                    amount = order_data.get("total_amount", 0)
                    
                    # Send payment success message ONLY to the specific user who made the payment
                    if telegram_id:
                        logger.info(f"Sending manual payment confirmation for order {order_id} to user {telegram_id}")
                        from gurtoy_bot_polling import send_payment_success_message
                        await send_payment_success_message(telegram_id, order_id, amount)
                        logger.info(f"Manual payment confirmation sent to user {telegram_id} for order {order_id}")
                    
                    return {
                        "success": True,
                        "message": f"✅ **Payment Successful!**\n\n📦 **Order ID:** {order_id}\n💰 **Amount Paid:** Rs {amount}\n\nYour payment has been confirmed and your order is being processed!",
                        "payment_status": "paid",
                        "order_id": order_id
                    }
                else:
                    return {
                        "success": True,
                        "message": f"✅ **Payment Successful!**\n\n📦 **Order ID:** {order_id}\n\nYour payment has been confirmed!",
                        "payment_status": "captured",
                        "order_id": order_id
                    }
            
            elif payment_status == "failed":
                return {
                    "success": True,
                    "message": f"❌ **Payment Failed**\n\n📦 **Order ID:** {order_id}\n\nYour payment could not be processed. Please try again or contact us for assistance.",
                    "payment_status": "failed",
                    "order_id": order_id
                }
            
            else:
                # Payment still pending
                return {
                    "success": True,
                    "message": f"⏳ **Payment Pending**\n\n📦 **Order ID:** {order_id}\n\nYour payment is still being processed. Please wait a moment and try again.",
                    "payment_status": payment_status,
                    "order_id": order_id
                }
            
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return {
                "success": False,
                "message": "Sorry, there was an error checking your payment status. Please try again or contact us directly.",
                "contact_info": self.get_contact_info("all")
            }
    
    async def handle_function_call(self, function_call, user_id: int = None, telegram_id: int = None, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle function calls from the AI model.
        
        Args:
            function_call: The function call from the AI
            user_id: Database user ID
            telegram_id: Telegram user ID (used for buy_product and other functions)
            user_context: Full user context (for product switching detection)
        """
        function_name = function_call.name
        args = function_call.args
        
        try:
            if function_name == "search_knowledge":
                results = await self.search_knowledge(args.get("query"), args.get("category", "all"))
                return {
                    "function": function_name,
                    "success": True,
                    "results": [
                        {
                            "title": r.title,
                            "content": r.content,
                            "category": r.category,
                            "similarity": r.similarity
                        }
                        for r in results
                    ]
                }
            
            elif function_name == "search_products":
                products = await self.search_products(
                    query=args.get("query"),
                    category=args.get("category", "all"),
                    min_price=args.get("min_price"),
                    max_price=args.get("max_price"),
                    age_range=None  # Don't use age_range parameter - age should be in query string
                )
                return {
                    "function": function_name,
                    "success": True,
                    "products": [
                        {
                            "product_id": p["product_id"],
                            "title": p["title"],
                            "category": p["category"],
                            "description": p["description"],
                            "age_range": p["age_range"],
                            "price": p["price"],
                            "discount_price": p["discount_price"],
                            "colors": p["colors"],
                            "specifications": p["specifications"],
                            "images": p["images"],  # FIXED: Added missing images field
                            "stock_status": p["stock_status"],  # FIXED: Added missing stock_status field
                            "warranty": p["warranty"],  # FIXED: Added missing warranty field
                            "similarity": p["similarity"]
                        }
                        for p in products
                    ],
                    "count": len(products)
                }
            
            elif function_name == "intelligent_search":
                products = await self.intelligent_search(
                    user_query=args.get("user_query"),
                    search_intent=args.get("search_intent"),
                    priority_keywords=args.get("priority_keywords")
                )
                return {
                    "function": function_name,
                    "success": True,
                    "products": [
                        {
                            "product_id": p["product_id"],
                            "title": p["title"],
                            "category": p["category"],
                            "description": p["description"],
                            "age_range": p["age_range"],
                            "price": p["price"],
                            "discount_price": p["discount_price"],
                            "colors": p["colors"],
                            "specifications": p["specifications"],
                            "images": p["images"],
                            "stock_status": p["stock_status"],
                            "warranty": p["warranty"],
                            "similarity": p["similarity"],
                            "llm_relevance_score": p.get("llm_relevance_score", p["similarity"]),
                            "llm_reason": p.get("llm_reason", "semantic match")
                        }
                        for p in products
                    ],
                    "count": len(products),
                    "search_method": "intelligent_llm_driven"
                }
            
            elif function_name == "get_contact_info":
                contact_info = self.get_contact_info(args.get("info_type", "all"))
                return {
                    "function": function_name,
                    "contact_info": contact_info
                }
            
            elif function_name == "escalate_to_human":
                success = await self.escalate_to_human(
                    user_id, session_id, 
                    args.get("reason"), 
                    args.get("priority", "medium")
                )
                return {
                    "function": function_name,
                    "escalated": success,
                    "message": "Your request has been forwarded to our team. We'll get back to you soon!" if success else "Sorry, there was an issue with your request."
                }
            
            elif function_name == "buy_product":
                result = await self.buy_product(
                    product_id=args.get("product_id"),
                    quantity=args.get("quantity", 1),
                    selected_color=args.get("selected_color"),
                    user_context=user_context
                )
                return {
                    "function": function_name,
                    **result
                }
            
            elif function_name == "switch_product":
                result = await self.switch_product(
                    product_id=args.get("product_id"),
                    reason=args.get("reason"),
                    telegram_id=telegram_id
                )
                return {
                    "function": function_name,
                    **result
                }
            
            elif function_name == "check_order_status":
                result = await self.check_order_status(args.get("order_id"))
                return {
                    "function": function_name,
                    **result
                }
            
            elif function_name == "check_payment_status":
                result = await self.check_payment_status(
                    order_id=args.get("order_id"),
                    telegram_id=telegram_id
                )
                return {
                    "function": function_name,
                    **result
                }
            
            elif function_name == "get_recent_orders":
                result = await self.get_recent_orders(
                    user_id=user_id,
                    limit=args.get("limit", 5)
                )
                return {
                    "function": function_name,
                    **result
                }
            
            elif function_name == "get_all_user_orders":
                result = await self.get_all_user_orders(user_id=user_id)
                return {
                    "function": function_name,
                    **result
                }
                
        except Exception as e:
            logger.error(f"Error handling function call {function_name}: {e}")
            return {"error": str(e)}
    
    def extract_conversation_context(self, recent_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract key information (age, color, budget, product type) from recent messages.
        Enhanced with intelligent processing and conversation analysis.
        """
        import re
        from datetime import datetime, timedelta
        
        context = {
            "age": None,
            "gender": None,
            "color_preference": None,
            "budget_max": None,
            "product_type": None,
            "delivery_address_mentioned": False,
            "conversation_summary": "",
            "key_preferences": [],
            "recent_intent": None,
            "conversation_stage": "initial"
        }
        
        if not recent_messages:
            return context
        
        # Intelligent message processing with recency weighting
        user_messages = []
        assistant_messages = []
        message_weights = []
        
        for i, msg in enumerate(recent_messages):
            content = msg.get("content", "").lower()
            msg_type = msg.get("message_type", "")
            created_at = msg.get("created_at", "")
            
            # Weight recent messages more heavily
            weight = 1.0 + (i * 0.1)  # More recent = higher weight
            
            if msg_type == "user":
                user_messages.append(content)
                message_weights.append(weight)
            elif msg_type == "assistant":
                assistant_messages.append(content)
        
        # Combine user messages with weighted importance
        combined_text = " ".join(user_messages)
        
        # Analyze conversation stage
        if any(word in combined_text for word in ["buy", "purchase", "order", "khareed", "leni"]):
            context["conversation_stage"] = "purchasing"
        elif any(word in combined_text for word in ["price", "cost", "kitna", "rate"]):
            context["conversation_stage"] = "pricing"
        elif any(word in combined_text for word in ["show", "dikhao", "options", "choices"]):
            context["conversation_stage"] = "browsing"
        elif any(word in combined_text for word in ["delivery", "address", "pincode", "shipping"]):
            context["conversation_stage"] = "delivery"
        
        # Extract recent intent from last few messages
        recent_text = " ".join(user_messages[:3])  # Last 3 user messages
        if any(word in recent_text for word in ["correction", "wrong", "change", "galat"]):
            context["recent_intent"] = "correction"
        elif any(word in recent_text for word in ["more", "aur", "other", "different"]):
            context["recent_intent"] = "more_options"
        elif any(word in recent_text for word in ["buy", "purchase", "order"]):
            context["recent_intent"] = "purchase"
        
        # Enhanced age extraction with more patterns
        age_patterns = [
            r'(\d+)\s*saal',  # "3 saal", "5 saal ka"
            r'(\d+)\s*year',  # "3 year old", "5 years"
            r'(\d+)\s*sal',   # "3 sal ka"
            r'(\d+)\s*month', # "18 month old"
            r'(\d+)\s*mahine', # "18 mahine ka"
            r'age\s*(\d+)',   # "age 5"
            r'(\d+)\s*ke\s*liye', # "5 ke liye"
        ]
        
        # Find most recent age mention (weighted by recency)
        best_age_match = None
        best_weight = 0
        
        for i, pattern in enumerate(age_patterns):
            for j, text in enumerate(user_messages):
                match = re.search(pattern, text)
            if match:
                    weight = message_weights[j] if j < len(message_weights) else 1.0
                    if weight > best_weight:
                        best_age_match = int(match.group(1))
                        best_weight = weight
        
        if best_age_match:
            context["age"] = best_age_match
        
        # Enhanced gender extraction
        gender_words = {
            "girl": ["beti", "daughter", "girl", "ladki", "female", "bachi"],
            "boy": ["beta", "bete", "son", "boy", "ladka", "male", "bacha"]
        }
        
        for gender, words in gender_words.items():
            for word in words:
                if word in combined_text:
                    context["gender"] = gender
                    break
            if context["gender"]:
                break
        
        # Enhanced color preference extraction
        color_mapping = {
            "red": ["red", "lal", "rang"],
            "blue": ["blue", "neela", "neeli"],
            "pink": ["pink", "gulabi"],
            "green": ["green", "hara", "hari"],
            "yellow": ["yellow", "peela", "peeli"],
            "orange": ["orange", "narangi"],
            "purple": ["purple", "jamuni"],
            "white": ["white", "safed", "safedi"],
            "black": ["black", "kala", "kali"],
            "grey": ["grey", "gray", "surahi"]
        }
        
        colors_found = []
        for color, variants in color_mapping.items():
            for variant in variants:
                if variant in combined_text:
                    colors_found.append(color)
                    break
        
        if colors_found:
            # Use most recent color mentioned
            context["color_preference"] = colors_found[0]
        
        # Enhanced budget extraction
        budget_patterns = [
            r'(\d+)\s*se\s*kam',  # "3000 se kam"
            r'under\s*(\d+)',     # "under 5000"
            r'below\s*(\d+)',     # "below 2000"
            r'budget\s*(\d+)',    # "budget 2000"
            r'(\d+)\s*tak',       # "5000 tak"
            r'(\d+)\s*rupees',    # "3000 rupees"
            r'(\d+)\s*rs',        # "3000 rs"
            r'₹(\d+)',            # "₹3000"
        ]
        
        best_budget_match = None
        best_budget_weight = 0
        
        for pattern in budget_patterns:
            for j, text in enumerate(user_messages):
                match = re.search(pattern, text)
            if match:
                    weight = message_weights[j] if j < len(message_weights) else 1.0
                    if weight > best_budget_weight:
                        best_budget_match = int(match.group(1))
                        best_budget_weight = weight
        
        if best_budget_match:
            context["budget_max"] = best_budget_match
        
        # Enhanced product type extraction
        product_types = {
            "bike": ["bike", "cycle", "scooter", "electric bike", "motorcycle"],
            "jeep": ["jeep", "car", "toy car", "vehicle", "gaadi"],
            "soft toy": ["soft toy", "teddy", "bear", "doll", "stuffed"],
            "educational": ["educational", "learning", "puzzle", "blocks", "books"],
            "outdoor": ["outdoor", "swing", "slide", "playground", "garden"],
            "electronic": ["electronic", "music", "lights", "sound", "battery"]
        }
        
        for product_type, keywords in product_types.items():
            if any(keyword in combined_text for keyword in keywords):
                context["product_type"] = product_type
                break
        
        # Enhanced delivery address detection
        address_indicators = [
            "delivery", "address", "pincode", "shipping", "home", "house",
            "street", "road", "colony", "sector", "block", "flat", "apartment"
        ]
        
        if any(indicator in combined_text for indicator in address_indicators):
                context["delivery_address_mentioned"] = True
        
        # Generate conversation summary
        summary_parts = []
        if context["age"]:
            summary_parts.append(f"Child age: {context['age']} years")
        if context["gender"]:
            summary_parts.append(f"Gender: {context['gender']}")
        if context["color_preference"]:
            summary_parts.append(f"Color preference: {context['color_preference']}")
        if context["budget_max"]:
            summary_parts.append(f"Budget: under ₹{context['budget_max']}")
        if context["product_type"]:
            summary_parts.append(f"Looking for: {context['product_type']}")
        
        context["conversation_summary"] = "; ".join(summary_parts) if summary_parts else "Initial conversation"
        
        # Extract key preferences for better context
        preferences = []
        if context["age"]:
            preferences.append(f"age_{context['age']}")
        if context["gender"]:
            preferences.append(f"gender_{context['gender']}")
        if context["color_preference"]:
            preferences.append(f"color_{context['color_preference']}")
        
        context["key_preferences"] = preferences
        
        return context
    
    async def generate_response(self, user_message: str, user_context: Dict[str, Any] = None) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        """
        Generate AI response to user message with rate limit handling.
        Returns: (response_text, products_to_show)
        """
        max_retries = 3
        base_delay = 2  # seconds
        products_to_show = None
        
        for attempt in range(max_retries):
            try:
                # Start chat with context if available
                chat = self.model.start_chat(history=[])
                
                # Add context to the message if available
                if user_context:
                    # 🔥 STEP 1: Load persistent session context (stored from previous turns)
                    session_id = user_context.get("session_data", {}).get("id")
                    user_id = user_context.get("user_id")
                    session_context = {}
                    if session_id:
                        session_context = await UserManager.get_session_context(session_id)
                    
                    # 🔥 STEP 2: Extract key context from recent messages programmatically
                    recent_messages = user_context.get("recent_messages", [])
                    extracted_context = self.extract_conversation_context(recent_messages)
                    
                    # 🔥 STEP 3: Merge session context with extracted context
                    # Session context takes priority (persistent across turns)
                    # Extracted context fills in any missing values
                    merged_context = {**extracted_context, **session_context}
                    
                    # 🔥 STEP 4: Save updated context back to session for next turn
                    if session_id and user_id and merged_context:
                        await UserManager.save_session_context(user_id, session_id, merged_context)
                    
                    # Debug logging
                    logger.info(f"📂 Session context: {session_context}")
                    logger.info(f"🔍 Extracted context: {extracted_context}")
                    logger.info(f"🔄 Merged context: {merged_context}")
                    logger.info(f"📝 Recent messages count: {len(recent_messages)}")
                    
                    # 🔥 STEP 5: Build INTELLIGENT context reminder for AI
                    context_reminder = ""
                    has_context = False
                    
                    # Enhanced context with conversation intelligence
                    if merged_context.get("age"):
                        context_reminder += f"\n🧠 REMEMBERED: Child age is {merged_context['age']} years old - Use this directly!\n"
                        has_context = True
                    if merged_context.get("gender"):
                        context_reminder += f"\n🧠 REMEMBERED: Child is {merged_context['gender']} - Use this directly!\n"
                        has_context = True
                    if merged_context.get("color_preference"):
                        context_reminder += f"\n🧠 REMEMBERED: Preferred color is {merged_context['color_preference']} - Use this directly!\n"
                        has_context = True
                    if merged_context.get("budget_max"):
                        context_reminder += f"\n🧠 REMEMBERED: Budget is under ₹{merged_context['budget_max']} - Use this directly!\n"
                        has_context = True
                    if merged_context.get("product_type"):
                        context_reminder += f"\n🧠 REMEMBERED: Looking for {merged_context['product_type']} - Use this directly!\n"
                        has_context = True
                    if merged_context.get("delivery_address_mentioned"):
                        context_reminder += f"\n🧠 REMEMBERED: User provided delivery address - Don't ask again!\n"
                        has_context = True
                    
                    # Add conversation intelligence
                    if merged_context.get("conversation_stage"):
                        context_reminder += f"\n🎯 CONVERSATION STAGE: {merged_context['conversation_stage'].upper()}\n"
                        has_context = True
                    if merged_context.get("recent_intent"):
                        context_reminder += f"\n🎯 RECENT INTENT: {merged_context['recent_intent'].upper()}\n"
                        has_context = True
                    if merged_context.get("conversation_summary"):
                        context_reminder += f"\n📋 CONVERSATION SUMMARY: {merged_context['conversation_summary']}\n"
                        has_context = True
                    
                    if has_context:
                        # Make it IMPOSSIBLE to miss
                        context_reminder = f"""
{'='*80}
🔴🔴🔴 MANDATORY CONTEXT - YOU ALREADY KNOW THIS INFORMATION 🔴🔴🔴
{'='*80}
{context_reminder}
{'='*80}
⛔ CRITICAL INSTRUCTION: DO NOT ASK FOR ANY OF THE ABOVE INFORMATION! ⛔
⛔ YOU ALREADY KNOW THIS! USE IT DIRECTLY IN YOUR RESPONSE! ⛔
{'='*80}

"""
                    else:
                        context_reminder = ""  # No extracted context to show
                    
                    # Combine context reminder with full user context
                    context_message = f"{context_reminder}User context: {json.dumps(user_context, indent=2)}\n\nUser message: {user_message}"
                else:
                    context_message = user_message
                
                # Send message to AI
                response = chat.send_message(context_message)
                
                # If successful, break out of retry loop
                break
                
            except google_exceptions.ResourceExhausted as e:
                # Rate limit exceeded
                if attempt < max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Max retries reached
                    logger.error(f"Rate limit exceeded after {max_retries} attempts: {e}")
                    return ("I'm currently experiencing high demand. Please try again in a moment, or contact us directly at 8300000086. 🙏", None)
            
            except Exception as e:
                # Other errors - don't retry
                logger.error(f"Error generating AI response: {e}", exc_info=True)
                return ("I'm experiencing some technical difficulties. Please contact us directly at 8300000086 for immediate assistance. 🙏", None)
        
        try:
            
            # Check if AI wants to call a function
            # Safely check for function call without accessing response.text first
            # IMPORTANT: Gemini can return multiple parts (text + function_call), so we need to check ALL parts
            if (response.candidates and 
                len(response.candidates) > 0 and 
                response.candidates[0].content.parts and 
                len(response.candidates[0].content.parts) > 0):
                
                # Iterate through all parts to find function_call (it may not be in parts[0])
                function_call = None
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        function_call = part.function_call
                        break
                
                # If a function call was found, handle it
                if function_call:
                    logger.info(f"AI called function: {function_call.name}")
                    
                    # Handle the function call
                    # Pass both user_id and telegram_id for proper function handling
                    function_result = await self.handle_function_call(
                        function_call,
                        user_context.get("user_id") if user_context else None,
                        user_context.get("telegram_id") if user_context else None,
                        user_context
                    )
                    
                    # Store products if search_products was called
                    if function_call.name == "search_products" and "products" in function_result:
                        products_to_show = function_result["products"]
                        logger.info(f"Stored {len(products_to_show)} products to show")
                    
                    # Store products if intelligent_search was called
                    if function_call.name == "intelligent_search" and "products" in function_result:
                        products_to_show = function_result["products"]
                        logger.info(f"Stored {len(products_to_show)} products from intelligent search to show")
                    
                    # CRITICAL FIX: For buy_product, use function result directly
                    # The AI was calling the function but then generating its own response
                    # instead of using the detailed order collection message from the function
                    if function_call.name == "buy_product" and "message" in function_result:
                        logger.info("Using buy_product function result message directly")
                        return (function_result["message"], None)
                    
                    # Send function result back to AI using protobuf format
                    # This is the correct format for google-generativeai SDK
                    import google.ai.generativelanguage as glm
                    
                    # Enhanced function response with better error handling
                    try:
                        function_response = glm.Part(
                            function_response=glm.FunctionResponse(
                                name=function_call.name,
                                response={"result": function_result}
                            )
                        )
                    
                        # Send the function response back to the model
                        response = chat.send_message(function_response)
                        
                        # Log successful function execution
                        logger.info(f"Function {function_call.name} executed successfully")
                        
                    except Exception as e:
                        logger.error(f"Error sending function response for {function_call.name}: {e}")
                        # Continue with normal response processing
            
            # Safely access response.text
            # Check if response has text before accessing it
            if (response.candidates and 
                len(response.candidates) > 0 and 
                response.candidates[0].content.parts):
                
                # Try to get text from parts
                text_parts = []
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)
                
                if text_parts:
                    raw_response = " ".join(text_parts)
                    
                    # DEBUG: Log what AI actually returned
                    logger.info(f"🤖 AI raw response: '{raw_response}'")
                    logger.info(f"🤖 Products to show: {len(products_to_show) if products_to_show else 0}")
                    
                    # Check if AI wants to show products
                    if "SHOW_PRODUCTS" in raw_response:
                        # FIXED: Always return the marker if AI wants to show products
                        # Even if products_to_show is empty - the calling code will handle it
                        logger.info("✅ AI returned SHOW_PRODUCTS marker")
                        return ("SHOW_PRODUCTS", products_to_show if products_to_show else [])
                    else:
                        logger.warning(f"⚠️ AI did NOT return SHOW_PRODUCTS. Response: '{raw_response}'")
                    
                    # Apply formatting cleanup
                    formatted_response = MessageFormatter.ensure_proper_structure(raw_response)
                    
                    # Check if this is an order-related response that should not be truncated
                    is_order_response = any(keyword in raw_response.lower() for keyword in [
                        "order:", "orders:", "aapke saare orders", "aapka recent order", 
                        "order id:", "payment successful", "order created successfully"
                    ])
                    
                    # Don't enforce length limit for questions or order responses
                    if len(formatted_response) > 300 and "?" not in formatted_response[-50:] and not is_order_response:
                        final_response = MessageFormatter.enforce_length_limit(formatted_response, max_length=300)
                    else:
                        final_response = formatted_response
                    
                    return (final_response, None)
            
            # Fallback if no text found
            return ("I'm sorry, I couldn't generate a response. Please try again.", None)
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}", exc_info=True)
            return ("I'm experiencing some technical difficulties. Please contact us directly at 8300000086 for immediate assistance. 🙏", None)

# Initialize AI assistant
gurtoy_ai = GurtoyAI()

class UserManager:
    """Manages user data and sessions."""
    
    @staticmethod
    async def get_or_create_user(telegram_user: TelegramUser) -> Dict[str, Any]:
        """Get existing user or create new one."""
        try:
            # Try to get existing user (without .single() to avoid 406 error on empty result)
            result = supabase.table("users").select("*").eq("telegram_id", telegram_user.id).execute()
            
            if result.data and len(result.data) > 0:
                # Update last active
                supabase.rpc("update_user_activity", {"telegram_user_id": telegram_user.id}).execute()
                return result.data[0]
            else:
                # Create new user
                new_user = {
                    "telegram_id": telegram_user.id,
                    "username": telegram_user.username,
                    "first_name": telegram_user.first_name,
                    "last_name": telegram_user.last_name,
                    "language_code": telegram_user.language_code or "en"
                }
                
                result = supabase.table("users").insert(new_user).execute()
                return result.data[0]
                
        except Exception as e:
            logger.error(f"Error managing user {telegram_user.id}: {e}")
            return None
    
    @staticmethod
    async def get_user_context(telegram_id: int) -> Dict[str, Any]:
        """Get user context including session and recent messages."""
        try:
            result = supabase.rpc("get_user_context", {"telegram_user_id": telegram_id}).execute()
            
            if result.data:
                return result.data[0]
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting user context for {telegram_id}: {e}")
            return {}
    
    @staticmethod
    async def log_conversation(user_id: int, session_id: int, message_type: str, content: str, intent: str = None, response_time_ms: int = None):
        """Log conversation for analytics."""
        try:
            log_entry = {
                "user_id": user_id,
                "session_id": session_id,
                "message_type": message_type,
                "content": content,
                "intent": intent,
                "response_time_ms": response_time_ms
            }
            
            supabase.table("conversation_logs").insert(log_entry).execute()
            
        except Exception as e:
            logger.error(f"Error logging conversation: {e}")
    
    @staticmethod
    async def save_session_context(user_id: int, session_id: int, context_data: Dict[str, Any]):
        """
        Save extracted context to session for persistent memory across conversation turns.
        This ensures the bot doesn't forget important information like age, color preference, budget.
        """
        try:
            # Only save non-empty context
            if not context_data:
                return
            
            # Get current session
            result = supabase.table("sessions").select("session_data").eq("id", session_id).execute()
            
            if result.data and len(result.data) > 0:
                # Merge with existing session data
                existing_data = result.data[0].get("session_data") or {}
                
                # Update with new context (new values override old ones)
                # Only update if new value is not None
                for key, value in context_data.items():
                    if value is not None:
                        existing_data[key] = value
                
                # Save back to database
                supabase.table("sessions").update({
                    "session_data": existing_data
                }).eq("id", session_id).execute()
                
                logger.info(f"💾 Saved session context for session {session_id}: {existing_data}")
            
        except Exception as e:
            logger.error(f"Error saving session context: {e}")
    
    @staticmethod
    async def get_session_context(session_id: int) -> Dict[str, Any]:
        """
        Retrieve persistent context from session storage.
        Returns extracted context that should be remembered across turns.
        """
        try:
            result = supabase.table("sessions").select("session_data").eq("id", session_id).execute()
            
            if result.data and len(result.data) > 0:
                session_data = result.data[0].get("session_data") or {}
                logger.info(f"📂 Retrieved session context for session {session_id}: {session_data}")
                return session_data
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting session context: {e}")
            return {}

class TelegramAPI:
    """Handles Telegram API interactions."""
    
    @staticmethod
    async def send_message(chat_id: int, text: str, reply_markup: Dict[str, Any] = None) -> bool:
        """Send message to Telegram chat."""
        try:
            # Ensure text is not empty and not too long
            if not text or not text.strip():
                text = "I apologize, but I couldn't generate a proper response. Please try again."
            
            # Telegram message limit is 4096 characters
            if len(text) > 4096:
                text = text[:4093] + "..."
            
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            
            if reply_markup:
                payload["reply_markup"] = reply_markup
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{config.TELEGRAM_API_URL}/sendMessage",
                    json=payload
                )
                response.raise_for_status()
                return True
                
        except httpx.HTTPStatusError as e:
            # If Markdown parsing fails, try sending without Markdown
            logger.warning(f"Markdown parsing failed, retrying without parse_mode: {e}")
            try:
                payload_plain = {
                    "chat_id": chat_id,
                    "text": text
                }
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        f"{config.TELEGRAM_API_URL}/sendMessage",
                        json=payload_plain
                    )
                    response.raise_for_status()
                    return True
            except Exception as retry_error:
                logger.error(f"Error sending plain text message: {retry_error}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    @staticmethod
    async def send_photo(chat_id: int, photo_url: str, caption: str = None) -> bool:
        """Send photo message to Telegram chat."""
        try:
            payload = {
                "chat_id": chat_id,
                "photo": photo_url,
                "parse_mode": "Markdown"
            }
            
            if caption:
                # Telegram caption limit is 1024 characters
                if len(caption) > 1024:
                    caption = caption[:1021] + "..."
                payload["caption"] = caption
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{config.TELEGRAM_API_URL}/sendPhoto",
                    json=payload
                )
                response.raise_for_status()
                return True
                
        except httpx.HTTPStatusError as e:
            # If Markdown parsing fails, try sending without Markdown
            logger.warning(f"Photo caption markdown failed, retrying without parse_mode: {e}")
            try:
                payload_plain = {
                    "chat_id": chat_id,
                    "photo": photo_url
                }
                if caption:
                    payload_plain["caption"] = caption
                    
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        f"{config.TELEGRAM_API_URL}/sendPhoto",
                        json=payload_plain
                    )
                    response.raise_for_status()
                    return True
            except Exception as retry_error:
                logger.error(f"Error sending photo without markdown: {retry_error}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            return False
    
    @staticmethod
    async def send_product_cards(chat_id: int, products: List[Dict[str, Any]]) -> bool:
        """Send product cards with images to user."""
        try:
            if not products:
                await TelegramAPI.send_message(
                    chat_id, 
                    "Sorry, main koi product nahi dhoondh payi. Kya aap kuch aur try karna chahenge? 😊"
                )
                return False
            
            # Send intro message
            intro_text = f"✨ Maine **{len(products)} products** dhoondhе hain aapke liye:\n\n"
            await TelegramAPI.send_message(chat_id, intro_text)
            
            # Small delay to ensure intro message is sent first
            await asyncio.sleep(0.3)
            
            # Send each product as a separate card with image
            for idx, product in enumerate(products, 1):
                try:
                    # Get first image URL
                    images = product.get("images", [])
                    if isinstance(images, str):
                        import json
                        images = json.loads(images)
                    
                    image_url = images[0] if images and len(images) > 0 else None
                    
                    # Format product caption
                    title = product.get("title", "Product")
                    age_range = product.get("age_range", "N/A")
                    price = product.get("price", 0)
                    discount_price = product.get("discount_price", price)
                    description = product.get("description", "")
                    
                    # Get specifications
                    specs = product.get("specifications", {})
                    if isinstance(specs, str):
                        import json
                        specs = json.loads(specs)
                    
                    battery = specs.get("battery", "")
                    features = specs.get("features", [])
                    if isinstance(features, str):
                        features = [features]
                    
                    # Get colors
                    colors = product.get("colors", [])
                    if isinstance(colors, str):
                        import json
                        colors = json.loads(colors)
                    
                    # Build caption
                    caption = f"🎯 **{title}**\n\n"
                    caption += f"👶 **Age:** {age_range}\n"
                    # Add product ID for purchase functionality (hidden in caption)
                    caption += f"🆔 **ID:** {product.get('product_id', 'N/A')}\n"
                    
                    # Price display logic
                    if discount_price and discount_price < price:
                        # Show discounted price with strikethrough original
                        caption += f"💰 **Price:** ~~₹{int(price):,}~~ → **₹{int(discount_price):,}**\n"
                        caption += f"🎁 **Special Offer!** Pay only ₹{int(discount_price):,}"
                    else:
                        # Show regular price
                        caption += f"💰 **Price:** ₹{int(price):,}"
                    
                    caption += "\n\n"
                    
                    # Add key features (first 2 lines of description)
                    desc_lines = description.split('\n')
                    short_desc = desc_lines[0] if desc_lines else ""
                    if len(short_desc) > 100:
                        short_desc = short_desc[:97] + "..."
                    caption += f"📝 {short_desc}\n\n"
                    
                    # Add specifications
                    if battery:
                        caption += f"🔋 **Battery:** {battery}\n"
                    
                    if colors:
                        colors_str = ", ".join(colors[:3])  # Show max 3 colors
                        caption += f"🎨 **Colors:** {colors_str}\n"
                    
                    if features:
                        features_str = ", ".join(features[:3])  # Show max 3 features
                        caption += f"✨ **Features:** {features_str}\n"
                    
                    caption += f"\n📞 **Order:** Call {config.BUSINESS_PHONE}"
                    
                    # Send product card
                    if image_url:
                        success = await TelegramAPI.send_photo(chat_id, image_url, caption)
                    else:
                        # If no image, send as text message
                        success = await TelegramAPI.send_message(chat_id, caption)
                    
                    if not success:
                        logger.warning(f"Failed to send product card {idx}/{len(products)}")
                    
                    # Small delay between products to avoid rate limiting
                    if idx < len(products):
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.error(f"Error sending product card {idx}: {e}")
                    continue
            
            # Send closing message
            await asyncio.sleep(0.3)
            closing_text = "💬 Kya aapko koi product pasand aaya? Ya aur options chahiye? 😊"
            await TelegramAPI.send_message(chat_id, closing_text)
            
            # Store recently shown products in session for purchase context
            await SessionManager.store_recent_products(chat_id, products)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending product cards: {e}")
            return False
    
    @staticmethod
    async def send_document(
        chat_id: int, 
        document_path: str,
        caption: str = None,
        filename: str = None
    ) -> bool:
        """
        Send PDF document to user.
        
        Args:
            chat_id: Telegram chat ID
            document_path: Path to PDF file
            caption: Optional caption for the document
            filename: Optional custom filename
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(document_path):
                logger.error(f"Document not found: {document_path}")
                return False
            
            url = f"{config.TELEGRAM_API_URL}/sendDocument"
            
            with open(document_path, 'rb') as doc:
                files = {'document': (filename or 'document.pdf', doc, 'application/pdf')}
                data = {'chat_id': chat_id}
                if caption:
                    data['caption'] = caption
                
                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.post(url, data=data, files=files)
                    response.raise_for_status()
                    logger.info(f"Document sent successfully to chat {chat_id}")
                    return True
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error sending document: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Error sending document to chat {chat_id}: {e}", exc_info=True)
            return False

class SessionManager:
    """Manages user session data including recently shown products."""
    
    @staticmethod
    async def store_recent_products(telegram_id: int, products: List[Dict[str, Any]]) -> bool:
        """Store recently shown products in user session for purchase context."""
        try:
            if not supabase:
                return False
                
            # Get user ID
            user_result = supabase.table("users").select("id").eq("telegram_id", telegram_id).execute()
            if not user_result.data:
                logger.warning(f"User not found for telegram_id: {telegram_id}")
                return False
                
            user_id = user_result.data[0]["id"]
            
            # Prepare recent products data (store essential info for purchase)
            recent_products = []
            for product in products[:5]:  # Store max 5 recent products
                recent_products.append({
                    "product_id": product.get("product_id"),
                    "product_name": product.get("title", ""),
                    "price": product.get("price", 0),
                    "discount_price": product.get("discount_price"),
                    "age_range": product.get("age_range", ""),
                    "colors": product.get("colors", []),
                    "shown_at": datetime.now(timezone.utc).isoformat()
                })
            
            # Update or create session with recent products
            session_data = {
                "recent_products": recent_products,
                "last_product_show": datetime.now(timezone.utc).isoformat()
            }
            
            # Try to update existing session first
            existing_session = supabase.table("sessions").select("id").eq("user_id", user_id).eq("telegram_chat_id", telegram_id).execute()
            
            if existing_session.data:
                # Update existing session
                session_id = existing_session.data[0]["id"]
                supabase.table("sessions").update({
                    "session_data": session_data,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", session_id).execute()
            else:
                # Create new session
                supabase.table("sessions").insert({
                    "user_id": user_id,
                    "telegram_chat_id": telegram_id,
                    "session_data": session_data,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
                }).execute()
            
            logger.info(f"✅ Stored {len(recent_products)} recent products for user {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing recent products: {e}")
            return False
    
    @staticmethod
    async def get_recent_products(telegram_id: int) -> List[Dict[str, Any]]:
        """Get recently shown products from user session."""
        try:
            if not supabase:
                return []
                
            # Get user ID
            user_result = supabase.table("users").select("id").eq("telegram_id", telegram_id).execute()
            if not user_result.data:
                return []
                
            user_id = user_result.data[0]["id"]
            
            # Get recent session data
            session_result = supabase.table("sessions").select("session_data").eq("user_id", user_id).eq("telegram_chat_id", telegram_id).order("updated_at", desc=True).limit(1).execute()
            
            if not session_result.data:
                return []
                
            session_data = session_result.data[0].get("session_data", {})
            recent_products = session_data.get("recent_products", [])
            
            # Filter products shown in last 30 minutes (for purchase context)
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=30)
            valid_products = []
            
            for product in recent_products:
                try:
                    shown_at_str = product.get("shown_at", "")
                    # Handle both timezone-aware and timezone-naive ISO strings
                    if shown_at_str.endswith('Z'):
                        shown_at_str = shown_at_str[:-1] + '+00:00'
                    elif '+' not in shown_at_str and 'T' in shown_at_str:
                        shown_at_str += '+00:00'
                    
                    shown_at = datetime.fromisoformat(shown_at_str)
                    
                    # Ensure both datetimes are timezone-aware for comparison
                    if shown_at.tzinfo is None:
                        shown_at = shown_at.replace(tzinfo=timezone.utc)
                    
                    if shown_at > cutoff_time:
                        valid_products.append(product)
                except Exception as e:
                    logger.warning(f"Error parsing product timestamp: {e}")
                    continue
            
            logger.info(f"📦 Retrieved {len(valid_products)} recent products for user {telegram_id}")
            return valid_products
            
        except Exception as e:
            logger.error(f"Error getting recent products: {e}")
            return []

# API Routes
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Gurtoy Telegram Bot",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check."""
    try:
        # Test Supabase connection
        supabase.table("gurtoy_knowledge").select("count").limit(1).execute()
        supabase_status = "healthy"
    except:
        supabase_status = "unhealthy"
    
    return {
        "status": "healthy",
        "services": {
            "supabase": supabase_status,
            "gemini": "healthy" if config.GEMINI_API_KEY else "not_configured"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming Telegram updates."""
    try:
        update_data = await request.json()
        update = TelegramUpdate(**update_data)
        
        if not update.message or not update.message.text:
            return {"status": "ignored", "reason": "no_text_message"}
        
        # Process message in background
        background_tasks.add_task(process_telegram_message, update)
        
        return {"status": "accepted"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/razorpay/webhook")
async def razorpay_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Razorpay payment webhooks."""
    if not PAYMENT_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Payment system not available")
    
    try:
        # Get raw body and headers
        body = await request.body()
        signature = request.headers.get("X-Razorpay-Signature")
        
        if not signature:
            logger.warning("Razorpay webhook received without signature")
            raise HTTPException(status_code=400, detail="Missing signature")
        
        # Verify webhook signature
        webhook_verified = gurtoy_ai.payment_manager.verify_webhook_signature(
            body.decode('utf-8'), signature
        )
        
        if not webhook_verified:
            logger.warning("Razorpay webhook signature verification failed")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Parse webhook data
        webhook_data = json.loads(body.decode('utf-8'))
        
        # Process webhook in background
        background_tasks.add_task(process_razorpay_webhook, webhook_data)
        
        return {"status": "accepted"}
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in Razorpay webhook")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Error processing Razorpay webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def process_telegram_message(update: TelegramUpdate):
    """Process incoming Telegram message."""
    start_time = datetime.utcnow()
    
    try:
        message = update.message
        telegram_user = message.from_user
        chat_id = message.chat["id"]
        user_text = message.text
        
        logger.info(f"Processing message from user {telegram_user.id}: {user_text[:50]}...")
        
        # Get or create user
        user_data = await UserManager.get_or_create_user(telegram_user)
        if not user_data:
            await TelegramAPI.send_message(chat_id, "Sorry, I'm having trouble accessing your profile. Please try again later.")
            return
        
        # Get user context
        user_context = await UserManager.get_user_context(telegram_user.id)
        user_context["user_id"] = user_data["id"]
        
        logger.info(f"[DEBUG] User context created for user {telegram_user.id}")
        
        # PHASE 3: Intelligent Response System Preprocessing
        if INTELLIGENT_RESPONSE_SYSTEM_AVAILABLE and gurtoy_ai.intelligent_response_system:
            try:
                logger.info(f"[PHASE3] Starting intelligent message preprocessing for user {telegram_user.id}")
                
                # Create enhanced message context
                message_context = MessageContext(
                    original_message=user_text,
                    telegram_user_id=telegram_user.id,
                    chat_id=chat_id,
                    reply_to_message=message.reply_to_message.__dict__ if message.reply_to_message else None,
                    recent_messages=user_context.get("recent_messages", []),
                    user_preferences=user_context.get("session_data", {}),
                    session_data=user_context.get("session_data", {}),
                    recent_products=user_context.get("recent_products", [])
                )
                
                # Phase 3.1: Intelligent message preprocessing
                intent_analysis = await gurtoy_ai.intelligent_response_system.preprocess_message(message_context)
                logger.info(f"[PHASE3] Intent analysis: {intent_analysis.primary_intent.value} (confidence: {intent_analysis.confidence})")
                
                # Phase 3.2: Conversation flow management
                conversation_state = await gurtoy_ai.intelligent_response_system.manage_conversation_flow(
                    message_context, intent_analysis
                )
                logger.info(f"[PHASE3] Conversation state: {conversation_state.value}")
                
                # Phase 3.3: Context-aware response routing
                routing_decision = await gurtoy_ai.intelligent_response_system.route_response(
                    message_context, intent_analysis, conversation_state
                )
                logger.info(f"[PHASE3] Response routing: {routing_decision['route_type']}")
                
                # Add Phase 3 analysis to user context
                user_context["phase3_analysis"] = {
                    "intent_analysis": {
                        "primary_intent": intent_analysis.primary_intent.value,
                        "confidence": intent_analysis.confidence,
                        "requires_function_call": intent_analysis.requires_function_call,
                        "function_name": intent_analysis.function_name,
                        "function_params": intent_analysis.function_params
                    },
                    "conversation_state": conversation_state.value,
                    "routing_decision": routing_decision
                }
                
                # Handle reply-to-message context (Phase 3 enhancement)
                if message.reply_to_message and not user_context.get("replied_product"):
                    logger.info(f"[PHASE3] Processing reply-to-message context")
                    # Extract product context from replied message
                    replied_text = message.reply_to_message.text or ""
                    if any(keyword in replied_text.lower() for keyword in ["bike", "jeep", "product", "₹", "price"]):
                        # This looks like a product message, add context
                        user_context["replied_product"] = {
                            "message_text": replied_text,
                            "is_product_message": True,
                            "extracted_from_reply": True
                        }
                        logger.info(f"[PHASE3] Added reply context: {replied_text[:50]}...")
                
            except Exception as e:
                logger.error(f"[PHASE3] Error in intelligent preprocessing: {e}")
                # Continue with normal processing if Phase 3 fails
        
        # Add order collection session info to context
        if PAYMENT_SYSTEM_AVAILABLE:
            logger.info(f"[DEBUG] PAYMENT_SYSTEM_AVAILABLE is True, checking for order session")
            order_session = gurtoy_ai.order_collector.get_session(telegram_user.id)
            if order_session:
                logger.info(f"[DEBUG] Order session found, adding to context")
                user_context["active_order_session"] = {
                    "state": order_session.state.value,
                    "product": order_session.product_details.get("title", "Unknown Product"),
                    "quantity": order_session.quantity
                }
            else:
                logger.info(f"[DEBUG] No order session found for user {telegram_user.id}")
        else:
            logger.info(f"[DEBUG] PAYMENT_SYSTEM_AVAILABLE is False")
        
        # Check if user is in order collection process - MUST happen BEFORE AI processing
        if PAYMENT_SYSTEM_AVAILABLE:
            try:
                logger.info(f"[ORDER_COLLECTION] Checking for active order session for user {telegram_user.id}")
                order_session = gurtoy_ai.order_collector.get_session(telegram_user.id)
                logger.info(f"[ORDER_COLLECTION] Session check result for user {telegram_user.id}: {'Found' if order_session else 'Not found'}")
                if order_session:
                    logger.info(f"[ORDER_COLLECTION] Processing order collection input for user {telegram_user.id}")
                    # Process order collection input
                    success, response_message, order_data = gurtoy_ai.order_collector.process_user_input(
                        telegram_id=telegram_user.id,
                        user_input=user_text
                    )
                    
                    if success:
                        if order_data:
                            # Order collection completed, create payment
                            try:
                                # Create order and payment using PaymentManager (this creates both database order and Razorpay order)
                                payment_result = await gurtoy_ai.payment_manager.create_order_with_qr(
                                    user_id=user_data["id"],
                                    product_details=order_data["product_details"],
                                    customer_details=order_data["customer_details"],
                                    shipping_address=order_data["shipping_address"],
                                    quantity=order_data["quantity"]
                                )
                                
                                if payment_result["success"]:
                                    order_id = payment_result["order_id"]  # Get order ID from PaymentManager
                                    
                                    # Send payment message with real payment link
                                    if payment_result.get("payment_link_url"):
                                        # Get product details from order data
                                        product_title = order_data.get("product_details", {}).get("title", "Product")
                                        quantity = order_data.get("quantity", 1)
                                        
                                        payment_message = f"""🎉 **Order Created Successfully!**

📦 **Order ID:** {order_id}
🎯 **Product:** {product_title}
📊 **Quantity:** {quantity}
💰 **Amount:** ₹{payment_result["total_amount"]}

**Payment Instructions:**
1. Click the payment link below
2. Complete the payment within 30 minutes
3. You'll receive confirmation once payment is successful

⏰ **Payment link expires in 30 minutes**

🔗 **Payment Link:** {payment_result["payment_link_url"]}

Need help? Contact us at 8300000086"""
                                    else:
                                        # Fallback to QR code if payment link not available
                                        # Get product details from order data
                                        product_title = order_data.get("product_details", {}).get("title", "Product")
                                        quantity = order_data.get("quantity", 1)
                                        
                                        payment_message = f"""🎉 **Order Created Successfully!**

📦 **Order ID:** {order_id}
🎯 **Product:** {product_title}
📊 **Quantity:** {quantity}
💰 **Amount:** ₹{payment_result["total_amount"]}

**Payment Instructions:**
1. Scan the QR code below
2. Complete the payment within 30 minutes
3. You'll receive confirmation once payment is successful

⏰ **QR code expires in 30 minutes**

📱 **QR Code:** {payment_result.get("qr_code_url", "QR code not available")}

Need help? Contact us at 8300000086"""
                                    
                                    success = await TelegramAPI.send_message(chat_id, payment_message)
                                    
                                    if success:
                                        response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                                        await UserManager.log_conversation(
                                            user_data["id"], session_id, "assistant", payment_message,
                                            response_time_ms=response_time
                                        )
                                        logger.info(f"Real payment link sent to user {telegram_user.id} for order {order_id}")
                                    return
                                else:
                                    # Payment creation failed
                                    error_msg = f"Sorry, there was an error creating your payment: {payment_result.get('error', 'Unknown error')}. Please try again or contact us directly."
                                    await TelegramAPI.send_message(chat_id, error_msg)
                                    await UserManager.log_conversation(
                                        user_data["id"], session_id, "assistant", error_msg
                                    )
                                    logger.error(f"Payment creation failed: {payment_result.get('error')}")
                                    return
                            except Exception as e:
                                logger.error(f"Error creating payment: {e}")
                                error_msg = "Sorry, there was an error processing your payment. Please try again or contact us directly."
                                await TelegramAPI.send_message(chat_id, error_msg)
                                await UserManager.log_conversation(
                                    user_data["id"], session_id, "assistant", error_msg
                                )
                                return
                        else:
                            # Order collection in progress, send response
                            success = await TelegramAPI.send_message(chat_id, response_message)
                            
                            if success:
                                response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                                await UserManager.log_conversation(
                                    user_data["id"], session_id, "assistant", response_message,
                                    response_time_ms=response_time
                                )
                                logger.info(f"Order collection response sent to {telegram_user.first_name}")
                            return
                    else:
                        # Order collection error
                        success = await TelegramAPI.send_message(chat_id, response_message)
                        if success:
                            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                            await UserManager.log_conversation(
                                user_data["id"], session_id, "assistant", response_message,
                                response_time_ms=response_time
                            )
                        return
                else:
                    logger.info(f"No active order session found for user {telegram_user.id}, proceeding with normal AI processing")
            except Exception as e:
                logger.error(f"Error in order collection process: {e}")
        
        # Check if user replied to a message (product card)
        if message.reply_to_message:
            product_context = ProductContextExtractor.extract_product_context(message.reply_to_message)
            if product_context:
                # Add product context to user_context
                user_context["replied_product"] = product_context
                formatted_context = ProductContextExtractor.format_product_context_for_ai(product_context)
                logger.info(f"📦 User replied to product: {formatted_context}")
        
        # Add recent products to context (for purchase without reply)
        recent_products = await SessionManager.get_recent_products(telegram_user.id)
        if recent_products:
            user_context["recent_products"] = recent_products
            logger.info(f"📦 Added {len(recent_products)} recent products to context")
        
        # Log user message
        session_id = user_context.get("session_data", {}).get("id")
        await UserManager.log_conversation(
            user_data["id"], session_id, "user", user_text
        )
        
        # Generate AI response
        logger.info(f"[DEBUG] About to call AI generate_response for user {telegram_user.id}")
        ai_response, products = await gurtoy_ai.generate_response(user_text, user_context)
        logger.info(f"[DEBUG] AI response generated, length: {len(ai_response) if ai_response else 0}")
        
        # Check if we need to show products
        if ai_response == "SHOW_PRODUCTS":
            if products and len(products) > 0:
                # Send product cards instead of text response
                success = await TelegramAPI.send_product_cards(chat_id, products)
                
                if success:
                    # Log that products were shown
                    response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    log_message = f"Showed {len(products)} products"
                    await UserManager.log_conversation(
                        user_data["id"], session_id, "assistant", log_message, 
                        response_time_ms=response_time
                    )
                    logger.info(f"Successfully showed {len(products)} products to user {telegram_user.id} in {response_time}ms")
                else:
                    logger.error(f"Failed to send product cards to user {telegram_user.id}")
            else:
                # FIXED: Handle case when AI wants to show products but none were found
                # Don't send "SHOW_PRODUCTS" text to user - send a proper message
                no_products_msg = "Sorry, main koi product nahi dhoondh payi. Kya aap kuch aur try karna chahenge? 😊"
                success = await TelegramAPI.send_message(chat_id, no_products_msg)
                
                if success:
                    response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    await UserManager.log_conversation(
                        user_data["id"], session_id, "assistant", no_products_msg, 
                        response_time_ms=response_time
                    )
                    logger.warning(f"⚠️ AI wanted to show products but none were found for user {telegram_user.id}")
        else:
            # Send regular text response
            success = await TelegramAPI.send_message(chat_id, ai_response)
            
            if success:
                # Log AI response
                response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                await UserManager.log_conversation(
                    user_data["id"], session_id, "assistant", ai_response, 
                    response_time_ms=response_time
                )
                
                logger.info(f"Successfully responded to user {telegram_user.id} in {response_time}ms")
            else:
                logger.error(f"Failed to send response to user {telegram_user.id}")
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        try:
            await TelegramAPI.send_message(
                update.message.chat["id"],
                "I'm experiencing technical difficulties. Please contact us at 8300000086 for immediate assistance. 🙏"
            )
        except:
            pass

async def process_razorpay_webhook(webhook_data: Dict[str, Any]):
    """Process Razorpay webhook events."""
    try:
        event = webhook_data.get("event")
        payload = webhook_data.get("payload", {})
        
        logger.info(f"Processing Razorpay webhook event: {event}")
        
        if event == "payment.captured":
            # Payment successful
            payment_entity = payload.get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")
            payment_id = payment_entity.get("id")
            amount = payment_entity.get("amount", 0) / 100  # Convert from paise to rupees
            
            if not order_id:
                logger.warning("Payment captured webhook missing order_id")
                return
            
            # Update payment status
            result = await gurtoy_ai.payment_manager.handle_payment_success(
                order_id=order_id,
                payment_id=payment_id,
                amount=amount,
                webhook_data=webhook_data
            )
            
            if result["success"]:
                # Get order details to send confirmation
                order_result = supabase.rpc("get_order_details", {"p_order_id": order_id}).execute()
                
                if order_result.data:
                    order_data = order_result.data[0]["order_data"]
                    items_data = order_result.data[0]["items_data"]
                    
                    # Get user's telegram ID - CRITICAL for proper user targeting
                    user_result = supabase.table("users").select("telegram_id").eq("id", order_data["user_id"]).execute()
                    
                    if user_result.data:
                        telegram_id = user_result.data[0]["telegram_id"]
                        
                        # CRITICAL: Verify we have telegram_id before sending notification
                        if not telegram_id:
                            logger.error(f"Cannot send payment confirmation for order {order_id}: No telegram_id found for user {order_data['user_id']}")
                            return
                        
                        logger.info(f"Sending payment confirmation for order {order_id} to user {telegram_id} (User ID: {order_data['user_id']})")
                        
                        # Send payment confirmation ONLY to the user who made the payment
                        confirmation_msg = f"""✅ **Payment Successful!**

📦 **Order ID:** {order_id}
💰 **Amount Paid:** ₹{amount}
🎯 **Payment ID:** {payment_id}

**Your Order:**"""
                        
                        for item in items_data:
                            confirmation_msg += f"\n• {item['product_title']} (Qty: {item['quantity']})"
                        
                        confirmation_msg += f"""

📞 **Next Steps:**
• We'll process your order within 24 hours
• You'll receive shipping updates on this chat
• For any queries, contact us at 8300000086

Thank you for shopping with Gurtoy! 🎉"""
                        
                        success = await TelegramAPI.send_message(telegram_id, confirmation_msg)
                        
                        if success:
                            logger.info(f"Payment confirmation sent to user {telegram_id} for order {order_id}")
                        else:
                            logger.error(f"Failed to send payment confirmation to user {telegram_id}")
                
            else:
                logger.error(f"Failed to handle payment success for order {order_id}: {result.get('message')}")
        
        elif event == "payment.failed":
            # Payment failed
            payment_entity = payload.get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")
            
            if order_id:
                # Update payment status
                result = await gurtoy_ai.payment_manager.handle_payment_failure(
                    order_id=order_id,
                    webhook_data=webhook_data
                )
                
                if result["success"]:
                    logger.info(f"Payment failure handled for order {order_id}")
                else:
                    logger.error(f"Failed to handle payment failure for order {order_id}")
        
        else:
            logger.info(f"Unhandled Razorpay webhook event: {event}")
            
    except Exception as e:
        logger.error(f"Error processing Razorpay webhook: {e}")

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("APP_PORT", 8000))
    host = os.getenv("APP_HOST", "0.0.0.0")
    
    logger.info(f"Starting Gurtoy Telegram Bot on {host}:{port}")
    
    uvicorn.run(
        "gurtoy_bot:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )