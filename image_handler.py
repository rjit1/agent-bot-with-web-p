"""
Image Handler Module for Gurtoy Telegram Bot
Handles image download, analysis with Gemini, and cleanup.
"""
import os
import asyncio
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

import httpx
import aiofiles
import google.generativeai as genai

# Configure logging
logger = logging.getLogger(__name__)

class ImageHandler:
    """Handles image processing with Gemini 2.5 Flash."""
    
    # Directory for temporary image storage
    TEMP_IMAGE_DIR = Path(__file__).parent / "temp_images"
    
    # Maximum image file size (20MB for File API)
    MAX_IMAGE_SIZE_MB = 20
    MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024
    
    # Maximum number of images to process together
    MAX_IMAGES_PER_REQUEST = 6
    
    # Supported image formats
    SUPPORTED_FORMATS = ["jpg", "jpeg", "png", "webp", "heic", "heif"]
    
    def __init__(self, telegram_bot_token: str, gemini_api_key: str):
        """
        Initialize ImageHandler.
        
        Args:
            telegram_bot_token: Telegram bot token for file downloads
            gemini_api_key: Gemini API key for image analysis
        """
        self.telegram_bot_token = telegram_bot_token
        self.telegram_api_url = f"https://api.telegram.org/bot{telegram_bot_token}"
        
        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        
        # Ensure temp directory exists
        self.TEMP_IMAGE_DIR.mkdir(exist_ok=True)
        
        logger.info("📸 ImageHandler initialized")
    
    async def download_image(
        self, 
        file_id: str, 
        telegram_id: int
    ) -> Optional[str]:
        """
        Download image from Telegram.
        
        Args:
            file_id: Telegram file ID
            telegram_id: User's Telegram ID (for unique filename)
            
        Returns:
            Path to downloaded image file or None if failed
        """
        try:
            # Step 1: Get file info from Telegram
            logger.info(f"📥 Downloading image (file_id: {file_id})")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.telegram_api_url}/getFile",
                    params={"file_id": file_id}
                )
                response.raise_for_status()
                result = response.json()
                
                if not result.get("ok"):
                    logger.error(f"Failed to get file info: {result}")
                    return None
                
                file_path = result["result"]["file_path"]
                file_size = result["result"]["file_size"]
                
                # Check file size
                if file_size > self.MAX_IMAGE_SIZE_BYTES:
                    logger.warning(f"Image too large: {file_size} bytes (max: {self.MAX_IMAGE_SIZE_BYTES})")
                    return None
                
                logger.info(f"File info: {file_path} ({file_size} bytes)")
            
            # Step 2: Download file
            file_url = f"https://api.telegram.org/file/bot{self.telegram_bot_token}/{file_path}"
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(file_url)
                response.raise_for_status()
                image_data = response.content
            
            # Step 3: Save to temp directory with unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            # Extract extension from file_path
            ext = file_path.split('.')[-1].lower()
            if ext not in self.SUPPORTED_FORMATS:
                ext = "jpg"  # Default to jpg
            
            filename = f"{telegram_id}_{timestamp}.{ext}"
            image_path = self.TEMP_IMAGE_DIR / filename
            
            async with aiofiles.open(image_path, 'wb') as f:
                await f.write(image_data)
            
            logger.info(f"✅ Image saved: {image_path} ({len(image_data)} bytes)")
            return str(image_path)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading image: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error downloading image: {e}", exc_info=True)
            return None
    
    async def analyze_images(
        self, 
        image_paths: List[str], 
        caption: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze one or more images using Gemini 2.5 Flash.
        
        Args:
            image_paths: List of paths to image files
            caption: Optional caption/text from user
            
        Returns:
            Dictionary with analysis results:
            {
                "image_type": "toy|product_screenshot|reference|child_photo|comparison|damaged|unrelated|unclear",
                "description": "Brief description",
                "analysis": "Detailed analysis for conversation",
                "key_features": ["feature1", "feature2"],
                "suggested_age": "age range if applicable",
                "confidence": "high|medium|low",
                "num_images": 1
            }
        """
        start_time = datetime.now()
        uploaded_files = []
        
        try:
            num_images = len(image_paths)
            logger.info(f"🔍 Analyzing {num_images} image(s)...")
            
            # Upload all images to Gemini File API
            for i, image_path in enumerate(image_paths):
                file_size_kb = os.path.getsize(image_path) / 1024
                logger.info(f"📤 Uploading image {i+1}/{num_images}: {file_size_kb:.2f} KB")
                
                uploaded_file = await asyncio.to_thread(
                    genai.upload_file,
                    path=image_path,
                    display_name=f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}"
                )
                
                # Wait for file to be processed
                while uploaded_file.state.name == "PROCESSING":
                    logger.info(f"⏳ Waiting for image {i+1} processing...")
                    await asyncio.sleep(1)
                    uploaded_file = await asyncio.to_thread(genai.get_file, uploaded_file.name)
                
                if uploaded_file.state.name == "FAILED":
                    logger.error(f"❌ Image {i+1} processing failed")
                    continue
                
                uploaded_files.append(uploaded_file)
                logger.info(f"✅ Image {i+1} uploaded: {uploaded_file.uri}")
            
            if not uploaded_files:
                logger.error("No images were successfully uploaded")
                return None
            
            # Create intelligent prompt
            prompt = self._create_analysis_prompt(num_images, caption)
            
            # Create Gemini model
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Prepare content (prompt + all uploaded images)
            content_parts = [prompt] + uploaded_files
            
            # Generate analysis
            logger.info("🤖 Sending to Gemini for analysis...")
            response = await asyncio.to_thread(
                model.generate_content,
                content_parts
            )
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            analysis_result = json.loads(response_text)
            analysis_result["num_images"] = num_images
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            analysis_result["processing_time"] = processing_time
            
            logger.info(f"✅ Analysis complete ({processing_time:.2f}s)")
            logger.info(f"📊 Type: {analysis_result.get('image_type')}, Confidence: {analysis_result.get('confidence')}")
            logger.info(f"📝 Description: {analysis_result.get('description', '')[:100]}...")
            
            return analysis_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error analyzing images: {e}", exc_info=True)
            return None
        
        finally:
            # Clean up uploaded files from Gemini File API
            for uploaded_file in uploaded_files:
                try:
                    await asyncio.to_thread(genai.delete_file, uploaded_file.name)
                    logger.info(f"🗑️ Deleted uploaded file from Gemini: {uploaded_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete uploaded file: {e}")
    
    async def generate_product_search_description(
        self, 
        image_paths: List[str], 
        caption: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate detailed product description for image-based search.
        This is different from the general analysis - focused on product matching.
        
        Args:
            image_paths: List of paths to image files
            caption: Optional caption/text from user
            
        Returns:
            Dictionary with product-focused analysis for search
        """
        try:
            logger.info(f"🖼️ Generating product search description for {len(image_paths)} image(s)")
            
            # Upload images to Gemini
            uploaded_files = []
            for image_path in image_paths:
                uploaded_file = await asyncio.to_thread(
                    genai.upload_file,
                    path=image_path,
                    display_name=f"product_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                uploaded_files.append(uploaded_file)
            
            # Wait for processing
            max_wait = 30  # seconds
            wait_time = 0
            for uploaded_file in uploaded_files:
                while uploaded_file.state.name == "PROCESSING" and wait_time < max_wait:
                    await asyncio.sleep(1)
                    wait_time += 1
                    uploaded_file = await asyncio.to_thread(genai.get_file, uploaded_file.name)
                
                if uploaded_file.state.name == "FAILED":
                    logger.error("Image upload failed")
                    return None
            
            # Create product-focused prompt
            prompt = """You are a product search expert. Analyze this image to understand what product the customer is looking for.

**Your Task:**
Generate a detailed description that would help find similar products in a toy store database.

**Focus on:**
1. **Product Type**: What kind of product? (electric jeep, bike, scooter, doll, puzzle, etc.)
2. **Design & Style**: Describe the overall design and appearance
3. **Colors**: List ALL visible colors (primary and secondary)
4. **Key Features**: Identify visible features (lights, wheels, seats, steering, buttons, etc.)
5. **Size Category**: Estimate size (small, medium, large, extra-large)
6. **Age Suitability**: Estimate appropriate age range
7. **Material & Build**: Describe visible materials (plastic, metal, rubber wheels, etc.)

**Response Format:**
Return ONLY valid JSON (no markdown, no extra text):
{
    "product_type": "specific product category",
    "detailed_description": "comprehensive description for embedding (3-5 sentences)",
    "colors": ["color1", "color2", "color3"],
    "primary_color": "main color",
    "key_features": ["feature1", "feature2", "feature3", "feature4"],
    "age_range": "X-Y years",
    "size_category": "small|medium|large|extra-large",
    "style_keywords": ["keyword1", "keyword2", "keyword3"],
    "confidence": "high|medium|low"
}

**Important:**
- Be specific and detailed in the description
- Include all visible colors
- Focus on searchable features
- Use keywords that customers would use
- Output ONLY the JSON, nothing else

Now analyze the product image:"""

            if caption:
                prompt += f"\n\n**User's Caption:** {caption}"

            # Generate description
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = await asyncio.to_thread(
                model.generate_content,
                [prompt] + uploaded_files
            )
            
            # Parse response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            
            # Clean up uploaded files
            for uploaded_file in uploaded_files:
                await asyncio.to_thread(genai.delete_file, uploaded_file.name)
            
            logger.info(f"✅ Generated product search description: {result.get('product_type')}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating product search description: {e}", exc_info=True)
            return None
        
        finally:
            # Clean up uploaded files from Gemini File API
            for uploaded_file in uploaded_files:
                try:
                    await asyncio.to_thread(genai.delete_file, uploaded_file.name)
                    logger.info(f"🗑️ Deleted uploaded file from Gemini: {uploaded_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete uploaded file: {e}")
    
    def _create_analysis_prompt(self, num_images: int, caption: Optional[str]) -> str:
        """
        Create intelligent prompt for image analysis.
        
        Args:
            num_images: Number of images being analyzed
            caption: Optional user caption
            
        Returns:
            Formatted prompt string
        """
        if num_images == 1:
            prompt = """You are an intelligent assistant for Gurtoy toy store.

**Your Task:**
Analyze this image carefully and respond appropriately based on what you see.

**Possible Scenarios:**

1. **TOY/PRODUCT IMAGE:**
   - Identify: toy type, brand, colors, age suitability, features
   - Response: Describe the toy and offer to help find similar products

2. **PRODUCT SCREENSHOT (from other websites/apps):**
   - Identify: product details, price (if visible), features
   - Response: Acknowledge and offer to find similar items in store

3. **REFERENCE IMAGE (what user wants):**
   - Identify: key features, colors, style, type
   - Response: Understand requirements and offer to search

4. **CHILD'S PHOTO:**
   - Identify: approximate age (if visible)
   - Response: Offer age-appropriate toy suggestions

5. **DAMAGED/DEFECTIVE TOY:**
   - Identify: product issue or damage
   - Response: Offer support and replacement options

6. **UNRELATED IMAGE (selfie, food, scenery, etc.):**
   - Identify: not toy-related
   - Response: Politely acknowledge and redirect to toy shopping

7. **UNCLEAR/BLURRY IMAGE:**
   - Identify: image quality issues
   - Response: Ask for clarification or better image

**Response Format:**
Return ONLY valid JSON (no markdown, no extra text):
{
    "image_type": "toy|product_screenshot|reference|child_photo|damaged|unrelated|unclear",
    "description": "Brief description of what you see (1-2 sentences)",
    "analysis": "Detailed analysis for AI conversation context (what the user likely wants)",
    "key_features": ["feature1", "feature2", "feature3"],
    "suggested_age": "age range if applicable or null",
    "confidence": "high|medium|low"
}

**Important:**
- Be accurate and describe what you actually see
- Don't make assumptions beyond what's visible
- Always relate back to toy shopping context
- Output ONLY the JSON, nothing else"""
        
        else:
            prompt = f"""You are an intelligent assistant for Gurtoy toy store.

**Your Task:**
Analyze these {num_images} images carefully. The user sent multiple images together.

**Possible Scenarios:**

1. **MULTIPLE TOYS (Comparison):**
   - User wants to compare different toys
   - Identify each toy and help them decide

2. **SAME TOY (Different Angles):**
   - User showing one toy from multiple angles
   - Provide comprehensive understanding

3. **PRODUCT COLLECTION:**
   - User showing their collection or wishlist
   - Understand their preferences

4. **BEFORE/AFTER (Damaged Product):**
   - User showing product condition
   - Offer support

5. **MIXED IMAGES:**
   - Combination of different types
   - Analyze the overall intent

**Response Format:**
Return ONLY valid JSON (no markdown, no extra text):
{{
    "image_type": "comparison|same_product|collection|damaged|mixed",
    "description": "Brief description of all images (2-3 sentences)",
    "analysis": "Detailed analysis combining all images for conversation context",
    "key_features": ["feature1", "feature2", "feature3"],
    "suggested_age": "age range if applicable or null",
    "confidence": "high|medium|low"
}}

**Important:**
- Analyze ALL {num_images} images together
- Find connections between images
- Understand the user's overall intent
- Output ONLY the JSON, nothing else"""
        
        if caption:
            prompt += f"\n\n**User's Caption/Message:** {caption}"
        
        prompt += "\n\nNow analyze the image(s) and respond with JSON:"
        
        return prompt
    
    async def cleanup_image_file(self, image_path: str) -> bool:
        """
        Delete temporary image file.
        
        Args:
            image_path: Path to image file
            
        Returns:
            True if deleted successfully
        """
        try:
            if os.path.exists(image_path):
                await asyncio.to_thread(os.remove, image_path)
                logger.info(f"🗑️ Cleaned up image file: {image_path}")
                return True
            else:
                logger.warning(f"Image file not found for cleanup: {image_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error cleaning up image file: {e}")
            return False
    
    async def cleanup_multiple_images(self, image_paths: List[str]) -> int:
        """
        Delete multiple temporary image files.
        
        Args:
            image_paths: List of paths to image files
            
        Returns:
            Number of files successfully deleted
        """
        deleted_count = 0
        for image_path in image_paths:
            if await self.cleanup_image_file(image_path):
                deleted_count += 1
        return deleted_count


# Global instance
_image_handler_instance: Optional[ImageHandler] = None


def initialize_image_handler(telegram_bot_token: str, gemini_api_key: str) -> ImageHandler:
    """
    Initialize the global ImageHandler instance.
    
    Args:
        telegram_bot_token: Telegram bot token
        gemini_api_key: Gemini API key
        
    Returns:
        ImageHandler instance
    """
    global _image_handler_instance
    _image_handler_instance = ImageHandler(telegram_bot_token, gemini_api_key)
    return _image_handler_instance


def get_image_handler() -> Optional[ImageHandler]:
    """
    Get the global ImageHandler instance.
    
    Returns:
        ImageHandler instance or None if not initialized
    """
    return _image_handler_instance