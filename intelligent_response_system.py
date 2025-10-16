"""
Phase 6: Intelligent Response System for Fashion Mart Telegram Bot
Implements advanced message preprocessing, context-aware routing, and fashion-specific conversation flow management.
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

import google.generativeai as genai

logger = logging.getLogger(__name__)

class ConversationState(Enum):
    """States of conversation flow for fashion consultation."""
    INITIAL = "initial"
    BROWSING = "browsing"
    PRODUCT_INQUIRY = "product_inquiry"
    SIZE_CONSULTATION = "size_consultation"
    STYLE_CONSULTATION = "style_consultation"
    OCCASION_BASED = "occasion_based"
    PRICING = "pricing"
    PURCHASING = "purchasing"
    ORDER_COLLECTION = "order_collection"
    DELIVERY = "delivery"
    SUPPORT = "support"
    COMPLETED = "completed"

class IntentType(Enum):
    """Types of user intents for fashion consultation."""
    # Product-related intents
    PRODUCT_SEARCH = "product_search"
    PRODUCT_QUESTION = "product_question"
    PRODUCT_COMPARISON = "product_comparison"
    PRODUCT_AVAILABILITY = "product_availability"
    
    # Fashion-specific intents
    SIZE_RECOMMENDATION = "size_recommendation"
    STYLE_ADVICE = "style_advice"
    OCCASION_RECOMMENDATION = "occasion_recommendation"
    COLOR_PREFERENCE = "color_preference"
    FASHION_CONSULTATION = "fashion_consultation"
    SIZE_GUIDE = "size_guide"
    STYLING_TIPS = "styling_tips"
    
    # Purchase-related intents
    PURCHASE_INTENT = "purchase_intent"
    PRICE_INQUIRY = "price_inquiry"
    ORDER_STATUS = "order_status"
    PAYMENT_INQUIRY = "payment_inquiry"
    
    # Information intents
    CONTACT_INFO = "contact_info"
    STORE_INFO = "store_info"
    DELIVERY_INFO = "delivery_info"
    WARRANTY_INFO = "warranty_info"
    
    # Conversation intents
    GREETING = "greeting"
    THANKS = "thanks"
    GOODBYE = "goodbye"
    HESITATION = "hesitation"
    CORRECTION = "correction"
    MORE_OPTIONS = "more_options"
    
    # Support intents
    COMPLAINT = "complaint"
    ESCALATION = "escalation"
    TECHNICAL_SUPPORT = "technical_support"

@dataclass
class IntentAnalysis:
    """Result of intent analysis."""
    primary_intent: IntentType
    confidence: float
    secondary_intents: List[IntentType]
    context_clues: Dict[str, Any]
    suggested_action: str
    requires_function_call: bool
    function_name: Optional[str] = None
    function_params: Optional[Dict[str, Any]] = None

@dataclass
class MessageContext:
    """Enhanced message context for intelligent processing."""
    original_message: str
    telegram_user_id: int
    chat_id: int
    reply_to_message: Optional[Dict[str, Any]] = None
    replied_product: Optional[Dict[str, Any]] = None
    conversation_state: ConversationState = ConversationState.INITIAL
    recent_messages: List[Dict[str, Any]] = None
    user_preferences: Dict[str, Any] = None
    session_data: Dict[str, Any] = None
    active_order_session: Optional[Dict[str, Any]] = None
    recent_products: List[Dict[str, Any]] = None

class IntelligentResponseSystem:
    """Phase 6: Intelligent Response System with fashion-specific preprocessing and routing."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        
        # Initialize Gemini model for intent analysis
        self.intent_model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=self._get_intent_analysis_instruction()
        )
        
        # Initialize conversation flow model
        self.flow_model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=self._get_conversation_flow_instruction()
        )
        
        # Conversation state tracking
        self.conversation_states: Dict[int, ConversationState] = {}
        
        # Intent patterns for quick detection
        self.intent_patterns = self._build_intent_patterns()
        
    def _get_intent_analysis_instruction(self) -> str:
        """Get system instruction for fashion-specific intent analysis."""
        return """You are an expert intent analysis system for a women's fashion store chatbot.

Your task is to analyze user messages and determine their primary intent with high accuracy for fashion consultation.

**INTENT CATEGORIES:**

**Product-Related:**
- PRODUCT_SEARCH: User wants to see/find fashion items ("kurtas dikhao", "show me cardigans")
- PRODUCT_QUESTION: User asks about specific product features ("material kya hai?", "wash care kya hai?")
- PRODUCT_COMPARISON: User compares products ("yeh wala better hai ya woh?")
- PRODUCT_AVAILABILITY: User asks about stock/availability ("available hai?")

**Fashion-Specific:**
- SIZE_RECOMMENDATION: User asks for size advice ("mera size kya hai?", "size guide chahiye")
- STYLE_ADVICE: User asks for styling help ("kaise pehnu?", "styling tips")
- OCCASION_RECOMMENDATION: User asks for occasion-based suggestions ("wedding ke liye", "office wear")
- COLOR_PREFERENCE: User mentions color preferences ("red color chahiye", "blue pasand hai")
- FASHION_CONSULTATION: User wants general fashion advice ("fashion advice", "kya pehnu?")
- SIZE_GUIDE: User asks about size measurements ("size chart", "measurements")
- STYLING_TIPS: User asks for styling suggestions ("kaise style karein?")

**Purchase-Related:**
- PURCHASE_INTENT: User wants to buy ("order kar do", "buy this")
- PRICE_INQUIRY: User asks about price ("kitne ka hai?", "price kya hai?")
- ORDER_STATUS: User asks about order status ("order status kya hai?")
- PAYMENT_INQUIRY: User asks about payment ("payment kaise karein?")

**Information:**
- CONTACT_INFO: User asks for contact details ("phone number", "address")
- STORE_INFO: User asks about store ("kaha ho tum?", "timings")
- DELIVERY_INFO: User asks about delivery ("delivery kahan tak?")
- WARRANTY_INFO: User asks about warranty ("warranty kitne din ki?")

**Conversation:**
- GREETING: User greets ("hi", "hello", "namaste")
- THANKS: User thanks ("thanks", "dhanyawad")
- GOODBYE: User says goodbye ("bye", "alvida")
- HESITATION: User shows hesitation ("soch rha hu", "not sure")
- CORRECTION: User corrects something ("galat hai", "correction")
- MORE_OPTIONS: User wants more options ("aur dikhao", "more options")

**Support:**
- COMPLAINT: User complains ("problem hai", "issue")
- ESCALATION: User wants human help ("human se baat karo")
- TECHNICAL_SUPPORT: User needs technical help ("kaise use karein?")

**ANALYSIS RULES:**
1. Consider the FULL context, not just keywords
2. Look for fashion-specific conversation patterns
3. Consider reply-to-message context
4. Analyze user's conversation state
5. Provide confidence score (0.0-1.0)
6. Suggest specific action to take
7. Pay special attention to size, style, and occasion mentions

**OUTPUT FORMAT:**
Return JSON with:
{
    "primary_intent": "INTENT_TYPE",
    "confidence": 0.95,
    "secondary_intents": ["INTENT_TYPE2"],
    "context_clues": {
        "has_product_context": true,
        "is_reply_to_product": false,
        "mentions_size": true,
        "mentions_occasion": false,
        "mentions_style": true,
        "conversation_stage": "size_consultation"
    },
    "suggested_action": "Call size recommendation function",
    "requires_function_call": true,
    "function_name": "search_products",
    "function_params": {"query": "cardigans", "size_range": "M", "occasion": "office"}
}

**CRITICAL:** Always return valid JSON. Be precise and accurate for fashion consultation."""

    def _get_conversation_flow_instruction(self) -> str:
        """Get system instruction for fashion consultation flow management."""
        return """You are a conversation flow management system for a women's fashion store chatbot.

Your task is to analyze conversation context and determine the optimal conversation state and flow for fashion consultation.

**CONVERSATION STATES:**

**INITIAL:** User just started conversation
**BROWSING:** User is looking at products, exploring fashion options
**PRODUCT_INQUIRY:** User is asking specific questions about fashion items
**SIZE_CONSULTATION:** User needs size recommendations and guidance
**STYLE_CONSULTATION:** User needs styling advice and tips
**OCCASION_BASED:** User is shopping for specific occasions
**PRICING:** User is discussing prices, offers, payment
**PURCHASING:** User has decided to buy, in purchase process
**ORDER_COLLECTION:** User is providing order details
**DELIVERY:** User is asking about delivery, shipping
**SUPPORT:** User needs help, has issues
**COMPLETED:** Conversation/transaction completed

**FASHION CONSULTATION WORKFLOW:**

1. **Initial Contact:** Greet and understand fashion needs
2. **Style Assessment:** Determine user's style preferences
3. **Size Consultation:** Help with size recommendations
4. **Occasion Matching:** Suggest items for specific occasions
5. **Product Presentation:** Show relevant fashion items
6. **Styling Advice:** Provide styling tips and suggestions
7. **Purchase Process:** Guide through ordering
8. **Follow-up:** Ensure satisfaction and offer additional help

**SIZE RECOMMENDATION PROCESS:**

1. **Body Measurements:** Ask for or estimate measurements
2. **Size Chart Reference:** Use size charts for different brands
3. **Fit Preferences:** Understand loose/fitted preferences
4. **Recommendation:** Suggest appropriate sizes
5. **Verification:** Confirm size choice

**STYLE ADVICE INTEGRATION:**

1. **Style Assessment:** Determine user's style (casual, formal, ethnic)
2. **Occasion Matching:** Match styles to occasions
3. **Color Coordination:** Suggest color combinations
4. **Accessory Pairing:** Recommend accessories
5. **Trend Awareness:** Share current fashion trends

**FLOW RULES:**
1. Track conversation progression naturally for fashion consultation
2. Detect state transitions based on user intent and fashion needs
3. Maintain context across state changes
4. Suggest appropriate responses for each state
5. Handle interruptions and topic changes
6. Focus on size, style, and occasion-based recommendations

**OUTPUT FORMAT:**
Return JSON with:
{
    "current_state": "CONVERSATION_STATE",
    "state_transition": "from_browsing_to_size_consultation",
    "confidence": 0.9,
    "context_factors": {
        "user_intent": "size_recommendation",
        "product_context": true,
        "fashion_consultation_needed": true,
        "size_help_required": true,
        "occasion": "wedding"
    },
    "suggested_response_strategy": "Provide size guidance and occasion-based recommendations",
    "next_expected_intent": "style_advice"
}

**CRITICAL:** Always return valid JSON. Focus on fashion consultation flow."""

    def _build_intent_patterns(self) -> Dict[IntentType, List[str]]:
        """Build keyword patterns for quick intent detection."""
        return {
            IntentType.PRODUCT_SEARCH: [
                "dikhao", "show", "kurtas", "cardigans", "tops", "fashion", "clothes",
                "search", "find", "available", "hain", "products", "dresses"
            ],
            IntentType.PRODUCT_QUESTION: [
                "material", "wash", "care", "instructions", "quality", "comfort", "fit",
                "kaise", "how", "what", "kya", "details", "info", "stretch", "breathable"
            ],
            IntentType.SIZE_RECOMMENDATION: [
                "size", "measurement", "chart", "guide", "mera size", "kya size",
                "loose", "tight", "fitted", "comfortable", "perfect fit"
            ],
            IntentType.STYLE_ADVICE: [
                "style", "styling", "tips", "advice", "kaise pehnu", "coordination",
                "accessories", "matching", "combination", "trend", "fashionable"
            ],
            IntentType.OCCASION_RECOMMENDATION: [
                "wedding", "office", "party", "casual", "formal", "occasion",
                "function", "meeting", "date", "festival", "celebration"
            ],
            IntentType.COLOR_PREFERENCE: [
                "color", "colour", "red", "blue", "green", "black", "white",
                "pink", "purple", "yellow", "orange", "brown", "grey"
            ],
            IntentType.FASHION_CONSULTATION: [
                "fashion advice", "consultation", "help", "guidance", "suggest",
                "recommend", "what to wear", "kya pehnu", "fashion tips"
            ],
            IntentType.PURCHASE_INTENT: [
                "order", "buy", "purchase", "le lunga", "lena hai", "kar do",
                "checkout", "proceed", "confirm", "thik hai", "haan"
            ],
            IntentType.PRICE_INQUIRY: [
                "price", "kitne ka", "cost", "amount", "rupees", "₹",
                "budget", "expensive", "cheap", "offer", "discount"
            ],
            IntentType.CONTACT_INFO: [
                "phone", "number", "contact", "address", "location",
                "kaha", "where", "timings", "hours", "call"
            ],
            IntentType.GREETING: [
                "hi", "hello", "namaste", "good morning", "good evening",
                "hey", "hii", "hlo", "start"
            ],
            IntentType.THANKS: [
                "thanks", "thank you", "dhanyawad", "shukriya",
                "appreciate", "grateful"
            ],
            IntentType.HESITATION: [
                "soch rha", "thinking", "not sure", "maybe", "confused",
                "doubt", "hesitate", "considering"
            ]
        }

    async def preprocess_message(self, message_context: MessageContext) -> IntentAnalysis:
        """
        Phase 3.1: Intelligent message preprocessing with advanced intent analysis.
        
        Args:
            message_context: Enhanced message context
            
        Returns:
            IntentAnalysis: Detailed intent analysis result
        """
        try:
            # Step 1: Quick pattern-based detection
            quick_intent = self._quick_intent_detection(message_context.original_message)
            
            # Step 2: Context-aware analysis
            context_analysis = self._analyze_message_context(message_context)
            
            # Step 3: LLM-based intent analysis
            llm_analysis = await self._llm_intent_analysis(message_context)
            
            # Step 4: Combine and rank intents
            final_analysis = self._combine_intent_analyses(
                quick_intent, context_analysis, llm_analysis, message_context
            )
            
            logger.info(f"🎯 Intent analysis complete: {final_analysis.primary_intent.value} (confidence: {final_analysis.confidence})")
            
            return final_analysis
            
        except Exception as e:
            logger.error(f"Error in message preprocessing: {e}")
            # Fallback to basic analysis
            return IntentAnalysis(
                primary_intent=IntentType.PRODUCT_SEARCH,
                confidence=0.5,
                secondary_intents=[],
                context_clues={},
                suggested_action="Process as general inquiry",
                requires_function_call=False
            )

    def _quick_intent_detection(self, message: str) -> Optional[IntentType]:
        """Quick pattern-based intent detection."""
        message_lower = message.lower()
        
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in message_lower:
                    return intent_type
        
        return None

    def _analyze_message_context(self, context: MessageContext) -> Dict[str, Any]:
        """Analyze message context for intent clues."""
        analysis = {
            "has_reply_context": context.reply_to_message is not None,
            "has_product_context": context.replied_product is not None,
            "has_recent_products": context.recent_products is not None,
            "has_order_session": context.active_order_session is not None,
            "message_length": len(context.original_message),
            "is_question": "?" in context.original_message,
            "mentions_price": any(word in context.original_message.lower() 
                                for word in ["price", "kitne", "rupees", "₹", "cost"]),
            "mentions_age": any(word in context.original_message.lower() 
                              for word in ["saal", "year", "age", "ke liye"]),
            "conversation_stage": context.conversation_state.value
        }
        
        return analysis

    async def _llm_intent_analysis(self, context: MessageContext) -> Dict[str, Any]:
        """Use LLM for advanced intent analysis."""
        try:
            # Prepare context for LLM
            context_prompt = f"""
Analyze this user message and determine the intent:

**User Message:** {context.original_message}

**Context Information:**
- Reply to message: {context.reply_to_message is not None}
- Has product context: {context.replied_product is not None}
- Conversation state: {context.conversation_state.value}
- Has order session: {context.active_order_session is not None}
- Recent products count: {len(context.recent_products) if context.recent_products else 0}

**Recent Messages Context:**
{self._format_recent_messages(context.recent_messages)}

Analyze the intent and provide detailed analysis.
"""

            response = self.intent_model.generate_content(context_prompt)
            
            # Parse JSON response
            try:
                analysis = json.loads(response.text)
                return analysis
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM intent analysis JSON")
                return {}
                
        except Exception as e:
            logger.error(f"Error in LLM intent analysis: {e}")
            return {}

    def _format_recent_messages(self, recent_messages: List[Dict[str, Any]]) -> str:
        """Format recent messages for context."""
        if not recent_messages:
            return "No recent messages"
        
        formatted = []
        for msg in recent_messages[-5:]:  # Last 5 messages
            msg_type = msg.get("message_type", "unknown")
            content = msg.get("content", "")[:100]  # First 100 chars
            formatted.append(f"- {msg_type}: {content}")
        
        return "\n".join(formatted)

    def _combine_intent_analyses(
        self, 
        quick_intent: Optional[IntentType],
        context_analysis: Dict[str, Any],
        llm_analysis: Dict[str, Any],
        context: MessageContext
    ) -> IntentAnalysis:
        """Combine different intent analyses into final result."""
        
        # Determine primary intent
        if llm_analysis.get("primary_intent"):
            try:
                primary_intent = IntentType(llm_analysis["primary_intent"])
                confidence = llm_analysis.get("confidence", 0.8)
            except ValueError:
                primary_intent = quick_intent or IntentType.PRODUCT_SEARCH
                confidence = 0.6
        else:
            primary_intent = quick_intent or IntentType.PRODUCT_SEARCH
            confidence = 0.7
        
        # Determine if function call is required
        requires_function_call = self._determine_function_call_requirement(
            primary_intent, context_analysis, llm_analysis
        )
        
        # Get suggested action and function details
        suggested_action, function_name, function_params = self._get_suggested_action(
            primary_intent, context_analysis, llm_analysis, context
        )
        
        return IntentAnalysis(
            primary_intent=primary_intent,
            confidence=confidence,
            secondary_intents=[],  # Could be enhanced
            context_clues=context_analysis,
            suggested_action=suggested_action,
            requires_function_call=requires_function_call,
            function_name=function_name,
            function_params=function_params
        )

    def _determine_function_call_requirement(
        self, 
        intent: IntentType, 
        context_analysis: Dict[str, Any],
        llm_analysis: Dict[str, Any]
    ) -> bool:
        """Determine if a function call is required based on intent."""
        
        function_required_intents = {
            IntentType.PRODUCT_SEARCH,
            IntentType.PURCHASE_INTENT,
            IntentType.PRICE_INQUIRY,
            IntentType.ORDER_STATUS,
            IntentType.CONTACT_INFO,
            IntentType.STORE_INFO,
            IntentType.DELIVERY_INFO
        }
        
        return intent in function_required_intents

    def _get_suggested_action(
        self,
        intent: IntentType,
        context_analysis: Dict[str, Any],
        llm_analysis: Dict[str, Any],
        context: MessageContext
    ) -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
        """Get suggested action and function details."""
        
        if intent == IntentType.PRODUCT_SEARCH:
            return "Search for products", "search_products", {"query": context.original_message}
        
        elif intent == IntentType.PURCHASE_INTENT:
            if context_analysis.get("has_product_context"):
                return "Start purchase process", "buy_product", {"product_id": context.replied_product.get("product_id")}
            else:
                return "Ask for product selection", None, None
        
        elif intent == IntentType.PRICE_INQUIRY:
            if context_analysis.get("has_product_context"):
                return "Provide pricing information", None, None
            else:
                return "Ask for specific product", None, None
        
        elif intent == IntentType.CONTACT_INFO:
            return "Provide contact information", "get_contact_info", {}
        
        elif intent == IntentType.ORDER_STATUS:
            return "Check order status", "check_order_status", {"order_id": "extract_from_message"}
        
        else:
            return "Provide conversational response", None, None

    async def manage_conversation_flow(
        self, 
        context: MessageContext, 
        intent_analysis: IntentAnalysis
    ) -> ConversationState:
        """
        Phase 3.2: Advanced conversation flow management.
        
        Args:
            context: Message context
            intent_analysis: Intent analysis result
            
        Returns:
            ConversationState: Updated conversation state
        """
        try:
            # Get current state
            current_state = self.conversation_states.get(context.telegram_user_id, ConversationState.INITIAL)
            
            # Analyze flow transition
            flow_analysis = await self._analyze_conversation_flow(
                current_state, intent_analysis, context
            )
            
            # Update conversation state
            new_state = ConversationState(flow_analysis.get("current_state", current_state.value))
            self.conversation_states[context.telegram_user_id] = new_state
            
            logger.info(f"🔄 Conversation flow: {current_state.value} → {new_state.value}")
            
            return new_state
            
        except Exception as e:
            logger.error(f"Error in conversation flow management: {e}")
            return ConversationState.INITIAL

    async def _analyze_conversation_flow(
        self, 
        current_state: ConversationState,
        intent_analysis: IntentAnalysis,
        context: MessageContext
    ) -> Dict[str, Any]:
        """Analyze conversation flow using LLM."""
        try:
            flow_prompt = f"""
Analyze the conversation flow and determine the optimal state transition:

**Current State:** {current_state.value}
**User Intent:** {intent_analysis.primary_intent.value}
**Intent Confidence:** {intent_analysis.confidence}

**Context:**
- Has product context: {context.replied_product is not None}
- Has order session: {context.active_order_session is not None}
- Message: {context.original_message}

Determine the next conversation state and provide analysis.
"""

            response = self.flow_model.generate_content(flow_prompt)
            
            try:
                analysis = json.loads(response.text)
                return analysis
            except json.JSONDecodeError:
                logger.warning("Failed to parse conversation flow analysis JSON")
                return {"current_state": current_state.value}
                
        except Exception as e:
            logger.error(f"Error in conversation flow analysis: {e}")
            return {"current_state": current_state.value}

    async def route_response(
        self,
        context: MessageContext,
        intent_analysis: IntentAnalysis,
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """
        Phase 3.3: Context-aware response routing.
        
        Args:
            context: Message context
            intent_analysis: Intent analysis result
            conversation_state: Current conversation state
            
        Returns:
            Dict: Response routing decision
        """
        try:
            routing_decision = {
                "route_type": "ai_response",
                "priority": "normal",
                "context_enhancements": {},
                "response_strategy": "conversational",
                "function_call_required": intent_analysis.requires_function_call,
                "function_name": intent_analysis.function_name,
                "function_params": intent_analysis.function_params
            }
            
            # Determine routing strategy based on state and intent
            if conversation_state == ConversationState.ORDER_COLLECTION:
                routing_decision["route_type"] = "order_collection"
                routing_decision["priority"] = "high"
                
            elif intent_analysis.primary_intent == IntentType.PRODUCT_QUESTION and context.replied_product:
                routing_decision["route_type"] = "product_context_response"
                routing_decision["context_enhancements"]["product_details"] = context.replied_product
                
            elif intent_analysis.requires_function_call:
                routing_decision["route_type"] = "function_call_response"
                routing_decision["priority"] = "high"
                
            elif conversation_state == ConversationState.SUPPORT:
                routing_decision["route_type"] = "support_response"
                routing_decision["priority"] = "high"
                
            # Add context enhancements
            routing_decision["context_enhancements"].update({
                "conversation_state": conversation_state.value,
                "intent_confidence": intent_analysis.confidence,
                "user_preferences": context.user_preferences or {},
                "recent_products": context.recent_products or []
            })
            
            logger.info(f"🎯 Response routing: {routing_decision['route_type']} (priority: {routing_decision['priority']})")
            
            return routing_decision
            
        except Exception as e:
            logger.error(f"Error in response routing: {e}")
            return {
                "route_type": "ai_response",
                "priority": "normal",
                "context_enhancements": {},
                "response_strategy": "conversational",
                "function_call_required": False
            }

    def get_conversation_state(self, telegram_user_id: int) -> ConversationState:
        """Get current conversation state for a user."""
        return self.conversation_states.get(telegram_user_id, ConversationState.INITIAL)

    def set_conversation_state(self, telegram_user_id: int, state: ConversationState):
        """Set conversation state for a user."""
        self.conversation_states[telegram_user_id] = state
        logger.info(f"🔄 Set conversation state for user {telegram_user_id}: {state.value}")

    def clear_conversation_state(self, telegram_user_id: int):
        """Clear conversation state for a user."""
        if telegram_user_id in self.conversation_states:
            del self.conversation_states[telegram_user_id]
            logger.info(f"🔄 Cleared conversation state for user {telegram_user_id}")

    # Phase 6: Fashion-specific methods
    
    async def analyze_size_requirements(self, user_message: str, context: MessageContext) -> Dict[str, Any]:
        """
        Analyze user's size requirements and provide recommendations.
        
        Args:
            user_message: User's message about size
            context: Message context
            
        Returns:
            Dict: Size analysis and recommendations
        """
        try:
            size_prompt = f"""You are a fashion size consultant. Analyze the user's size requirements.

**User Message:** "{user_message}"

**Context:**
- Previous products viewed: {context.recent_products}
- User preferences: {context.user_preferences}

**Size Analysis Tasks:**
1. Extract size-related information (measurements, preferences, concerns)
2. Determine size category (S, M, L, XL)
3. Identify fit preferences (loose, fitted, comfortable)
4. Suggest size recommendations
5. Provide size guide information

**Output Format:**
{{
    "size_category": "M",
    "fit_preference": "comfortable",
    "measurements_mentioned": false,
    "size_concerns": ["not sure about fit"],
    "recommendations": ["Try M size for comfortable fit"],
    "size_guide_needed": true,
    "confidence": 0.8
}}

**CRITICAL:** Always return valid JSON."""

            response = self.intent_model.generate_content(size_prompt)
            analysis = json.loads(response.text)
            
            logger.info(f"📏 Size analysis completed: {analysis.get('size_category', 'Unknown')}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in size analysis: {e}")
            return {
                "size_category": "M",
                "fit_preference": "comfortable",
                "recommendations": ["Please try our size guide for accurate sizing"],
                "confidence": 0.5
            }

    async def analyze_style_preferences(self, user_message: str, context: MessageContext) -> Dict[str, Any]:
        """
        Analyze user's style preferences and provide styling advice.
        
        Args:
            user_message: User's message about style
            context: Message context
            
        Returns:
            Dict: Style analysis and recommendations
        """
        try:
            style_prompt = f"""You are a fashion style consultant. Analyze the user's style preferences.

**User Message:** "{user_message}"

**Context:**
- Previous products viewed: {context.recent_products}
- User preferences: {context.user_preferences}

**Style Analysis Tasks:**
1. Identify style preferences (casual, formal, ethnic, western)
2. Determine color preferences
3. Analyze occasion requirements
4. Suggest styling tips
5. Recommend accessories

**Output Format:**
{{
    "style_type": "ethnic",
    "color_preferences": ["red", "blue"],
    "occasion": "wedding",
    "styling_tips": ["Pair with matching accessories"],
    "accessory_suggestions": ["earrings", "bangles"],
    "confidence": 0.9
}}

**CRITICAL:** Always return valid JSON."""

            response = self.intent_model.generate_content(style_prompt)
            analysis = json.loads(response.text)
            
            logger.info(f"👗 Style analysis completed: {analysis.get('style_type', 'Unknown')}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in style analysis: {e}")
            return {
                "style_type": "casual",
                "color_preferences": [],
                "styling_tips": ["Choose colors that complement your skin tone"],
                "confidence": 0.5
            }

    async def analyze_occasion_requirements(self, user_message: str, context: MessageContext) -> Dict[str, Any]:
        """
        Analyze user's occasion requirements and provide recommendations.
        
        Args:
            user_message: User's message about occasion
            context: Message context
            
        Returns:
            Dict: Occasion analysis and recommendations
        """
        try:
            occasion_prompt = f"""You are a fashion occasion consultant. Analyze the user's occasion requirements.

**User Message:** "{user_message}"

**Context:**
- Previous products viewed: {context.recent_products}
- User preferences: {context.user_preferences}

**Occasion Analysis Tasks:**
1. Identify the occasion (wedding, office, party, casual, formal)
2. Determine dress code requirements
3. Suggest appropriate styles
4. Recommend color choices
5. Provide occasion-specific tips

**Output Format:**
{{
    "occasion": "wedding",
    "dress_code": "formal",
    "recommended_styles": ["kurtas", "cardigans"],
    "color_suggestions": ["red", "maroon", "gold"],
    "occasion_tips": ["Choose comfortable fabrics for long events"],
    "confidence": 0.9
}}

**CRITICAL:** Always return valid JSON."""

            response = self.intent_model.generate_content(occasion_prompt)
            analysis = json.loads(response.text)
            
            logger.info(f"🎉 Occasion analysis completed: {analysis.get('occasion', 'Unknown')}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in occasion analysis: {e}")
            return {
                "occasion": "casual",
                "dress_code": "casual",
                "recommended_styles": ["comfortable tops"],
                "confidence": 0.5
            }

    async def provide_fashion_consultation(self, user_message: str, context: MessageContext) -> Dict[str, Any]:
        """
        Provide comprehensive fashion consultation based on user needs.
        
        Args:
            user_message: User's message requesting consultation
            context: Message context
            
        Returns:
            Dict: Comprehensive fashion consultation
        """
        try:
            consultation_prompt = f"""You are a comprehensive fashion consultant. Provide detailed fashion advice.

**User Message:** "{user_message}"

**Context:**
- Previous products viewed: {context.recent_products}
- User preferences: {context.user_preferences}
- Conversation state: {context.conversation_state}

**Consultation Tasks:**
1. Analyze user's fashion needs
2. Provide size recommendations
3. Suggest style advice
4. Recommend occasion-appropriate items
5. Offer styling tips
6. Suggest color combinations

**Output Format:**
{{
    "consultation_type": "comprehensive",
    "size_recommendation": "M",
    "style_advice": "Choose comfortable, breathable fabrics",
    "occasion_suggestions": ["office wear", "casual outings"],
    "color_recommendations": ["navy blue", "white", "pastels"],
    "styling_tips": ["Layer with cardigans for versatility"],
    "product_suggestions": ["kurtas", "cardigans", "tops"],
    "confidence": 0.9
}}

**CRITICAL:** Always return valid JSON."""

            response = self.intent_model.generate_content(consultation_prompt)
            analysis = json.loads(response.text)
            
            logger.info(f"👩‍💼 Fashion consultation completed: {analysis.get('consultation_type', 'Unknown')}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in fashion consultation: {e}")
            return {
                "consultation_type": "basic",
                "size_recommendation": "M",
                "style_advice": "Choose items that make you feel confident",
                "product_suggestions": ["versatile pieces"],
                "confidence": 0.5
            }
