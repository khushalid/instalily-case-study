# backend/tools_config.py (MODIFIED)

DB_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_part_details",
            "description": "Get detailed information about a specific appliance part using its PartSelect number. Use this tool if the user asks for information about a part like its description, price, availability, or manufacturer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_number": {
                        "type": "string",
                        "description": "The PartSelect part number, typically starting with 'PS' followed by digits (e.g., 'PS11752778')."
                    }
                },
                "required": ["part_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_compatibility",
            "description": "Check if a specific appliance part is compatible with a given appliance model number. Use this if the user asks 'Is this part compatible with my model X?'",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_number": {
                        "type": "string",
                        "description": "The PartSelect part number (e.g., 'PS11752778')."
                    },
                    "model_number": {
                        "type": "string",
                        "description": "The appliance model number (e.g., 'WDT780SAEM1')."
                    }
                },
                "required": ["part_number", "model_number"]
            }
        }
    },
    # --- NEW: Split get_installation_guide into two specific functions ---
    {
        "type": "function",
        "function": {
            "name": "get_installation_guide_by_part",
            "description": "Retrieve installation instructions or repair guides for a specific part by its PartSelect number. Can also search for 'Troubleshooting' guides related to a part. Use this if the user asks 'How do I install part X?' or 'How can I fix Y related to part Z?'",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_number": {
                        "type": "string",
                        "description": "The PartSelect part number (e.g., 'PS11752778')."
                    },
                    "guide_type": {
                        "type": "string",
                        "description": "The type of guide to retrieve (e.g., 'Installation', 'Troubleshooting', 'Repair'). Defaults to 'Installation'.",
                        "enum": ["Installation", "Troubleshooting", "Repair", "Guide"]
                    }
                },
                "required": ["part_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_installation_guide_by_model",
            "description": "Retrieve installation instructions or repair guides for a specific appliance model. Can also search for 'Troubleshooting' guides related to a model. Use this if the user asks 'How do I fix issues with model X?' or 'Can I get a guide for model Y?'",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_number": {
                        "type": "string",
                        "description": "The appliance model number (e.g., 'WDT780SAEM1')."
                    },
                    "guide_type": {
                        "type": "string",
                        "description": "The type of guide to retrieve (e.g., 'Installation', 'Troubleshooting', 'Repair'). Defaults to 'Installation'.",
                        "enum": ["Installation", "Troubleshooting", "Repair", "Guide"]
                    }
                },
                "required": ["model_number"]
            }
        }
    },
    # The troubleshoot_appliance tool remains the same
    {
        "type": "function",
        "function": {
            "name": "troubleshoot_appliance",
            "description": "Provide troubleshooting steps or common fixes for a specific appliance symptom. Use this if the user describes a problem with their refrigerator or dishwasher.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appliance_type": {
                        "type": "string",
                        "description": "The type of appliance the symptom applies to (e.g., 'Refrigerator', 'Dishwasher').",
                        "enum": ["Refrigerator", "Dishwasher"] # Constrain to our scope
                    },
                    "symptom": {
                        "type": "string",
                        "description": "A concise description of the appliance problem (e.g., 'ice maker not working', 'leaking water', 'dishes not cleaning')."
                    }
                },
                "required": ["appliance_type", "symptom"]
            }
        }
    },
    # Web search tool
    {
        "type": "function",
        "function": {
            "name": "perform_partselect_web_search",
            "description": "Searches the PartSelect.com website for parts, models, or brands when specific information is not found in the internal database. This tool is a fallback when other specific database lookups fail, or for general queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search term (e.g., 'Whirlpool ice maker', 'oven temperature sensor')."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional: The maximum number of top results to retrieve for each category (parts, models, brands). Defaults to 5."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "semantic_search",
            "description": "Performs a deep, semantic search within the database for parts or guides based on a natural language query or symptom. Use this when the user's query is vague, doesn't contain exact part/model numbers, or describes a problem (e.g., 'noisy fridge', 'my dishwasher isn't cleaning'). Can be narrowed by appliance type.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The natural language query or symptom to search for (e.g., 'ice maker not making ice', 'drawer keeps falling out', 'part for water dispenser')."
                    },
                    "appliance_type": {
                        "type": "string",
                        "description": "Optional: The type of appliance to narrow the search (e.g., 'Refrigerator', 'Dishwasher').",
                        "enum": ["Refrigerator", "Dishwasher"]
                    },
                    "search_limit": {
                        "type": "integer",
                        "description": "Optional: The maximum number of top semantic results to retrieve for parts and guides. Defaults to 5.",
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_models",
            "description": "Compares two appliance models and provides their differences based on available specifications, brand, and type. Use this when the user explicitly asks to compare two models (e.g., 'What's the difference between model X and model Y?', 'Compare model A and B').",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_number_1": {
                        "type": "string",
                        "description": "The model number of the first appliance to compare (e.g., 'GFSS2HCYCSS')."
                    },
                    "model_number_2": {
                        "type": "string",
                        "description": "The model number of the second appliance to compare (e.g., 'LFX28968ST')."
                    }
                },
                "required": ["model_number_1", "model_number_2"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_parts",
            "description": "Compares two appliance parts and provides their differences based on available details like name, description, price, and availability. Use this when the user explicitly asks to compare two parts (e.g., 'What's the difference between part X and part Y?', 'Compare part A and B').",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_number_1": {
                        "type": "string",
                        "description": "The PartSelect number of the first part to compare (e.g., 'PS11752778')."
                    },
                    "part_number_2": {
                        "type": "string",
                        "description": "The PartSelect number of the second part to compare (e.g., 'PS429871')."
                    }
                },
                "required": ["part_number_1", "part_number_2"]
            }
        }
    },
]