"""
Image Handler Module for Fashion Mart Telegram Bot - Phase 7
Handles fashion image download, analysis with Gemini, and fashion-specific recognition.
"""
import os
import asyncio
import logging
import json
import base64
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

import httpx
import aiofiles
import google.generativeai as genai

# Configure logging
logger = logging.getLogger(__name__)

class ImageHandler:
    """Handles fashion image processing with Gemini 2.5 Flash for Fashion Mart."""
    
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
        Analyze one or more fashion images using Gemini 2.5 Flash with base64 encoding.
        
        Args:
            image_paths: List of paths to image files
            caption: Optional caption/text from user
            
        Returns:
            Dictionary with fashion analysis results:
            {
                "image_type": "fashion_item|style_reference|outfit_inspiration|size_reference|color_coordination|unrelated|unclear",
                "description": "Brief description of fashion item",
                "analysis": "Detailed fashion analysis for conversation",
                "fashion_category": "kurta|cardigan|top|dress|accessory",
                "style_type": "casual|formal|ethnic|western|traditional",
                "color_analysis": ["primary_color", "secondary_colors"],
                "size_estimation": "S|M|L|XL",
                "occasion_suitability": ["office", "party", "casual", "wedding"],
                "styling_suggestions": ["suggestion1", "suggestion2"],
                "confidence": "high|medium|low",
                "num_images": 1
            }
        """
        start_time = datetime.now()
        
        try:
            num_images = len(image_paths)
            logger.info(f"🔍 Analyzing {num_images} image(s)...")
            
            # Prepare image content in base64 format
            image_content = []
            mime_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp',
                '.heic': 'image/heic',
                '.heif': 'image/heif'
            }
            
            for i, image_path in enumerate(image_paths):
                file_size_kb = os.path.getsize(image_path) / 1024
                logger.info(f"📤 Processing image {i+1}/{num_images}: {file_size_kb:.2f} KB")
                
                # Read and encode image as base64
                async with aiofiles.open(image_path, 'rb') as f:
                    image_data = await f.read()
                
                image_base64 = base64.standard_b64encode(image_data).decode('utf-8')
                
                # Determine MIME type
                file_ext = Path(image_path).suffix.lower()
                mime_type = mime_type_map.get(file_ext, 'image/jpeg')
                
                image_content.append({
                    "mime_type": mime_type,
                    "data": image_base64
                })
                logger.info(f"✅ Image {i+1} encoded: {file_ext} -> {mime_type}")
            
            # Create intelligent prompt
            prompt = self._create_analysis_prompt(num_images, caption)
            
            # Create Gemini model
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Prepare content (prompt + all base64-encoded images)
            content_parts = [prompt] + image_content
            
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
            if 'response_text' in locals():
                logger.error(f"Response text: {response_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error analyzing images: {e}", exc_info=True)
            return None
    
    async def generate_product_search_description(
        self, 
        image_paths: List[str], 
        caption: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate detailed product description for image-based search with base64 encoding.
        This is different from the general analysis - focused on product matching.
        
        Args:
            image_paths: List of paths to image files
            caption: Optional caption/text from user
            
        Returns:
            Dictionary with product-focused analysis for search
        """
        try:
            logger.info(f"🖼️ Generating product search description for {len(image_paths)} image(s)")
            
            # Prepare images in base64 format
            mime_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp',
                '.heic': 'image/heic',
                '.heif': 'image/heif'
            }
            
            image_content = []
            for image_path in image_paths:
                async with aiofiles.open(image_path, 'rb') as f:
                    image_data = await f.read()
                
                image_base64 = base64.standard_b64encode(image_data).decode('utf-8')
                file_ext = Path(image_path).suffix.lower()
                mime_type = mime_type_map.get(file_ext, 'image/jpeg')
                
                image_content.append({
                    "mime_type": mime_type,
                    "data": image_base64
                })
            
            # Create product-focused prompt
            prompt = """You are a product search expert. Analyze this image to understand what EXACT product the customer is looking for.

**Your Task:**
Generate a DETAILED description that would help find the EXACT same product in a fashion store database.

**Focus on SPECIFIC details:**
1. **Exact Product Type**: Be very specific (e.g., "women's casual cotton kurta", not just "dress")
2. **Specific Brand/Model**: If visible, include brand and model information
3. **Exact Colors**: List specific color names and shades
4. **Unique Features**: Identify distinctive features that make this product unique
5. **Exact Specifications**: Size, fabric, sleeve type, style, etc.
6. **Visual Characteristics**: Any unique visual elements

**Response Format:**
Return ONLY valid JSON (no markdown, no extra text):
{
    "product_type": "VERY SPECIFIC product category with brand/model if visible",
    "detailed_description": "COMPREHENSIVE description with ALL specific details (5-7 sentences)",
    "colors": ["exact_color1", "exact_color2"],
    "primary_color": "exact main color",
    "key_features": ["specific_feature1", "specific_feature2", "specific_feature3"],
    "brand_model": "brand and model if visible",
    "unique_characteristics": ["unique_element1", "unique_element2"],
    "style": "casual|formal|ethnic|western|traditional",
    "size_estimate": "XS|S|M|L|XL|XXL",
    "confidence": "high|medium|low"
}

**CRITICAL:** Be as specific as possible. Include brand names, exact colors, and unique features that would distinguish this exact product from similar ones.

Now analyze the product image:"""

            if caption:
                prompt += f"\n\n**User's Caption:** {caption}"

            # Generate description
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = await asyncio.to_thread(
                model.generate_content,
                [prompt] + image_content
            )
            
            # Parse response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            
            logger.info(f"✅ Generated product search description: {result.get('product_type')}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating product search description: {e}", exc_info=True)
            return None
    
    def _create_analysis_prompt(self, num_images: int, caption: Optional[str]) -> str:
        """
        Create intelligent prompt for fashion image analysis.
        
        Args:
            num_images: Number of images being analyzed
            caption: Optional user caption
            
        Returns:
            Formatted prompt string for fashion analysis
        """
        if num_images == 1:
            prompt = """You are an intelligent fashion consultant for Fashion Mart women's fashion store.

**Your Task:**
Analyze this fashion image carefully and provide comprehensive fashion analysis.

**Possible Scenarios:**

1. **FASHION ITEM (Clothing):**
   - Identify: garment type, style, colors, fabric, fit, occasion suitability
   - Response: Describe the fashion item and offer styling suggestions

2. **STYLE REFERENCE (Inspiration):**
   - Identify: outfit style, color coordination, fashion trends
   - Response: Understand style preferences and suggest similar items

3. **OUTFIT INSPIRATION (Complete Look):**
   - Identify: complete outfit, styling, accessories, occasion
   - Response: Break down the look and suggest individual pieces

4. **SIZE REFERENCE (Fit Check):**
   - Identify: garment fit, size estimation, styling advice
   - Response: Provide size recommendations and fit guidance

5. **COLOR COORDINATION (Color Matching):**
   - Identify: color palette, coordination, complementary colors
   - Response: Suggest color combinations and styling tips

6. **UNRELATED IMAGE (Non-fashion):**
   - Identify: not fashion-related
   - Response: Politely acknowledge and redirect to fashion shopping

7. **UNCLEAR/BLURRY IMAGE:**
   - Identify: image quality issues
   - Response: Ask for clarification or better image

**Response Format:**
Return ONLY valid JSON (no markdown, no extra text):
{
    "image_type": "fashion_item|style_reference|outfit_inspiration|size_reference|color_coordination|unrelated|unclear",
    "description": "Brief description of fashion item/style (1-2 sentences)",
    "analysis": "Detailed fashion analysis for conversation context",
    "fashion_category": "kurta|cardigan|top|dress|accessory",
    "style_type": "casual|formal|ethnic|western|traditional",
    "color_analysis": ["primary_color", "secondary_colors"],
    "size_estimation": "S|M|L|XL",
    "occasion_suitability": ["office", "party", "casual", "wedding"],
    "styling_suggestions": ["suggestion1", "suggestion2"],
    "confidence": "high|medium|low"
}

**Important:**
- Focus on fashion-specific details (style, color, occasion, fit)
- Provide practical styling advice
- Consider Indian women's fashion preferences
- Output ONLY the JSON, nothing else"""
        
        else:
            prompt = f"""You are an intelligent fashion consultant for Fashion Mart women's fashion store.

**Your Task:**
Analyze these {num_images} fashion images carefully. The user sent multiple images together.

**Possible Scenarios:**

1. **MULTIPLE FASHION ITEMS (Comparison):**
   - User wants to compare different fashion items
   - Identify each item and help them decide

2. **SAME ITEM (Different Angles):**
   - User showing one fashion item from multiple angles
   - Provide comprehensive understanding

3. **OUTFIT COLLECTION:**
   - User showing their outfit collection or inspiration
   - Understand their style preferences

4. **STYLE VARIATIONS:**
   - User showing different styling options
   - Provide styling advice and recommendations

5. **MIXED FASHION IMAGES:**
   - Combination of different fashion types
   - Analyze the overall style intent

**Response Format:**
Return ONLY valid JSON (no markdown, no extra text):
{{
    "image_type": "comparison|same_item|collection|style_variations|mixed",
    "description": "Brief description of all fashion images (2-3 sentences)",
    "analysis": "Detailed fashion analysis combining all images for conversation context",
    "fashion_category": "kurta|cardigan|top|dress|accessory",
    "style_type": "casual|formal|ethnic|western|traditional",
    "color_analysis": ["primary_color", "secondary_colors"],
    "size_estimation": "S|M|L|XL",
    "occasion_suitability": ["office", "party", "casual", "wedding"],
    "styling_suggestions": ["suggestion1", "suggestion2"],
    "confidence": "high|medium|low"
}}

**Important:**
- Focus on fashion-specific details across all images
- Provide comprehensive styling advice
- Consider Indian women's fashion preferences
- Output ONLY the JSON, nothing else"""
        
        if caption:
            prompt += f"\n\n**User's Caption/Message:** {caption}"
        
        prompt += "\n\nNow analyze the image(s) and respond with JSON:"
        
        return prompt
    
    # Phase 7: Fashion-specific image analysis methods
    
    async def analyze_fashion_item(self, image_paths: List[str], caption: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze fashion items in images for detailed fashion recognition.
        
        Args:
            image_paths: List of paths to image files
            caption: Optional caption/text from user
            
        Returns:
            Dictionary with detailed fashion analysis
        """
        try:
            logger.info(f"👗 Analyzing fashion items in {len(image_paths)} image(s)")
            
            # Use the main analysis method
            analysis = await self.analyze_images(image_paths, caption)
            
            if analysis and analysis.get("image_type") in ["fashion_item", "style_reference", "outfit_inspiration"]:
                # Enhance with additional fashion-specific analysis
                enhanced_analysis = await self._enhance_fashion_analysis(analysis, image_paths)
                return enhanced_analysis
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in fashion item analysis: {e}")
            return None

    async def analyze_style_and_color(self, image_paths: List[str], caption: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze style and color coordination in fashion images with base64 encoding.
        
        Args:
            image_paths: List of paths to image files
            caption: Optional caption/text from user
            
        Returns:
            Dictionary with style and color analysis
        """
        try:
            logger.info(f"🎨 Analyzing style and color in {len(image_paths)} image(s)")
            
            # Prepare images in base64 format
            mime_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp',
                '.heic': 'image/heic',
                '.heif': 'image/heif'
            }
            
            image_content = []
            for image_path in image_paths:
                async with aiofiles.open(image_path, 'rb') as f:
                    image_data = await f.read()
                
                image_base64 = base64.standard_b64encode(image_data).decode('utf-8')
                file_ext = Path(image_path).suffix.lower()
                mime_type = mime_type_map.get(file_ext, 'image/jpeg')
                
                image_content.append({
                    "mime_type": mime_type,
                    "data": image_base64
                })
            
            # Create style and color analysis prompt
            prompt = """You are a fashion style and color expert for Fashion Mart.

**Your Task:**
Analyze the style and color coordination in these fashion images.

**Focus Areas:**
1. **Style Analysis**: Identify the overall style (casual, formal, ethnic, western, traditional)
2. **Color Analysis**: Identify primary and secondary colors, color harmony
3. **Color Coordination**: Suggest complementary colors and color combinations
4. **Style Recommendations**: Provide styling tips and suggestions
5. **Occasion Suitability**: Determine appropriate occasions for the style

**Response Format:**
Return ONLY valid JSON:
{
    "style_type": "casual|formal|ethnic|western|traditional",
    "primary_colors": ["color1", "color2"],
    "secondary_colors": ["color1", "color2"],
    "color_harmony": "monochromatic|complementary|analogous|triadic",
    "color_coordination_suggestions": ["suggestion1", "suggestion2"],
    "styling_tips": ["tip1", "tip2"],
    "occasion_suitability": ["office", "party", "casual", "wedding"],
    "accessory_suggestions": ["accessory1", "accessory2"],
    "confidence": "high|medium|low"
}

**Important:**
- Focus on Indian women's fashion preferences
- Provide practical styling advice
- Consider color theory and coordination
- Output ONLY the JSON, nothing else"""

            if caption:
                prompt += f"\n\n**User's Caption/Message:** {caption}"
            
            prompt += "\n\nNow analyze the style and color coordination:"
            
            # Create Gemini model and analyze
            model = genai.GenerativeModel('gemini-2.5-flash')
            content_parts = [prompt] + image_content
            
            response = await asyncio.to_thread(model.generate_content, content_parts)
            
            # Parse response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            analysis = json.loads(response_text)
            
            logger.info(f"✅ Style and color analysis complete")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in style and color analysis: {e}")
            return None

    async def estimate_size_from_image(self, image_paths: List[str], caption: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Estimate size from fashion images for size recommendations using base64 encoding.
        
        Args:
            image_paths: List of paths to image files
            caption: Optional caption/text from user
            
        Returns:
            Dictionary with size estimation analysis
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"📏 Estimating size from {len(image_paths)} image(s)")
            
            # Prepare image content in base64 format
            image_content = []
            mime_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp',
                '.heic': 'image/heic',
                '.heif': 'image/heif'
            }
            
            for i, image_path in enumerate(image_paths):
                file_size_kb = os.path.getsize(image_path) / 1024
                logger.info(f"📤 Processing image {i+1}/{len(image_paths)}: {file_size_kb:.2f} KB")
                
                # Read and encode image as base64
                async with aiofiles.open(image_path, 'rb') as f:
                    image_data = await f.read()
                
                image_base64 = base64.standard_b64encode(image_data).decode('utf-8')
                
                # Determine MIME type
                file_ext = Path(image_path).suffix.lower()
                mime_type = mime_type_map.get(file_ext, 'image/jpeg')
                
                image_content.append({
                    "mime_type": mime_type,
                    "data": image_base64
                })
                logger.info(f"✅ Image {i+1} encoded: {file_ext} -> {mime_type}")
            
            # Create size estimation prompt
            prompt = """You are a fashion size expert for Fashion Mart.

**Your Task:**
Analyze the fashion images to estimate appropriate sizes for Indian women.

**Size Estimation Focus:**
1. **Fit Analysis**: Analyze how the garment fits on the person
2. **Size Estimation**: Estimate appropriate size (S, M, L, XL)
3. **Fit Preferences**: Determine if loose, fitted, or comfortable fit
4. **Size Recommendations**: Provide size guidance and tips
5. **Fit Concerns**: Identify any potential fit issues

**Response Format:**
Return ONLY valid JSON:
{
    "estimated_size": "S|M|L|XL",
    "fit_analysis": "loose|fitted|comfortable|tight",
    "size_recommendation": "recommended size with reasoning",
    "fit_preferences": ["preference1", "preference2"],
    "size_concerns": ["concern1", "concern2"],
    "size_guide_needed": true|false,
    "confidence": "high|medium|low"
}

**Important:**
- Consider Indian women's body types and preferences
- Provide practical size guidance
- Be conservative in size recommendations
- Output ONLY the JSON, nothing else"""

            if caption:
                prompt += f"\n\n**User's Caption/Message:** {caption}"
            
            prompt += "\n\nNow estimate the appropriate size:"
            
            # Create Gemini model and analyze
            model = genai.GenerativeModel('gemini-2.5-flash')
            content_parts = [prompt] + image_content
            
            logger.info("🤖 Sending to Gemini for size estimation...")
            response = await asyncio.to_thread(model.generate_content, content_parts)
            
            # Parse response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            analysis = json.loads(response_text)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            analysis["processing_time"] = processing_time
            
            logger.info(f"✅ Size estimation complete ({processing_time:.2f}s): {analysis.get('estimated_size', 'Unknown')}")
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            if 'response_text' in locals():
                logger.error(f"Response text: {response_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error in size estimation: {e}", exc_info=True)
            return None

    async def _enhance_fashion_analysis(self, base_analysis: Dict[str, Any], image_paths: List[str]) -> Dict[str, Any]:
        """
        Enhance base fashion analysis with additional details.
        
        Args:
            base_analysis: Base analysis result
            image_paths: List of paths to image files
            
        Returns:
            Enhanced analysis dictionary
        """
        try:
            # Add fashion-specific enhancements
            enhanced = base_analysis.copy()
            
            # Add fashion-specific fields if not present
            if "fashion_category" not in enhanced:
                enhanced["fashion_category"] = "unknown"
            
            if "style_type" not in enhanced:
                enhanced["style_type"] = "casual"
            
            if "color_analysis" not in enhanced:
                enhanced["color_analysis"] = []
            
            if "size_estimation" not in enhanced:
                enhanced["size_estimation"] = "M"
            
            if "occasion_suitability" not in enhanced:
                enhanced["occasion_suitability"] = ["casual"]
            
            if "styling_suggestions" not in enhanced:
                enhanced["styling_suggestions"] = []
            
            # Add processing metadata
            enhanced["analysis_type"] = "fashion_enhanced"
            enhanced["processing_timestamp"] = datetime.now().isoformat()
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Error enhancing fashion analysis: {e}")
            return base_analysis

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