"""
AI-Powered Order Collection System for Gurtoy Telegram Bot - Phase 3
Uses Gemini 2.5 Flash for intelligent order details extraction and validation.
"""
from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

import google.generativeai as genai
from payment_manager import AddressValidator

logger = logging.getLogger(__name__)

class OrderCollectionState(Enum):
    """States in the order collection process."""
    INITIAL = "initial"
    COLLECTING_DETAILS = "collecting_details"
    CONFIRMING_DETAILS = "confirming_details"
    CREATING_PAYMENT = "creating_payment"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PRODUCT_CHANGE_REQUESTED = "product_change_requested"  # NEW: For product switching

@dataclass
class OrderCollectionSession:
    """Represents an active order collection session."""
    user_id: int
    telegram_id: int
    state: OrderCollectionState
    product_details: Dict[str, Any]
    customer_info: Dict[str, Any]
    shipping_address: Dict[str, Any]
    quantity: int
    errors: List[str]
    step_history: List[str]
    # PHASE 2: Enhanced session management
    session_id: Optional[str] = None  # Database session ID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    preserved_customer_info: Optional[Dict[str, Any]] = None  # For product switching
    fashion_preferences: Optional[Dict[str, Any]] = None  # PHASE 4: Fashion preferences (size, color, style, occasion)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "user_id": self.user_id,
            "telegram_id": self.telegram_id,
            "state": self.state.value,
            "product_details": self.product_details,
            "customer_info": self.customer_info,
            "shipping_address": self.shipping_address,
            "fashion_preferences": self.fashion_preferences or {},
            "quantity": self.quantity,
            "errors": self.errors,
            "step_history": self.step_history,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "preserved_customer_info": self.preserved_customer_info
        }

ACTIVE_SESSION_STATES = {
    OrderCollectionState.INITIAL,
    OrderCollectionState.COLLECTING_DETAILS,
    OrderCollectionState.CONFIRMING_DETAILS,
    OrderCollectionState.PRODUCT_CHANGE_REQUESTED
}

TERMINAL_SESSION_STATES = {
    OrderCollectionState.CREATING_PAYMENT,
    OrderCollectionState.COMPLETED,
    OrderCollectionState.CANCELLED
}

class AIOrderCollector:
    """AI-powered order collection system using Gemini 2.5 Flash."""
    
    def __init__(self, supabase_client):
        """Initialize the AI Order Collector."""
        self.supabase = supabase_client
        self.active_sessions: Dict[int, OrderCollectionSession] = {}
        
        # Initialize Gemini AI
        try:
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=self._get_extraction_system_instruction(),
                tools=[self._create_extraction_tool()]
            )
            logger.info("AI Order Collector initialized with Gemini 2.5 Flash")
        except Exception as e:
            logger.error(f"Failed to initialize AI Order Collector: {e}")
            raise
    
    def _create_extraction_tool(self) -> Dict[str, Any]:
        """Create the intelligent order processing function tool."""
        return {
            "function_declarations": [
                {
                    "name": "process_order_conversation",
                    "description": "Intelligently process user messages during order collection - handle confirmations, questions, order details, corrections, and cancellations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_intent": {
                                "type": "string",
                                "enum": ["providing_details", "confirming_order", "asking_question", "correcting_info", "canceling_order"],
                                "description": "What the user is trying to do: providing_details (giving name/phone/address), confirming_order (saying yes/okay to proceed), asking_question (what details needed?), correcting_info (fixing wrong info), canceling_order (wants to stop)"
                            },
                            "extracted_info": {
                                "type": "object",
                                "properties": {
                                    "customer_info": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string", "description": "Full name of the customer"},
                                            "phone": {"type": "string", "description": "10-digit phone number"},
                                            "email": {"type": "string", "description": "Valid email address (optional)"}
                                        }
                                    },
                                    "shipping_address": {
                                        "type": "object",
                                        "properties": {
                                            "street": {"type": "string", "description": "Complete street address with house/building details"},
                                            "city": {"type": "string", "description": "City name"},
                                            "state": {"type": "string", "description": "State name"},
                                            "pincode": {"type": "string", "description": "6-digit postal code"}
                                        }
                                    },
                                    "fashion_preferences": {
                                        "type": "object",
                                        "properties": {
                                            "size": {"type": "string", "enum": ["S", "M", "L", "XL"], "description": "Preferred size for the fashion item"},
                                            "color": {"type": "string", "description": "Preferred color from available options"},
                                            "style": {"type": "string", "enum": ["casual", "formal", "traditional"], "description": "Preferred style for the occasion"},
                                            "occasion": {"type": "string", "enum": ["casual", "office", "party", "traditional"], "description": "Intended occasion for wearing"}
                                        }
                                    }
                                },
                                "description": "Extracted customer, shipping, and fashion preference information (only if user_intent is providing_details or correcting_info)"
                            },
                            "is_complete": {"type": "boolean", "description": "Whether all required information (name, phone, address, city, state, pincode, size, color) is now present"},
                            "missing_fields": {"type": "array", "items": {"type": "string"}, "description": "List of specific missing fields (e.g., 'phone number', 'complete address', 'city', 'pincode', 'size preference', 'color preference')"},
                            "correction_details": {"type": "string", "description": "Description of what was corrected (only if user_intent is correcting_info)"},
                            "response_message": {"type": "string", "description": "Intelligent, context-aware response to user in natural Hinglish"}
                        },
                        "required": ["user_intent", "extracted_info", "is_complete", "missing_fields", "response_message"]
                    }
                }
            ]
        }
    
    def _get_extraction_system_instruction(self) -> str:
        """Get system instruction for intelligent order processing."""
        return """You are an intelligent order collection assistant for Fashion Mart with a smart brain that understands context and user intent.

🧠 **YOUR INTELLIGENCE:**
You understand what users MEAN, not just what they SAY. You're context-aware and conversational.

📋 **REQUIRED ORDER INFORMATION:**
- **Customer Info:** name, phone (10 digits), email (optional)
- **Shipping Address:** street address, city, state, pincode (6 digits)
- **Fashion Details:** size preference (S, M, L, XL), color preference, style preference

🎯 **UNDERSTAND USER INTENT - Think Like a Human:**

**1. CONFIRMING_ORDER Intent:**
User says: "Yes", "Okay", "Sure", "Thik hai", "Haan", "Bilkul", "Proceed", "Continue", "All details are okay", "Sahi hai", "Correct hai"
→ They're CONFIRMING to proceed, not providing details!
→ Check current state:
   - If ALL details complete → Proceed to payment
   - If details INCOMPLETE → Tell them what's still missing
   - If just started → Guide them on what details to provide

**2. ASKING_QUESTION Intent:**
User says: "What you want?", "What details?", "Kya chahiye?", "What information?", "Tell me what you need", "What's missing?"
→ They're ASKING what information you need!
→ Response: Tell them EXACTLY what's missing or what to provide next
→ Be specific: "Mujhe aapka phone number, complete address, aur size preference chahiye..."

**3. PROVIDING_DETAILS Intent:**
User gives: "Rahul Sharma 9876543210", "123 Model Town Ludhiana Punjab 141001", "My name is Amit", "Size M", "Black color"
→ They're GIVING you information!
→ Extract and acknowledge what you received
→ Ask for what's still missing (if any)

**4. CORRECTING_INFO Intent:**
User says: "Wrong number", "Correction", "Change address", "Galat hai", "Phone number sahi nahi", "Size change karna hai"
→ They're FIXING something!
→ Acknowledge the correction
→ Ask what the correct information is

**5. CANCELING_ORDER Intent:**
User says: "Cancel", "Stop", "Forget it", "Nahi chahiye", "Exit"
→ They want to STOP!
→ Cancel the order gracefully

🎯 **CONTEXT-AWARE RESPONSES:**

**Scenario 1: User says "Yes" when details are COMPLETE**
Current State: All info collected (name, phone, address, city, state, pincode, size, color)
Your Response: "Perfect! Sab details confirm ho gayi hain. Main abhi aapke liye payment link generate kar raha hoon. Ek minute... 😊"
Action: Set is_complete=true, user_intent="confirming_order"

**Scenario 2: User says "Okay" when details are INCOMPLETE**
Current State: Only name collected, missing phone, address, and size
Your Response: "Great! Ab mujhe aapka phone number, complete delivery address, aur size preference chahiye. Please provide karein. 📱📍👕"
Action: Set is_complete=false, user_intent="confirming_order", missing_fields=["phone", "address", "city", "state", "pincode", "size"]

**Scenario 3: User says "What you want?" or "What details you want?"**
Current State: Missing phone, address, and size
Your Response: "Main aapki ye details chahta hoon:
📱 Phone Number (10 digits)
📍 Complete Address (street, city, state, pincode)
👕 Size Preference (S, M, L, XL)
🎨 Color Preference

Please provide karein. 😊"
Action: Set user_intent="asking_question", missing_fields=["phone", "address", "city", "state", "pincode", "size", "color"]

**Scenario 4: User says "All details are okay"**
Current State: All details collected
Your Response: "Bahut accha! Sab details confirm hain. Main payment link generate kar raha hoon... 💳"
Action: Set is_complete=true, user_intent="confirming_order"

**Scenario 5: User provides details**
User: "Rahul Sharma 9876543210 rahul@gmail.com Size M Black"
Your Response: "Thanks Rahul! Main aapki details save kar raha hoon. Ab mujhe aapka complete delivery address chahiye (street, city, state, pincode). 📍"
Action: Extract info, set user_intent="providing_details", missing_fields=["address", "city", "state", "pincode"]

**Scenario 6: User corrects information**
User: "Phone number wrong hai, correct is 9988776655"
Your Response: "✅ Got it! Phone number update kar diya: 9988776655. Kya aur koi correction hai? 😊"
Action: Update phone, set user_intent="correcting_info", correction_details="Updated phone number"

🎯 **FASHION-SPECIFIC GUIDANCE:**

**Size Selection:**
- Ask: "Aapka size kya hai? (S, M, L, XL)"
- Help: "Size guide: S (Small), M (Medium), L (Large), XL (Extra Large)"
- Confirm: "Size M confirm hai?"

**Color Preferences:**
- Ask: "Konsa color pasand hai?"
- Options: "Available colors: Black, White, Navy, Gray, Pink, Red"
- Confirm: "Black color confirm hai?"

**Style Preferences:**
- Ask: "Konsa style pasand hai? (Casual, Formal, Traditional)"
- Occasion: "Kiske liye chahiye? (Office, Party, Casual wear)"
- Confirm: "Casual style confirm hai?"

🎯 **RESPONSE GUIDELINES:**

**When ALL details complete:**
"Perfect, [Name]! Aapki details confirm hain:
📱 Phone: [Phone]
📧 Email: [Email]
📍 Address: [Street], [City], [State] - [Pincode]
👕 Size: [Size]
🎨 Color: [Color]

Agar sab sahi hai toh main payment link generate kar raha hoon! 😊"

**When details INCOMPLETE:**
"Thanks! Main process kar raha hoon. Lekin mujhe ye details aur chahiye:
[List specific missing fields with emojis]

Please provide karein. 😊"

**When user asks what's needed:**
"Main aapki ye details chahta hoon:
[List ALL missing fields clearly with emojis]

Aap ek saath sab de sakte hain ya step by step. 😊"

**When user confirms but incomplete:**
"Main samajh gaya aap proceed karna chahte hain! Lekin pehle ye details chahiye:
[List missing fields]

Please provide karein, phir hum payment pe jayenge. 😊"

🚨 **CRITICAL RULES:**
1. **ALWAYS call process_order_conversation function** - Never respond with text directly
2. **Understand INTENT first** - What is user trying to do?
3. **Be CONTEXT-AWARE** - Check what's already collected vs what's missing
4. **Be SPECIFIC** - Don't say "provide details", say "phone number, address, aur size chahiye"
5. **Be NATURAL** - Talk like a helpful human, not a robot
6. **Handle Hinglish** - Understand Hindi, English, and mixed language
7. **Validate data** - Phone (10 digits), Pincode (6 digits), Email (valid format), Size (S/M/L/XL)
8. **Be FASHION-AWARE** - Understand fashion terminology, sizes, colors, and styles

Remember: You're smart! Understand what users mean, not just what they say. You're helping customers buy fashion items, so be enthusiastic about style! 🧠👗"""

    def start_order_collection(
        self, 
        user_id: int, 
        telegram_id: int, 
        product_details: Dict[str, Any], 
        quantity: int = 1,
        force_new_session: bool = False
    ) -> OrderCollectionSession:
        """Start a new order collection session."""
        # Ensure quantity is an integer (AI might return float like 1.0)
        quantity = int(quantity)
        
        # Check if there's an existing session in database
        existing_session = self._load_session_from_database(telegram_id)
        if existing_session and not force_new_session:
            # Restore existing session
            self.active_sessions[telegram_id] = existing_session
            logger.info(f"Restored existing order collection session for user {telegram_id}")
            return existing_session
        
        # If force_new_session is True, cancel the existing session first
        if existing_session and force_new_session:
            logger.info(f"Cancelling existing session for user {telegram_id} to start new session")
            self.cancel_session(telegram_id)
        
        # Create new session
        now = datetime.now()
        session = OrderCollectionSession(
            user_id=user_id,
            telegram_id=telegram_id,
            state=OrderCollectionState.INITIAL,
            product_details=product_details,
            customer_info={},
            shipping_address={},
            fashion_preferences={},
            quantity=quantity,
            errors=[],
            step_history=["Order collection started"],
            created_at=now,
            updated_at=now
        )
        
        self.active_sessions[telegram_id] = session
        
        # Save to database
        self._save_session_to_database(session)
        
        logger.info(f"Started new order collection session for user {telegram_id}")
        return session
    
    def get_session(self, telegram_id: int) -> Optional[OrderCollectionSession]:
        """Get active session for a user."""
        session = self.active_sessions.get(telegram_id)
        
        if not session:
            if self.restore_session_from_database(telegram_id):
                session = self.active_sessions.get(telegram_id)
        
        if session and session.state in TERMINAL_SESSION_STATES:
            return None
        
        return session
    
    def cancel_session(self, telegram_id: int) -> bool:
        """Cancel an active session."""
        if telegram_id in self.active_sessions:
            session = self.active_sessions[telegram_id]
            session.state = OrderCollectionState.CANCELLED
            session.updated_at = datetime.now()
            
            # Save cancellation to database
            self._save_session_to_database(session)
            
            del self.active_sessions[telegram_id]
            logger.info(f"Cancelled order collection session for user {telegram_id}")
            return True
        return False
    
    def get_collection_prompt(self, session: OrderCollectionSession) -> str:
        """Get the initial collection prompt."""
        product = session.product_details
        price = product.get('discount_price', product.get('price', 0))
        # Ensure quantity is an integer for calculations
        quantity = int(session.quantity)
        
        return f"""🛒 **Order Summary**

**Product:** {product.get('title', 'Product')}
**Quantity:** {quantity}
**Price:** ₹{price} each
**Total:** ₹{float(price) * quantity}

Great choice! Main aapka order process karta hoon. 

Pehle mujhe aapki kuch details chahiye:

**Customer Information Needed:**
1️⃣ **Full Name** (delivery ke liye)
2️⃣ **Phone Number** (delivery updates ke liye)  
3️⃣ **Email** (optional - invoice ke liye)

**Shipping Address Needed:**
4️⃣ **Complete Address** with pincode
5️⃣ **City & State**
6️⃣ **Landmark** (optional)

Aap ek saath saari details de sakte hain ya step by step. Main samjh jaunga! 😊

**Example:**
"Mera naam Rohit Sharma hai, phone 9876543210, email rohit@gmail.com. Address: 123 MG Road, Model Town, Ludhiana, Punjab, 141002"

Ya phir sirf naam se start kariye: "Mera naam Rahul hai"

**Note:** Test mode hai, so main aapko payment link bhejunga (QR code nahi). """
    
    def process_user_input(
        self, 
        telegram_id: int, 
        user_input: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Process user input using FULLY INTELLIGENT AI - NO keyword-based detection.
        
        Returns:
            (success, response_message, order_data_if_complete)
        """
        session = self.get_session(telegram_id)
        if not session:
            return False, "No active order session found.", None
        
        # Clear previous errors
        session.errors = []
        
        try:
            # Create intelligent context-aware prompt with full session state
            context_prompt = self._create_intelligent_context_prompt(session, user_input)
            
            # Start a chat session for function calling
            chat = self.model.start_chat()
            
            # Send context-aware prompt to AI
            logger.info(f"🧠 Sending to AI: User said '{user_input}' | State: {session.state.value}")
            response = chat.send_message(context_prompt)
            
            # Check for function call in response
            if (response.candidates and 
                len(response.candidates) > 0 and 
                response.candidates[0].content.parts and 
                len(response.candidates[0].content.parts) > 0):
                
                # Look for function call in parts
                function_call = None
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        function_call = part.function_call
                        break
                
                if function_call and function_call.name == "process_order_conversation":
                    # Extract function arguments from AI
                    args = function_call.args
                    
                    user_intent = args.get("user_intent", "providing_details")
                    extracted_info = args.get("extracted_info", {})
                    is_complete = args.get("is_complete", False)
                    missing_fields = args.get("missing_fields", [])
                    correction_details = args.get("correction_details", "")
                    response_message = args.get("response_message", "Please provide your details.")
                    
                    logger.info(f"🎯 AI detected intent: {user_intent} | Complete: {is_complete} | Missing: {missing_fields}")
                    
                    # Handle CANCELING_ORDER intent
                    if user_intent == "canceling_order":
                        self.cancel_session(telegram_id)
                        return True, response_message, None
                    
                    # Handle ASKING_QUESTION intent - just respond, don't update data
                    if user_intent == "asking_question":
                        session.step_history.append(f"User asked: {user_input}")
                        session.updated_at = datetime.now()
                        self._save_session_to_database(session)
                        return True, response_message, None
                    
                    # Handle PROVIDING_DETAILS or CORRECTING_INFO - update session data
                    if user_intent in ["providing_details", "correcting_info"]:
                        if extracted_info.get("customer_info"):
                            session.customer_info.update(extracted_info["customer_info"])
                        if extracted_info.get("shipping_address"):
                            session.shipping_address.update(extracted_info["shipping_address"])
                        if extracted_info.get("fashion_preferences"):
                            if not hasattr(session, 'fashion_preferences'):
                                session.fashion_preferences = {}
                            session.fashion_preferences.update(extracted_info["fashion_preferences"])
                            color_pref = session.fashion_preferences.get("color")
                            size_pref = session.fashion_preferences.get("size")
                            style_pref = session.fashion_preferences.get("style")
                            occasion_pref = session.fashion_preferences.get("occasion")
                            if color_pref:
                                session.product_details["selected_color"] = color_pref
                            if size_pref:
                                session.product_details["selected_size"] = size_pref
                            if style_pref:
                                session.product_details["selected_style"] = style_pref
                            if occasion_pref:
                                session.product_details["selected_occasion"] = occasion_pref
                            session.product_details["fashion_preferences"] = session.fashion_preferences.copy()
                        
                        if user_intent == "correcting_info":
                            logger.info(f"🔧 Correction: {correction_details}")
                            session.step_history.append(f"Correction: {correction_details}")
                    
                    # Validate extracted information
                    self._validate_extracted_info(session)
                    
                    # Handle CONFIRMING_ORDER intent
                    if user_intent == "confirming_order":
                        if is_complete and not session.errors:
                            product_details = session.product_details.copy()
                            fashion_preferences = session.fashion_preferences or {}
                            if fashion_preferences:
                                product_details["fashion_preferences"] = fashion_preferences.copy()
                                if fashion_preferences.get("color") and not product_details.get("selected_color"):
                                    product_details["selected_color"] = fashion_preferences["color"]
                                if fashion_preferences.get("size") and not product_details.get("selected_size"):
                                    product_details["selected_size"] = fashion_preferences["size"]
                                if fashion_preferences.get("style") and not product_details.get("selected_style"):
                                    product_details["selected_style"] = fashion_preferences["style"]
                                if fashion_preferences.get("occasion") and not product_details.get("selected_occasion"):
                                    product_details["selected_occasion"] = fashion_preferences["occasion"]
                            
                            order_data = {
                                "user_id": session.user_id,
                                "product_details": product_details,
                                "customer_details": {
                                    "name": session.customer_info["name"],
                                    "phone": session.customer_info["phone"],
                                    "email": session.customer_info.get("email")
                                },
                                "shipping_address": session.shipping_address,
                                "quantity": session.quantity,
                                "fashion_preferences": fashion_preferences
                            }
                            
                            session.state = OrderCollectionState.CREATING_PAYMENT
                            session.step_history.append("Order confirmed, payment initiated")
                            session.updated_at = datetime.now()
                            self._save_session_to_database(session)
                            self.active_sessions.pop(telegram_id, None)
                            
                            logger.info(f"✅ Order confirmed for user {telegram_id}, proceeding to payment")
                            return True, response_message, order_data
                        else:
                            # User wants to confirm but details incomplete
                            session.state = OrderCollectionState.COLLECTING_DETAILS
                            session.step_history.append("User tried to confirm but details incomplete")
                            session.updated_at = datetime.now()
                            self._save_session_to_database(session)
                            return True, response_message, None
                    
                    # For providing_details or correcting_info, check if complete
                    if is_complete and not session.errors:
                        # All details collected, move to confirmation state
                        session.state = OrderCollectionState.CONFIRMING_DETAILS
                        session.step_history.append("All details collected, awaiting confirmation")
                    else:
                        # Still collecting details
                        session.state = OrderCollectionState.COLLECTING_DETAILS
                        session.step_history.append(f"Collecting details, missing: {', '.join(missing_fields)}")
                    
                    # Save session state
                    session.updated_at = datetime.now()
                    self._save_session_to_database(session)
                    
                    return True, response_message, None
                else:
                    # No function call found
                    logger.warning("AI did not call process_order_conversation function")
                    return False, "Sorry, I couldn't process your message. Please try again.", None
            else:
                logger.error("No valid response from AI")
                return False, "Sorry, I encountered an error. Please try again.", None
                
        except Exception as e:
            logger.error(f"Error processing user input with AI: {e}", exc_info=True)
            return False, "Sorry, I encountered an error processing your message. Please try again.", None
    
    def _create_intelligent_context_prompt(self, session: OrderCollectionSession, user_input: str) -> str:
        """Create an intelligent, context-aware prompt for the AI with full session state."""
        
        # Build comprehensive context
        context_parts = []
        
        # Current order state
        context_parts.append(f"🔄 **CURRENT ORDER STATE:** {session.state.value.upper()}")
        context_parts.append(f"📦 **PRODUCT:** {session.product_details.get('title', 'Unknown')}")
        context_parts.append(f"📊 **QUANTITY:** {session.quantity}")
        context_parts.append("")
        
        # Already collected information
        collected_info = []
        missing_info = []
        
        # Check customer info
        if session.customer_info.get("name"):
            collected_info.append(f"✅ Name: {session.customer_info['name']}")
        else:
            missing_info.append("❌ Name")
        
        if session.customer_info.get("phone"):
            collected_info.append(f"✅ Phone: {session.customer_info['phone']}")
        else:
            missing_info.append("❌ Phone")
        
        if session.customer_info.get("email"):
            collected_info.append(f"✅ Email: {session.customer_info['email']}")
        else:
            collected_info.append("⚠️ Email: Not provided (optional)")
        
        # Check shipping address
        if session.shipping_address.get("street"):
            collected_info.append(f"✅ Street Address: {session.shipping_address['street']}")
        else:
            missing_info.append("❌ Street Address")
        
        if session.shipping_address.get("city"):
            collected_info.append(f"✅ City: {session.shipping_address['city']}")
        else:
            missing_info.append("❌ City")
        
        if session.shipping_address.get("state"):
            collected_info.append(f"✅ State: {session.shipping_address['state']}")
        else:
            missing_info.append("❌ State")
        
        if session.shipping_address.get("pincode"):
            collected_info.append(f"✅ Pincode: {session.shipping_address['pincode']}")
        else:
            missing_info.append("❌ Pincode")
        
        fashion_preferences = session.fashion_preferences or {}
        if not fashion_preferences and isinstance(session.product_details, dict):
            fashion_preferences = session.product_details.get("fashion_preferences") or {}
        size_pref = fashion_preferences.get("size")
        color_pref = fashion_preferences.get("color")
        style_pref = fashion_preferences.get("style")
        occasion_pref = fashion_preferences.get("occasion")
        
        if size_pref:
            collected_info.append(f"✅ Size Preference: {size_pref}")
        else:
            missing_info.append("❌ Size Preference")
        
        if color_pref:
            collected_info.append(f"✅ Color Preference: {color_pref}")
        else:
            missing_info.append("❌ Color Preference")
        
        if style_pref:
            collected_info.append(f"✅ Style Preference: {style_pref}")
        if occasion_pref:
            collected_info.append(f"✅ Occasion: {occasion_pref}")
        
        # Add to context
        if collected_info:
            context_parts.append("📋 **ALREADY COLLECTED:**")
            context_parts.extend(collected_info)
            context_parts.append("")
        
        if missing_info:
            context_parts.append("🔍 **STILL MISSING:**")
            context_parts.extend(missing_info)
            context_parts.append("")
        
        # Build final prompt
        context_text = "\n".join(context_parts)
        
        prompt = f"""{'='*80}
🧠 INTELLIGENT ORDER COLLECTION CONTEXT
{'='*80}

{context_text}

{'='*80}
👤 USER SAID: "{user_input}"
{'='*80}

🎯 YOUR TASK:
1. **UNDERSTAND USER INTENT:** What is the user trying to do?
   - Confirming to proceed? (Yes, Okay, Sure, Thik hai)
   - Asking what's needed? (What you want?, Kya chahiye?)
   - Providing details? (Name, phone, address)
   - Correcting info? (Wrong, galat, change)
   - Canceling? (Cancel, stop, nahi chahiye)

2. **BE CONTEXT-AWARE:** Look at what's already collected vs what's missing

3. **RESPOND INTELLIGENTLY:** 
   - If user confirms but details incomplete → Tell them what's missing
   - If user asks what's needed → List specific missing fields
   - If user provides details → Extract and ask for what's still missing
   - If all complete and user confirms → Proceed to payment

4. **CALL THE FUNCTION:** Always call process_order_conversation with:
   - user_intent: The detected intent
   - extracted_info: Any new data provided
   - is_complete: True if ALL required fields are now present
   - missing_fields: List of specific missing fields
   - response_message: Natural, helpful response in Hinglish

Remember: Be smart! Understand what the user MEANS, not just what they SAY. 🧠"""
        
        return prompt
    
    def _detect_user_intent(self, user_input: str, session: OrderCollectionSession) -> str:
        """
        Detect user intent during order collection using LLM intelligence.
        
        Returns:
            "PRODUCT_CHANGE_REQUEST", "PRODUCT_QUESTION", "HESITATION", or "ORDER_DETAILS"
        """
        try:
            # Use LLM for intelligent intent detection
            intent = self._llm_detect_intent(user_input, session)
            logger.info(f"🧠 LLM detected intent: {intent}")
            return intent
        except Exception as e:
            logger.error(f"Error in LLM intent detection: {e}")
            # Fallback to keyword-based detection
            return self._fallback_intent_detection(user_input)
    
    def _llm_detect_intent(self, user_input: str, session: OrderCollectionSession) -> str:
        """Use LLM to intelligently detect user intent."""
        try:
            product_title = session.product_details.get('title', 'Product')

            prompt = f"""You are an intelligent intent detection system for a toy store order collection process.

**Current Context:**
- User is in order collection process for: {product_title}
- User message: "{user_input}"

**Analyze the user's intent and classify it into ONE of these categories:**

1. **PRODUCT_QUESTION** - User is asking about the current product (features, specs, details, "tell me about this", "batao", "iskye baare me batao")

2. **PRODUCT_CHANGE_REQUEST** - User wants to change to a different product ("change product", "different one", "aur dikhao", "ye nahi")

3. **HESITATION** - User is unsure or thinking ("soch rha hu", "not sure", "maybe", "doubt")

4. **ORDER_DETAILS** - User is providing customer details (name, phone, address, email)

5. **GENERAL_CONVERSATION** - User wants to talk about something else (images, prices, general questions, "what do you see", "tell me about this image", "how much does it cost")

6. **CANCEL_ORDER** - User wants to cancel/exit order process ("cancel", "forget this order", "exit", "stop", "nahi chahiye", "cancel order")

**Examples:**
- "iskye baare me batao ye lena hai" → PRODUCT_QUESTION
- "tell me about this product" → PRODUCT_QUESTION
- "batao kya features hai" → PRODUCT_QUESTION
- "change product" → PRODUCT_CHANGE_REQUEST
- "soch rha hu" → HESITATION
- "Rahul Sharma 9876543210" → ORDER_DETAILS
- "what do you see in this image" → GENERAL_CONVERSATION
- "how much does this cost" → GENERAL_CONVERSATION
- "cancel this order" → CANCEL_ORDER
- "forget this" → CANCEL_ORDER

**Respond with ONLY the intent category name (e.g., PRODUCT_QUESTION):**"""

            response = self.model.generate_content(prompt)
            intent = response.text.strip().upper()

            # Validate intent
            valid_intents = ["PRODUCT_QUESTION", "PRODUCT_CHANGE_REQUEST", "HESITATION", "ORDER_DETAILS", "GENERAL_CONVERSATION", "CANCEL_ORDER"]
            if intent in valid_intents:
                return intent
            else:
                logger.warning(f"Invalid intent from LLM: {intent}, using fallback")
                return self._fallback_intent_detection(user_input)

        except Exception as e:
            logger.error(f"Error in LLM intent detection: {e}")
            return self._fallback_intent_detection(user_input)
    
    def _fallback_intent_detection(self, user_input: str) -> str:
        """Fallback keyword-based intent detection."""
        user_input_lower = user_input.lower().strip()

        # 1. Cancel Order Detection
        cancel_keywords = [
            "cancel", "forget this", "forget this order", "exit", "stop", "quit",
            "nahi chahiye", "cancel order", "end order", "stop order", "exit order",
            "forget", "clear", "reset", "start over", "new order"
        ]

        if any(keyword in user_input_lower for keyword in cancel_keywords):
            return "CANCEL_ORDER"

        # 2. General Conversation Detection (images, prices, general questions)
        general_keywords = [
            "what do you see", "tell me about this image", "analyze this", "what's in this",
            "how much", "price", "cost", "rate", "kitna paisa", "kitne ka",
            "image", "photo", "picture", "pic", "see this", "look at this",
            "what is this", "kya hai yeh", "yeh kya hai", "identify", "recognize"
        ]

        if any(keyword in user_input_lower for keyword in general_keywords):
            return "GENERAL_CONVERSATION"

        # 3. Product Change Detection
        product_change_keywords = [
            "change product", "different product", "aur product", "dusra product",
            "ye nahi", "ye wala nahi", "instead", "rather", "prefer",
            "red jeep", "blue bike", "police car", "luxury jeep", "electric bike",
            "gurtoy", "jeep", "bike", "car", "scooter", "toy"
        ]

        # Check for specific product names or change keywords
        if any(keyword in user_input_lower for keyword in product_change_keywords):
            # Additional check: if it contains product names, it's likely a change request
            if any(product_word in user_input_lower for product_word in ["jeep", "bike", "car", "scooter", "toy"]):
                return "PRODUCT_CHANGE_REQUEST"
            # Check for change intent keywords
            change_intent_keywords = ["change", "different", "aur", "dusra", "instead", "rather", "prefer"]
            if any(keyword in user_input_lower for keyword in change_intent_keywords):
                return "PRODUCT_CHANGE_REQUEST"

        # 4. Product Question Detection
        question_keywords = [
            "does this have", "kitne time", "battery life", "kitne volt", "kitne ah",
            "led lights", "music system", "remote control", "age range", "suitable for",
            "kya hai", "kaise hai", "kitna hai", "kya features", "specifications",
            "kitna price", "price kitna", "cost", "rate", "charges",
            "batao", "bataiye", "tell me", "about this", "iske baare", "iskye baare",
            "details", "info", "information", "features", "specs", "specifications"
        ]

        if any(keyword in user_input_lower for keyword in question_keywords):
            return "PRODUCT_QUESTION"

        # 5. Hesitation Detection
        hesitation_keywords = [
            "soch rha hu", "thinking", "not sure", "maybe", "doubt", "confused",
            "nhi soch rha", "soch raha", "soch rahi", "soch rahe", "doubt hai",
            "confusion hai", "sure nahi", "not decided", "decide nahi"
        ]

        if any(keyword in user_input_lower for keyword in hesitation_keywords):
            return "HESITATION"

        # 6. Default to order details
        return "ORDER_DETAILS"
    
    def _handle_product_change_request(self, telegram_id: int, user_input: str, session: OrderCollectionSession) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Handle when user wants to change product during order collection."""
        logger.info(f"🔄 Product change request detected for user {telegram_id}")
        
        # Extract potential product name from user input
        product_name = self._extract_product_name_from_input(user_input)
        
        if product_name:
            # Try to find product by name
            product_id = self._find_product_by_name(product_name)
            
            if product_id:
                # Use smart product switching
                success, response_message = self.switch_product_in_session(telegram_id, product_id)
                if success:
                    session.step_history.append(f"User requested product change to: {product_name}")
                    return True, response_message, None
                else:
                    return True, f"Sorry, I couldn't switch to {product_name}. {response_message}", None
            else:
                # Product not found, cancel current session and ask user to search
                self.cancel_session(telegram_id)
                session.step_history.append(f"User requested product change to: {product_name} (not found)")
                
                return True, f"I couldn't find '{product_name}' in our catalog. 😊\n\nPlease search for the product you want:\n- Use the search function\n- Or tell me more details about what you're looking for\n\nI'll help you find the perfect product!", None
        else:
            # Generic product change request
            self.cancel_session(telegram_id)
            session.step_history.append("User requested product change (no specific product mentioned)")
            
            return True, "Bilkul! Aap koi aur product select kar sakte hain. 😊\n\nPlease mujhe batayein ki aapko kaunsa product chahiye, main aapke liye search kar dunga!", None
    
    def _handle_general_product_info(self, session: OrderCollectionSession, user_input: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Handle general product information requests using LLM intelligence."""
        logger.info(f"📋 General product info request for user {session.telegram_id}")
        
        try:
            # Use LLM to generate intelligent product information response
            response = self._llm_generate_product_info(session, user_input)
            session.step_history.append("User requested general product information")
            return True, response, None
        except Exception as e:
            logger.error(f"Error in LLM product info generation: {e}")
            # Fallback to template-based response
            return self._fallback_product_info_response(session)
    
    def _llm_generate_product_info(self, session: OrderCollectionSession, user_input: str) -> str:
        """Use LLM to generate intelligent product information response."""
        product = session.product_details
        
        prompt = f"""You are a helpful fashion store assistant. A user is asking about a product during order collection.

**Product Details:**
- Title: {product.get('title', 'Product')}
- Size Range: {product.get('size_range', 'Not specified')}
- Original Price: ₹{product.get('price', 0):,.0f}
- Special Offer Price: ₹{product.get('discount_price', product.get('price', 0)):,.0f}
- Colors: {', '.join(product.get('colors', [])) if product.get('colors') else 'Multiple colors'}
- Material: {product.get('specifications', {}).get('material', 'Mixed materials')}
- Care Instructions: {product.get('specifications', {}).get('wash_care', 'Hand wash cold, lay flat to dry')}
- Warranty: {product.get('warranty', 'Quality guarantee')}

**User's Question:** "{user_input}"

**Instructions:**
1. Provide comprehensive information about the fashion item
2. Highlight key features, materials, and care instructions
3. Mention the special offer price prominently
4. Be enthusiastic and engaging about fashion
5. End with a call-to-action for ordering
6. Use emojis appropriately
7. Keep response under 300 characters

**Generate a helpful, engaging response:**"""

        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    def _fallback_product_info_response(self, session: OrderCollectionSession) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Fallback template-based product information response."""
        product = session.product_details
        
        # Build comprehensive product information
        title = product.get('title', 'Product')
        size_range = product.get('size_range', 'Not specified')
        original_price = product.get('price', 0)
        discount_price = product.get('discount_price', original_price)
        colors = product.get('colors', [])
        material = product.get('specifications', {}).get('material', 'Mixed materials')
        care_instructions = product.get('specifications', {}).get('wash_care', 'Hand wash cold, lay flat to dry')
        warranty = product.get('warranty', 'Quality guarantee')
        
        # Format colors
        colors_text = ", ".join(colors) if colors else "Multiple colors available"
        
        # Build response
        response = f"""👗 **{title}**

📊 **Product Details:**
• **Size Range:** {size_range}
• **Material:** {material}
• **Care Instructions:** {care_instructions}
• **Colors:** {colors_text}
• **Warranty:** {warranty}

💰 **Pricing:**
• **Original Price:** ₹{original_price:,.0f}
• **Special Offer Price:** ₹{discount_price:,.0f} (You pay this amount!)

✅ **Ready to Order?**
Aap iska order kar sakte hain! Main aapki details collect karunga. 😊"""
        
        session.step_history.append("User requested general product information")
        return True, response, None
    
    def _get_occasion_recommendations(self, occasion: str) -> Dict[str, Any]:
        """Get product recommendations based on occasion for fashion items."""
        occasion_mappings = {
            'casual': {
                'categories': ['Cardigan', 'Crop top', 'Tunic'],
                'styles': ['comfortable', 'relaxed', 'everyday'],
                'description': 'Casual everyday wear for comfort and style',
                'size_guide': 'Choose your regular size for comfortable fit'
            },
            'office': {
                'categories': ['Cardigan', 'High neck top', 'Court set'],
                'styles': ['professional', 'elegant', 'sophisticated'],
                'description': 'Professional and formal wear for office and business',
                'size_guide': 'Choose fitted size for professional look'
            },
            'party': {
                'categories': ['Crop top', 'Cardigan crop', 'V neck crop top'],
                'styles': ['stylish', 'trendy', 'party-ready'],
                'description': 'Stylish and trendy pieces for parties and events',
                'size_guide': 'Choose your preferred fit - fitted for bold look or loose for comfort'
            },
            'traditional': {
                'categories': ['Kot', 'Court set', 'Tunic'],
                'styles': ['ethnic', 'traditional', 'cultural'],
                'description': 'Traditional and ethnic wear for festivals and ceremonies',
                'size_guide': 'Choose comfortable size for traditional occasions'
            }
        }
        
        return occasion_mappings.get(occasion, {
            'categories': ['Cardigan', 'Crop top', 'Tunic'],
            'styles': ['versatile', 'stylish'],
            'description': 'Versatile pieces for any occasion',
            'size_guide': 'Choose your regular size'
        })
    
    def _handle_occasion_based_recommendation(self, session: OrderCollectionSession, user_input: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Handle occasion-based recommendations for fashion items."""
        user_input_lower = user_input.lower()
        
        # Detect occasion keywords
        occasion_keywords = {
            'casual': ['casual', 'everyday', 'daily', 'comfortable', 'relaxed'],
            'office': ['office', 'work', 'professional', 'business', 'formal'],
            'party': ['party', 'night', 'evening', 'celebration', 'event'],
            'traditional': ['traditional', 'ethnic', 'festival', 'wedding', 'ceremony']
        }
        
        detected_occasion = None
        for occasion, keywords in occasion_keywords.items():
            if any(keyword in user_input_lower for keyword in keywords):
                detected_occasion = occasion
                break
        
        if detected_occasion:
            recommendations = self._get_occasion_recommendations(detected_occasion)
            product = session.product_details
            
            response = f"""🎯 **Perfect for {detected_occasion.title()} Occasion!**

👗 **{product.get('title', 'Product')}** is ideal for {detected_occasion} wear!

✨ **Why it's perfect:**
• {recommendations['description']}
• {recommendations['size_guide']}

🎨 **Style:** {', '.join(recommendations['styles'])}
📏 **Available Sizes:** {product.get('size_range', 'S, M, L, XL')}

💰 **Price:** ₹{product.get('discount_price', product.get('price', 0)):,.0f}

Ready to order for your {detected_occasion} occasion? 😊"""
            
            session.step_history.append(f"User requested {detected_occasion} occasion recommendation")
            return True, response, None
        
        return False, "", None

    def _handle_product_question(self, session: OrderCollectionSession, user_input: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Handle when user asks questions about current product."""
        logger.info(f"❓ Product question detected for user {session.telegram_id}")
        
        product = session.product_details
        user_input_lower = user_input.lower()
        
        # Handle occasion-based recommendations first
        occasion_result = self._handle_occasion_based_recommendation(session, user_input)
        if occasion_result[0]:  # If occasion was detected and handled
            return occasion_result
        
        # Handle general product information requests
        if any(keyword in user_input_lower for keyword in ["batao", "bataiye", "tell me", "about this", "iske baare", "iskye baare", "details", "info"]):
            return self._handle_general_product_info(session, user_input)
        
        # Answer common fashion product questions
        if "size" in user_input_lower or "fit" in user_input_lower:
            size_range = product.get("size_range", "S, M, L, XL")
            return True, f"Yeh {product.get('title', 'product')} {size_range} sizes mein available hai! Aap apna regular size choose kar sakte hain. 👗\n\nKya aap iska order karna chahenge?", None
        
        elif "material" in user_input_lower or "fabric" in user_input_lower:
            material = product.get("specifications", {}).get("material", "Mixed materials")
            return True, f"Yeh {product.get('title', 'product')} {material} se bana hai. Bahut comfortable aur durable hai! 🧵\n\nKya aap iska order karna chahenge?", None
        
        elif "wash" in user_input_lower or "care" in user_input_lower:
            care_instructions = product.get("specifications", {}).get("wash_care", "Hand wash cold, lay flat to dry")
            return True, f"Yeh {product.get('title', 'product')} ke liye care instructions: {care_instructions} 💧\n\nKya aap iska order karna chahenge?", None
        
        elif "age" in user_input_lower or "suitable" in user_input_lower:
            # Check if product is suitable for the user's size preference
            size_range = product.get("size_range", "S, M, L, XL")
            return True, f"Yeh {product.get('title', 'product')} {size_range} sizes mein available hai! 👗\n\nKya aap iska order karna chahenge?", None
        
        elif "price" in user_input_lower or "kitna" in user_input_lower:
            price = product.get("discount_price", product.get("price", 0))
            original_price = product.get("price", 0)
            if price != original_price:
                return True, f"Yeh {product.get('title', 'product')} ka original price ₹{original_price} hai, lekin abhi special offer mein sirf ₹{price} mein mil raha hai! 🎉\n\nKya aap iska order karna chahenge?", None
            else:
                return True, f"Yeh {product.get('title', 'product')} ka price ₹{price} hai! 😊\n\nKya aap iska order karna chahenge?", None
        
        else:
            # Generic product question response
            return True, f"Yeh {product.get('title', 'product')} bahut accha product hai! 😊\n\nAgar aur koi specific question hai toh pooch sakte hain, ya phir order kar sakte hain!", None
    
    def _handle_hesitation(self, session: OrderCollectionSession, user_input: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Handle when user expresses hesitation or thinking."""
        logger.info(f"🤔 Hesitation detected for user {session.telegram_id}")
        
        session.step_history.append("User expressed hesitation")
        
        return True, "Koi baat nahi! Aap soch sakte hain. 😊\n\nKya aap:\n1️⃣ Continue karna chahenge is product ke saath?\n2️⃣ Koi aur product dekhna chahenge?\n3️⃣ Pehle aur details jaanna chahenge?\n\nMain aapki help kar sakta hoon!", None

    def _handle_cancel_order(self, telegram_id: int, session: OrderCollectionSession) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Handle when user wants to cancel the order process."""
        logger.info(f"❌ Order cancellation requested for user {telegram_id}")

        # Remove the session
        if telegram_id in self.active_sessions:
            del self.active_sessions[telegram_id]

        # Also delete from database
        try:
            self.supabase.table("order_collection_sessions").delete().eq("telegram_id", telegram_id).execute()
            logger.info(f"🗑️ Deleted order session from database for user {telegram_id}")
        except Exception as e:
            logger.error(f"Error deleting session from database: {e}")

        return True, "❌ Order cancelled successfully! You can start fresh anytime by asking about products. 😊\n\nWhat would you like to do now?", None

    def _handle_general_conversation(self, telegram_id: int, user_input: str, session: OrderCollectionSession) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Handle general conversation that should bypass order collection."""
        logger.info(f"💬 General conversation detected for user {telegram_id}, bypassing order collection")

        # For now, return a flag that tells the main bot to handle this with normal AI
        # We'll modify the main bot logic to check for this special return
        return True, "__GENERAL_CONVERSATION__", None

    def _extract_product_name_from_input(self, user_input: str) -> Optional[str]:
        """Extract product name from user input."""
        user_input_lower = user_input.lower()
        
        # Common product names and their variations
        product_mappings = {
            "red jeep": "Red Jeep",
            "blue jeep": "Blue Jeep", 
            "police jeep": "Police Jeep",
            "luxury jeep": "Luxury Jeep",
            "electric jeep": "Electric Jeep",
            "red bike": "Red Bike",
            "blue bike": "Blue Bike",
            "police bike": "Police Bike",
            "electric bike": "Electric Bike",
            "scooter": "Scooter",
            "car": "Car",
            "toy": "Toy"
        }
        
        # Check for exact matches first
        for key, value in product_mappings.items():
            if key in user_input_lower:
                return value
        
        # Check for individual product words
        if "jeep" in user_input_lower:
            return "Jeep"
        elif "bike" in user_input_lower:
            return "Bike"
        elif "car" in user_input_lower:
            return "Car"
        elif "scooter" in user_input_lower:
            return "Scooter"
        
        return None
    
    def _find_product_by_name(self, product_name: str) -> Optional[str]:
        """Find product ID by name using fuzzy matching."""
        try:
            # Search for products with similar names
            result = self.supabase.table("products").select("product_id, title").ilike("title", f"%{product_name}%").execute()
            
            if result.data and len(result.data) > 0:
                # Return the first match
                return result.data[0]["product_id"]
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding product by name '{product_name}': {e}")
            return None
    
    # PHASE 2: Smart Session Management Methods
    
    def switch_product_in_session(self, telegram_id: int, new_product_id: str) -> Tuple[bool, str]:
        """
        Switch product in active order collection session while preserving customer details.
        
        Returns:
            (success, response_message)
        """
        session = self.get_session(telegram_id)
        if not session:
            return False, "No active order session found."
        
        try:
            # Get new product details from database
            new_product = self._get_product_by_id(new_product_id)
            if not new_product:
                return False, f"Product with ID '{new_product_id}' not found. Please check the product ID."
            
            # Preserve existing customer info
            preserved_info = {
                "customer_info": session.customer_info.copy(),
                "shipping_address": session.shipping_address.copy(),
                "quantity": session.quantity
            }
            
            # Update session with new product
            old_product_title = session.product_details.get("title", "Unknown Product")
            session.product_details = new_product
            session.preserved_customer_info = preserved_info
            session.state = OrderCollectionState.COLLECTING_DETAILS
            session.step_history.append(f"Product switched from '{old_product_title}' to '{new_product['title']}'")
            session.updated_at = datetime.now()
            
            # Save session to database
            self._save_session_to_database(session)
            
            logger.info(f"🔄 Product switched for user {telegram_id}: {old_product_title} → {new_product['title']}")
            
            return True, f"✅ Product switched successfully!\n\n**New Product:** {new_product['title']}\n**Price:** ₹{new_product.get('discount_price', new_product.get('price', 0))}\n\nYour previous details have been preserved. Would you like to continue with the order or make any changes?"
            
        except Exception as e:
            logger.error(f"Error switching product for user {telegram_id}: {e}")
            return False, "Sorry, I encountered an error switching the product. Please try again."
    
    def _get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product details by ID from database."""
        try:
            result = self.supabase.rpc("get_product_by_id", {"p_product_id": product_id}).execute()
            
            if result.data and len(result.data) > 0:
                product_data = result.data[0]
                
                # Convert to expected format
                return {
                    "product_id": product_data["product_id"],
                    "title": product_data["title"],
                    "category": product_data["category"],
                    "description": product_data["description"],
                    "age_range": product_data["age_range"],
                    "colors": product_data.get("colors", []),
                    "specifications": product_data.get("specifications", {}),
                    "images": product_data.get("images", []),
                    "price": float(product_data["price"]),
                    "discount_price": float(product_data.get("discount_price", product_data["price"])),
                    "stock_status": product_data["stock_status"],
                    "warranty": product_data.get("warranty", "")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting product by ID {product_id}: {e}")
            return None
    
    def _save_session_to_database(self, session: OrderCollectionSession):
        """Save order collection session to database for persistence."""
        try:
            # Create or update order collection session in database
            session_data = {
                "telegram_id": session.telegram_id,
                "user_id": session.user_id,
                "state": session.state.value,
                "product_details": session.product_details,
                "customer_info": session.customer_info,
                "shipping_address": session.shipping_address,
                "fashion_preferences": session.fashion_preferences or {},
                "quantity": session.quantity,
                "errors": session.errors,
                "step_history": session.step_history,
                "preserved_customer_info": session.preserved_customer_info,
                "created_at": session.created_at.isoformat() if session.created_at else datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Check if session already exists
            existing = self.supabase.table("order_collection_sessions").select("id").eq("telegram_id", session.telegram_id).execute()
            
            if existing.data and len(existing.data) > 0:
                # Update existing session
                self.supabase.table("order_collection_sessions").update(session_data).eq("telegram_id", session.telegram_id).execute()
            else:
                # Create new session
                self.supabase.table("order_collection_sessions").insert(session_data).execute()
            
            logger.info(f"💾 Saved order collection session to database for user {session.telegram_id}")
            
        except Exception as e:
            logger.error(f"Error saving session to database: {e}")
    
    def _load_session_from_database(self, telegram_id: int) -> Optional[OrderCollectionSession]:
        """Load order collection session from database."""
        try:
            result = self.supabase.table("order_collection_sessions").select("*").eq("telegram_id", telegram_id).execute()
            
            if result.data and len(result.data) > 0:
                data = result.data[0]
                
                # Convert timestamps
                created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
                updated_at = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
                
                product_details = data["product_details"]
                if isinstance(product_details, str):
                    try:
                        product_details = json.loads(product_details)
                    except Exception:
                        product_details = {}
                fashion_preferences = {}
                if isinstance(product_details, dict):
                    fashion_preferences = product_details.get("fashion_preferences") or {}
                if not fashion_preferences:
                    fashion_preferences = data.get("fashion_preferences") or {}
                
                session = OrderCollectionSession(
                    user_id=data["user_id"],
                    telegram_id=data["telegram_id"],
                    state=OrderCollectionState(data["state"]),
                    product_details=product_details,
                    customer_info=data["customer_info"],
                    shipping_address=data["shipping_address"],
                    fashion_preferences=fashion_preferences,
                    quantity=data["quantity"],
                    errors=data.get("errors", []),
                    step_history=data.get("step_history", []),
                    session_id=str(data["id"]),
                    created_at=created_at,
                    updated_at=updated_at,
                    preserved_customer_info=data.get("preserved_customer_info")
                )
                
                if session.fashion_preferences:
                    session.product_details["fashion_preferences"] = session.fashion_preferences.copy()
                    if session.fashion_preferences.get("color"):
                        session.product_details["selected_color"] = session.fashion_preferences["color"]
                    if session.fashion_preferences.get("size"):
                        session.product_details["selected_size"] = session.fashion_preferences["size"]
                    if session.fashion_preferences.get("style"):
                        session.product_details["selected_style"] = session.fashion_preferences["style"]
                    if session.fashion_preferences.get("occasion"):
                        session.product_details["selected_occasion"] = session.fashion_preferences["occasion"]
                
                logger.info(f"📂 Loaded order collection session from database for user {telegram_id}")
                return session
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading session from database: {e}")
            return None
    
    def restore_session_from_database(self, telegram_id: int) -> bool:
        """Restore order collection session from database to active sessions."""
        try:
            session = self._load_session_from_database(telegram_id)
            if session:
                # Only restore if session is not completed or cancelled
                if session.state in ACTIVE_SESSION_STATES:
                    self.active_sessions[telegram_id] = session
                    logger.info(f"🔄 Restored order collection session for user {telegram_id}")
                    return True
                
                try:
                    self.supabase.table("order_collection_sessions").delete().eq("telegram_id", telegram_id).execute()
                    logger.info(f"🧹 Cleared terminal order session for user {telegram_id}")
                except Exception as cleanup_error:
                    logger.warning(f"Error clearing terminal session for user {telegram_id}: {cleanup_error}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error restoring session for user {telegram_id}: {e}")
            return False
    
    def cleanup_expired_sessions(self):
        """Clean up expired order collection sessions from database."""
        try:
            # Delete sessions older than 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            self.supabase.table("order_collection_sessions").delete().lt("updated_at", cutoff_time.isoformat()).execute()
            
            logger.info("🧹 Cleaned up expired order collection sessions")
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
    
    def _validate_extracted_info(self, session: OrderCollectionSession):
        """Validate extracted information and add errors if invalid."""
        session.errors = []
        if session.fashion_preferences is None:
            session.fashion_preferences = {}
        
        # Validate name
        if session.customer_info.get("name"):
            is_valid, error = AddressValidator.validate_name(session.customer_info["name"])
            if not is_valid:
                session.errors.append(f"Name: {error}")
        
        # Validate phone
        if session.customer_info.get("phone"):
            is_valid, cleaned_phone, error = AddressValidator.validate_phone(session.customer_info["phone"])
            if is_valid:
                session.customer_info["phone"] = cleaned_phone
            else:
                session.errors.append(f"Phone: {error}")
        
        # Validate email
        if session.customer_info.get("email"):
            is_valid, error = AddressValidator.validate_email(session.customer_info["email"])
            if not is_valid:
                session.errors.append(f"Email: {error}")
        
        # Validate pincode
        if session.shipping_address.get("pincode"):
            is_valid, error = AddressValidator.validate_pincode(session.shipping_address["pincode"])
            if not is_valid:
                session.errors.append(f"Pincode: {error}")
        
        # Validate required fields
        required_customer_fields = ["name", "phone"]
        for field in required_customer_fields:
            if not session.customer_info.get(field):
                session.errors.append(f"Missing required field: {field}")
        
        required_address_fields = ["street", "city", "state", "pincode"]
        for field in required_address_fields:
            if not session.shipping_address.get(field):
                session.errors.append(f"Missing required field: {field}")
        
        required_fashion_fields = [("size", "size preference"), ("color", "color preference")]
        for field, label in required_fashion_fields:
            if not session.fashion_preferences.get(field):
                session.errors.append(f"Missing required fashion preference: {label}")

# Import os for environment variables
import os
