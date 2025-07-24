# backend/web_search_service.py

import requests
import json
from urllib.parse import quote_plus, urljoin
import time
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://www.partselect.com/"
PARTSELECT_SEARCH_API_URL = urljoin(BASE_URL, "api/search/")

# Headers to mimic a browser, similar to scraper.py
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1', # Do Not Track request header
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

def perform_partselect_web_search(query: str, limit: int = 5) -> dict:
    """
    Performs a search on PartSelect.com's internal search API
    and extracts relevant product, model, and brand information.

    Args:
        query (str): The search term provided by the user or derived from context.
        limit (int): Maximum number of top results to return for each category.

    Returns:
        dict: A dictionary containing structured search results (parts, models, brands).
              Returns an empty dictionary or a message if no results or on error.
    """
    if not query:
        return {"status": "error", "message": "Search query cannot be empty."}

    encoded_query = quote_plus(query)
    search_url = f"{PARTSELECT_SEARCH_API_URL}?searchterm={encoded_query}"

    print(f"\n--- Performing PartSelect Web Search for: '{query}' ---")
    print(f"  URL: {search_url}")

    try:
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        search_results = response.json()
        print(f"  Search API responded successfully. Processing results.")
        # print(json.dumps(search_results, indent=2)) # Uncomment for full debug of raw API response

        # --- Parse Search Results ---
        parsed_results = {
            "query": query,
            "parts": [],
            "models": [],
            "brands": [],
            "total_results": 0,
            "message": "No specific results found within categories."
        }

        # The 'totalResults' field directly in the API response
        parsed_results['total_results'] = search_results.get('totalResults', 0)

        # Parts (often under a key like 'products' or 'parts')
        # Based on typical search APIs, assume a 'products' list, each with 'partNumber', 'name', 'productPageUrl', etc.
        products = search_results.get('products', [])
        for product in products[:limit]:
            part_data = {
                "part_number": product.get('partNumber'),
                "name": product.get('name'),
                "product_page_url": urljoin(BASE_URL, product.get('productPageUrl', '')),
                "price": product.get('salePrice') or product.get('price'), # Check both sale and regular price
                "availability": product.get('availabilityStatus'),
                "image_url": urljoin(BASE_URL, product.get('thumbnailImage', '')) if product.get('thumbnailImage') else None
            }
            # Clean up if any essential data is missing
            if part_data['part_number'] and part_data['name'] and part_data['product_page_url']:
                parsed_results['parts'].append(part_data)
        
        # Models (often under a key like 'models')
        models = search_results.get('models', [])
        for model in models[:limit]:
            model_data = {
                "model_number": model.get('modelNumber'),
                "name": model.get('modelName'), # Or 'modelDescription'
                "model_page_url": urljoin(BASE_URL, model.get('modelPageUrl', ''))
            }
            if model_data['model_number'] and model_data['model_page_url']:
                parsed_results['models'].append(model_data)

        # Brands (often under a key like 'brands')
        brands = search_results.get('brands', [])
        for brand in brands[:limit]:
            brand_data = {
                "name": brand.get('brandName'),
                "brand_page_url": urljoin(BASE_URL, brand.get('brandPageUrl', ''))
            }
            if brand_data['name'] and brand_data['brand_page_url']:
                parsed_results['brands'].append(brand_data)

        if parsed_results['parts'] or parsed_results['models'] or parsed_results['brands']:
            parsed_results['message'] = f"Found {parsed_results['total_results']} total results. Here are some top matches:"
        else:
            parsed_results['message'] = f"No specific products, models, or brands found for '{query}' in web search results."

        return {"status": "success", "results": parsed_results}

    except requests.exceptions.RequestException as e:
        print(f"Network or HTTP error during web search for '{query}': {e}")
        return {"status": "error", "message": f"Could not perform web search due to a network error: {e}"}
    except json.JSONDecodeError as e:
        print(f"JSON parsing error for web search results for '{query}': {e}")
        print(f"Raw response content: {response.text[:500]}...") # Print a snippet of raw response
        return {"status": "error", "message": "Could not parse web search results."}
    except Exception as e:
        print(f"An unexpected error occurred during web search for '{query}': {e}")
        return {"status": "error", "message": "An unexpected error occurred during web search."}
    finally:
        time.sleep(2) # Be polite to the search API too