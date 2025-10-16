"""
Payment Manager for Fashion Mart Telegram Bot - Phase 5
Handles Razorpay integration, QR code generation, and order management.
"""
from __future__ import annotations

import os
import json
import hmac
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import re

import razorpay
from supabase import Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class PaymentManager:
    """Manages payment processing with Razorpay integration."""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        
        # Initialize Razorpay client
        self.razorpay_key_id = os.getenv("RAZORPAY_KEY_ID")
        self.razorpay_key_secret = os.getenv("RAZORPAY_KEY_SECRET")
        self.razorpay_webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
        
        if not all([self.razorpay_key_id, self.razorpay_key_secret]):
            raise ValueError("Razorpay credentials are required")
        
        self.razorpay_client = razorpay.Client(auth=(self.razorpay_key_id, self.razorpay_key_secret))
    
    async def create_order_with_qr(
        self,
        user_id: int,
        product_details: Dict[str, Any],
        customer_details: Dict[str, Any],
        shipping_address: Dict[str, Any],
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        Create order and generate QR code for payment.
        
        Args:
            user_id: Internal user ID from database
            product_details: Product information
            customer_details: Customer name, phone, email
            shipping_address: Complete shipping address
            quantity: Number of items
            
        Returns:
            Dictionary with order details and QR code information
        """
        try:
            # Ensure quantity is an integer (AI might return float like 1.0)
            quantity = int(quantity)
            
            # Calculate total amount
            unit_price = Decimal(str(product_details.get('discount_price', product_details.get('price', 0))))
            total_amount = unit_price * quantity
            
            # Validate minimum amount (Razorpay minimum is ₹1)
            if total_amount < Decimal('1'):
                total_amount = Decimal('1')
            
            # Create order in database
            order_result = self.supabase.rpc(
                "create_order",
                {
                    "p_user_id": user_id,
                    "p_customer_name": customer_details["name"],
                    "p_customer_phone": customer_details["phone"],
                    "p_customer_email": customer_details.get("email"),
                    "p_shipping_address": json.dumps(shipping_address),
                    "p_total_amount": float(total_amount),
                    "p_notes": f"Order for {product_details.get('title', 'Product')}"
                }
            ).execute()
            
            if not order_result.data:
                raise Exception("Failed to create order in database")
            
            order_id = order_result.data[0]["order_id"]
            
            # Add order item
            item_added = self.supabase.rpc(
                "add_order_item",
                {
                    "p_order_id": order_id,
                    "p_product_id": product_details["product_id"],
                    "p_product_title": product_details["title"],
                    "p_quantity": quantity,
                    "p_unit_price": float(unit_price),
                    "p_product_details": json.dumps({
                        "color": product_details.get("selected_color"),
                        "age_range": product_details.get("age_range"),
                        "specifications": product_details.get("specifications", {})
                    })
                }
            ).execute()
            
            if not item_added.data:
                raise Exception("Failed to add item to order")
            
            # Create Razorpay order
            razorpay_order_data = {
                "amount": int(total_amount * 100),  # Amount in paise
                "currency": "INR",
                "receipt": order_id,
                "notes": {
                    "order_id": order_id,
                    "customer_name": customer_details["name"],
                    "customer_phone": customer_details["phone"],
                    "product_name": product_details["title"]
                }
            }
            
            razorpay_order = self.razorpay_client.order.create(data=razorpay_order_data)
            
            # Update order with Razorpay order ID
            self.supabase.table("orders").update({
                "razorpay_order_id": razorpay_order["id"],
                "status": "pending_payment"
            }).eq("order_id", order_id).execute()
            
            # Try to create QR code, fallback to payment link
            qr_expiry = datetime.now() + timedelta(minutes=30)
            qr_code_url = None
            payment_link_url = None
            
            try:
                # Try QR code creation first
                qr_code_data = {
                    "type": "upi_qr",
                    "name": f"Gurtoy Order {order_id}",
                    "usage": "single_use",
                    "fixed_amount": True,
                    "payment_amount": int(total_amount * 100),  # Amount in paise
                    "description": f"Payment for {product_details['title']}",
                    "customer_id": str(user_id),
                    "close_by": int(qr_expiry.timestamp()),
                    "notes": {
                        "order_id": order_id,
                        "customer_name": customer_details["name"]
                    }
                }
                
                qr_code = self.razorpay_client.qrcode.create(data=qr_code_data)
                qr_code_url = qr_code["image_url"]
                logger.info(f"QR code created successfully for order {order_id}")
                
            except Exception as qr_error:
                logger.warning(f"QR code creation failed: {qr_error}. Creating payment link instead.")
                
                # Create payment link as fallback
                try:
                    payment_link_data = {
                        "amount": int(total_amount * 100),  # Amount in paise
                        "currency": "INR",
                        "accept_partial": False,
                        "expire_by": int(qr_expiry.timestamp()),
                        "reference_id": order_id,
                        "description": f"Payment for {product_details['title']}",
                        "customer": {
                            "name": customer_details["name"],
                            "contact": customer_details["phone"],
                            "email": customer_details.get("email", "")
                        },
                        "notify": {
                            "sms": True,
                            "email": True if customer_details.get("email") else False
                        },
                        "reminder_enable": True,
                        "notes": {
                            "order_id": order_id,
                            "customer_name": customer_details["name"]
                        }
                    }
                    
                    payment_link = self.razorpay_client.payment_link.create(data=payment_link_data)
                    payment_link_url = payment_link["short_url"]
                    logger.info(f"Payment link created successfully for order {order_id}")
                    
                except Exception as link_error:
                    logger.error(f"Both QR code and payment link creation failed: {link_error}")
                    raise Exception("Failed to create payment method")
            
            # Store payment record
            payment_id = f"PAY_{order_id}_{int(datetime.now().timestamp())}"
            
            payment_data = {
                "payment_id": payment_id,
                "order_id": self._get_order_internal_id(order_id),
                "status": "created",
                "amount": float(total_amount),
                "currency": "INR"
            }
            
            # Add QR code or payment link specific data
            if qr_code_url:
                payment_data.update({
                    "razorpay_qr_code_id": qr_code["id"],
                    "qr_code_url": qr_code_url,
                    "qr_code_expires_at": qr_expiry.isoformat()
                })
            elif payment_link_url:
                # Use existing columns for payment link data
                payment_data.update({
                    "qr_code_url": payment_link_url,  # Store payment link in qr_code_url field
                    "qr_code_expires_at": qr_expiry.isoformat()  # Store expiry in existing field
                })
            
            self.supabase.table("payments").insert(payment_data).execute()
            
            # Log status change
            payment_method = "QR code" if qr_code_url else "Payment link"
            self.supabase.rpc(
                "update_order_status",
                {
                    "p_order_id": order_id,
                    "p_new_status": "pending_payment",
                    "p_changed_by": "system",
                    "p_notes": f"{payment_method} generated for payment"
                }
            ).execute()
            
            # Prepare return data
            result = {
                "success": True,
                "order_id": order_id,
                "razorpay_order_id": razorpay_order["id"],
                "total_amount": float(total_amount),
                "currency": "INR",
                "expires_at": qr_expiry,
                "payment_method": payment_method.lower().replace(" ", "_")
            }
            
            # Add method-specific data
            if qr_code_url:
                result.update({
                    "qr_code_url": qr_code_url,
                    "payment_instructions": self._generate_qr_payment_instructions(
                        order_id, total_amount, qr_expiry
                    )
                })
            elif payment_link_url:
                result.update({
                    "payment_link_url": payment_link_url,
                    "payment_instructions": self._generate_link_payment_instructions(
                        order_id, total_amount, qr_expiry, payment_link_url
                    )
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating order with QR: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_order_internal_id(self, order_id: str) -> int:
        """Get internal order ID from order_id string."""
        result = self.supabase.table("orders").select("id").eq("order_id", order_id).execute()
        if result.data:
            return result.data[0]["id"]
        raise Exception(f"Order not found: {order_id}")
    
    def _generate_qr_payment_instructions(
        self, 
        order_id: str, 
        amount: Decimal, 
        expires_at: datetime
    ) -> str:
        """Generate QR code payment instructions for the user."""
        return f"""💳 **QR Code Payment Instructions**

🆔 **Order ID:** {order_id}
💰 **Amount:** ₹{amount}
⏰ **Expires:** {expires_at.strftime('%I:%M %p')} ({expires_at.strftime('%d %b')})

**How to Pay:**
1️⃣ Scan the QR code with any UPI app
2️⃣ Or manually enter UPI ID from QR code
3️⃣ Complete payment within 30 minutes

**Supported Apps:** PhonePe, Google Pay, Paytm, BHIM, etc.

✅ You'll get instant confirmation once payment is successful!"""

    def _generate_link_payment_instructions(
        self, 
        order_id: str, 
        amount: Decimal, 
        expires_at: datetime,
        payment_link: str
    ) -> str:
        """Generate payment link instructions for the user."""
        return f"""💳 **Payment Link Instructions**

🆔 **Order ID:** {order_id}
💰 **Amount:** ₹{amount}
⏰ **Expires:** {expires_at.strftime('%I:%M %p')} ({expires_at.strftime('%d %b')})
🔗 **Payment Link:** {payment_link}

**How to Pay:**
1️⃣ Click on the payment link above
2️⃣ Choose your preferred payment method
3️⃣ Complete payment within 30 minutes

**Supported Methods:** UPI, Cards, Net Banking, Wallets

✅ You'll get instant confirmation once payment is successful!"""
    
    async def _update_payment_status(
        self, 
        order_id: str, 
        status: str, 
        razorpay_payment_id: str = None,
        payment_method: str = None
    ) -> bool:
        """Update payment status in database."""
        try:
            update_data = {"status": status, "updated_at": datetime.now().isoformat()}
            
            if razorpay_payment_id:
                update_data["razorpay_payment_id"] = razorpay_payment_id
                update_data["captured_at"] = datetime.now().isoformat()
            
            if payment_method:
                update_data["method"] = payment_method
            
            # Update payment status
            self.supabase.table("payments").update(update_data).eq(
                "order_id", self._get_order_internal_id(order_id)
            ).execute()
            
            # Update order status if payment is captured
            if status == "captured":
                self.supabase.rpc(
                    "update_order_status",
                    {
                        "p_order_id": order_id,
                        "p_new_status": "paid",
                        "p_changed_by": "system",
                        "p_notes": f"Payment captured: {razorpay_payment_id}"
                    }
                ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating payment status: {e}")
            return False
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify Razorpay webhook signature."""
        if not self.razorpay_webhook_secret:
            logger.warning("Webhook secret not configured")
            return False
        
        try:
            expected_signature = hmac.new(
                self.razorpay_webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    async def handle_webhook(self, payload: Dict[str, Any], signature: str) -> Dict[str, Any]:
        """Handle Razorpay webhook events."""
        try:
            # Verify signature
            payload_str = json.dumps(payload, separators=(',', ':'))
            if not self.verify_webhook_signature(payload_str, signature):
                return {"success": False, "error": "Invalid signature"}
            
            event = payload.get("event")
            entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            
            if not entity:
                entity = payload.get("payload", {}).get("qr_code", {}).get("entity", {})
            
            order_id = None
            
            # Extract order ID from notes or receipt
            if "notes" in entity and "order_id" in entity["notes"]:
                order_id = entity["notes"]["order_id"]
            elif "receipt" in entity:
                order_id = entity["receipt"]
            
            if not order_id:
                logger.warning(f"No order ID found in webhook payload: {payload}")
                return {"success": False, "error": "No order ID found"}
            
            # Handle different webhook events
            if event == "payment.captured":
                await self._handle_payment_captured(entity, order_id)
            elif event == "payment.failed":
                await self._handle_payment_failed(entity, order_id)
            elif event == "qr_code.credited":
                await self._handle_qr_code_credited(entity, order_id)
            
            # Log webhook event
            await self._log_webhook_event(order_id, event, payload)
            
            return {"success": True, "event": event, "order_id": order_id}
            
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_payment_captured(self, payment_entity: Dict[str, Any], order_id: str):
        """Handle payment captured webhook."""
        await self._update_payment_status(
            order_id, 
            "captured", 
            payment_entity.get("id"),
            payment_entity.get("method")  # Pass payment method
        )
        logger.info(f"Payment captured for order {order_id}: {payment_entity.get('id')}")
    
    async def _handle_payment_failed(self, payment_entity: Dict[str, Any], order_id: str):
        """Handle payment failed webhook."""
        await self._update_payment_status(order_id, "failed")
        
        # Update order status
        self.supabase.rpc(
            "update_order_status",
            {
                "p_order_id": order_id,
                "p_new_status": "created",  # Reset to allow retry
                "p_changed_by": "webhook",
                "p_notes": f"Payment failed: {payment_entity.get('error_description', 'Unknown error')}"
            }
        ).execute()
        
        logger.info(f"Payment failed for order {order_id}")
    
    async def _handle_qr_code_credited(self, qr_entity: Dict[str, Any], order_id: str):
        """Handle QR code credited webhook (UPI payment)."""
        # This is similar to payment captured but for QR code payments
        await self._update_payment_status(
            order_id, 
            "captured", 
            qr_entity.get("payment_id")
        )
        logger.info(f"QR code payment credited for order {order_id}")
    
    async def _log_webhook_event(self, order_id: str, event: str, payload: Dict[str, Any]):
        """Log webhook event in database."""
        try:
            order_internal_id = self._get_order_internal_id(order_id)
            
            # Get current webhook events
            result = self.supabase.table("payments").select("webhook_events").eq(
                "order_id", order_internal_id
            ).execute()
            
            if result.data:
                current_events = result.data[0].get("webhook_events", [])
                current_events.append({
                    "event": event,
                    "timestamp": datetime.now().isoformat(),
                    "payload": payload
                })
                
                # Update webhook events
                self.supabase.table("payments").update({
                    "webhook_events": current_events,
                    "last_webhook_at": datetime.now().isoformat()
                }).eq("order_id", order_internal_id).execute()
                
        except Exception as e:
            logger.error(f"Error logging webhook event: {e}")
    
    async def handle_payment_success(self, order_id: str, payment_id: str, amount: float, webhook_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle successful payment."""
        try:
            logger.info(f"Handling payment success for order {order_id}, payment {payment_id}, amount {amount}")
            
            # Update payment status
            await self._update_payment_status(order_id, "captured", payment_id)
            
            # Update order status
            self.supabase.rpc(
                "update_order_status",
                {
                    "p_order_id": order_id,
                    "p_new_status": "paid",
                    "p_changed_by": "payment_success",
                    "p_notes": f"Payment successful: {payment_id}"
                }
            ).execute()
            
            # Log webhook event if provided
            if webhook_data:
                await self._log_webhook_event(order_id, "payment.captured", webhook_data)
            
            logger.info(f"Payment success handled for order {order_id}")
            return {"success": True, "order_id": order_id, "payment_id": payment_id}
            
        except Exception as e:
            logger.error(f"Error handling payment success: {e}")
            return {"success": False, "error": str(e)}
    
    async def handle_payment_failure(self, order_id: str, webhook_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle failed payment."""
        try:
            logger.info(f"Handling payment failure for order {order_id}")
            
            # Update payment status
            await self._update_payment_status(order_id, "failed")
            
            # Update order status
            self.supabase.rpc(
                "update_order_status",
                {
                    "p_order_id": order_id,
                    "p_new_status": "created",  # Reset to allow retry
                    "p_changed_by": "payment_failure",
                    "p_notes": f"Payment failed: {webhook_data.get('error_description', 'Unknown error') if webhook_data else 'Unknown error'}"
                }
            ).execute()
            
            # Log webhook event if provided
            if webhook_data:
                await self._log_webhook_event(order_id, "payment.failed", webhook_data)
            
            logger.info(f"Payment failure handled for order {order_id}")
            return {"success": True, "order_id": order_id}
            
        except Exception as e:
            logger.error(f"Error handling payment failure: {e}")
            return {"success": False, "error": str(e)}
    
    async def check_payment_status(self, order_id: str) -> Dict[str, Any]:
        """
        Check payment status by querying Razorpay API.
        
        IMPROVED: Searches for ALL Razorpay orders with matching receipt ID,
        not just the one stored in database. This handles cases where payment
        links were regenerated and database has newer unpaid order ID.
        """
        try:
            # Get order record from database
            order_result = self.supabase.table("orders").select("*").eq("order_id", order_id).execute()
            
            if not order_result.data:
                return {"success": False, "error": "Order not found"}
            
            order_data = order_result.data[0]
            razorpay_order_id = order_data.get("razorpay_order_id")
            
            if not razorpay_order_id:
                return {"success": False, "error": "Razorpay order ID not found"}
            
            # CRITICAL FIX: Search for ALL Razorpay orders with this receipt ID
            # This handles cases where payment link was regenerated but old one was paid
            try:
                # First, try to fetch all recent orders (last 100)
                all_razorpay_orders = self.razorpay_client.order.all({'count': 100})
                
                # Find ALL orders with matching receipt (our order_id)
                matching_orders = [
                    ro for ro in all_razorpay_orders.get('items', [])
                    if ro.get('receipt') == order_id
                ]
                
                logger.info(f"Found {len(matching_orders)} Razorpay order(s) with receipt={order_id}")
                
                # Check each matching order for payments (prioritize paid orders)
                paid_order_found = None
                
                for razorpay_order in matching_orders:
                    current_razorpay_id = razorpay_order['id']
                    logger.info(f"Checking Razorpay order {current_razorpay_id} (status: {razorpay_order.get('status')})")
                    
                    # Check for payments associated with this order
                    payments_response = self.razorpay_client.order.payments(current_razorpay_id)
                    
                    if payments_response.get("items"):
                        # Check for captured payments
                        for payment in payments_response["items"]:
                            if payment["status"] == "captured":
                                # Found a captured payment!
                                paid_order_found = {
                                    "razorpay_order_id": current_razorpay_id,
                                    "payment": payment
                                }
                                logger.info(f"✅ Found captured payment {payment['id']} for order {order_id}")
                                break
                        
                        if paid_order_found:
                            break  # Stop searching once we find a paid order
                
                # Process the result
                if paid_order_found:
                    # Payment successful - update database if needed
                    payment = paid_order_found["payment"]
                    payment_id = payment["id"]
                    
                    # Update database with correct Razorpay order ID if different
                    if paid_order_found["razorpay_order_id"] != razorpay_order_id:
                        logger.info(f"Updating database: {order_id} razorpay_order_id from {razorpay_order_id} to {paid_order_found['razorpay_order_id']}")
                        self.supabase.table("orders").update({
                            "razorpay_order_id": paid_order_found["razorpay_order_id"]
                        }).eq("order_id", order_id).execute()
                    
                    # Handle payment success
                    await self.handle_payment_success(
                        order_id=order_id,
                        payment_id=payment_id,
                        amount=payment["amount"] / 100,  # Convert from paise
                        webhook_data={"event": "payment.captured", "payment": payment}
                    )
                    return {"success": True, "status": "paid", "payment_id": payment_id}
                
                # No paid orders found, check for failed payments
                for razorpay_order in matching_orders:
                    current_razorpay_id = razorpay_order['id']
                    payments_response = self.razorpay_client.order.payments(current_razorpay_id)
                    
                    if payments_response.get("items"):
                        latest_payment = payments_response["items"][0]
                        if latest_payment["status"] == "failed":
                            # Payment failed
                            await self.handle_payment_failure(
                                order_id=order_id,
                                webhook_data={"event": "payment.failed", "payment": latest_payment}
                            )
                            return {"success": True, "status": "failed", "payment_id": latest_payment["id"]}
                        else:
                            # Payment pending
                            return {"success": True, "status": latest_payment["status"], "payment_id": latest_payment["id"]}
                
                # No payments found for any matching order
                return {"success": True, "status": "created", "payment_id": None}
                    
            except Exception as razorpay_error:
                logger.error(f"Error querying Razorpay API: {razorpay_error}")
                return {"success": False, "error": f"Razorpay API error: {str(razorpay_error)}"}
                
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return {"success": False, "error": str(e)}


class AddressValidator:
    """Validates and formats Indian addresses."""
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str, str]:
        """
        Validate Indian phone number.
        
        Returns:
            (is_valid, cleaned_phone, error_message)
        """
        if not phone:
            return False, "", "Phone number is required"
        
        # Remove all non-digit characters
        cleaned = re.sub(r'\D', '', phone)
        
        # Check for valid Indian mobile number patterns
        if len(cleaned) == 10 and cleaned[0] in '6789':
            return True, cleaned, ""
        elif len(cleaned) == 12 and cleaned.startswith('91') and cleaned[2] in '6789':
            return True, cleaned[2:], ""  # Remove country code
        elif len(cleaned) == 13 and cleaned.startswith('091') and cleaned[3] in '6789':
            return True, cleaned[3:], ""  # Remove country code with 0
        else:
            return False, "", "Please enter a valid 10-digit Indian mobile number"
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """
        Validate email address.
        
        Returns:
            (is_valid, error_message)
        """
        if not email:
            return True, ""  # Email is optional
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, email.strip()):
            return True, ""
        else:
            return False, "Please enter a valid email address"
    
    @staticmethod
    def validate_pincode(pincode: str) -> Tuple[bool, str]:
        """
        Validate Indian pincode.
        
        Returns:
            (is_valid, error_message)
        """
        if not pincode:
            return False, "Pincode is required"
        
        cleaned = re.sub(r'\D', '', pincode)
        if len(cleaned) == 6:
            return True, ""
        else:
            return False, "Please enter a valid 6-digit pincode"
    
    @staticmethod
    def validate_name(name: str) -> Tuple[bool, str]:
        """
        Validate person name.
        
        Returns:
            (is_valid, error_message)
        """
        if not name or len(name.strip()) < 2:
            return False, "Name must be at least 2 characters long"
        
        if len(name.strip()) > 50:
            return False, "Name must be less than 50 characters"
        
        # Check for valid characters (letters, spaces, common punctuation)
        if not re.match(r'^[a-zA-Z\s\.\-\']+$', name.strip()):
            return False, "Name can only contain letters, spaces, dots, hyphens, and apostrophes"
        
        return True, ""
    
    @staticmethod
    def format_address(address_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Format and validate complete address.
        
        Returns:
            Dictionary with validation results and formatted address
        """
        errors = []
        formatted_address = {}
        
        # Validate name
        name_valid, name_error = AddressValidator.validate_name(address_data.get("name", ""))
        if not name_valid:
            errors.append(f"Name: {name_error}")
        else:
            formatted_address["name"] = address_data["name"].strip().title()
        
        # Validate phone
        phone_valid, cleaned_phone, phone_error = AddressValidator.validate_phone(address_data.get("phone", ""))
        if not phone_valid:
            errors.append(f"Phone: {phone_error}")
        else:
            formatted_address["phone"] = cleaned_phone
        
        # Validate email (optional)
        email_valid, email_error = AddressValidator.validate_email(address_data.get("email", ""))
        if not email_valid:
            errors.append(f"Email: {email_error}")
        elif address_data.get("email"):
            formatted_address["email"] = address_data["email"].strip().lower()
        
        # Validate address fields
        required_fields = ["street", "city", "state", "pincode"]
        for field in required_fields:
            value = address_data.get(field, "").strip()
            if not value:
                errors.append(f"{field.title()}: This field is required")
            elif field == "pincode":
                pincode_valid, pincode_error = AddressValidator.validate_pincode(value)
                if not pincode_valid:
                    errors.append(f"Pincode: {pincode_error}")
                else:
                    formatted_address[field] = value
            else:
                if len(value) < 2:
                    errors.append(f"{field.title()}: Must be at least 2 characters")
                elif len(value) > 100:
                    errors.append(f"{field.title()}: Must be less than 100 characters")
                else:
                    formatted_address[field] = value.title()
        
        # Optional landmark
        if address_data.get("landmark"):
            landmark = address_data["landmark"].strip()
            if len(landmark) <= 100:
                formatted_address["landmark"] = landmark.title()
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "formatted_address": formatted_address if len(errors) == 0 else {}
        }