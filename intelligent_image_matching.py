"""
Intelligent Match Classification and Smart Response Generation System
Provides production-level intelligence for image-based product matching.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from visual_verification_system import VisualMatchResult, MatchType, ConfidenceLevel, ProductMatchAnalysis

logger = logging.getLogger(__name__)

class ResponseType(Enum):
    """Types of responses to generate."""
    EXACT_MATCH_FOUND = "exact_match_found"
    COLOR_VARIANT_FOUND = "color_variant_found"
    SIMILAR_PRODUCTS_FOUND = "similar_products_found"
    RELATED_PRODUCTS_FOUND = "related_products_found"
    NO_MATCHES_FOUND = "no_matches_found"
    ERROR_RESPONSE = "error_response"

@dataclass
class SmartResponse:
    """Intelligent response with context-aware messaging."""
    response_type: ResponseType
    primary_message: str
    secondary_message: Optional[str]
    product_cards_to_show: List[Dict[str, Any]]
    suggested_actions: List[str]
    confidence_level: str
    match_summary: str

class IntelligentMatchClassifier:
    """Production-level intelligent match classification system."""
    
    def __init__(self):
        """Initialize the match classifier."""
        self.confidence_thresholds = {
            "very_high": 0.9,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
            "very_low": 0.0
        }
        
        logger.info("🧠 IntelligentMatchClassifier initialized")
    
    def classify_matches(self, analysis: ProductMatchAnalysis) -> ResponseType:
        """
        Classify the overall match analysis into response type.
        
        Args:
            analysis: Complete product match analysis
            
        Returns:
            ResponseType indicating the best response strategy
        """
        try:
            if not analysis.matched_products:
                return ResponseType.NO_MATCHES_FOUND
            
            if not analysis.best_match:
                return ResponseType.NO_MATCHES_FOUND
            
            best_match = analysis.best_match
            
            # Check for exact matches first
            exact_matches = [m for m in analysis.matched_products if m.match_type == MatchType.EXACT_MATCH]
            if exact_matches and best_match.match_type == MatchType.EXACT_MATCH:
                return ResponseType.EXACT_MATCH_FOUND
            
            # Check for color variants
            color_variants = [m for m in analysis.matched_products if m.match_type == MatchType.COLOR_VARIANT]
            if color_variants and best_match.match_type == MatchType.COLOR_VARIANT:
                return ResponseType.COLOR_VARIANT_FOUND
            
            # Check for similar products
            similar_products = [m for m in analysis.matched_products if m.match_type == MatchType.SIMILAR_PRODUCT]
            if similar_products and best_match.match_type == MatchType.SIMILAR_PRODUCT:
                return ResponseType.SIMILAR_PRODUCTS_FOUND
            
            # Check for related products
            related_products = [m for m in analysis.matched_products if m.match_type == MatchType.RELATED_PRODUCT]
            if related_products and best_match.match_type == MatchType.RELATED_PRODUCT:
                return ResponseType.RELATED_PRODUCTS_FOUND
            
            # Default to no matches if confidence is too low
            if best_match.confidence_score < self.confidence_thresholds["low"]:
                return ResponseType.NO_MATCHES_FOUND
            
            return ResponseType.SIMILAR_PRODUCTS_FOUND
            
        except Exception as e:
            logger.error(f"Error classifying matches: {e}")
            return ResponseType.ERROR_RESPONSE
    
    def get_match_summary(self, analysis: ProductMatchAnalysis) -> str:
        """Generate a summary of the match analysis."""
        try:
            if not analysis.matched_products:
                return "No matching products found"
            
            exact_count = sum(1 for m in analysis.matched_products if m.match_type == MatchType.EXACT_MATCH)
            color_count = sum(1 for m in analysis.matched_products if m.match_type == MatchType.COLOR_VARIANT)
            similar_count = sum(1 for m in analysis.matched_products if m.match_type == MatchType.SIMILAR_PRODUCT)
            related_count = sum(1 for m in analysis.matched_products if m.match_type == MatchType.RELATED_PRODUCT)
            
            summary_parts = []
            if exact_count > 0:
                summary_parts.append(f"{exact_count} exact match(es)")
            if color_count > 0:
                summary_parts.append(f"{color_count} color variant(s)")
            if similar_count > 0:
                summary_parts.append(f"{similar_count} similar product(s)")
            if related_count > 0:
                summary_parts.append(f"{related_count} related product(s)")
            
            return f"Found: {', '.join(summary_parts)}"
            
        except Exception as e:
            logger.error(f"Error generating match summary: {e}")
            return "Match analysis completed"

class SmartResponseGenerator:
    """Production-level smart response generation system."""
    
    def __init__(self):
        """Initialize the response generator."""
        logger.info("💬 SmartResponseGenerator initialized")
    
    def generate_response(
        self,
        analysis: ProductMatchAnalysis,
        response_type: ResponseType
    ) -> SmartResponse:
        """
        Generate intelligent, context-aware response based on match analysis.
        
        Args:
            analysis: Complete product match analysis
            response_type: Classified response type
            
        Returns:
            SmartResponse with intelligent messaging
        """
        try:
            if response_type == ResponseType.EXACT_MATCH_FOUND:
                return self._generate_exact_match_response(analysis)
            elif response_type == ResponseType.COLOR_VARIANT_FOUND:
                return self._generate_color_variant_response(analysis)
            elif response_type == ResponseType.SIMILAR_PRODUCTS_FOUND:
                return self._generate_similar_products_response(analysis)
            elif response_type == ResponseType.RELATED_PRODUCTS_FOUND:
                return self._generate_related_products_response(analysis)
            elif response_type == ResponseType.NO_MATCHES_FOUND:
                return self._generate_no_matches_response(analysis)
            else:
                return self._generate_error_response(analysis)
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self._generate_error_response(analysis)
    
    def _generate_exact_match_response(self, analysis: ProductMatchAnalysis) -> SmartResponse:
        """Generate response for exact matches."""
        best_match = analysis.best_match
        exact_matches = [m for m in analysis.matched_products if m.match_type == MatchType.EXACT_MATCH]
        
        if len(exact_matches) == 1:
            primary_message = f"🎯 Perfect! Yeh exact same product hai jo aapne image mein dikhaya hai!\n\n**{best_match.product_title}**\n\n{best_match.customer_message}"
            secondary_message = f"✅ Exact Match Found!\n💰 Price: ₹{self._get_product_price(exact_matches[0])}\n🎨 Available Colors: {self._get_available_colors(exact_matches[0])}"
        else:
            primary_message = f"🎯 Excellent! Maine {len(exact_matches)} exact same products dhoondh liye hain!\n\nSabse pehle: **{best_match.product_title}**\n\n{best_match.customer_message}"
            secondary_message = f"✅ {len(exact_matches)} Exact Matches Found!\n💰 Starting from: ₹{self._get_product_price(best_match)}\n🎨 Multiple color options available"
        
        suggested_actions = [
            "Order this exact product",
            "Check other exact matches",
            "Ask about availability",
            "Get more details"
        ]
        
        return SmartResponse(
            response_type=ResponseType.EXACT_MATCH_FOUND,
            primary_message=primary_message,
            secondary_message=secondary_message,
            product_cards_to_show=self._convert_matches_to_products(exact_matches),
            suggested_actions=suggested_actions,
            confidence_level=best_match.confidence.value,
            match_summary=f"{len(exact_matches)} exact match(es) found"
        )
    
    def _generate_color_variant_response(self, analysis: ProductMatchAnalysis) -> SmartResponse:
        """Generate response for color variants."""
        best_match = analysis.best_match
        color_variants = [m for m in analysis.matched_products if m.match_type == MatchType.COLOR_VARIANT]
        
        primary_message = f"🎨 Great! Yeh same product hai, bas color different hai!\n\n**{best_match.product_title}**\n\n{best_match.customer_message}"
        
        if best_match.color_difference:
            secondary_message = f"✅ Same Product, Different Color!\n🎨 Color Difference: {best_match.color_difference}\n💰 Price: ₹{self._get_product_price(best_match)}\n🌈 Available in multiple colors"
        else:
            secondary_message = f"✅ Same Product, Different Color!\n💰 Price: ₹{self._get_product_price(best_match)}\n🌈 Available in multiple colors"
        
        suggested_actions = [
            "See all color options",
            "Order in preferred color",
            "Check availability",
            "Compare with original"
        ]
        
        return SmartResponse(
            response_type=ResponseType.COLOR_VARIANT_FOUND,
            primary_message=primary_message,
            secondary_message=secondary_message,
            product_cards_to_show=self._convert_matches_to_products(color_variants),
            suggested_actions=suggested_actions,
            confidence_level=best_match.confidence.value,
            match_summary=f"{len(color_variants)} color variant(s) found"
        )
    
    def _generate_similar_products_response(self, analysis: ProductMatchAnalysis) -> SmartResponse:
        """Generate response for similar products."""
        best_match = analysis.best_match
        similar_products = [m for m in analysis.matched_products if m.match_type == MatchType.SIMILAR_PRODUCT]
        
        primary_message = f"👀 Perfect! Main aapke image jaisi similar products dhoondh payi hoon!\n\n**{best_match.product_title}**\n\n{best_match.customer_message}"
        
        if best_match.feature_differences:
            secondary_message = f"✅ Similar Products Found!\n🔧 Key Differences: {', '.join(best_match.feature_differences[:2])}\n💰 Price: ₹{self._get_product_price(best_match)}\n🎯 {len(similar_products)} similar options available"
        else:
            secondary_message = f"✅ Similar Products Found!\n💰 Price: ₹{self._get_product_price(best_match)}\n🎯 {len(similar_products)} similar options available"
        
        suggested_actions = [
            "See all similar products",
            "Compare features",
            "Check specifications",
            "Ask about differences"
        ]
        
        return SmartResponse(
            response_type=ResponseType.SIMILAR_PRODUCTS_FOUND,
            primary_message=primary_message,
            secondary_message=secondary_message,
            product_cards_to_show=self._convert_matches_to_products(similar_products),
            suggested_actions=suggested_actions,
            confidence_level=best_match.confidence.value,
            match_summary=f"{len(similar_products)} similar product(s) found"
        )
    
    def _generate_related_products_response(self, analysis: ProductMatchAnalysis) -> SmartResponse:
        """Generate response for related products."""
        best_match = analysis.best_match
        related_products = [m for m in analysis.matched_products if m.match_type == MatchType.RELATED_PRODUCT]
        
        primary_message = f"🔍 Main aapke image se related products dhoondh payi hoon!\n\n**{best_match.product_title}**\n\n{best_match.customer_message}"
        
        secondary_message = f"✅ Related Products Found!\n💰 Price: ₹{self._get_product_price(best_match)}\n🎯 {len(related_products)} related options available\n💡 These are in the same category"
        
        suggested_actions = [
            "See all related products",
            "Browse this category",
            "Get recommendations",
            "Ask for alternatives"
        ]
        
        return SmartResponse(
            response_type=ResponseType.RELATED_PRODUCTS_FOUND,
            primary_message=primary_message,
            secondary_message=secondary_message,
            product_cards_to_show=self._convert_matches_to_products(related_products),
            suggested_actions=suggested_actions,
            confidence_level=best_match.confidence.value,
            match_summary=f"{len(related_products)} related product(s) found"
        )
    
    def _generate_no_matches_response(self, analysis: ProductMatchAnalysis) -> SmartResponse:
        """Generate response when no matches are found."""
        user_analysis = analysis.user_image_analysis
        
        primary_message = f"😔 Sorry, main aapki image jaisa exact product nahi dhoondh payi.\n\nLekin main help kar sakti hoon! 😊"
        
        secondary_message = f"🔍 Aapka image analysis:\n• Product Type: {user_analysis.get('product_type', 'Unknown')}\n• Colors: {', '.join(user_analysis.get('colors', []))}\n• Features: {', '.join(user_analysis.get('key_features', [])[:2])}\n\nKya aap text mein describe kar sakte hain?"
        
        suggested_actions = [
            "Describe in text",
            "Try different image",
            "Browse categories",
            "Contact support"
        ]
        
        return SmartResponse(
            response_type=ResponseType.NO_MATCHES_FOUND,
            primary_message=primary_message,
            secondary_message=secondary_message,
            product_cards_to_show=[],
            suggested_actions=suggested_actions,
            confidence_level="very_low",
            match_summary="No matching products found"
        )
    
    def _generate_error_response(self, analysis: ProductMatchAnalysis) -> SmartResponse:
        """Generate error response."""
        primary_message = "😔 Sorry, main aapki image process nahi kar payi. Kya aap dobara try kar sakte hain?"
        secondary_message = "Please try:\n• Different image\n• Text description\n• Contact support"
        
        suggested_actions = [
            "Try different image",
            "Describe in text",
            "Contact support"
        ]
        
        return SmartResponse(
            response_type=ResponseType.ERROR_RESPONSE,
            primary_message=primary_message,
            secondary_message=secondary_message,
            product_cards_to_show=[],
            suggested_actions=suggested_actions,
            confidence_level="very_low",
            match_summary="Error in processing"
        )
    
    def _get_product_price(self, match: VisualMatchResult) -> str:
        """Get formatted price for a product match."""
        # This would need to be connected to the actual product data
        # For now, return a placeholder
        return "Check product card"
    
    def _get_available_colors(self, match: VisualMatchResult) -> str:
        """Get available colors for a product match."""
        # This would need to be connected to the actual product data
        # For now, return a placeholder
        return "Multiple colors"
    
    def _convert_matches_to_products(self, matches: List[VisualMatchResult]) -> List[Dict[str, Any]]:
        """Convert visual match results to product format for display."""
        products = []
        for match in matches:
            # This would need to be connected to the actual product data
            # For now, create a basic structure
            product = {
                "product_id": match.product_id,
                "title": match.product_title,
                "match_type": match.match_type.value,
                "confidence": match.confidence.value,
                "customer_message": match.customer_message,
                "explanation": match.explanation
            }
            products.append(product)
        
        return products


class ProductionImageMatchingSystem:
    """Complete production-level image matching system."""
    
    def __init__(self, visual_verification_system, gemini_api_key: str):
        """Initialize the complete system."""
        self.visual_verification = visual_verification_system
        self.match_classifier = IntelligentMatchClassifier()
        self.response_generator = SmartResponseGenerator()
        
        logger.info("🚀 ProductionImageMatchingSystem initialized")
    
    async def process_image_search(
        self,
        user_image_path: str,
        database_products: List[Dict[str, Any]],
        user_analysis: Optional[Dict[str, Any]] = None
    ) -> Tuple[SmartResponse, List[Dict[str, Any]]]:
        """
        Complete production-level image search processing.
        
        Args:
            user_image_path: Path to user's image
            database_products: Products from database search
            user_analysis: Optional pre-analyzed user image data
            
        Returns:
            Tuple of (SmartResponse, products_to_show)
        """
        try:
            logger.info(f"🚀 Starting production-level image search processing")
            
            # Step 1: Analyze user image (if not already provided)
            if not user_analysis:
                logger.info("🔍 Analyzing user image...")
                user_analysis = await self.visual_verification.analyze_user_image(user_image_path)
                if not user_analysis:
                    logger.error("Failed to analyze user image")
                    return self.response_generator._generate_error_response(None), []
            else:
                logger.info("✅ Using pre-analyzed user image data")
            
            # Step 2: Perform visual verification with database products
            logger.info("🔍 Performing visual verification...")
            analysis = await self.visual_verification.analyze_product_matches(
                user_image_path,
                database_products,
                user_analysis
            )
            
            # Step 3: Classify matches intelligently
            response_type = self.match_classifier.classify_matches(analysis)
            
            # Step 4: Generate smart response
            smart_response = self.response_generator.generate_response(analysis, response_type)
            
            logger.info(f"✅ Production-level processing completed: {response_type.value}")
            
            return smart_response, smart_response.product_cards_to_show
            
        except Exception as e:
            logger.error(f"Error in production-level image search: {e}", exc_info=True)
            return self.response_generator._generate_error_response(None), []


# Global instances
_match_classifier_instance: Optional[IntelligentMatchClassifier] = None
_response_generator_instance: Optional[SmartResponseGenerator] = None
_production_system_instance: Optional[ProductionImageMatchingSystem] = None

def initialize_intelligent_systems(visual_verification_system, gemini_api_key: str):
    """Initialize all intelligent systems."""
    global _match_classifier_instance, _response_generator_instance, _production_system_instance
    
    _match_classifier_instance = IntelligentMatchClassifier()
    _response_generator_instance = SmartResponseGenerator()
    _production_system_instance = ProductionImageMatchingSystem(visual_verification_system, gemini_api_key)
    
    logger.info("🧠 All intelligent systems initialized")

def get_production_system() -> Optional[ProductionImageMatchingSystem]:
    """Get the production image matching system."""
    return _production_system_instance
