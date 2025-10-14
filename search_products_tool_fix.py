    def _create_search_products_tool(self) -> Dict[str, Any]:
        """Create the product search function tool."""
        return {
            "name": "search_products",
            "description": "REQUIRED: Search Gurtoy's product catalog for specific toys and ride-on vehicles. MUST be called IMMEDIATELY when users mention: specific product names/IDs (g63, 2188, police bike), product types (red jeep, electric scooter, bike with lights), or specific features. DO NOT ask questions first for specific product queries - search immediately! Only ask questions for vague queries like 'show me toys' or 'kuch dikhao'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Product search query. IMPORTANT: Always include age information in the query string itself (e.g., 'jeep for 5 year old child', 'bike for 3 to 7 year old', 'scooter for toddler'). Do NOT use the age_range parameter. Examples: 'red jeep for 4 year old', 'bike with lights for 6 year old', 'police style toys for 5 year old', 'scooter under 15000 for 3 year old'"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["Electric Bikes & Scooters for Kids", "Electric Ride-On Jeeps & Cars for Kids", "Petrol Bike & Cars for Kids", "E-Scooter For Kids & Adults", "all"],
                        "description": "Product category filter. Use 'all' for general search. Default: 'all'"
                    },
                    "min_price": {
                        "type": "number",
                        "description": "Minimum price filter in rupees (optional)"
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum price filter in rupees (optional)"
                    }
                },
                "required": ["query"]
            }
        }
