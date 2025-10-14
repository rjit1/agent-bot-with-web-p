"""
Gurtoy Telegram Bot - Polling Mode
A polling-based version that doesn't require webhook setup.
This is ideal for local development and testing without ngrok.
"""
import os
import asyncio
import logging
from typing import Optional, List
from datetime import datetime

import httpx
from dotenv import load_dotenv

# Import the main bot components
from gurtoy_bot import (
    config, 
    UserManager, 
    GurtoyAI,
    gurtoy_ai,  # Import the initialized instance
    TelegramAPI,
    TelegramUser,
    logger,
    supabase  # Import supabase client
)

# Import invoice generator
from invoice_generator import InvoiceGenerator

# Load environment variables
load_dotenv()

# Initialize invoice generator
invoice_generator = None  # Will be initialized in check_pending_payments

async def send_message_with_delay(chat_id: int, message: str, delay: float = 1.0):
    """Send a message with a delay for better user experience."""
    await asyncio.sleep(delay)
    await TelegramAPI.send_message(chat_id, message)

async def send_long_message(chat_id: int, message: str, max_length: int = 1000):
    """Send a long message by splitting it into multiple messages if needed."""
    if len(message) <= max_length:
        await TelegramAPI.send_message(chat_id, message)
        return
    
    # For order messages, split more intelligently
    if "**Aapke Saare Orders" in message or "**Aapke Recent" in message:
        await send_order_messages(chat_id, message)
        return
    
    # Split message into chunks for other long messages
    lines = message.split('\n')
    current_chunk = ""
    
    for line in lines:
        # If adding this line would exceed the limit, send current chunk and start new one
        if len(current_chunk) + len(line) + 1 > max_length and current_chunk:
            await TelegramAPI.send_message(chat_id, current_chunk.strip())
            await asyncio.sleep(0.5)  # Small delay between messages
            current_chunk = line
        else:
            if current_chunk:
                current_chunk += "\n" + line
            else:
                current_chunk = line
    
    # Send the last chunk if there's any content
    if current_chunk.strip():
        await TelegramAPI.send_message(chat_id, current_chunk.strip())

async def send_order_messages(chat_id: int, message: str):
    """Send order messages in a structured way."""
    lines = message.split('\n')
    
    # First message: Summary
    summary_lines = []
    details_start = -1
    
    for i, line in enumerate(lines):
        if "**Complete Details:**" in line:
            details_start = i
            break
        summary_lines.append(line)
    
    # Send summary first
    if summary_lines:
        summary_message = '\n'.join(summary_lines)
        await TelegramAPI.send_message(chat_id, summary_message)
        await asyncio.sleep(1.0)  # Delay between summary and details
    
    # Send details in chunks
    if details_start >= 0:
        detail_lines = lines[details_start:]
        current_chunk = ""
        
        for line in detail_lines:
            # If this is a new order section and current chunk is not empty
            if line.startswith("📦 **Order:") and current_chunk:
                # Send current chunk
                await TelegramAPI.send_message(chat_id, current_chunk.strip())
                await asyncio.sleep(0.8)  # Delay between order details
                current_chunk = line
            else:
                if current_chunk:
                    current_chunk += "\n" + line
                else:
                    current_chunk = line
        
        # Send the last chunk
        if current_chunk.strip():
            await TelegramAPI.send_message(chat_id, current_chunk.strip())

async def send_payment_success_message(chat_id: int, order_id: str, amount: float, product_details: str = ""):
    """Send payment success confirmation message."""
    success_message = f"""🎉 **Payment Successful!**

✅ **Order ID:** {order_id}
💰 **Amount Paid:** Rs {amount}
{product_details}

**What's Next:**
📦 Your order is being processed
🚚 You'll receive shipping updates via SMS
📞 Contact us at 8300000086 for any queries

Thank you for choosing Gurtoy! 😊"""
    
    await TelegramAPI.send_message(chat_id, success_message)
    logger.info(f"Payment success message sent for order {order_id}")

async def check_pending_payments():
    """Check for pending payments and send success notifications."""
    try:
        global invoice_generator
        from gurtoy_bot import gurtoy_ai
        
        # Initialize invoice generator if not already done
        if invoice_generator is None:
            invoice_generator = InvoiceGenerator(supabase)
        
        logger.info(f"[PAYMENT_CHECKER] Starting payment status check...")
        
        # Get all pending orders (created in last 2 hours) that have Razorpay order IDs
        from datetime import timedelta
        two_hours_ago = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        
        pending_orders = supabase.table("orders").select("""
            order_id,
            razorpay_order_id,
            status,
            total_amount,
            user_id,
            users!inner(telegram_id, first_name)
        """).eq("status", "pending_payment").not_.is_("razorpay_order_id", "null").gte("created_at", two_hours_ago).execute()
        
        if pending_orders.data:
            logger.info(f"[PAYMENT_CHECKER] Found {len(pending_orders.data)} pending orders to check")
            
            for order in pending_orders.data:
                order_id = order["order_id"]
                razorpay_order_id = order["razorpay_order_id"]
                telegram_id = order["users"]["telegram_id"]
                user_id = order["user_id"]
                amount = order["total_amount"]
                
                # CRITICAL: Verify we have all required data for proper user targeting
                if not telegram_id:
                    logger.error(f"Cannot send payment notification for order {order_id}: No telegram_id found for user {user_id}")
                    continue
                
                if not razorpay_order_id:
                    logger.warning(f"Skipping payment check for order {order_id}: No Razorpay order ID")
                    continue
                
                logger.info(f"Checking payment for order {order_id} (User: {telegram_id}, Razorpay Order ID: {razorpay_order_id})")
                
                # Check payment status with Razorpay
                status_result = await gurtoy_ai.payment_manager.check_payment_status(order_id)
                
                if status_result["success"] and status_result["status"] == "paid":
                    # Payment successful - send confirmation ONLY to the user who made the payment
                    logger.info(f"Payment successful for order {order_id}, sending confirmation to user {telegram_id}")
                    
                    # Get product details for the success message
                    product_details = ""
                    if status_result.get("order_data") and status_result["order_data"].get("items_data"):
                        product_details = "\n**Your Order:**"
                        for item in status_result["order_data"]["items_data"]:
                            product_details += f"\n• {item['product_title']} (Qty: {item['quantity']})"
                    
                    await send_payment_success_message(telegram_id, order_id, amount, product_details)
                    logger.info(f"Payment success notification sent to user {telegram_id} for order {order_id}")
                    
                    # Generate and send invoice PDF
                    try:
                        logger.info(f"Generating invoice for order {order_id}")
                        invoice_path = await invoice_generator.generate_invoice(order_id)
                        
                        if invoice_path:
                            logger.info(f"Invoice generated successfully: {invoice_path}")
                            
                            # Send invoice PDF to user
                            caption = f"📄 Invoice for Order {order_id}\n\nThank you for your purchase! 🎉"
                            filename = f"Gurtoy_Invoice_{order_id}.pdf"
                            
                            invoice_sent = await TelegramAPI.send_document(
                                chat_id=telegram_id,
                                document_path=invoice_path,
                                caption=caption,
                                filename=filename
                            )
                            
                            if invoice_sent:
                                logger.info(f"Invoice sent successfully to user {telegram_id} for order {order_id}")
                            else:
                                logger.error(f"Failed to send invoice to user {telegram_id} for order {order_id}")
                        else:
                            logger.error(f"Invoice generation failed for order {order_id}")
                            
                    except Exception as invoice_error:
                        logger.error(f"Error in invoice generation/sending for order {order_id}: {invoice_error}", exc_info=True)
                    
                elif status_result["success"] and status_result["status"] == "failed":
                    # Payment failed - send failure message ONLY to the user who made the payment
                    failure_message = f"""❌ **Payment Failed**

📦 **Order ID:** {order_id}

**What happened:**
Your payment could not be processed. This could be due to:
• Insufficient funds
• Card declined
• Network issues

**What to do:**
1. Check your payment method
2. Try again with a different payment method
3. Contact us at 8300000086 for assistance

We'll keep your order ready for 24 hours."""
                    
                    logger.info(f"Payment failed for order {order_id}, sending failure notification to user {telegram_id}")
                    await TelegramAPI.send_message(telegram_id, failure_message)
                    logger.info(f"Payment failure notification sent to user {telegram_id} for order {order_id}")
                
                else:
                    logger.info(f"[PAYMENT_CHECKER] Payment status for order {order_id}: {status_result.get('status', 'unknown')} - no notification needed")
        else:
            logger.info(f"[PAYMENT_CHECKER] No pending orders found to check")
        
        logger.info(f"[PAYMENT_CHECKER] Payment status check completed")
        
    except Exception as e:
        logger.error(f"[PAYMENT_CHECKER] Error checking pending payments: {e}")

class TelegramPollingBot:
    """Telegram bot using polling mode (getUpdates)."""
    
    def __init__(self):
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.offset = 0
        self.timeout = 30  # Long polling timeout
        self.running = False
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        
        # Initialize audio handler for voice message processing
        from audio_handler import initialize_audio_handler
        initialize_audio_handler(config.TELEGRAM_BOT_TOKEN, config.GEMINI_API_KEY)
        logger.info("🎤 Audio handler initialized for voice messages")
        
        # Initialize image handler for image processing
        from image_handler import initialize_image_handler
        initialize_image_handler(config.TELEGRAM_BOT_TOKEN, config.GEMINI_API_KEY)
        logger.info("📸 Image handler initialized for image messages")
        
        logger.info("Telegram Polling Bot initialized")
    
    async def delete_webhook(self):
        """Delete any existing webhook to enable polling."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/deleteWebhook",
                    json={"drop_pending_updates": False}
                )
                result = response.json()
                if result.get("ok"):
                    logger.info("✅ Webhook deleted, polling mode enabled")
                    return True
                else:
                    logger.warning(f"Failed to delete webhook: {result.get('description')}")
                    return False
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            return False
    
    async def get_updates(self) -> list:
        """Get updates from Telegram using long polling."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout + 5) as client:
                response = await client.post(
                    f"{self.api_url}/getUpdates",
                    json={
                        "offset": self.offset,
                        "timeout": self.timeout,
                        "allowed_updates": ["message", "callback_query"]
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        return result.get("result", [])
                    else:
                        logger.error(f"API error: {result.get('description')}")
                        return []
                else:
                    logger.error(f"HTTP error: {response.status_code}")
                    return []
                    
        except httpx.TimeoutException:
            # Timeout is expected with long polling
            return []
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return []
    
    async def process_update(self, update: dict):
        """Process a single update."""
        try:
            update_id = update.get("update_id")
            message = update.get("message")
            
            if not message:
                logger.debug(f"Skipping update {update_id}: no message")
                return
            
            # Extract message data
            telegram_user_data = message.get("from", {})
            chat = message.get("chat", {})
            chat_id = chat.get("id")
            
            # Create TelegramUser object
            telegram_user = TelegramUser(
                id=telegram_user_data.get("id"),
                is_bot=telegram_user_data.get("is_bot", False),
                first_name=telegram_user_data.get("first_name", "User"),
                last_name=telegram_user_data.get("last_name"),
                username=telegram_user_data.get("username"),
                language_code=telegram_user_data.get("language_code", "en")
            )

            # Get or create user data early (needed for all message types)
            user_data = await UserManager.get_or_create_user(telegram_user)
            if not user_data:
                await TelegramAPI.send_message(
                    chat_id,
                    "Sorry, I'm having trouble accessing your profile. Please try again later."
                )
                return

            # Get user context
            user_context = await UserManager.get_user_context(telegram_user.id)
            user_context["user_id"] = user_data["id"]
            user_context["telegram_id"] = telegram_user.id  # Add Telegram ID for buy_product function

            # Add order collection session info to context
            from gurtoy_bot import PAYMENT_SYSTEM_AVAILABLE
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

            # Check if this is a voice message
            voice = message.get("voice")
            if voice:
                logger.info(f"🎤 Voice message from {telegram_user.first_name} ({telegram_user.id})")
                
                # Send "processing" message
                processing_msg = "🎤 Aapka voice message sun raha hoon... ek second! 😊"
                await TelegramAPI.send_message(chat_id, processing_msg)
                
                # Import audio handler
                from audio_handler import get_audio_handler
                audio_handler = get_audio_handler()
                
                if not audio_handler:
                    error_msg = "Sorry, voice message processing abhi available nahi hai. Please text message bhejiye. 🙏"
                    await TelegramAPI.send_message(chat_id, error_msg)
                    return
                
                # Process voice message
                file_id = voice.get("file_id")
                duration = voice.get("duration", 0)
                
                # Check duration limit
                if duration > audio_handler.MAX_AUDIO_DURATION:
                    error_msg = f"Sorry, voice message bahut lamba hai ({duration}s). Please {audio_handler.MAX_AUDIO_DURATION}s se chhota message bhejiye. 🙏"
                    await TelegramAPI.send_message(chat_id, error_msg)
                    return
                
                # Process voice message (download + transcribe + cleanup)
                transcription_result = await audio_handler.process_voice_message(
                    file_id, 
                    telegram_user.id,
                    duration
                )
                
                if not transcription_result or not transcription_result.get("transcription"):
                    error_msg = "Sorry, main aapka voice message samajh nahi payi. Kya aap text mein likh sakte hain? 🙏"
                    await TelegramAPI.send_message(chat_id, error_msg)
                    return
                
                # Use transcription as user text
                user_text = transcription_result["transcription"]
                confidence = transcription_result.get("confidence", "medium")
                language = transcription_result.get("language", "Unknown")
                
                logger.info(f"📝 Transcription ({language}, {confidence} confidence): {user_text}")
                
                # Send confirmation with transcription
                if confidence == "high":
                    confirmation_msg = f"✅ Samajh gayi! Aapne kaha:\n\n\"{user_text}\"\n\nJawab de rahi hoon... 💭"
                else:
                    confirmation_msg = f"✅ Maine suna:\n\n\"{user_text}\"\n\nAgar galat hai toh text mein bata dijiye. Jawab de rahi hoon... 💭"
                
                await TelegramAPI.send_message(chat_id, confirmation_msg)
                
            # Check if this is an image message
            elif message.get("photo"):
                logger.info(f"📸 Image from {telegram_user.first_name} ({telegram_user.id})")
                
                # Import image handler and queue manager
                from image_handler import get_image_handler
                from image_queue_manager import get_queue_manager
                
                image_handler = get_image_handler()
                queue_manager = get_queue_manager()
                
                if not image_handler:
                    error_msg = "Sorry, image processing abhi available nahi hai. 🙏"
                    await TelegramAPI.send_message(chat_id, error_msg)
                    return
                
                # Get highest resolution photo (Telegram sends multiple sizes)
                photos = message.get("photo", [])
                largest_photo = max(photos, key=lambda p: p.get("file_size", 0))
                file_id = largest_photo.get("file_id")
                caption = message.get("caption")
                
                # Download image
                image_path = await image_handler.download_image(file_id, telegram_user.id)
                
                if not image_path:
                    error_msg = "Sorry, main image download nahi kar payi. Kya aap dobara try kar sakte hain? 🙏"
                    await TelegramAPI.send_message(chat_id, error_msg)
                    return
                
                # Add to queue (will accumulate if user sends more images)
                queue_added = queue_manager.add_image(
                    user_id=telegram_user.id,
                    chat_id=chat_id,
                    image_path=image_path,
                    file_id=file_id,
                    caption=caption
                )
                
                if not queue_added:
                    error_msg = "Sorry, bahut saare images ek saath nahi bhej sakte. Pehle wale ka response wait karein. 🙏"
                    await TelegramAPI.send_message(chat_id, error_msg)
                    await image_handler.cleanup_image_file(image_path)
                    return
                
                # Create timeout task to process images after waiting period
                async def handle_image_timeout(chat_id, user_id, user_context, session_id, user_data):
                    """Process images after timeout (no more images or text received)."""
                    try:
                        await asyncio.sleep(queue_manager.IMAGE_WAIT_TIMEOUT)

                        # Check if still in queue (might have been processed by text message)
                        pending = queue_manager.get_pending(user_id)
                        if pending and pending.timeout_task == asyncio.current_task():
                            # Remove from queue now that we're committed to processing
                            pending = queue_manager.remove_pending(user_id)

                            if pending:
                                # Mark as processing started to prevent cancellation
                                pending.processing_started = True

                                num_images = len(pending.image_paths)
                                logger.info(
                                    f"⏰ Timeout reached for user {user_id}, "
                                    f"processing {num_images} image(s)"
                                )

                                # Analyze images for product search
                                analysis_result = await image_handler.generate_product_search_description(
                                    pending.image_paths,
                                    self._combine_captions(pending.captions)  # Combine all captions
                                )

                                # DON'T cleanup images yet - we need them for visual verification
                                # await image_handler.cleanup_multiple_images(pending.image_paths)

                                if not analysis_result:
                                    # Cleanup images if analysis failed
                                    await image_handler.cleanup_multiple_images(pending.image_paths)
                                    error_msg = "Sorry, main image samajh nahi payi. Text mein bata sakte hain? 🙏"
                                    await TelegramAPI.send_message(chat_id, error_msg)
                                    return

                                # Create enhanced context for AI with product-focused analysis
                                image_context = f"""[User sent {num_images} image(s) of a product they want to find]
[Product Type: {analysis_result.get('product_type')}]
[Detailed Description: {analysis_result.get('detailed_description')}]
[Colors: {', '.join(analysis_result.get('colors', []))}]
[Key Features: {', '.join(analysis_result.get('key_features', []))}]
[Age Range: {analysis_result.get('age_range', 'Not specified')}]
[Size Category: {analysis_result.get('size_category', 'Not specified')}]"""

                                if analysis_result.get('style_keywords'):
                                    image_context += f"\n[Style Keywords: {', '.join(analysis_result['style_keywords'])}]"

                                # Add combined captions if any exist
                                combined_caption = self._combine_captions(pending.captions)
                                if combined_caption:
                                    image_context += f"\n[User's Captions: {combined_caption}]"

                                logger.info(f"📝 Image-only context: {image_context[:150]}...")

                                # Process through AI directly (avoid synthetic message recursion)
                                # Pass the first image path for visual verification
                                await self._process_image_context_directly(
                                    chat_id, user_id, image_context, user_context, session_id, user_data, pending.image_paths[0]
                                )
                                
                                # Cleanup images after processing is complete
                                await image_handler.cleanup_multiple_images(pending.image_paths)

                    except asyncio.CancelledError:
                        logger.info(f"✅ Timeout cancelled for user {user_id} (follow-up received)")
                    except Exception as e:
                        logger.error(f"Error in image timeout handler: {e}", exc_info=True)
                
                # Get session ID for logging
                session_id = user_context.get("session_data", {}).get("id")

                # Start timeout task
                timeout_task = asyncio.create_task(handle_image_timeout(
                    chat_id, telegram_user.id, user_context, session_id, user_data
                ))
                queue_manager.set_timeout_task(telegram_user.id, timeout_task)
                
                image_count = queue_manager.get_user_image_count(telegram_user.id)
                logger.info(
                    f"📸 Image {image_count}/{queue_manager.MAX_IMAGES_PER_USER} queued for user {telegram_user.id}, "
                    f"waiting {queue_manager.IMAGE_WAIT_TIMEOUT}s for more images or text..."
                )
                
                # Don't process yet - wait for timeout or text message
                return
                
            # Check if this is a text message
            elif message.get("text"):
                user_text = message.get("text", "")
                logger.info(f"📨 Message from {telegram_user.first_name} ({telegram_user.id}): {user_text[:50]}...")
                
                # Check if user has pending images (text follow-up to images)
                from image_queue_manager import get_queue_manager
                from image_handler import get_image_handler
                
                queue_manager = get_queue_manager()
                image_handler = get_image_handler()
                
                if queue_manager.has_pending(telegram_user.id):
                    # User sent text after image(s) - combine them!
                    pending = queue_manager.remove_pending(telegram_user.id)
                    
                    if pending and image_handler:
                        num_images = len(pending.image_paths)
                        logger.info(
                            f"✅ Combining {num_images} image(s) + text for user {telegram_user.id}"
                        )
                        
                        # Analyze images for product search
                        analysis_result = await image_handler.generate_product_search_description(
                            pending.image_paths,
                            self._combine_captions(pending.captions)  # Combine all captions
                        )
                        
                        # DON'T cleanup images yet - we need them for visual verification
                        # await image_handler.cleanup_multiple_images(pending.image_paths)
                        
                        if analysis_result:
                            # Combine image analysis with user's text
                            image_context = f"""[User sent {num_images} image(s) followed by text message]
[Product Type: {analysis_result.get('product_type')}]
[Detailed Description: {analysis_result.get('detailed_description')}]
[Colors: {', '.join(analysis_result.get('colors', []))}]
[Key Features: {', '.join(analysis_result.get('key_features', []))}]
[Age Range: {analysis_result.get('age_range', 'Not specified')}]
[Size Category: {analysis_result.get('size_category', 'Not specified')}]"""

                            if analysis_result.get('style_keywords'):
                                image_context += f"\n[Style Keywords: {', '.join(analysis_result['style_keywords'])}]"

                            # Add combined captions if any exist
                            combined_caption = self._combine_captions(pending.captions)
                            if combined_caption:
                                image_context += f"\n[Image Captions: {combined_caption}]"

                            image_context += f"\n[User's Follow-up Message: {user_text}]"
                            
                            # Replace user_text with combined context
                            user_text = image_context
                            logger.info(f"📝 Combined image+text context: {user_text[:150]}...")
                            
                            # Store image path for visual verification
                            user_context["user_image_path"] = pending.image_paths[0]
                            
                            # Store pending images for cleanup after processing
                            self._current_pending_images = pending.image_paths
                        else:
                            logger.warning("Image analysis failed, using text only")
                            # Cleanup images if analysis failed
                            await image_handler.cleanup_multiple_images(pending.image_paths)

            else:
                logger.debug(f"Skipping update {update_id}: no text, voice, or image message")
                return
            
            # Check if user replied to a message (product card)
            reply_to_message = message.get("reply_to_message")
            logger.info(f"🔍 Checking for reply: reply_to_message={'present' if reply_to_message else 'absent'}")
            
            if reply_to_message:
                logger.info(f"🔍 Reply detected! Has caption: {reply_to_message.get('caption') is not None}, Has photo: {reply_to_message.get('photo') is not None}")
                # Import ProductContextExtractor from main bot
                from gurtoy_bot import ProductContextExtractor, TelegramMessage, TelegramUser as TGUser
                
                # Convert reply_to_message dict to TelegramMessage object
                try:
                    # Create TelegramUser for the replied message sender
                    replied_from = reply_to_message.get("from", {})
                    replied_user = TGUser(
                        id=replied_from.get("id", 0),
                        is_bot=replied_from.get("is_bot", True),
                        first_name=replied_from.get("first_name", "Bot"),
                        last_name=replied_from.get("last_name"),
                        username=replied_from.get("username"),
                        language_code=replied_from.get("language_code", "en")
                    )
                    
                    # Create TelegramMessage object
                    replied_message = TelegramMessage(
                        message_id=reply_to_message.get("message_id", 0),
                        **{"from": replied_user},
                        chat=reply_to_message.get("chat", {}),
                        date=reply_to_message.get("date", 0),
                        text=reply_to_message.get("text"),
                        photo=reply_to_message.get("photo"),
                        caption=reply_to_message.get("caption")
                    )
                    
                    # Extract product context
                    product_context = ProductContextExtractor.extract_product_context(replied_message)
                    if product_context:
                        # Add product context to user_context
                        user_context["replied_product"] = product_context
                        formatted_context = ProductContextExtractor.format_product_context_for_ai(product_context)
                        logger.info(f"📦 User replied to product: {formatted_context}")
                    else:
                        logger.info(f"ℹ️ Reply detected but no product context extracted (not a product card)")
                except Exception as e:
                    logger.error(f"❌ Error parsing reply_to_message: {e}", exc_info=True)
            
            # Log user message
            session_id = user_context.get("session_data", {}).get("id")
            await UserManager.log_conversation(
                user_data["id"], session_id, "user", user_text
            )
            
            # Check if user is in order collection process - MUST happen BEFORE AI processing
            from gurtoy_bot import PAYMENT_SYSTEM_AVAILABLE, supabase
            import json
            from datetime import datetime
            
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
                                    # Send confirmation message first
                                    confirmation_message = "Great! Aapki details confirm ho gayi hain. Ab main aapke liye payment link generate kar raha hoon. Thoda wait karein. 😊"
                                    await TelegramAPI.send_message(chat_id, confirmation_message)
                                    await UserManager.log_conversation(
                                        user_data["id"], session_id, "assistant", confirmation_message
                                    )
                                    
                                    # Wait a bit for better UX
                                    await asyncio.sleep(2)
                                    
                                    # Create order and payment using PaymentManager (this creates both database order and Razorpay order)
                                    try:
                                        logger.info(f"[ORDER_COLLECTION] Creating order and payment using PaymentManager")
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
                                            
                                            await TelegramAPI.send_message(chat_id, payment_message)
                                            await UserManager.log_conversation(
                                                user_data["id"], session_id, "assistant", payment_message
                                            )
                                            logger.info(f"[ORDER_COLLECTION] Real payment link sent to user {telegram_user.id} for order {order_id}")
                                            return
                                        else:
                                            # Payment creation failed
                                            error_msg = f"Sorry, there was an error creating your payment: {payment_result.get('error', 'Unknown error')}. Please try again or contact us directly."
                                            await TelegramAPI.send_message(chat_id, error_msg)
                                            await UserManager.log_conversation(
                                                user_data["id"], session_id, "assistant", error_msg
                                            )
                                            logger.error(f"[ORDER_COLLECTION] Payment creation failed: {payment_result.get('error')}")
                                            return
                                            
                                    except Exception as payment_error:
                                        logger.error(f"[ORDER_COLLECTION] Error creating Razorpay payment: {payment_error}")
                                        error_msg = "Sorry, there was an error processing your payment. Please try again or contact us directly."
                                        await TelegramAPI.send_message(chat_id, error_msg)
                                        await UserManager.log_conversation(
                                            user_data["id"], session_id, "assistant", error_msg
                                        )
                                        return
                                except Exception as e:
                                    logger.error(f"[ORDER_COLLECTION] Error creating payment: {e}")
                                    error_msg = "Sorry, there was an error processing your payment. Please try again or contact us directly."
                                    await TelegramAPI.send_message(chat_id, error_msg)
                                    await UserManager.log_conversation(
                                        user_data["id"], session_id, "assistant", error_msg
                                    )
                                    return
                            else:
                                # Check if this is a general conversation flag (should bypass order collection)
                                if response_message == "__GENERAL_CONVERSATION__":
                                    logger.info(f"[GENERAL_CONVERSATION] User sent general conversation during order collection, bypassing to normal AI")
                                    # Don't return - let it fall through to normal AI processing below
                                else:
                                    # Order collection in progress, send response
                                    logger.info(f"[ORDER_COLLECTION] Order collection in progress, sending response")
                                    
                                    # Check if this is a confirmation message (shows extracted details)
                                    if "Main aapki details process kar raha hoon:" in response_message:
                                        # Send confirmation message first
                                        await TelegramAPI.send_message(chat_id, response_message)
                                        await UserManager.log_conversation(
                                            user_data["id"], session_id, "assistant", response_message
                                        )
                                        logger.info(f"[ORDER_COLLECTION] Confirmation message sent to {telegram_user.first_name}")
                                    else:
                                        # Regular response
                                        await TelegramAPI.send_message(chat_id, response_message)
                                        await UserManager.log_conversation(
                                            user_data["id"], session_id, "assistant", response_message
                                        )
                                        logger.info(f"[ORDER_COLLECTION] Order collection response sent to {telegram_user.first_name}")
                                    return
                        else:
                            # Order collection error
                            logger.error(f"[ORDER_COLLECTION] Order collection error for user {telegram_user.id}")
                            await TelegramAPI.send_message(chat_id, response_message)
                            await UserManager.log_conversation(
                                user_data["id"], session_id, "assistant", response_message
                            )
                            return
                    else:
                        logger.info(f"[ORDER_COLLECTION] No active order session found for user {telegram_user.id}, proceeding with normal AI processing")
                except Exception as e:
                    logger.error(f"[ORDER_COLLECTION] Error in order collection process: {e}")

            # Check if order collector returned general conversation flag
            # This means the user message should be processed by normal AI instead of order collection
            if 'response_message' in locals() and response_message == "__GENERAL_CONVERSATION__":
                logger.info(f"[GENERAL_CONVERSATION] Bypassing order collection for user {telegram_user.id}, proceeding with normal AI")

            # Generate AI response using the initialized instance
            ai_response, products = await gurtoy_ai.generate_response(user_text, user_context)
            
            # Check if we need to show products
            if ai_response == "SHOW_PRODUCTS":
                if products and len(products) > 0:
                    # Send product cards instead of text response
                    success = await TelegramAPI.send_product_cards(chat_id, products)
                    
                    if success:
                        # Log that products were shown
                        log_message = f"Showed {len(products)} products"
                        await UserManager.log_conversation(
                            user_data["id"], session_id, "assistant", log_message
                        )
                        logger.info(f"✅ Showed {len(products)} products to {telegram_user.first_name}")
                    else:
                        logger.error(f"Failed to send product cards to {telegram_user.first_name}")
                else:
                    # FIXED: Handle case when AI wants to show products but none were found
                    # Don't send "SHOW_PRODUCTS" text to user - send a proper message
                    no_products_msg = "Sorry, main koi product nahi dhoondh payi. Kya aap kuch aur try karna chahenge? 😊"
                    await TelegramAPI.send_message(chat_id, no_products_msg)
                    await UserManager.log_conversation(
                        user_data["id"], session_id, "assistant", no_products_msg
                    )
                    logger.warning(f"⚠️ AI wanted to show products but none were found for {telegram_user.first_name}")
            else:
                # Send regular text response - use multi-message for long responses
                if len(ai_response) > 1000:
                    await send_long_message(chat_id, ai_response)
                    logger.info(f"✅ Long response sent in multiple messages to {telegram_user.first_name}")
                else:
                    await TelegramAPI.send_message(chat_id, ai_response)
                    logger.info(f"✅ Response sent to {telegram_user.first_name}")
                
                # Log bot response
                await UserManager.log_conversation(
                    user_data["id"], session_id, "assistant", ai_response
                )
            
            # Cleanup images after processing is complete (if we have pending images)
            if hasattr(self, '_current_pending_images') and self._current_pending_images:
                try:
                    await image_handler.cleanup_multiple_images(self._current_pending_images)
                    logger.info(f"🗑️ Cleaned up {len(self._current_pending_images)} images after processing")
                    self._current_pending_images = None
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup images after processing: {cleanup_error}")
            
        except Exception as e:
            logger.error(f"Error processing update: {e}", exc_info=True)
            try:
                if message and message.get("chat"):
                    await TelegramAPI.send_message(
                        message["chat"]["id"],
                        "Sorry, I encountered an error processing your message. Please try again."
                    )
            except:
                pass
    
    async def start_polling(self):
        """Start the polling loop."""
        logger.info("🤖 Starting Gurtoy Telegram Bot in POLLING mode...")
        logger.info("=" * 60)
        
        # Delete webhook first
        await self.delete_webhook()
        
        # Get bot info
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_url}/getMe")
                if response.status_code == 200:
                    bot_info = response.json().get("result", {})
                    logger.info(f"✅ Bot: @{bot_info.get('username')} ({bot_info.get('first_name')})")
                    logger.info(f"📱 Bot ID: {bot_info.get('id')}")
        except Exception as e:
            logger.warning(f"Could not get bot info: {e}")
        
        logger.info("=" * 60)
        logger.info("🟢 Bot is now running and listening for messages...")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        self.running = True
        payment_check_counter = 0  # Counter for payment status checks
        audio_cleanup_counter = 0  # Counter for audio file cleanup
        
        try:
            while self.running:
                # Get updates
                updates = await self.get_updates()
                
                # Process each update
                for update in updates:
                    update_id = update.get("update_id")
                    
                    # Update offset to acknowledge this update
                    self.offset = update_id + 1
                    
                    # Process update
                    await self.process_update(update)
                
                # Check payment statuses every 3 iterations (approximately every 3 seconds)
                payment_check_counter += 1
                logger.info(f"[POLLING_DEBUG] Counter: {payment_check_counter}")

                if payment_check_counter >= 3:
                    payment_check_counter = 0
                    try:
                        logger.info(f"[PAYMENT_CHECKER] Running payment status check (counter reached 3)")
                        await check_pending_payments()
                        logger.info(f"[PAYMENT_CHECKER] Payment status check completed")
                    except Exception as e:
                        logger.error(f"[PAYMENT_CHECKER] Error in payment status check: {e}")

                # Cleanup expired order collection sessions every 60 iterations (approximately every 1 minute)
                session_cleanup_counter = getattr(self, 'session_cleanup_counter', 0) + 1
                setattr(self, 'session_cleanup_counter', session_cleanup_counter)

                if session_cleanup_counter >= 60:
                    setattr(self, 'session_cleanup_counter', 0)
                    try:
                        logger.info(f"[SESSION_CLEANUP] Running session cleanup (counter reached 60)")
                        from ai_order_collector import AIOrderCollector
                        order_collector = AIOrderCollector.get_instance()
                        if order_collector:
                            order_collector.cleanup_expired_sessions()
                        logger.info(f"[SESSION_CLEANUP] Session cleanup completed")
                    except Exception as e:
                        logger.error(f"[SESSION_CLEANUP] Error in session cleanup: {e}")

                # Cleanup old audio files every 120 iterations (approximately every 2 minutes)
                audio_cleanup_counter += 1
                if audio_cleanup_counter >= 120:
                    audio_cleanup_counter = 0
                    try:
                        from audio_handler import get_audio_handler
                        audio_handler = get_audio_handler()
                        if audio_handler:
                            deleted_count = await audio_handler.cleanup_old_audio_files()
                            if deleted_count > 0:
                                logger.info(f"🧹 [AUDIO_CLEANUP] Cleaned up {deleted_count} old audio files")
                    except Exception as e:
                        logger.error(f"[AUDIO_CLEANUP] Error in audio cleanup: {e}")
                
                # Small delay to prevent CPU spinning
                if not updates:
                    await asyncio.sleep(0.1)
                    
        except KeyboardInterrupt:
            logger.info("\n🛑 Bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
        finally:
            self.running = False
            logger.info("👋 Bot shutdown complete")
    
    def _combine_captions(self, captions: List[Optional[str]]) -> Optional[str]:
        """Combine multiple captions into a single string."""
        valid_captions = [c for c in captions if c and c.strip()]
        if not valid_captions:
            return None
        elif len(valid_captions) == 1:
            return valid_captions[0]
        else:
            return " | ".join(f"Image {i+1}: {caption}" for i, caption in enumerate(valid_captions))

    async def _process_image_context_directly(self, chat_id: int, user_id: int, image_context: str, user_context: dict, session_id: Optional[str], user_data: dict, image_path: Optional[str] = None):
        """Process image context directly through AI without synthetic message recursion."""
        try:
            # Update user context
            user_context["user_id"] = user_data["id"]
            user_context["telegram_id"] = user_id
            
            # Store image path for visual verification if provided
            if image_path:
                user_context["user_image_path"] = image_path

            # Log user message
            await UserManager.log_conversation(
                user_data["id"], session_id, "user", image_context
            )

            # Generate AI response using the initialized instance
            ai_response, products = await gurtoy_ai.generate_response(image_context, user_context)

            # Check if we need to show products
            if ai_response == "SHOW_PRODUCTS":
                if products and len(products) > 0:
                    # Send product cards instead of text response
                    success = await TelegramAPI.send_product_cards(chat_id, products)

                    if success:
                        # Log that products were shown
                        log_message = f"Showed {len(products)} products from image analysis"
                        await UserManager.log_conversation(
                            user_data["id"], session_id, "assistant", log_message
                        )
                        logger.info(f"✅ Showed {len(products)} products from image analysis to user {user_id}")
                    else:
                        logger.error(f"Failed to send product cards from image analysis to user {user_id}")
                else:
                    # Handle case when AI wants to show products but none were found
                    no_products_msg = "Sorry, main koi product nahi dhoondh payi jo aapki image mein dikhe. Kya aap kuch aur try karna chahenge? 😊"
                    await TelegramAPI.send_message(chat_id, no_products_msg)
                    await UserManager.log_conversation(
                        user_data["id"], session_id, "assistant", no_products_msg
                    )
                    logger.warning(f"⚠️ AI wanted to show products from image but none were found for user {user_id}")
            else:
                # Send regular text response - use multi-message for long responses
                if len(ai_response) > 1000:
                    await send_long_message(chat_id, ai_response)
                    logger.info(f"✅ Long image analysis response sent in multiple messages to user {user_id}")
                else:
                    await TelegramAPI.send_message(chat_id, ai_response)
                    logger.info(f"✅ Image analysis response sent to user {user_id}")

                # Log bot response
                await UserManager.log_conversation(
                    user_data["id"], session_id, "assistant", ai_response
                )
            
            # Cleanup images after processing is complete
            if image_path and os.path.exists(image_path):
                try:
                    await asyncio.to_thread(os.remove, image_path)
                    logger.info(f"🗑️ Cleaned up image file after processing: {image_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup image file: {cleanup_error}")

        except Exception as e:
            logger.error(f"Error processing image context directly: {e}", exc_info=True)
            try:
                await TelegramAPI.send_message(
                    chat_id,
                    "Sorry, I encountered an error processing your image. Please try again."
                )
            except:
                pass
            
            # Cleanup images on error
            if image_path and os.path.exists(image_path):
                try:
                    await asyncio.to_thread(os.remove, image_path)
                    logger.info(f"🗑️ Cleaned up image file after error: {image_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup image file after error: {cleanup_error}")

    def stop(self):
        """Stop the polling loop."""
        self.running = False


async def main():
    """Main entry point."""
    bot = TelegramPollingBot()
    await bot.start_polling()


async def manual_payment_check():
    """Manual payment check for testing."""
    print("=" * 60)
    print("MANUAL PAYMENT CHECK")
    print("=" * 60)
    try:
        await check_pending_payments()
        print("[SUCCESS] Manual payment check completed")
    except Exception as e:
        print(f"[ERROR] Manual payment check failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "check-payments":
        # Manual payment check mode
        asyncio.run(manual_payment_check())
    else:
        # Normal bot mode
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")