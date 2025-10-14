"""
Test Image-Based Product Matching System
Tests the complete workflow:
1. Generate product description from database image
2. Create embedding from description
3. Analyze user image
4. Generate embedding from user image description
5. Compare embeddings (simulate vector search)
6. Visual verification with both images
7. Provide match result with confidence and color analysis
"""

import os
import asyncio
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

import google.generativeai as genai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ImageProductMatcher:
    """Handles image-based product matching with embeddings and visual verification."""
    
    def __init__(self, gemini_api_key: str):
        """Initialize the matcher with Gemini API."""
        genai.configure(api_key=gemini_api_key)
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
        self.chat_model = os.getenv("CHAT_MODEL", "models/gemini-2.5-flash")
        self.embedding_dimensionality = int(os.getenv("EMBEDDING_DIMENSIONALITY", "768"))
        
        logger.info(f"🤖 Initialized with model: {self.chat_model}")
        logger.info(f"📊 Embedding model: {self.embedding_model} ({self.embedding_dimensionality}D)")
    
    async def generate_product_description(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Generate detailed product description from database product image.
        This simulates what would be stored in the database for each product.
        
        Args:
            image_path: Path to product image
            
        Returns:
            Dictionary with product description and metadata
        """
        try:
            logger.info(f"📸 Analyzing database product image: {image_path}")
            
            # Upload image to Gemini
            uploaded_file = await asyncio.to_thread(
                genai.upload_file,
                path=image_path,
                display_name=f"db_product_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            # Wait for processing
            while uploaded_file.state.name == "PROCESSING":
                await asyncio.sleep(1)
                uploaded_file = await asyncio.to_thread(genai.get_file, uploaded_file.name)
            
            if uploaded_file.state.name == "FAILED":
                logger.error("❌ Image upload failed")
                return None
            
            # Create prompt for product description
            prompt = """You are a product catalog expert. Analyze this product image and generate a comprehensive product description.

**Your Task:**
Extract all visible product details that would help customers find this product.

**Focus on:**
1. **Product Type**: What kind of product is this? (e.g., ride-on car, electric bike, toy jeep)
2. **Design & Style**: Describe the overall design, style, and appearance
3. **Colors**: List ALL visible colors (primary and secondary colors)
4. **Key Features**: Identify visible features (lights, wheels, seats, steering, etc.)
5. **Size Category**: Estimate size (small, medium, large, extra-large)
6. **Age Suitability**: Estimate appropriate age range based on size and complexity
7. **Material & Build**: Describe visible materials (plastic, metal, rubber wheels, etc.)
8. **Unique Characteristics**: Any distinctive features that make this product stand out

**Response Format:**
Return ONLY valid JSON (no markdown, no extra text):
{
    "product_type": "specific product category",
    "product_name": "suggested product name",
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

            # Generate description
            model = genai.GenerativeModel(self.chat_model)
            response = await asyncio.to_thread(
                model.generate_content,
                [prompt, uploaded_file]
            )
            
            # Parse response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            
            # Clean up
            await asyncio.to_thread(genai.delete_file, uploaded_file.name)
            
            logger.info(f"✅ Product description generated")
            logger.info(f"   Type: {result.get('product_type')}")
            logger.info(f"   Colors: {', '.join(result.get('colors', []))}")
            logger.info(f"   Features: {len(result.get('key_features', []))} features")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error generating product description: {e}", exc_info=True)
            return None
    
    async def generate_user_query_description(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Generate search query description from user's image.
        This extracts what the user is looking for.
        
        Args:
            image_path: Path to user's image
            
        Returns:
            Dictionary with search query and metadata
        """
        try:
            logger.info(f"🔍 Analyzing user query image: {image_path}")
            
            # Upload image to Gemini
            uploaded_file = await asyncio.to_thread(
                genai.upload_file,
                path=image_path,
                display_name=f"user_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            # Wait for processing
            while uploaded_file.state.name == "PROCESSING":
                await asyncio.sleep(1)
                uploaded_file = await asyncio.to_thread(genai.get_file, uploaded_file.name)
            
            if uploaded_file.state.name == "FAILED":
                logger.error("❌ Image upload failed")
                return None
            
            # Create prompt for user query analysis
            prompt = """You are a product search expert. Analyze this image sent by a customer and understand what product they're looking for.

**Your Task:**
Extract the customer's search intent and product requirements from this image.

**The image might contain:**
- A product photo (what they want to buy)
- A screenshot from another website
- A reference image showing similar product
- Multiple products in a store/display
- A product with background/people

**Focus on:**
1. **Main Product**: Identify the primary product the customer is interested in
2. **Product Type**: What category of product? (ride-on car, bike, jeep, etc.)
3. **Desired Colors**: What colors are visible on the product they're showing?
4. **Key Features**: What features are visible that they might want?
5. **Search Query**: Generate a natural search query that would find this product
6. **Context**: Is this a clear product photo, screenshot, or reference image?

**Response Format:**
Return ONLY valid JSON (no markdown, no extra text):
{
    "product_type": "what they're looking for",
    "search_query": "natural language search query (2-3 sentences)",
    "desired_colors": ["color1", "color2"],
    "primary_color": "main color they want",
    "key_features": ["feature1", "feature2", "feature3"],
    "age_range": "estimated age range or null",
    "image_context": "clear_product|screenshot|reference|store_display|with_background",
    "confidence": "high|medium|low",
    "notes": "any additional context or observations"
}

**Important:**
- Focus on what the customer WANTS, not just what you see
- If there are multiple products, identify the main one
- If there's background/people, focus on the product
- Generate a search query that would find similar products
- Output ONLY the JSON, nothing else

Now analyze the customer's image:"""

            # Generate description
            model = genai.GenerativeModel(self.chat_model)
            response = await asyncio.to_thread(
                model.generate_content,
                [prompt, uploaded_file]
            )
            
            # Parse response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            
            # Clean up
            await asyncio.to_thread(genai.delete_file, uploaded_file.name)
            
            logger.info(f"✅ User query analyzed")
            logger.info(f"   Looking for: {result.get('product_type')}")
            logger.info(f"   Desired colors: {', '.join(result.get('desired_colors', []))}")
            logger.info(f"   Context: {result.get('image_context')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error analyzing user query: {e}", exc_info=True)
            return None
    
    async def generate_embedding(self, text: str, task_type: str = "retrieval_document") -> Optional[List[float]]:
        """
        Generate embedding vector from text.
        
        Args:
            text: Text to embed
            task_type: "retrieval_document" for products, "retrieval_query" for search
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            embed_params = {
                "model": self.embedding_model,
                "content": text,
                "task_type": task_type,
                "output_dimensionality": self.embedding_dimensionality
            }
            
            result = await asyncio.to_thread(genai.embed_content, **embed_params)
            
            logger.info(f"✅ Generated {len(result['embedding'])}D embedding")
            return result['embedding']
            
        except Exception as e:
            logger.error(f"❌ Error generating embedding: {e}", exc_info=True)
            return None
    
    def calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def visual_verification(
        self, 
        product_image_path: str,
        user_image_path: str,
        product_info: Dict[str, Any],
        user_query: Dict[str, Any],
        similarity_score: float
    ) -> Optional[Dict[str, Any]]:
        """
        Perform visual verification by comparing both images directly.
        This is the final step to confirm the match.
        
        Args:
            product_image_path: Path to database product image
            user_image_path: Path to user's query image
            product_info: Product description from database
            user_query: User's search query analysis
            similarity_score: Embedding similarity score
            
        Returns:
            Dictionary with verification results
        """
        try:
            logger.info(f"👁️ Performing visual verification...")
            
            # Upload both images
            product_file = await asyncio.to_thread(
                genai.upload_file,
                path=product_image_path,
                display_name="product_image"
            )
            
            user_file = await asyncio.to_thread(
                genai.upload_file,
                path=user_image_path,
                display_name="user_query_image"
            )
            
            # Wait for processing
            for file in [product_file, user_file]:
                while file.state.name == "PROCESSING":
                    await asyncio.sleep(1)
                    file = await asyncio.to_thread(genai.get_file, file.name)
            
            # Create verification prompt
            prompt = f"""You are a product matching expert. Compare these two images to determine if they show the same or similar product.

**Context:**
- **Image 1 (Product from Database)**: {product_info.get('product_name', 'Product')}
  - Type: {product_info.get('product_type')}
  - Colors: {', '.join(product_info.get('colors', []))}
  - Features: {', '.join(product_info.get('key_features', [])[:3])}

- **Image 2 (Customer's Query)**: Customer is looking for this product
  - Looking for: {user_query.get('product_type')}
  - Desired colors: {', '.join(user_query.get('desired_colors', []))}
  - Context: {user_query.get('image_context')}

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
    "match_type": "exact_match|color_variant|similar_product|different_product",
    "confidence": "high|medium|low",
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
- **different_product**: Not a match

**Important:**
- Be accurate - don't force a match if products are different
- Consider that customer's image might have background/people
- Color differences are OK if everything else matches
- Focus on product type, design, and features
- Output ONLY the JSON, nothing else

Now compare the images:"""

            # Generate verification
            model = genai.GenerativeModel(self.chat_model)
            response = await asyncio.to_thread(
                model.generate_content,
                [prompt, product_file, user_file]
            )
            
            # Parse response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            
            # Clean up
            await asyncio.to_thread(genai.delete_file, product_file.name)
            await asyncio.to_thread(genai.delete_file, user_file.name)
            
            logger.info(f"✅ Visual verification complete")
            logger.info(f"   Match type: {result.get('match_type')}")
            logger.info(f"   Confidence: {result.get('confidence')} ({result.get('confidence_score', 0):.2f})")
            logger.info(f"   Recommendation: {result.get('recommendation')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in visual verification: {e}", exc_info=True)
            return None
    
    async def match_product(
        self,
        product_image_path: str,
        user_image_path: str
    ) -> Dict[str, Any]:
        """
        Complete product matching workflow.
        
        Args:
            product_image_path: Path to database product image
            user_image_path: Path to user's query image
            
        Returns:
            Complete matching results
        """
        start_time = datetime.now()
        
        logger.info("=" * 80)
        logger.info("🚀 Starting Image-Based Product Matching")
        logger.info("=" * 80)
        
        # Step 1: Generate product description
        logger.info("\n📦 STEP 1: Analyzing Database Product Image")
        logger.info("-" * 80)
        product_info = await self.generate_product_description(product_image_path)
        if not product_info:
            return {"error": "Failed to analyze product image"}
        
        # Step 2: Generate product embedding
        logger.info("\n🔢 STEP 2: Generating Product Embedding")
        logger.info("-" * 80)
        product_text = f"{product_info['product_name']}. {product_info['detailed_description']}. Colors: {', '.join(product_info['colors'])}. Features: {', '.join(product_info['key_features'])}."
        logger.info(f"Product text: {product_text[:200]}...")
        product_embedding = await self.generate_embedding(product_text, "retrieval_document")
        if not product_embedding:
            return {"error": "Failed to generate product embedding"}
        
        # Step 3: Analyze user query
        logger.info("\n🔍 STEP 3: Analyzing User Query Image")
        logger.info("-" * 80)
        user_query = await self.generate_user_query_description(user_image_path)
        if not user_query:
            return {"error": "Failed to analyze user query"}
        
        # Step 4: Generate query embedding
        logger.info("\n🔢 STEP 4: Generating Query Embedding")
        logger.info("-" * 80)
        query_text = user_query['search_query']
        logger.info(f"Query text: {query_text}")
        query_embedding = await self.generate_embedding(query_text, "retrieval_query")
        if not query_embedding:
            return {"error": "Failed to generate query embedding"}
        
        # Step 5: Calculate similarity
        logger.info("\n📊 STEP 5: Calculating Embedding Similarity")
        logger.info("-" * 80)
        similarity = self.calculate_cosine_similarity(product_embedding, query_embedding)
        logger.info(f"Cosine similarity: {similarity:.4f}")
        
        # Interpret similarity score
        if similarity >= 0.80:
            similarity_level = "Very High - Excellent Match"
        elif similarity >= 0.70:
            similarity_level = "High - Good Match"
        elif similarity >= 0.60:
            similarity_level = "Medium - Possible Match"
        elif similarity >= 0.50:
            similarity_level = "Low - Weak Match"
        else:
            similarity_level = "Very Low - Poor Match"
        
        logger.info(f"Similarity level: {similarity_level}")
        
        # Step 6: Visual verification
        logger.info("\n👁️ STEP 6: Visual Verification")
        logger.info("-" * 80)
        verification = await self.visual_verification(
            product_image_path,
            user_image_path,
            product_info,
            user_query,
            similarity
        )
        if not verification:
            return {"error": "Failed visual verification"}
        
        # Calculate total time
        total_time = (datetime.now() - start_time).total_seconds()
        
        # Compile results
        results = {
            "success": True,
            "processing_time": total_time,
            "product_info": product_info,
            "user_query": user_query,
            "embedding_similarity": similarity,
            "similarity_level": similarity_level,
            "visual_verification": verification,
            "final_recommendation": verification.get('recommendation'),
            "customer_message": verification.get('customer_message')
        }
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ MATCHING COMPLETE")
        logger.info("=" * 80)
        logger.info(f"⏱️  Total time: {total_time:.2f}s")
        logger.info(f"📊 Embedding similarity: {similarity:.4f} ({similarity_level})")
        logger.info(f"👁️  Visual match: {verification.get('match_type')}")
        logger.info(f"🎯 Confidence: {verification.get('confidence')} ({verification.get('confidence_score', 0):.2f})")
        logger.info(f"💡 Recommendation: {verification.get('recommendation')}")
        logger.info("=" * 80)
        
        return results


async def main():
    """Run the test."""
    
    # Get API key
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.error("❌ GEMINI_API_KEY not found in environment")
        return
    
    # Initialize matcher
    matcher = ImageProductMatcher(gemini_api_key)
    
    # Test images
    product_image = r"e:\tele_agent\img_com_test\db.png"
    user_image = r"e:\tele_agent\img_com_test\user.png"
    
    # Check if images exist
    if not Path(product_image).exists():
        logger.error(f"❌ Product image not found: {product_image}")
        return
    
    if not Path(user_image).exists():
        logger.error(f"❌ User image not found: {user_image}")
        return
    
    logger.info(f"📸 Product image: {product_image}")
    logger.info(f"📸 User image: {user_image}")
    
    # Run matching
    results = await matcher.match_product(product_image, user_image)
    
    # Print final results
    if results.get("success"):
        print("\n" + "=" * 80)
        print("📋 FINAL RESULTS")
        print("=" * 80)
        print(f"\n🏷️  PRODUCT INFO:")
        print(f"   Name: {results['product_info']['product_name']}")
        print(f"   Type: {results['product_info']['product_type']}")
        print(f"   Colors: {', '.join(results['product_info']['colors'])}")
        print(f"   Primary Color: {results['product_info']['primary_color']}")
        
        print(f"\n🔍 USER QUERY:")
        print(f"   Looking for: {results['user_query']['product_type']}")
        print(f"   Desired colors: {', '.join(results['user_query']['desired_colors'])}")
        print(f"   Primary color: {results['user_query']['primary_color']}")
        
        print(f"\n📊 SIMILARITY ANALYSIS:")
        print(f"   Embedding similarity: {results['embedding_similarity']:.4f}")
        print(f"   Level: {results['similarity_level']}")
        
        print(f"\n👁️  VISUAL VERIFICATION:")
        print(f"   Match type: {results['visual_verification']['match_type']}")
        print(f"   Confidence: {results['visual_verification']['confidence']} ({results['visual_verification']['confidence_score']:.2f})")
        print(f"   Product type match: {results['visual_verification']['product_type_match']}")
        print(f"   Design match: {results['visual_verification']['design_match']}")
        print(f"   Color match: {results['visual_verification']['color_match']}")
        if results['visual_verification']['color_difference']:
            print(f"   Color difference: {results['visual_verification']['color_difference']}")
        
        print(f"\n🎯 FINAL RECOMMENDATION:")
        print(f"   {results['final_recommendation']}")
        
        print(f"\n💬 CUSTOMER MESSAGE:")
        print(f"   {results['customer_message']}")
        
        print(f"\n⏱️  PERFORMANCE:")
        print(f"   Total processing time: {results['processing_time']:.2f}s")
        
        print("\n" + "=" * 80)
        
        # Save results to file
        output_file = Path("e:/tele_agent/test_results_image_matching.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {output_file}")
        
    else:
        print(f"\n❌ Matching failed: {results.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())