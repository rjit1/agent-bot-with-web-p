"""
Order Collection System for Gurtoy Telegram Bot - Phase 3
Handles intelligent order details collection using Gemini 2.5 Flash.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from payment_manager import AddressValidator

logger = logging.getLogger(__name__)

class OrderCollectionState(Enum):
    """States in the order collection process."""
    INITIAL = "initial"
    COLLECTING_CUSTOMER_INFO = "collecting_customer_info"
    COLLECTING_ADDRESS = "collecting_address"
    CONFIRMING_DETAILS = "confirming_details"
    CREATING_PAYMENT = "creating_payment"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "user_id": self.user_id,
            "telegram_id": self.telegram_id,
            "state": self.state.value,
            "product_details": self.product_details,
            "customer_info": self.customer_info,
            "shipping_address": self.shipping_address,
            "quantity": self.quantity,
            "errors": self.errors,
            "step_history": self.step_history
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OrderCollectionSession':
        """Create from dictionary."""
        return cls(
            user_id=data["user_id"],
            telegram_id=data["telegram_id"],
            state=OrderCollectionState(data["state"]),
            product_details=data["product_details"],
            customer_info=data["customer_info"],
            shipping_address=data["shipping_address"],
            quantity=data["quantity"],
            errors=data["errors"],
            step_history=data["step_history"]
        )

class OrderCollector:
    """Manages the order collection process with intelligent conversation."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.active_sessions: Dict[int, OrderCollectionSession] = {}
    
    def start_order_collection(
        self, 
        user_id: int, 
        telegram_id: int, 
        product_details: Dict[str, Any],
        quantity: int = 1
    ) -> OrderCollectionSession:
        """Start a new order collection session."""
        session = OrderCollectionSession(
            user_id=user_id,
            telegram_id=telegram_id,
            state=OrderCollectionState.INITIAL,
            product_details=product_details,
            customer_info={},
            shipping_address={},
            quantity=quantity,
            errors=[],
            step_history=["Order collection started"]
        )
        
        self.active_sessions[telegram_id] = session
        return session
    
    def get_session(self, telegram_id: int) -> Optional[OrderCollectionSession]:
        """Get active order collection session."""
        return self.active_sessions.get(telegram_id)
    
    def cancel_session(self, telegram_id: int) -> bool:
        """Cancel active order collection session."""
        if telegram_id in self.active_sessions:
            self.active_sessions[telegram_id].state = OrderCollectionState.CANCELLED
            del self.active_sessions[telegram_id]
            return True
        return False
    
    def get_collection_prompt(self, session: OrderCollectionSession) -> str:
        """Get the appropriate prompt for current collection state."""
        
        if session.state == OrderCollectionState.INITIAL:
            return self._get_initial_prompt(session)
        elif session.state == OrderCollectionState.COLLECTING_CUSTOMER_INFO:
            return self._get_customer_info_prompt(session)
        elif session.state == OrderCollectionState.COLLECTING_ADDRESS:
            return self._get_address_prompt(session)
        elif session.state == OrderCollectionState.CONFIRMING_DETAILS:
            return self._get_confirmation_prompt(session)
        else:
            return ""
    
    def _get_initial_prompt(self, session: OrderCollectionSession) -> str:
        """Get initial order collection prompt."""
        product = session.product_details
        price = product.get('discount_price', product.get('price', 0))
        
        return f"""🛒 **Order Summary**

**Product:** {product.get('title', 'Product')}
**Quantity:** {session.quantity}
**Price:** ₹{price} each
**Total:** ₹{float(price) * session.quantity}

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
"Mera naam Rahul Sharma hai, phone 9876543210, email rahul@gmail.com. Address: 123 MG Road, Model Town, Ludhiana, Punjab, 141002"

Ya phir sirf naam se start kariye: "Mera naam Rahul hai" """
    
    def _get_customer_info_prompt(self, session: OrderCollectionSession) -> str:
        """Get customer info collection prompt."""
        missing_fields = []
        
        if not session.customer_info.get("name"):
            missing_fields.append("Name")
        if not session.customer_info.get("phone"):
            missing_fields.append("Phone Number")
        
        if not missing_fields:
            session.state = OrderCollectionState.COLLECTING_ADDRESS
            return self._get_address_prompt(session)
        
        errors_text = ""
        if session.errors:
            errors_text = f"\n❌ **Please fix these issues:**\n" + "\n".join(f"• {error}" for error in session.errors) + "\n"
        
        return f"""{errors_text}📝 **Customer Information**

Still need: {', '.join(missing_fields)}

{self._get_current_info_summary(session.customer_info)}

Please provide the missing information:
• **Name:** Your full name for delivery
• **Phone:** 10-digit mobile number for delivery updates
• **Email:** (Optional) For order confirmation

**Example:** "Mera naam Priya Singh hai, phone 9876543210, email priya@gmail.com" """
    
    def _get_address_prompt(self, session: OrderCollectionSession) -> str:
        """Get address collection prompt."""
        required_fields = ["street", "city", "state", "pincode"]
        missing_fields = [field for field in required_fields if not session.shipping_address.get(field)]
        
        if not missing_fields:
            session.state = OrderCollectionState.CONFIRMING_DETAILS
            return self._get_confirmation_prompt(session)
        
        errors_text = ""
        if session.errors:
            errors_text = f"\n❌ **Please fix these issues:**\n" + "\n".join(f"• {error}" for error in session.errors) + "\n"
        
        return f"""{errors_text}🏠 **Shipping Address**

Still need: {', '.join([field.title() for field in missing_fields])}

{self._get_current_address_summary(session.shipping_address)}

Please provide complete address:
• **Street Address:** House/flat number, street name
• **City:** Your city name  
• **State:** Your state
• **Pincode:** 6-digit postal code
• **Landmark:** (Optional) Nearby landmark

**Example:** "Address: 123 MG Road, near City Mall, Ludhiana, Punjab, 141002" """
    
    def _get_confirmation_prompt(self, session: OrderCollectionSession) -> str:
        """Get order confirmation prompt."""
        product = session.product_details
        price = product.get('discount_price', product.get('price', 0))
        total = float(price) * session.quantity
        
        return f"""✅ **Order Confirmation**

**Product Details:**
🎯 {product.get('title', 'Product')}
📦 Quantity: {session.quantity}
💰 Price: ₹{price} each
💳 **Total Amount: ₹{total}**

**Customer Information:**
👤 Name: {session.customer_info.get('name', 'Not provided')}
📱 Phone: {session.customer_info.get('phone', 'Not provided')}
📧 Email: {session.customer_info.get('email', 'Not provided')}

**Shipping Address:**
🏠 {session.shipping_address.get('street', '')}
🏙️ {session.shipping_address.get('city', '')}, {session.shipping_address.get('state', '')}
📮 Pincode: {session.shipping_address.get('pincode', '')}
{f"🗺️ Landmark: {session.shipping_address.get('landmark', '')}" if session.shipping_address.get('landmark') else ""}

**Delivery:** 3-5 business days
**Payment:** Pay after scanning QR code

Sab kuch sahi hai? Type:
• **"Confirm"** or **"Yes"** - to proceed with payment
• **"Edit"** or **"Change"** - to modify details
• **"Cancel"** - to cancel order"""
    
    def _get_current_info_summary(self, customer_info: Dict[str, Any]) -> str:
        """Get summary of currently collected customer info."""
        if not customer_info:
            return ""
        
        summary = "**Current Information:**\n"
        if customer_info.get("name"):
            summary += f"✅ Name: {customer_info['name']}\n"
        if customer_info.get("phone"):
            summary += f"✅ Phone: {customer_info['phone']}\n"
        if customer_info.get("email"):
            summary += f"✅ Email: {customer_info['email']}\n"
        
        return summary + "\n"
    
    def _get_current_address_summary(self, address: Dict[str, Any]) -> str:
        """Get summary of currently collected address info."""
        if not address:
            return ""
        
        summary = "**Current Address:**\n"
        if address.get("street"):
            summary += f"✅ Street: {address['street']}\n"
        if address.get("city"):
            summary += f"✅ City: {address['city']}\n"
        if address.get("state"):
            summary += f"✅ State: {address['state']}\n"
        if address.get("pincode"):
            summary += f"✅ Pincode: {address['pincode']}\n"
        if address.get("landmark"):
            summary += f"✅ Landmark: {address['landmark']}\n"
        
        return summary + "\n"
    
    def process_user_input(
        self, 
        telegram_id: int, 
        user_input: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Process user input for order collection.
        
        Returns:
            (success, response_message, order_data_if_complete)
        """
        session = self.get_session(telegram_id)
        if not session:
            return False, "No active order session found.", None
        
        # Clear previous errors
        session.errors = []
        
        # Handle cancellation
        if user_input.lower().strip() in ['cancel', 'stop', 'quit', 'exit', 'cancel order']:
            self.cancel_session(telegram_id)
            return True, "❌ Order cancelled. You can start a new order anytime!", None
        
        # Process based on current state
        if session.state == OrderCollectionState.INITIAL:
            return self._process_initial_input(session, user_input)
        elif session.state == OrderCollectionState.COLLECTING_CUSTOMER_INFO:
            return self._process_customer_info_input(session, user_input)
        elif session.state == OrderCollectionState.COLLECTING_ADDRESS:
            return self._process_address_input(session, user_input)
        elif session.state == OrderCollectionState.CONFIRMING_DETAILS:
            return self._process_confirmation_input(session, user_input)
        
        return False, "Invalid session state.", None
    
    def _process_initial_input(
        self, 
        session: OrderCollectionSession, 
        user_input: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Process initial input - can contain any combination of details."""
        session.state = OrderCollectionState.COLLECTING_CUSTOMER_INFO
        session.step_history.append("Started collecting customer info")
        
        # Try to extract all possible information from the input
        extracted_info = self._extract_information_from_text(user_input)
        
        # Update session with extracted info
        session.customer_info.update(extracted_info.get("customer_info", {}))
        session.shipping_address.update(extracted_info.get("shipping_address", {}))
        
        # Validate what we have
        self._validate_customer_info(session)
        self._validate_address_info(session)
        
        # Determine next step
        if self._is_customer_info_complete(session) and self._is_address_complete(session):
            session.state = OrderCollectionState.CONFIRMING_DETAILS
            return True, self._get_confirmation_prompt(session), None
        elif self._is_customer_info_complete(session):
            session.state = OrderCollectionState.COLLECTING_ADDRESS
            return True, self._get_address_prompt(session), None
        else:
            return True, self._get_customer_info_prompt(session), None
    
    def _process_customer_info_input(
        self, 
        session: OrderCollectionSession, 
        user_input: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Process customer information input."""
        # Extract information from input
        extracted_info = self._extract_information_from_text(user_input)
        
        # Update session
        session.customer_info.update(extracted_info.get("customer_info", {}))
        session.shipping_address.update(extracted_info.get("shipping_address", {}))
        
        # Validate customer info
        self._validate_customer_info(session)
        
        # Check if we can proceed
        if self._is_customer_info_complete(session):
            if self._is_address_complete(session):
                session.state = OrderCollectionState.CONFIRMING_DETAILS
                return True, self._get_confirmation_prompt(session), None
            else:
                session.state = OrderCollectionState.COLLECTING_ADDRESS
                return True, self._get_address_prompt(session), None
        else:
            return True, self._get_customer_info_prompt(session), None
    
    def _process_address_input(
        self, 
        session: OrderCollectionSession, 
        user_input: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Process address input."""
        # Extract address information
        extracted_info = self._extract_information_from_text(user_input)
        
        # Update session
        session.shipping_address.update(extracted_info.get("shipping_address", {}))
        
        # Validate address
        self._validate_address_info(session)
        
        # Check if address is complete
        if self._is_address_complete(session):
            session.state = OrderCollectionState.CONFIRMING_DETAILS
            return True, self._get_confirmation_prompt(session), None
        else:
            return True, self._get_address_prompt(session), None
    
    def _process_confirmation_input(
        self, 
        session: OrderCollectionSession, 
        user_input: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Process confirmation input."""
        user_input_lower = user_input.lower().strip()
        
        if user_input_lower in ['confirm', 'yes', 'proceed', 'ok', 'confirm order', 'haan', 'theek hai']:
            # Order confirmed, prepare data for payment
            order_data = {
                "user_id": session.user_id,
                "product_details": session.product_details,
                "customer_details": {
                    "name": session.customer_info["name"],
                    "phone": session.customer_info["phone"],
                    "email": session.customer_info.get("email")
                },
                "shipping_address": session.shipping_address,
                "quantity": session.quantity
            }
            
            session.state = OrderCollectionState.CREATING_PAYMENT
            session.step_history.append("Order confirmed, creating payment")
            
            # Remove session as it's complete
            del self.active_sessions[session.telegram_id]
            
            return True, "✅ Order confirmed! Creating payment QR code...", order_data
        
        elif user_input_lower in ['edit', 'change', 'modify', 'update']:
            # Go back to customer info collection
            session.state = OrderCollectionState.COLLECTING_CUSTOMER_INFO
            session.step_history.append("User requested to edit details")
            return True, "📝 Sure! Let's update your details.\n\n" + self._get_customer_info_prompt(session), None
        
        else:
            return True, "Please type 'Confirm' to proceed, 'Edit' to change details, or 'Cancel' to cancel the order.", None
    
    def _extract_information_from_text(self, text: str) -> Dict[str, Any]:
        """Extract customer and address information from natural language text."""
        import re
        
        extracted = {
            "customer_info": {},
            "shipping_address": {}
        }
        
        # Extract name patterns
        name_patterns = [
            r'(?:mera naam|name|naam)\s+(?:hai\s+)?([a-zA-Z\s\.]+?)(?:\s+hai|\s*,|\s+phone|\s+email|\s*$)',
            r'^([a-zA-Z\s\.]+?)(?:\s*,|\s+phone|\s+email)',
            r'name:\s*([a-zA-Z\s\.]+?)(?:\s*,|\s*$)',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) > 1 and not any(char.isdigit() for char in name):
                    extracted["customer_info"]["name"] = name
                    break
        
        # Extract phone patterns
        phone_patterns = [
            r'(?:phone|mobile|number|contact)\s*(?:hai\s*)?(?:number\s*)?(?::\s*)?(\d{10,13})',
            r'(\d{10})',  # Simple 10-digit number
            r'(\+91\s*\d{10})',  # With country code
            r'(91\d{10})',  # Country code without +
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                phone = re.sub(r'\D', '', match.group(1))
                if len(phone) >= 10:
                    extracted["customer_info"]["phone"] = phone
                    break
        
        # Extract email patterns
        email_pattern = r'(?:email|mail)\s*(?:hai\s*)?(?::\s*)?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        email_match = re.search(email_pattern, text, re.IGNORECASE)
        if email_match:
            extracted["customer_info"]["email"] = email_match.group(1).strip()
        
        # Extract address components
        # Pincode (6 digits)
        pincode_match = re.search(r'(\d{6})', text)
        if pincode_match:
            extracted["shipping_address"]["pincode"] = pincode_match.group(1)
        
        # Common Indian states
        states = [
            'punjab', 'haryana', 'delhi', 'uttar pradesh', 'up', 'maharashtra', 'gujarat',
            'rajasthan', 'madhya pradesh', 'mp', 'karnataka', 'tamil nadu', 'kerala',
            'west bengal', 'bihar', 'jharkhand', 'odisha', 'assam', 'himachal pradesh',
            'uttarakhand', 'goa', 'manipur', 'meghalaya', 'nagaland', 'sikkim', 'tripura'
        ]
        
        for state in states:
            if state.lower() in text.lower():
                extracted["shipping_address"]["state"] = state.title()
                break
        
        # Extract city (look for common patterns)
        city_patterns = [
            r'(?:city|shahar)\s*(?:hai\s*)?(?::\s*)?([a-zA-Z\s]+?)(?:\s*,|\s+state|\s+pincode|\s*$)',
            r'([a-zA-Z]+(?:\s+[a-zA-Z]+)*),\s*(?:punjab|haryana|delhi)',  # City before state
        ]
        
        for pattern in city_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                city = match.group(1).strip()
                if len(city) > 1 and not any(char.isdigit() for char in city):
                    extracted["shipping_address"]["city"] = city
                    break
        
        # Extract street address (everything that looks like an address)
        address_patterns = [
            r'(?:address|addr)\s*(?:hai\s*)?(?::\s*)?([^,]+?)(?:\s*,|\s+city|\s+pincode)',
            r'(\d+[^,]*?)(?:\s*,|\s+near|\s+city)',  # Starting with number
        ]
        
        for pattern in address_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                street = match.group(1).strip()
                if len(street) > 5:
                    extracted["shipping_address"]["street"] = street
                    break
        
        # Extract landmark
        landmark_patterns = [
            r'(?:near|landmark|paas)\s+([^,]+?)(?:\s*,|\s*$)',
            r'landmark:\s*([^,]+?)(?:\s*,|\s*$)',
        ]
        
        for pattern in landmark_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                landmark = match.group(1).strip()
                if len(landmark) > 1:
                    extracted["shipping_address"]["landmark"] = landmark
                    break
        
        return extracted
    
    def _validate_customer_info(self, session: OrderCollectionSession):
        """Validate customer information and add errors if invalid."""
        # Validate name
        if session.customer_info.get("name"):
            is_valid, error = AddressValidator.validate_name(session.customer_info["name"])
            if not is_valid:
                session.errors.append(f"Name: {error}")
        
        # Validate phone
        if session.customer_info.get("phone"):
            is_valid, cleaned_phone, error = AddressValidator.validate_phone(session.customer_info["phone"])
            if not is_valid:
                session.errors.append(f"Phone: {error}")
            else:
                session.customer_info["phone"] = cleaned_phone
        
        # Validate email
        if session.customer_info.get("email"):
            is_valid, error = AddressValidator.validate_email(session.customer_info["email"])
            if not is_valid:
                session.errors.append(f"Email: {error}")
    
    def _validate_address_info(self, session: OrderCollectionSession):
        """Validate address information and add errors if invalid."""
        # Validate pincode
        if session.shipping_address.get("pincode"):
            is_valid, error = AddressValidator.validate_pincode(session.shipping_address["pincode"])
            if not is_valid:
                session.errors.append(f"Pincode: {error}")
        
        # Validate required fields
        required_fields = ["street", "city", "state"]
        for field in required_fields:
            value = session.shipping_address.get(field, "").strip()
            if value and len(value) < 2:
                session.errors.append(f"{field.title()}: Must be at least 2 characters")
            elif value and len(value) > 100:
                session.errors.append(f"{field.title()}: Must be less than 100 characters")
    
    def _is_customer_info_complete(self, session: OrderCollectionSession) -> bool:
        """Check if customer information is complete and valid."""
        required_fields = ["name", "phone"]
        return (
            all(session.customer_info.get(field) for field in required_fields) and
            not any("Name:" in error or "Phone:" in error for error in session.errors)
        )
    
    def _is_address_complete(self, session: OrderCollectionSession) -> bool:
        """Check if address information is complete and valid."""
        required_fields = ["street", "city", "state", "pincode"]
        return (
            all(session.shipping_address.get(field) for field in required_fields) and
            not any(any(field.title() in error for field in required_fields) for error in session.errors)
        )