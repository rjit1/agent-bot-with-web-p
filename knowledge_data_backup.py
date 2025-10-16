"""
Standalone knowledge data for Gurtoy Telegram Bot
"""

def get_knowledge_chunks():
    """Return all knowledge chunks as dictionaries."""
    return [
        {
            "chunk_id": "company_overview",
            "title": "Gurtoy Company Overview",
            "content": "Gurtoy is a premium toy store and retailer established as a leading toy retailer in the Ludhiana region. We specialize in children's toys, educational products, ride-on toys, and outdoor play equipment. Our mission is bringing joy and learning to children through quality toys. We serve families with children aged 0-12+ years with geographic coverage in Ludhiana, Punjab, and Pan-India shipping.",
            "category": "company_info",
            "keywords": ["gurtoy", "company", "overview", "toy store", "ludhiana", "premium", "children", "toys"],
            "priority": 1
        },
        {
            "chunk_id": "owner_management",
            "title": "Gurtoy Ownership and Management",
            "content": "Gurtoy is owned by Kawardeep Singh Khurana. Our business philosophy focuses on quality toys for child development and happiness. We provide family-oriented service with personalized attention, backed by years of expertise in toy retail and child development products.",
            "category": "company_info",
            "keywords": ["owner", "kawardeep", "singh", "khurana", "management", "philosophy", "quality"],
            "priority": 1
        },
        {
            "chunk_id": "product_categories",
            "title": "Gurtoy Product Categories",
            "content": "Our product range includes: Educational Toys (puzzles, STEM kits, learning games), Ride-on Toys (cars, bikes, scooters, electric vehicles), Outdoor Play Equipment (swings, slides, trampolines), Indoor Games (board games, card games, building blocks), Electronic Toys (remote control toys, interactive games), Soft Toys (stuffed animals, plush toys), Art & Craft Supplies (drawing kits, craft materials), Sports Equipment (balls, bats, outdoor sports gear).",
            "category": "products",
            "keywords": ["products", "toys", "educational", "ride-on", "outdoor", "indoor", "electronic", "soft toys", "art", "craft", "sports"],
            "priority": 1
        },
        {
            "chunk_id": "age_groups",
            "title": "Age-Appropriate Toy Categories",
            "content": "Age 0-2 years: Soft toys, rattles, teething toys, sensory toys, musical toys. Age 2-5 years: Building blocks, simple puzzles, ride-on toys, pretend play sets, educational games. Age 5-8 years: Advanced puzzles, STEM kits, board games, outdoor sports equipment, art supplies. Age 8-12+ years: Complex building sets, electronic toys, advanced board games, sports equipment, hobby kits.",
            "category": "products",
            "keywords": ["age groups", "0-2 years", "2-5 years", "5-8 years", "8-12 years", "development", "appropriate"],
            "priority": 2
        },
        {
            "chunk_id": "store_location",
            "title": "Gurtoy Store Location and Contact",
            "content": "Physical Store: Located in Ludhiana, Punjab. We welcome walk-in customers for hands-on toy selection and expert advice. Contact Information: Phone: Available for inquiries and orders. Operating Hours: Standard retail hours, customer service available during business hours. We provide personalized service and expert toy recommendations.",
            "category": "contact_info",
            "keywords": ["location", "ludhiana", "punjab", "store", "contact", "phone", "hours", "visit"],
            "priority": 2
        },
        {
            "chunk_id": "online_services",
            "title": "Online Services and Shipping",
            "content": "Online Ordering: Available for customers across India. Shipping: Pan-India shipping available with reliable delivery partners. Local Delivery: Special delivery services in Ludhiana area. Customer Support: Online and phone support for product selection and order assistance. We ensure safe packaging and timely delivery of all toy orders.",
            "category": "services",
            "keywords": ["online", "shipping", "pan-india", "delivery", "ludhiana", "support", "packaging"],
            "priority": 2
        },
        {
            "chunk_id": "safety_quality",
            "title": "Toy Safety and Quality Standards",
            "content": "All toys meet international safety standards including BIS (Bureau of Indian Standards) certification where applicable. We prioritize non-toxic materials, age-appropriate design, and durability testing. Quality assurance includes regular supplier audits and customer feedback integration. Safety features include rounded edges, secure small parts, and clear age recommendations.",
            "category": "quality",
            "keywords": ["safety", "quality", "standards", "BIS", "certification", "non-toxic", "durability", "testing"],
            "priority": 2
        },
        {
            "chunk_id": "educational_benefits",
            "title": "Educational Benefits of Our Toys",
            "content": "Our educational toys promote: Cognitive Development (problem-solving, memory, logical thinking), Motor Skills (fine and gross motor development), Creativity (imagination, artistic expression), Social Skills (sharing, cooperation, communication), STEM Learning (science, technology, engineering, mathematics), Language Development (vocabulary, reading, communication skills).",
            "category": "education",
            "keywords": ["educational", "cognitive", "motor skills", "creativity", "social", "STEM", "language", "development"],
            "priority": 3
        },
        {
            "chunk_id": "popular_brands",
            "title": "Popular Toy Brands at Gurtoy",
            "content": "We stock toys from leading brands known for quality and safety. Our selection includes both international and domestic brands that meet our quality standards. Brand selection is based on safety certifications, educational value, durability, and customer satisfaction. We regularly update our brand portfolio based on market trends and customer feedback.",
            "category": "products",
            "keywords": ["brands", "quality", "safety", "international", "domestic", "selection", "trends"],
            "priority": 3
        },
        {
            "chunk_id": "seasonal_special",
            "title": "Seasonal and Special Occasion Toys",
            "content": "Special collections for: Birthday Gifts (age-appropriate selections, gift wrapping available), Festival Seasons (Diwali, Christmas, Holi special toys), Back-to-School (educational supplies, learning aids), Summer Holidays (outdoor toys, water play equipment), Winter Indoor Activities (board games, craft kits, puzzles). Custom gift recommendations available.",
            "category": "seasonal",
            "keywords": ["seasonal", "birthday", "festival", "diwali", "christmas", "school", "summer", "winter", "gifts"],
            "priority": 3
        },
        {
            "chunk_id": "customer_service",
            "title": "Customer Service and Support",
            "content": "Our customer service includes: Pre-purchase consultation for toy selection, Age-appropriate recommendations, Product demonstrations (in-store), After-sales support and warranty assistance, Return and exchange policies, Bulk order services for schools and institutions, Gift wrapping and special packaging services.",
            "category": "services",
            "keywords": ["customer service", "consultation", "recommendations", "demonstrations", "warranty", "returns", "bulk orders", "gift wrapping"],
            "priority": 2
        },
        {
            "chunk_id": "pricing_value",
            "title": "Pricing and Value Proposition",
            "content": "Competitive pricing with focus on value for money. Regular promotions and seasonal discounts available. Bulk purchase discounts for schools and institutions. Price matching policy for identical products. Transparent pricing with no hidden costs. Quality assurance ensures long-term value and durability of purchases.",
            "category": "pricing",
            "keywords": ["pricing", "competitive", "value", "promotions", "discounts", "bulk", "transparent", "quality"],
            "priority": 3
        },
        {
            "chunk_id": "expert_advice",
            "title": "Expert Toy Selection Advice",
            "content": "Our team provides expert guidance on: Developmental appropriateness for different ages, Educational value and learning outcomes, Safety considerations and certifications, Durability and long-term value, Gender-neutral and inclusive toy options, Special needs considerations, Budget-friendly alternatives without compromising quality.",
            "category": "advice",
            "keywords": ["expert", "advice", "developmental", "educational", "safety", "durability", "inclusive", "special needs", "budget"],
            "priority": 2
        },
        {
            "chunk_id": "community_engagement",
            "title": "Community Engagement and Social Responsibility",
            "content": "Gurtoy actively engages with the local community through: Educational workshops on child development and play, Partnerships with local schools and daycare centers, Toy donation drives for underprivileged children, Environmental responsibility through eco-friendly packaging, Supporting local artisans and toy makers, Promoting traditional Indian games and toys.",
            "category": "community",
            "keywords": ["community", "workshops", "schools", "donations", "environmental", "eco-friendly", "artisans", "traditional", "indian games"],
            "priority": 4
        },
        {
            "chunk_id": "future_expansion",
            "title": "Future Plans and Expansion",
            "content": "Our growth plans include: Expanding product range with latest educational toys, Enhanced online presence and e-commerce capabilities, Additional service locations in Punjab region, Partnerships with international toy brands, Development of exclusive Gurtoy-branded products, Integration of technology in toy retail experience.",
            "category": "future",
            "keywords": ["expansion", "growth", "online", "e-commerce", "punjab", "international", "exclusive", "technology"],
            "priority": 5
        }
    ]