"""
Generate AI Image Descriptions and Embeddings for All Products
This script processes all products in the database:
1. Fetches products with images
2. Downloads first image for each product
3. Generates AI description using Gemini 2.5 Flash
4. Creates embedding from description
5. Updates database with ai_image_description, ai_image_metadata, and image_embedding
"""

import os
import asyncio
import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests
from io import BytesIO

import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('product_image_generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ProductImageDescriptionGenerator:
    """Generates AI descriptions and embeddings for product images."""
    
    def __init__(self):
        """Initialize the generator with API clients."""
        # Supabase setup
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Gemini setup
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=gemini_api_key)
        
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
        self.chat_model = os.getenv("CHAT_MODEL", "models/gemini-2.5-flash")
        self.embedding_dimensionality = int(os.getenv("EMBEDDING_DIMENSIONALITY", "768"))
        
        # Rate limiting for Gemini 2.5 Flash (9 requests per minute)
        self.max_requests_per_minute = 9
        self.request_timestamps = []  # Track request times
        
        # Create temp directory for images
        self.temp_dir = Path("temp_product_images")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Statistics
        self.stats = {
            "total_products": 0,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": None,
            "end_time": None,
            "rate_limit_waits": 0,
            "total_wait_time": 0
        }
        
        logger.info("=" * 80)
        logger.info("🚀 Product Image Description Generator Initialized")
        logger.info("=" * 80)
        logger.info(f"📊 Embedding Model: {self.embedding_model} ({self.embedding_dimensionality}D)")
        logger.info(f"🤖 Chat Model: {self.chat_model}")
        logger.info(f"⏱️  Rate Limit: {self.max_requests_per_minute} requests/minute")
        logger.info(f"🗄️  Database: {self.supabase_url}")
        logger.info("=" * 80)
    
    async def wait_for_rate_limit(self):
        """
        Implement rate limiting for Gemini API calls.
        Ensures we don't exceed max_requests_per_minute.
        """
        current_time = time.time()
        
        # Remove timestamps older than 60 seconds
        self.request_timestamps = [
            ts for ts in self.request_timestamps 
            if current_time - ts < 60
        ]
        
        # If we've hit the limit, wait until the oldest request is 60 seconds old
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            oldest_request = self.request_timestamps[0]
            wait_time = 60 - (current_time - oldest_request)
            
            if wait_time > 0:
                self.stats['rate_limit_waits'] += 1
                self.stats['total_wait_time'] += wait_time
                logger.info(f"   ⏳ Rate limit reached. Waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                
                # Clean up old timestamps again after waiting
                current_time = time.time()
                self.request_timestamps = [
                    ts for ts in self.request_timestamps 
                    if current_time - ts < 60
                ]
        
        # Record this request
        self.request_timestamps.append(time.time())
    
    async def fetch_products_without_image_descriptions(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Fetch products that have images but no AI image descriptions yet.
        
        Args:
            limit: Maximum number of products to fetch (None for all)
            
        Returns:
            List of product dictionaries
        """
        try:
            logger.info("📥 Fetching products from database...")
            
            # Build query
            query = self.supabase.table("products").select("*")
            
            # Filter: has images but no image description
            query = query.is_("ai_image_description", "null")
            query = query.not_.is_("images", "null")
            
            if limit:
                query = query.limit(limit)
            
            response = query.execute()
            
            # Filter products that actually have images in the array
            products = []
            for product in response.data:
                images = product.get('images', [])
                
                # Handle case where images might be a string (JSON string)
                if isinstance(images, str):
                    try:
                        images = json.loads(images)
                        product['images'] = images  # Update the product dict
                    except:
                        continue
                
                if images and len(images) > 0:
                    products.append(product)
            
            logger.info(f"✅ Found {len(products)} products needing image descriptions")
            return products
            
        except Exception as e:
            logger.error(f"❌ Error fetching products: {e}", exc_info=True)
            return []
    
    async def download_image(self, image_url: str, product_id: str) -> Optional[Path]:
        """
        Download product image from URL.
        
        Args:
            image_url: URL of the image
            product_id: Product ID for filename
            
        Returns:
            Path to downloaded image or None if failed
        """
        try:
            # Clean filename
            safe_product_id = "".join(c for c in product_id if c.isalnum() or c in ('-', '_'))
            image_path = self.temp_dir / f"{safe_product_id}.jpg"
            
            # Download image
            response = await asyncio.to_thread(requests.get, image_url, timeout=30)
            response.raise_for_status()
            
            # Save image
            with open(image_path, 'wb') as f:
                f.write(response.content)
            
            logger.debug(f"   📥 Downloaded image: {image_path}")
            return image_path
            
        except Exception as e:
            logger.error(f"   ❌ Error downloading image from {image_url}: {e}")
            return None
    
    async def generate_product_description(self, image_path: Path) -> Optional[Dict[str, Any]]:
        """
        Generate detailed product description from product image using Gemini.
        
        Args:
            image_path: Path to product image
            
        Returns:
            Dictionary with product description and metadata
        """
        try:
            logger.debug(f"   🤖 Analyzing product image with Gemini...")
            
            # Upload image to Gemini
            uploaded_file = await asyncio.to_thread(
                genai.upload_file,
                path=str(image_path),
                display_name=f"product_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            # Wait for processing
            max_wait = 30  # seconds
            wait_time = 0
            while uploaded_file.state.name == "PROCESSING" and wait_time < max_wait:
                await asyncio.sleep(1)
                wait_time += 1
                uploaded_file = await asyncio.to_thread(genai.get_file, uploaded_file.name)
            
            if uploaded_file.state.name == "FAILED":
                logger.error("   ❌ Image upload failed")
                return None
            
            # Create prompt for product description
            prompt = """You are a product catalog expert. Analyze this product image and generate a comprehensive product description.

**Your Task:**
Extract all visible product details that would help customers find this product.

**Focus on:**
1. **Product Type**: What kind of product is this? (e.g., ride-on car, electric bike, toy jeep, doll, puzzle, educational toy)
2. **Design & Style**: Describe the overall design, style, and appearance
3. **Colors**: List ALL visible colors (primary and secondary colors)
4. **Key Features**: Identify visible features (lights, wheels, seats, steering, buttons, accessories, etc.)
5. **Size Category**: Estimate size (small, medium, large, extra-large)
6. **Age Suitability**: Estimate appropriate age range based on size and complexity
7. **Material & Build**: Describe visible materials (plastic, metal, rubber wheels, fabric, wood, etc.)
8. **Unique Characteristics**: Any distinctive features that make this product stand out

**Response Format:**
Return ONLY valid JSON (no markdown, no extra text):
{
    "product_type": "specific product category",
    "product_name": "suggested descriptive product name",
    "detailed_description": "comprehensive description for embedding (3-5 sentences, include all key details)",
    "colors": ["color1", "color2", "color3"],
    "primary_color": "main color",
    "key_features": ["feature1", "feature2", "feature3", "feature4", "feature5"],
    "age_range": "X-Y years",
    "size_category": "small|medium|large|extra-large",
    "style_keywords": ["keyword1", "keyword2", "keyword3", "keyword4"],
    "confidence": "high|medium|low"
}

**Important:**
- Be specific and detailed in the description
- Include all visible colors
- Focus on searchable features
- Use keywords that customers would use when searching
- The detailed_description should be rich and comprehensive for semantic search
- Output ONLY the JSON, nothing else

Now analyze the product image:"""

            # Wait for rate limit before making API call
            await self.wait_for_rate_limit()
            
            # Generate description
            model = genai.GenerativeModel(self.chat_model)
            response = await asyncio.to_thread(
                model.generate_content,
                [prompt, uploaded_file]
            )
            
            # Parse response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            
            # Clean up uploaded file
            await asyncio.to_thread(genai.delete_file, uploaded_file.name)
            
            logger.debug(f"   ✅ Generated description: {result.get('product_type')}")
            return result
            
        except Exception as e:
            logger.error(f"   ❌ Error generating product description: {e}", exc_info=True)
            return None
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector from text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            embed_params = {
                "model": self.embedding_model,
                "content": text,
                "task_type": "retrieval_document",
                "output_dimensionality": self.embedding_dimensionality
            }
            
            result = await asyncio.to_thread(genai.embed_content, **embed_params)
            
            logger.debug(f"   ✅ Generated {len(result['embedding'])}D embedding")
            return result['embedding']
            
        except Exception as e:
            logger.error(f"   ❌ Error generating embedding: {e}", exc_info=True)
            return None
    
    async def update_product_in_database(
        self,
        product_id: str,
        ai_description: str,
        ai_metadata: Dict[str, Any],
        embedding: List[float]
    ) -> bool:
        """
        Update product in database with AI-generated data.
        
        Args:
            product_id: Product ID
            ai_description: AI-generated description
            ai_metadata: AI-extracted metadata
            embedding: Embedding vector
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use the database function
            response = self.supabase.rpc(
                "update_product_image_data",
                {
                    "p_product_id": product_id,
                    "p_ai_image_description": ai_description,
                    "p_ai_image_metadata": ai_metadata,
                    "p_image_embedding": embedding
                }
            ).execute()
            
            if response.data:
                logger.debug(f"   ✅ Updated database for product {product_id}")
                return True
            else:
                logger.error(f"   ❌ Failed to update database for product {product_id}")
                return False
            
        except Exception as e:
            logger.error(f"   ❌ Error updating database: {e}", exc_info=True)
            return False
    
    async def process_product(self, product: Dict[str, Any]) -> bool:
        """
        Process a single product: download image, generate description, create embedding, update database.
        
        Args:
            product: Product dictionary from database
            
        Returns:
            True if successful, False otherwise
        """
        product_id = product.get('product_id')
        title = product.get('title', 'Unknown')
        images = product.get('images', [])
        
        # Handle case where images might be a string (JSON string)
        if isinstance(images, str):
            try:
                images = json.loads(images)
            except:
                images = []
        
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"📦 Processing: {title}")
            logger.info(f"   ID: {product_id}")
            logger.info(f"   Images: {len(images)} available")
            
            # Get first image URL
            if not images or len(images) == 0:
                logger.warning(f"   ⚠️  No images available, skipping")
                self.stats['skipped'] += 1
                return False
            
            first_image_url = images[0]
            logger.info(f"   🖼️  Using first image: {first_image_url[:80]}...")
            
            # Step 1: Download image
            image_path = await self.download_image(first_image_url, product_id)
            if not image_path:
                logger.error(f"   ❌ Failed to download image")
                self.stats['failed'] += 1
                return False
            
            # Step 2: Generate AI description
            product_info = await self.generate_product_description(image_path)
            if not product_info:
                logger.error(f"   ❌ Failed to generate description")
                self.stats['failed'] += 1
                return False
            
            # Extract data
            detailed_description = product_info.get('detailed_description', '')
            
            # Prepare metadata (remove detailed_description to avoid duplication)
            metadata = {
                "product_type": product_info.get('product_type'),
                "product_name": product_info.get('product_name'),
                "colors": product_info.get('colors', []),
                "primary_color": product_info.get('primary_color'),
                "key_features": product_info.get('key_features', []),
                "age_range": product_info.get('age_range'),
                "size_category": product_info.get('size_category'),
                "style_keywords": product_info.get('style_keywords', []),
                "confidence": product_info.get('confidence', 'medium')
            }
            
            logger.info(f"   📝 Description: {detailed_description[:100]}...")
            logger.info(f"   🎨 Colors: {', '.join(metadata['colors'])}")
            logger.info(f"   ⭐ Features: {len(metadata['key_features'])} identified")
            
            # Step 3: Generate embedding
            embedding = await self.generate_embedding(detailed_description)
            if not embedding:
                logger.error(f"   ❌ Failed to generate embedding")
                self.stats['failed'] += 1
                return False
            
            # Step 4: Update database
            success = await self.update_product_in_database(
                product_id,
                detailed_description,
                metadata,
                embedding
            )
            
            if success:
                logger.info(f"   ✅ Successfully processed product {product_id}")
                self.stats['successful'] += 1
                return True
            else:
                logger.error(f"   ❌ Failed to update database")
                self.stats['failed'] += 1
                return False
            
        except Exception as e:
            logger.error(f"   ❌ Error processing product {product_id}: {e}", exc_info=True)
            self.stats['failed'] += 1
            return False
        
        finally:
            # Clean up downloaded image
            if 'image_path' in locals() and image_path and image_path.exists():
                try:
                    image_path.unlink()
                except:
                    pass
    
    async def process_all_products(self, limit: int = None, batch_size: int = 5):
        """
        Process all products sequentially (rate-limited to 9 requests/minute).
        
        Args:
            limit: Maximum number of products to process (None for all)
            batch_size: Ignored (kept for backward compatibility). Products are processed sequentially due to rate limits.
        """
        try:
            self.stats['start_time'] = datetime.now()
            
            # Fetch products
            products = await self.fetch_products_without_image_descriptions(limit)
            self.stats['total_products'] = len(products)
            
            if not products:
                logger.info("✅ No products need processing!")
                return
            
            # Calculate estimated time
            estimated_time_minutes = len(products) / self.max_requests_per_minute
            logger.info(f"\n{'='*80}")
            logger.info(f"🚀 Starting sequential processing of {len(products)} products")
            logger.info(f"   Rate limit: {self.max_requests_per_minute} requests/minute")
            logger.info(f"   Estimated time: {estimated_time_minutes:.1f} minutes")
            logger.info(f"{'='*80}\n")
            
            # Process products sequentially (rate limiting is handled in generate_product_description)
            for i, product in enumerate(products, 1):
                logger.info(f"\n{'='*80}")
                logger.info(f"📦 Processing Product {i}/{len(products)}")
                logger.info(f"{'='*80}")
                
                # Process product
                await self.process_product(product)
                
                self.stats['processed'] += 1
                
                # Progress update every 5 products or at the end
                if i % 5 == 0 or i == len(products):
                    progress = (self.stats['processed'] / self.stats['total_products']) * 100
                    elapsed_time = (datetime.now() - self.stats['start_time']).total_seconds() / 60
                    avg_time_per_product = elapsed_time / self.stats['processed'] if self.stats['processed'] > 0 else 0
                    remaining_products = self.stats['total_products'] - self.stats['processed']
                    estimated_remaining_time = remaining_products * avg_time_per_product
                    
                    logger.info(f"\n{'='*80}")
                    logger.info(f"📊 Progress: {self.stats['processed']}/{self.stats['total_products']} ({progress:.1f}%)")
                    logger.info(f"   ✅ Successful: {self.stats['successful']}")
                    logger.info(f"   ❌ Failed: {self.stats['failed']}")
                    logger.info(f"   ⏭️  Skipped: {self.stats['skipped']}")
                    logger.info(f"   ⏱️  Elapsed: {elapsed_time:.1f} min")
                    logger.info(f"   ⏳ Estimated remaining: {estimated_remaining_time:.1f} min")
                    if self.stats['rate_limit_waits'] > 0:
                        logger.info(f"   🛑 Rate limit waits: {self.stats['rate_limit_waits']} ({self.stats['total_wait_time']:.1f}s total)")
                    logger.info(f"{'='*80}\n")
            
            self.stats['end_time'] = datetime.now()
            self.print_final_report()
            
        except Exception as e:
            logger.error(f"❌ Error in batch processing: {e}", exc_info=True)
    
    def print_final_report(self):
        """Print final processing report."""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        logger.info(f"\n{'='*80}")
        logger.info("📊 FINAL PROCESSING REPORT")
        logger.info(f"{'='*80}")
        logger.info(f"⏱️  Total Time: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        logger.info(f"📦 Total Products: {self.stats['total_products']}")
        logger.info(f"✅ Successfully Processed: {self.stats['successful']}")
        logger.info(f"❌ Failed: {self.stats['failed']}")
        logger.info(f"⏭️  Skipped: {self.stats['skipped']}")
        
        if self.stats['successful'] > 0:
            avg_time = duration / self.stats['successful']
            logger.info(f"⚡ Average Time per Product: {avg_time:.2f} seconds")
        
        if self.stats['rate_limit_waits'] > 0:
            logger.info(f"🛑 Rate Limit Waits: {self.stats['rate_limit_waits']} times")
            logger.info(f"⏸️  Total Wait Time: {self.stats['total_wait_time']:.2f} seconds ({self.stats['total_wait_time']/60:.2f} minutes)")
        
        success_rate = (self.stats['successful'] / self.stats['total_products'] * 100) if self.stats['total_products'] > 0 else 0
        logger.info(f"📈 Success Rate: {success_rate:.1f}%")
        logger.info(f"{'='*80}\n")
        
        # Save report to file
        report = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "statistics": self.stats
        }
        
        with open('product_image_generation_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info("📄 Report saved to: product_image_generation_report.json")

async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate AI image descriptions for products')
    parser.add_argument('--limit', type=int, default=None, help='Maximum number of products to process')
    parser.add_argument('--batch-size', type=int, default=5, help='Number of products to process concurrently')
    parser.add_argument('--test', action='store_true', help='Test mode: process only 3 products')
    
    args = parser.parse_args()
    
    if args.test:
        logger.info("🧪 Running in TEST MODE - processing only 3 products")
        args.limit = 3
        args.batch_size = 1
    
    generator = ProductImageDescriptionGenerator()
    await generator.process_all_products(limit=args.limit, batch_size=args.batch_size)
    
    logger.info("\n✅ All done! Check the logs for details.")

if __name__ == "__main__":
    asyncio.run(main())