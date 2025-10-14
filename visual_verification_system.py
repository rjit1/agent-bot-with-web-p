"""
Visual Verification System for Gurtoy Telegram Bot
Handles intelligent image comparison and product matching with production-level intelligence.
"""
import os
import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

import google.generativeai as genai
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)

class MatchType(Enum):
    """Types of product matches."""
    EXACT_MATCH = "exact_match"
    COLOR_VARIANT = "color_variant"
    SIMILAR_PRODUCT = "similar_product"
    RELATED_PRODUCT = "related_product"
    NO_MATCH = "no_match"

class ConfidenceLevel(Enum):
    """Confidence levels for matches."""
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"

@dataclass
class VisualMatchResult:
    """Result of visual verification between user image and database product."""
    product_id: str
    product_title: str
    match_type: MatchType
    confidence: ConfidenceLevel
    confidence_score: float
    visual_similarity: str
    product_type_match: bool
    design_match: bool
    color_match: bool
    color_difference: Optional[str]
    feature_match: bool
    feature_differences: List[str]
    recommendation: str
    explanation: str
    customer_message: str
    similarity_score: float

@dataclass
class ProductMatchAnalysis:
    """Complete analysis of product matching."""
    user_image_path: str
    user_image_analysis: Dict[str, Any]
    matched_products: List[VisualMatchResult]
    best_match: Optional[VisualMatchResult]
    overall_recommendation: str
    processing_time: float

class VisualVerificationSystem:
    """Production-level visual verification system for intelligent product matching."""
    
    def __init__(self, gemini_api_key: str):
        """Initialize the visual verification system."""
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Configuration
        self.max_products_to_compare = 5  # Compare top 5 products visually
        self.min_confidence_threshold = 0.6  # Minimum confidence for recommendations
        
        logger.info("🔍 VisualVerificationSystem initialized")
    
    async def analyze_user_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Analyze user's image to extract product information.
        
        Args:
            image_path: Path to user's image
            
        Returns:
            Dictionary with product analysis
        """
        try:
            logger.info(f"🔍 Analyzing user image: {image_path}")
            
            # Upload image to Gemini
            image_file = await asyncio.to_thread(
                genai.upload_file,
                path=image_path,
                display_name="user_query_image"
            )
            
            # Wait for processing
            while image_file.state.name == "PROCESSING":
                await asyncio.sleep(1)
                image_file = await asyncio.to_thread(genai.get_file, image_file.name)
            
            # Create analysis prompt
            prompt = """You are a product analysis expert. Analyze this image to understand what product the customer is looking for.

**Your Task:**
Generate a detailed analysis that will help find the exact or similar product in a toy store database.

**Focus on:**
1. **Product Type**: What kind of product? (electric jeep, bike, scooter, doll, puzzle, etc.)
2. **Design & Style**: Describe the overall design and appearance
3. **Colors**: List ALL visible colors (primary and secondary)
4. **Key Features**: Identify visible features (lights, wheels, seats, steering, buttons, etc.)
5. **Size Category**: Estimate size (small, medium, large, extra-large)
6. **Age Suitability**: Estimate appropriate age range
7. **Material & Build**: Describe visible materials (plastic, metal, rubber wheels, etc.)
8. **Brand/Model**: If visible, identify brand or model information

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
    "brand_model": "brand or model if visible",
    "confidence": "high|medium|low",
    "image_context": "brief context about the image (indoor/outdoor, angle, etc.)"
}

**Important:**
- Be specific and detailed in the description
- Include all visible colors
- Focus on searchable features
- Use keywords that customers would use
- Output ONLY the JSON, nothing else

Now analyze the product image:"""

            # Generate analysis
            response = await asyncio.to_thread(
                self.model.generate_content,
                [prompt, image_file]
            )
            
            # Parse response
            response_text = response.text.strip()
            logger.info(f"📝 Raw analysis response: {response_text[:200]}...")
            
            # Extract JSON from response
            try:
                # Find JSON in response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != 0:
                    json_str = response_text[start_idx:end_idx]
                    analysis = json.loads(json_str)
                    
                    logger.info(f"✅ User image analysis completed: {analysis.get('product_type')}")
                    return analysis
                else:
                    logger.error("No JSON found in analysis response")
                    return None
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse analysis JSON: {e}")
                logger.error(f"Response text: {response_text}")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing user image: {e}", exc_info=True)
            return None
    
    async def compare_all_images_batch(
        self,
        user_image_path: str,
        products: List[Dict[str, Any]],
        user_analysis: Dict[str, Any]
    ) -> List[VisualMatchResult]:
        """
        Compare user image with all database product images in a single batch call.
        This is more efficient and accurate than individual comparisons.
        
        Args:
            user_image_path: Path to user's image
            products: List of products from database search
            user_analysis: User image analysis
            
        Returns:
            List of VisualMatchResult with detailed comparison
        """
        try:
            logger.info(f"🔍 Starting batch image comparison for {len(products)} products")
            
            # Download all product images first
            product_images = []
            for product in products[:self.max_products_to_compare]:  # Limit to top products
                try:
                    images = product.get('images', [])
                    if not images:
                        logger.warning(f"No images found for product: {product.get('title', 'Unknown')}")
                        continue
                    
                    image_url = images[0] if isinstance(images, list) else images
                    product_image_path = await self._download_product_image(image_url, product.get('product_id', 'unknown'))
                    
                    if product_image_path:
                        product_images.append({
                            'product': product,
                            'image_path': product_image_path
                        })
                        logger.info(f"📥 Downloaded image for: {product.get('title', 'Unknown')}")
                    else:
                        logger.warning(f"Failed to download image for: {product.get('title', 'Unknown')}")
                        
                except Exception as e:
                    logger.error(f"Error downloading image for product {product.get('product_id', 'unknown')}: {e}")
                    continue
            
            if not product_images:
                logger.error("No product images downloaded for comparison")
                return []
            
            # Upload user image to Gemini
            user_file = await asyncio.to_thread(
                genai.upload_file,
                path=user_image_path,
                display_name="user_query_image"
            )
            
            # Wait for user image processing
            while user_file.state.name == "PROCESSING":
                await asyncio.sleep(1)
                user_file = await asyncio.to_thread(genai.get_file, user_file.name)
            
            # Upload all product images to Gemini
            product_files = []
            for i, product_image in enumerate(product_images):
                try:
                    product_file = await asyncio.to_thread(
                        genai.upload_file,
                        path=product_image['image_path'],
                        display_name=f"product_image_{i}"
                    )
                    product_files.append({
                        'file': product_file,
                        'product': product_image['product']
                    })
                except Exception as e:
                    logger.error(f"Error uploading product image {i}: {e}")
                    continue
            
            # Wait for all product images to process
            for product_file_data in product_files:
                while product_file_data['file'].state.name == "PROCESSING":
                    await asyncio.sleep(1)
                    product_file_data['file'] = await asyncio.to_thread(genai.get_file, product_file_data['file'].name)
            
            # Create batch comparison prompt with product information
            product_info_text = ""
            for i, product_image in enumerate(product_images):
                product = product_image['product']
                product_info_text += f"""
**Product {i+1}:**
- Product ID: {product.get('product_id', 'unknown')}
- Title: {product.get('title', 'Unknown Product')}
- Price: ₹{product.get('price', 0):,}
- Colors: {', '.join(product.get('colors', [])[:3]) if isinstance(product.get('colors', []), list) else 'Not specified'}
- Age Range: {product.get('age_range', 'Not specified')}
- Description: {product.get('description', 'No description')[:100]}...
"""
            
            prompt = f"""You are a product matching expert. I will show you the customer's image and multiple product images from our database. 

**Customer's Image Analysis:**
- Product Type: {user_analysis.get('product_type', 'Unknown')}
- Colors: {', '.join(user_analysis.get('colors', [])[:3]) if isinstance(user_analysis.get('colors', []), list) else 'Not specified'}
- Key Features: {', '.join(user_analysis.get('key_features', [])[:3]) if isinstance(user_analysis.get('key_features', []), list) else 'Not specified'}

**Database Products to Compare:**
{product_info_text}

**Your Task:**
Compare the customer's image with each product image and determine:
1. Which product is the EXACT MATCH (same product, same color)
2. Which products are COLOR VARIANTS (same product, different color)
3. Which products are SIMILAR (similar type/style but different model)
4. Which products are RELATED (related category but different product)
5. Which products are NOT MATCHES

**For each product, provide:**
- Match type (exact_match, color_variant, similar_product, related_product, no_match)
- Confidence level (very_high, high, medium, low, very_low)
- Confidence score (0.0-1.0)
- Visual similarity level
- Whether product type, design, color, and features match
- Color differences (if any)
- Feature differences (if any)
- Recommendation
- Explanation
- Customer-friendly message

**Response Format:**
Return ONLY valid JSON array (no markdown, no extra text):
[
    {{
        "product_id": "USE_THE_EXACT_PRODUCT_ID_FROM_ABOVE",
        "product_title": "USE_THE_EXACT_TITLE_FROM_ABOVE",
        "match_type": "exact_match|color_variant|similar_product|related_product|no_match",
        "confidence": "very_high|high|medium|low|very_low",
        "confidence_score": 0.0-1.0,
        "visual_similarity": "very_high|high|medium|low|very_low",
        "product_type_match": true/false,
        "design_match": true/false,
        "color_match": true/false,
        "color_difference": "description of color differences or null",
        "feature_match": true/false,
        "feature_differences": ["difference1", "difference2"] or [],
        "recommendation": "exact_match|recommend_with_color_note|recommend_as_alternative|not_recommended",
        "explanation": "detailed explanation of the match (2-3 sentences)",
        "customer_message": "friendly message to send to customer explaining the match"
    }},
    // ... more products
]

**IMPORTANT:** 
- Use the EXACT product_id and product_title from the product information above
- Do NOT create new product IDs or titles
- Match the product_id to the correct product image

**Important:**
- Analyze ALL product images provided
- Be thorough in your comparisons
- Provide accurate confidence scores
- Generate helpful customer messages
- Output ONLY the JSON array, nothing else

Now analyze all the images:"""

            # Prepare all images for the batch call
            all_images = [user_file] + [pf['file'] for pf in product_files]
            
            # Generate batch comparison
            response = await asyncio.to_thread(
                self.model.generate_content,
                [prompt] + all_images
            )
            
            # Parse response
            response_text = response.text.strip()
            logger.info(f"📝 Raw batch comparison response: {response_text[:200]}...")
            
            # Extract JSON from response
            try:
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']') + 1
                
                if start_idx != -1 and end_idx != 0:
                    json_str = response_text[start_idx:end_idx]
                    comparisons = json.loads(json_str)
                    
                    # Convert to VisualMatchResult objects
                    results = []
                    for i, comparison in enumerate(comparisons):
                        if i < len(product_files):
                            product = product_files[i]['product']
                            similarity_score = product.get('similarity', 0.0)
                            
                            result = VisualMatchResult(
                                product_id=comparison.get('product_id', product.get('product_id', '')),
                                product_title=comparison.get('product_title', product.get('title', '')),
                                match_type=MatchType(comparison.get('match_type', 'no_match')),
                                confidence=ConfidenceLevel(comparison.get('confidence', 'very_low')),
                                confidence_score=comparison.get('confidence_score', 0.0),
                                visual_similarity=comparison.get('visual_similarity', 'very_low'),
                                product_type_match=comparison.get('product_type_match', False),
                                design_match=comparison.get('design_match', False),
                                color_match=comparison.get('color_match', False),
                                color_difference=comparison.get('color_difference'),
                                feature_match=comparison.get('feature_match', False),
                                feature_differences=comparison.get('feature_differences', []),
                                recommendation=comparison.get('recommendation', 'not_recommended'),
                                explanation=comparison.get('explanation', ''),
                                customer_message=comparison.get('customer_message', ''),
                                similarity_score=similarity_score
                            )
                            results.append(result)
                    
                    logger.info(f"✅ Batch comparison completed: {len(results)} results")
                    
                    # Cleanup downloaded images
                    for product_image in product_images:
                        await self._cleanup_image(product_image['image_path'])
                    
                    return results
                else:
                    logger.error("No JSON array found in batch comparison response")
                    return []
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse batch comparison JSON: {e}")
                logger.error(f"Response text: {response_text}")
                return []
                
        except Exception as e:
            logger.error(f"Error in batch image comparison: {e}", exc_info=True)
            return []
        """
        Compare user image with database product image using Gemini vision.
        
        Args:
            user_image_path: Path to user's image
            product_image_url: URL of database product image
            product_info: Product information from database
            user_analysis: User image analysis
            similarity_score: Embedding similarity score
            
        Returns:
            VisualMatchResult with detailed comparison
        """
        try:
            logger.info(f"👁️ Comparing user image with product: {product_info.get('title', 'Unknown')}")
            
            # Download product image
            product_image_path = await self._download_product_image(product_image_url, product_info.get('product_id', 'unknown'))
            if not product_image_path:
                logger.error("Failed to download product image")
                return None
            
            # Upload both images to Gemini
            user_file = await asyncio.to_thread(
                genai.upload_file,
                path=user_image_path,
                display_name="user_query_image"
            )
            
            product_file = await asyncio.to_thread(
                genai.upload_file,
                path=product_image_path,
                display_name="product_image"
            )
            
            # Wait for processing
            for file in [user_file, product_file]:
                while file.state.name == "PROCESSING":
                    await asyncio.sleep(1)
                    file = await asyncio.to_thread(genai.get_file, file.name)
            
            # Create comparison prompt
            prompt = f"""You are a product matching expert. Compare these two images to determine if they show the same or similar product.

**Context:**
- **Image 1 (Customer's Query)**: Customer is looking for this product
  - Looking for: {user_analysis.get('product_type', 'Unknown')}
  - Desired colors: {', '.join(user_analysis.get('colors', [])[:3]) if isinstance(user_analysis.get('colors', []), list) else 'Not specified'}
  - Key features: {', '.join(user_analysis.get('key_features', [])[:3]) if isinstance(user_analysis.get('key_features', []), list) else 'Not specified'}
  - Context: {user_analysis.get('image_context', 'Not specified')}

- **Image 2 (Database Product)**: {product_info.get('title', 'Product')}
  - Type: {product_info.get('category', 'Unknown')}
  - Colors: {', '.join(product_info.get('colors', [])[:3]) if isinstance(product_info.get('colors', []), list) else 'Not specified'}
  - Features: {', '.join(product_info.get('specifications', {}).get('features', [])[:3]) if isinstance(product_info.get('specifications', {}).get('features', []), list) else 'Not specified'}
  - Price: ₹{product_info.get('price', 'Unknown')}

- **Embedding Similarity Score**: {similarity_score:.3f} (0.0 to 1.0, higher is better)

**Your Task:**
Compare both images visually and determine:
1. Are they the SAME product? (exact match)
2. Are they SIMILAR products? (same type, different variant)
3. Are they DIFFERENT products? (not a match)

**Analyze:**
- Product type match (ride-on car, bike, jeep, etc.)
- Design and style similarity
- Color match or difference
- Feature similarity (wheels, lights, seats, etc.)
- Size and proportions
- Overall visual similarity

**Response Format:**
Return ONLY valid JSON (no markdown, no extra text):
{{
    "match_type": "exact_match|color_variant|similar_product|related_product|no_match",
    "confidence": "very_high|high|medium|low|very_low",
    "confidence_score": 0.0-1.0,
    "visual_similarity": "very_high|high|medium|low|very_low",
    "product_type_match": true/false,
    "design_match": true/false,
    "color_match": true/false,
    "color_difference": "description of color differences or null",
    "feature_match": true/false,
    "feature_differences": ["difference1", "difference2"] or [],
    "recommendation": "exact_match|recommend_with_color_note|recommend_as_alternative|not_recommended",
    "explanation": "detailed explanation of the match (2-3 sentences)",
    "customer_message": "friendly message to send to customer explaining the match"
}}

**Match Type Definitions:**
- **exact_match**: Same product, same color, same design
- **color_variant**: Same product, different color only
- **similar_product**: Similar type/style but different model/brand
- **related_product**: Related category but different product
- **no_match**: Not a match

**Confidence Levels:**
- **very_high**: 0.9-1.0 (Almost certain)
- **high**: 0.8-0.9 (Very confident)
- **medium**: 0.6-0.8 (Moderately confident)
- **low**: 0.4-0.6 (Somewhat confident)
- **very_low**: 0.0-0.4 (Not confident)

Now compare the images:"""

            # Generate comparison
            response = await asyncio.to_thread(
                self.model.generate_content,
                [prompt, user_file, product_file]
            )
            
            # Parse response
            response_text = response.text.strip()
            logger.info(f"📝 Raw comparison response: {response_text[:200]}...")
            
            # Extract JSON from response
            try:
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != 0:
                    json_str = response_text[start_idx:end_idx]
                    comparison = json.loads(json_str)
                    
                    # Create VisualMatchResult
                    result = VisualMatchResult(
                        product_id=product_info.get('product_id', ''),
                        product_title=product_info.get('title', ''),
                        match_type=MatchType(comparison.get('match_type', 'no_match')),
                        confidence=ConfidenceLevel(comparison.get('confidence', 'very_low')),
                        confidence_score=comparison.get('confidence_score', 0.0),
                        visual_similarity=comparison.get('visual_similarity', 'very_low'),
                        product_type_match=comparison.get('product_type_match', False),
                        design_match=comparison.get('design_match', False),
                        color_match=comparison.get('color_match', False),
                        color_difference=comparison.get('color_difference'),
                        feature_match=comparison.get('feature_match', False),
                        feature_differences=comparison.get('feature_differences', []),
                        recommendation=comparison.get('recommendation', 'not_recommended'),
                        explanation=comparison.get('explanation', ''),
                        customer_message=comparison.get('customer_message', ''),
                        similarity_score=similarity_score
                    )
                    
                    logger.info(f"✅ Visual comparison completed: {result.match_type.value} (confidence: {result.confidence.value})")
                    
                    # Cleanup downloaded image
                    await self._cleanup_image(product_image_path)
                    
                    return result
                else:
                    logger.error("No JSON found in comparison response")
                    return None
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse comparison JSON: {e}")
                logger.error(f"Response text: {response_text}")
                return None
                
        except Exception as e:
            logger.error(f"Error comparing images: {e}", exc_info=True)
            return None
    
    async def _download_product_image(self, image_url: str, product_id: str) -> Optional[str]:
        """Download product image for comparison."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                
                # Save to temp directory
                temp_dir = Path(__file__).parent / "temp_images"
                temp_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                image_path = temp_dir / f"product_{product_id}_{timestamp}.jpg"
                
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"📥 Downloaded product image: {image_path}")
                return str(image_path)
                
        except Exception as e:
            logger.error(f"Error downloading product image: {e}")
            return None
    
    async def _cleanup_image(self, image_path: str) -> bool:
        """Clean up temporary image file."""
        try:
            if os.path.exists(image_path):
                await asyncio.to_thread(os.remove, image_path)
                logger.info(f"🗑️ Cleaned up image: {image_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error cleaning up image: {e}")
            return False
    
    async def analyze_product_matches(
        self,
        user_image_path: str,
        products: List[Dict[str, Any]],
        user_analysis: Dict[str, Any]
    ) -> ProductMatchAnalysis:
        """
        Analyze all product matches with visual verification.
        
        Args:
            user_image_path: Path to user's image
            products: List of products from database search
            user_analysis: User image analysis
            
        Returns:
            Complete product match analysis
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"🔍 Starting batch visual verification for {len(products)} products")
            
            # Use batch comparison for better efficiency and accuracy
            matched_products = await self.compare_all_images_batch(
                user_image_path,
                products,
                user_analysis
            )
            
            logger.info(f"✅ Batch visual verification completed: {len(matched_products)} results")
            
            # Find best match
            best_match = None
            if matched_products:
                # Sort by confidence score and match type priority
                def match_priority(match):
                    type_priority = {
                        MatchType.EXACT_MATCH: 5,
                        MatchType.COLOR_VARIANT: 4,
                        MatchType.SIMILAR_PRODUCT: 3,
                        MatchType.RELATED_PRODUCT: 2,
                        MatchType.NO_MATCH: 1
                    }
                    return (type_priority[match.match_type], match.confidence_score)
                
                matched_products.sort(key=match_priority, reverse=True)
                best_match = matched_products[0]
            
            # Generate overall recommendation
            overall_recommendation = self._generate_overall_recommendation(matched_products, best_match)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            analysis = ProductMatchAnalysis(
                user_image_path=user_image_path,
                user_image_analysis=user_analysis,
                matched_products=matched_products,
                best_match=best_match,
                overall_recommendation=overall_recommendation,
                processing_time=processing_time
            )
            
            logger.info(f"✅ Visual verification analysis completed in {processing_time:.2f}s")
            logger.info(f"📊 Found {len(matched_products)} verified matches")
            if best_match:
                logger.info(f"🎯 Best match: {best_match.match_type.value} ({best_match.confidence.value})")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in product match analysis: {e}", exc_info=True)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return ProductMatchAnalysis(
                user_image_path=user_image_path,
                user_image_analysis=user_analysis,
                matched_products=[],
                best_match=None,
                overall_recommendation="Error in analysis",
                processing_time=processing_time
            )
    
    def _generate_overall_recommendation(
        self,
        matched_products: List[VisualMatchResult],
        best_match: Optional[VisualMatchResult]
    ) -> str:
        """Generate overall recommendation based on all matches."""
        if not matched_products:
            return "No matching products found. Please try a different image or contact us for assistance."
        
        if not best_match:
            return "Found some similar products, but no exact matches. Please check the suggestions below."
        
        # Count match types
        exact_matches = sum(1 for m in matched_products if m.match_type == MatchType.EXACT_MATCH)
        color_variants = sum(1 for m in matched_products if m.match_type == MatchType.COLOR_VARIANT)
        similar_products = sum(1 for m in matched_products if m.match_type == MatchType.SIMILAR_PRODUCT)
        
        if exact_matches > 0:
            return f"Perfect! Found {exact_matches} exact match(es) for your image! 🎯"
        elif color_variants > 0:
            return f"Great! Found the same product in different colors. {color_variants} color variant(s) available! 🎨"
        elif similar_products > 0:
            return f"Found {similar_products} similar product(s) that match your image! 👀"
        else:
            return "Found some related products. Check the suggestions below! 🔍"


# Global instance
_visual_verification_instance: Optional[VisualVerificationSystem] = None

def initialize_visual_verification(gemini_api_key: str) -> VisualVerificationSystem:
    """Initialize the global VisualVerificationSystem instance."""
    global _visual_verification_instance
    _visual_verification_instance = VisualVerificationSystem(gemini_api_key)
    return _visual_verification_instance

def get_visual_verification() -> Optional[VisualVerificationSystem]:
    """Get the global VisualVerificationSystem instance."""
    return _visual_verification_instance
