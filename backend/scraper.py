# backend/scraper.py

import requests
from bs4 import BeautifulSoup
import time
import re
import os
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urljoin # Useful for handling relative URLs

# Load environment variables (for DB credentials)
load_dotenv()

# --- Database Configuration ---
DB_NAME = os.getenv("PG_DB_NAME")
DB_USER = os.getenv("PG_DB_USER")
DB_PASSWORD = os.getenv("PG_DB_PASSWORD")
DB_HOST = os.getenv("PG_DB_HOST")
DB_PORT = os.getenv("PG_DB_PORT")

# --- Global Configuration ---
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
# HEADERS = {
#     'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'

# }
BASE_URL = "https://www.partselect.com/"

# Mapping for dynamic URL generation
APPLIANCE_URLS = {
    "Refrigerator": urljoin(BASE_URL, "Refrigerator-Parts.htm"),
    # IMPORTANT: Need the actual URL for Dishwasher here
    "Dishwasher": urljoin(BASE_URL, "Dishwasher-Parts.htm"), # <<< CONFIRM THIS URL
}
def get_db_connection():
    """Establishes and returns a database connection."""
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def insert_or_get_appliance_type(appliance_name):
    """Inserts appliance type if not exists, returns its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO ApplianceType (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id;", (appliance_name,))
        appliance_id = cursor.fetchone()[0]
        conn.commit()
        return appliance_id
    except Exception as e:
        conn.rollback()
        print(f"Error inserting/getting appliance type {appliance_name}: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def insert_or_get_brand(brand_name):
    """Inserts brand if not exists, returns its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Brand (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id;", (brand_name,))
        brand_id = cursor.fetchone()[0]
        conn.commit()
        return brand_id
    except Exception as e:
        conn.rollback()
        print(f"Error inserting/getting brand {brand_name}: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def insert_or_update_model(model_data):
    """Inserts or updates a model, returns its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO Model (model_number, appliance_type_id, brand_id, description, model_page_url)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (model_number) DO UPDATE SET
                appliance_type_id = EXCLUDED.appliance_type_id,
                brand_id = EXCLUDED.brand_id,
                description = EXCLUDED.description,
                model_page_url = EXCLUDED.model_page_url
            RETURNING id;
            """,
            (model_data['model_number'], model_data.get('appliance_type_id'),
             model_data.get('brand_id'), model_data.get('description'),
             model_data.get('model_page_url'))
        )
        model_id = cursor.fetchone()[0]
        conn.commit()
        return model_id
    except Exception as e:
        conn.rollback()
        print(f"Error inserting/updating model {model_data.get('model_number')}: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def insert_or_update_part(part_data):
    """Inserts or updates a part, returns its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO Part (part_number, manufacturer_part_number, name, description, price_usd,
                              availability_status, image_url, product_page_url, appliance_type_id, category, installation_guides, troubleshooting_guides)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (part_number) DO UPDATE SET
                manufacturer_part_number = EXCLUDED.manufacturer_part_number,
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                price_usd = EXCLUDED.price_usd,
                availability_status = EXCLUDED.availability_status,
                image_url = EXCLUDED.image_url,
                product_page_url = EXCLUDED.product_page_url,
                appliance_type_id = EXCLUDED.appliance_type_id,
                category = EXCLUDED.category,
                installation_guides = EXCLUDED.installation_guides,
                troubleshooting_guides = EXCLUDED.troubleshooting_guides
            RETURNING id;
            """,
            (part_data['part_number'], part_data.get('manufacturer_part_number'), part_data['name'],
             part_data.get('description'), part_data.get('price_usd'), part_data.get('availability_status'),
             part_data.get('image_url'), part_data.get('product_page_url'),
             part_data.get('appliance_type_id'), part_data.get('category'),
             part_data.get('installation_instructions_summary'), part_data.get('troubleshooting_summary'))
        )
        part_id = cursor.fetchone()[0]
        conn.commit()
        return part_id
    except Exception as e:
        conn.rollback()
        print(f"Error inserting/updating part {part_data.get('part_number')}: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def insert_part_compatibility(part_id, model_id):
    """Inserts a compatibility record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO PartCompatibility (part_id, model_id)
            VALUES (%s, %s)
            ON CONFLICT (part_id, model_id) DO NOTHING;
            """,
            (part_id, model_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error inserting compatibility for part {part_id} with model {model_id}: {e}")
    finally:
        cursor.close()
        conn.close()

def insert_or_update_guide(guide_data):
    """Inserts or updates an installation/troubleshooting guide."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO InstallationGuide (part_id, model_id, title, guide_text, guide_url, type)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (guide_url) DO UPDATE SET
                title = EXCLUDED.title,
                guide_text = EXCLUDED.guide_text,
                part_id = COALESCE(EXCLUDED.part_id, InstallationGuide.part_id),
                model_id = COALESCE(EXCLUDED.model_id, InstallationGuide.model_id),
                type = EXCLUDED.type
            RETURNING id;
            """,
            (guide_data.get('part_id'), guide_data.get('model_id'), guide_data['title'],
             guide_data.get('guide_text'), guide_data['guide_url'], guide_data['type'])
        )
        guide_id = cursor.fetchone()[0]
        conn.commit()
        return guide_id
    except Exception as e:
        conn.rollback()
        print(f"Error inserting/updating guide {guide_data.get('guide_url')}: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

# --- Utility Function for Fetching Pages ---
def fetch_page(url, retries=3, delay=3): # Keep delay at 3 or more seconds
    """Fetches a URL with retries and a delay."""
    for i in range(retries):
        try:
            print(f"Fetching: {url}") # Added print for visibility
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            time.sleep(delay)
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            if i < retries - 1:
                print(f"Retrying in {delay * (i+1)} seconds...")
                time.sleep(delay * (i+1))
            else:
                print(f"Failed to fetch {url} after {retries} attempts.")
                return None

# --- Scraping Functions ---

def scrape_main_appliance_page(appliance_type_name, appliance_type_url, appliance_type_id):
    """
    Scrapes the main appliance type page (e.g., Refrigerator-Parts.htm).
    Extracts:
    - Links to "Related Parts" categories
    - Links/info for Popular Models
    - Links/info for Popular Brands
    """
    print(f"\nScraping main page for {appliance_type_name}: {appliance_type_url}")
    soup = fetch_page(appliance_type_url)
    if not soup:
        print(f"Could not fetch main appliance page for {appliance_type_name}")
        return [], [], [] # Return empty lists

    part_category_urls = [] # List of (category_name, url) tuples
    model_urls = []         # List of (model_number, description, url) tuples
    brand_names = set()     # Set of brand names

    # --- PART CATEGORIES ---
    print(f"Looking for 'Related {appliance_type_name} Parts' section...")
    # Find the h2 with the specific id and text, then its next sibling ul.nf__links
    related_parts_heading = soup.find('h2', id="ShopByPartType", string=re.compile(f'Related\s+{appliance_type_name}\s+Parts'))
    if related_parts_heading:
        related_parts_container = related_parts_heading.find_next_sibling('ul', class_='nf__links')
        if related_parts_container:
            for li in related_parts_container.find_all('li'):
                link = li.find('a', href=True)
                if link:
                    category_name = link.get_text(strip=True)
                    full_url = urljoin(BASE_URL, link['href'])
                    part_category_urls.append((category_name, full_url))
                    print(f"  Found category: {category_name} - {full_url}")
    else:
        print(f"Could not find 'Related {appliance_type_name} Parts' section using expected selectors.")

    # --- POPULAR MODELS ---
    print(f"Looking for 'Popular {appliance_type_name} Models' section...")
    # Find the h2 with the specific id and text
    popular_models_heading = soup.find('h2', id="TopModelsSectionTitle", string=re.compile(f'Popular\s+{appliance_type_name}\s+Models'))
    if popular_models_heading:
        # The ul.nf__links is after a div.row.mb-4, which is after the h2
        # So we look for the next ul.nf__links after this heading.
        models_list_container = popular_models_heading.find_next_sibling('div', class_='row mb-4')
        if models_list_container:
            models_list_container = models_list_container.find_next_sibling('ul', class_='nf__links')
        if models_list_container:
            for li in models_list_container.find_all('li'):
                link = li.find('a', href=True)
                if link:
                    model_text = link.get_text(strip=True) # e.g., "LFSS2612TF0 Refrigerator"
                    # Extract model number, assuming it's the first part before a space or " Refrigerator" / " Dishwasher"
                    model_number_match = re.match(r'([A-Z0-9-]+)\s', model_text)
                    model_number = model_number_match.group(1) if model_number_match else model_text.split(' ')[0]
                    full_url = urljoin(BASE_URL, link['href'])
                    model_urls.append((model_number, model_text, full_url))
                    print(f"  Found model: {model_number} - {full_url}")
    else:
        print(f"Could not find 'Popular {appliance_type_name} Models' section using expected selectors.")

    # --- POPULAR BRANDS ---
    print(f"Looking for '{appliance_type_name} Brands' section...")
    # Find the h2 with the specific id and span text
    popular_brands_heading = soup.find('h2', id="ShopByBrand")
    if popular_brands_heading and popular_brands_heading.find('span', string=f'{appliance_type_name} Brands'):
        brands_list_container = popular_brands_heading.find_next_sibling('ul', class_='nf__links')
        if brands_list_container:
            for li in brands_list_container.find_all('li'):
                link = li.find('a', href=True)
                if link:
                    brand_name_full = link.get_text(strip=True) # e.g., "Admiral Refrigerator Parts"
                    # Extract just the brand name (e.g., "Admiral")
                    brand_name = brand_name_full.replace(f' {appliance_type_name} Parts', '').strip()
                    if brand_name: # Ensure it's not empty
                        brand_names.add(brand_name)
                        print(f"  Found brand: {brand_name}")
    else:
        print(f"Could not find '{appliance_type_name} Brands' section using expected selectors.")

    return part_category_urls, model_urls, brand_names

def scrape_part_category_page(category_url, appliance_type_id, category_name):
    """
    Scrapes a part category page (e.g., Refrigerator-Trays-and-Shelves.htm).
    Extracts:
    - PartSelect Number
    - Manufacturer Part Number
    - Part Name, URL, Image
    - Price, Availability
    - Short Description, Troubleshooting summary, Installation Instructions summary
    """
    print(f"\nScraping part category page: {category_name} ({category_url})")
    soup = fetch_page(category_url)
    if not soup:
        print(f"Could not fetch part category page for {category_name}")
        return []

    part_detail_urls = [] # List of (part_id, part_url) for deeper scraping

    # --- IDENTIFY INDIVIDUAL PRODUCT ITEMS ---
    # Each product is now clearly defined by <div class="nf__part mb-3">
    product_items = soup.find_all('div', class_='nf__part')

    if not product_items:
        print(f"  No product items found (div.nf__part) on {category_url}. Check selectors.")
        return []

    print(f"  Found {len(product_items)} product items.")

    for item in product_items:
        part_number = None
        manufacturer_part_number = None
        part_name = None
        product_page_url = None
        image_url = None
        price_usd = None
        availability_status = None
        product_description_summary = None
        troubleshooting_summary = None
        installation_instructions_summary = None


        # --- Extract Part Name & Product Page URL ---
        # <a class="nf__part__detail__title" href="..."><span>Dishwasher Access Valve</span></a>
        name_link_container = item.find('a', class_='nf__part__detail__title')
        if name_link_container:
            part_name = name_link_container.find('span').get_text(strip=True) if name_link_container.find('span') else name_link_container.get_text(strip=True)
            product_page_url = urljoin(BASE_URL, name_link_container['href'])

        # --- Extract Image URL ---
        # <div class="nf__part__left-col__img mb-2"> <a href="..."> <picture> <img src="..."> </picture> </a> </div>
        img_container = item.find('div', class_='nf__part__left-col__img')
        if img_container:
            img_tag = img_container.find('img', src=True)
            if img_tag:
                src = img_tag['src']
                # Ensure we get the main image, not just a srcset source.
                # Use .webp if available, otherwise .jpg (or just the src if it's already a full URL)
                if 'srcset' in img_tag.attrs:
                    # Prefer the largest or a specific size if multiple are in srcset
                    # For simplicity, taking the first one that looks like a direct URL
                    srcset = img_tag['srcset'].split(',')
                    image_url = next((s.strip().split(' ')[0] for s in srcset if s.strip().endswith(('.webp', '.jpg', '.jpeg', '.png'))), None)
                    if not image_url and src: # Fallback to src if srcset parsing fails
                        image_url = src
                elif src:
                    image_url = src

                if image_url and image_url.startswith('/'): # Make absolute if relative
                    image_url = urljoin(BASE_URL, image_url)


        # --- Extract PartSelect Number ---
        # <div class="nf__part__detail__part-number">PartSelect Number <strong>PS16746057</strong></div>
        part_select_num_div = item.find('div', class_='nf__part__detail__part-number')
        if part_select_num_div:
            strong_tag = part_select_num_div.find('strong')
            if strong_tag:
                part_number = strong_tag.get_text(strip=True)

        # --- Extract Manufacturer Part Number ---
        # <div class="nf__part__detail__part-number mb-2">Manufacturer Part Number <strong>10023852</strong></div>
        # Note: This has 'mb-2' which is common but not unique, so relying on text content.
        mfg_part_num_divs = item.find_all('div', class_='nf__part__detail__part-number')
        for div in mfg_part_num_divs:
            if 'Manufacturer Part Number' in div.get_text():
                strong_tag = div.find('strong')
                if strong_tag:
                    manufacturer_part_number = strong_tag.get_text(strip=True)
                    break  # Stop after finding the correct one


        # --- Extract Price ---
        # <div class="mt-sm-2 price"><span class="price__currency">$</span>25.28</div>
        price_div = item.find('div', class_='price')
        if price_div:
            price_text = price_div.get_text(strip=True).replace('$', '').replace(',', '')
            try:
                price_usd = float(price_text)
            except ValueError:
                pass # Price not found or invalid format

        # --- Extract Availability Status ---
        # <div class="mega-m__part__avlbl mt-2 bold js-tooltip"> ... <span> In Stock</span>
        availability_div = item.find('div', class_='mb-1 mb-sm-2 js-tooltip')
        if availability_div:
            span_tag = availability_div.find('span')
            if span_tag:
                availability_status = span_tag.get_text(strip=True)
        if not availability_status:
             availability_status = "Unknown" # Default if not found

        # --- Extract Product Description (summary from list page) ---
        # This is the direct text content within nf__part__detail, before the symptoms/instructions div
        detail_container = item.find('div', class_='nf__part__detail')
        product_description_summary = None

        if detail_container:
            # Find the last part-number div (since order is: ...part-number, part-number mb-2, [description], ...)
            all_part_num_divs = detail_container.find_all('div', class_=re.compile(r'nf__part__detail__part-number'))
            if all_part_num_divs:
                last_part_num_div = all_part_num_divs[-1]
                description_chunks = []
                for sib in last_part_num_div.next_siblings:
                    # Stop at the next "div" with a class – that's a new section
                    if getattr(sib, 'name', None) == 'div':
                        break
                    if isinstance(sib, str):
                        text = sib.strip()
                        if text:
                            description_chunks.append(text)
                    elif hasattr(sib, 'get_text'):
                        text = sib.get_text(strip=True)
                        if text:
                            description_chunks.append(text)
                if description_chunks:
                    product_description_summary = ' '.join(description_chunks)


        # --- Extract Troubleshooting (from list page) ---
        # <div class="nf__part__detail__symptoms mt-3"> ... <ul> ... </ul>
        troubleshooting_div = item.find('div', class_='nf__part__detail__symptoms')
        if troubleshooting_div:
            troubleshooting_summary = troubleshooting_div.get_text(separator='\n', strip=True)
            # Remove the "Fixes these symptoms" heading if it's there
            troubleshooting_summary = troubleshooting_summary.replace("Fixes these symptoms\n", "").strip()


        # --- Extract Installation Instructions (from list page) ---
        # <div class="nf__part__detail__instruction mt-3"> ... <span>The E:15 error code means...</span>
        installation_div = item.find('div', class_='nf__part__detail__instruction')
        if installation_div:
            # We want the main block of text, which is likely directly under the bold title.
            # Look for the span that contains the main text, or just get all text from the div.
            main_text_span = installation_div.find('span', class_='d-block') # The long text is in this span
            if main_text_span:
                installation_instructions_summary = main_text_span.get_text(separator='\n', strip=True)
            else: # Fallback to getting all text if the specific span is not found
                installation_instructions_summary = installation_div.get_text(separator='\n', strip=True)
                # Clean up known headings/links if they appear
                installation_instructions_summary = re.sub(r'Installation Instructions|Raymond from [A-Z, ]+|E:15 error code with Watertap|Read more...', '', installation_instructions_summary).strip()


        # --- Insert/Update Part in DB ---
        if part_number and product_page_url and part_name:
            part_data = {
                'part_number': part_number,
                'manufacturer_part_number': manufacturer_part_number,
                'name': part_name,
                'description': product_description_summary, # Now we have a summary from list page
                'price_usd': price_usd,
                'availability_status': availability_status,
                'image_url': image_url,
                'product_page_url': product_page_url,
                'appliance_type_id': appliance_type_id,
                'category': category_name,
                'installation_instructions_summary': installation_instructions_summary,
                'troubleshooting_summary': troubleshooting_summary
            }
            part_id = insert_or_update_part(part_data)
            if part_id:
                part_detail_urls.append((part_id, product_page_url)) # Still add to queue for full detail scrape if needed

                # --- Insert Troubleshooting Guide ---
                if troubleshooting_summary:
                    insert_or_update_guide({
                        'part_id': part_id,
                        'model_id': None,
                        'title': f"Troubleshooting for {part_name}",
                        'guide_text': troubleshooting_summary,
                        'guide_url': product_page_url + "#Troubleshooting", # Link to the section on product page
                        'type': 'Troubleshooting'
                    })

                # --- Insert Installation Guide ---
                if installation_instructions_summary:
                    insert_or_update_guide({
                        'part_id': part_id,
                        'model_id': None,
                        'title': f"Installation Instructions for {part_name}",
                        'guide_text': installation_instructions_summary,
                        'guide_url': product_page_url + "#Instructions", # Link to the section on product page
                        'type': 'Installation'
                    })
                
                print(f"    Added/Updated Part: {part_number} - {part_name} - Price: ${price_usd} - Avail: {availability_status}")
            else:
                print(f"    Failed to insert/update Part: {part_number} - {part_name}")
        else:
            print(f"    Skipping item due to missing essential data. Part Name: {part_name}, Part Number: {part_number}, URL: {product_page_url}")

    return part_detail_urls

# def scrape_part_detail_page(part_id, part_url):
#     """
#     Scrapes an individual part's detail page.
#     Extracts:
#     - Manufacturer Part Number
#     - Detailed Product Description
#     - Troubleshooting text
#     - Compatibility information (linking parts to models)
#     - Installation Guide links/text
#     """
#     print(f"\nScraping part detail page for part ID {part_id}: {part_url}")
#     soup = fetch_page(part_url)
#     if not soup:
#         print(f"Could not fetch part detail page for {part_url}")
#         return

#     # --- Extract Manufacturer Part Number ---
#     # Look for a <p> or <div> that contains "Manufacturer Part Number"
#     mfg_part_num_tag = soup.find(lambda tag: 'Manufacturer Part Number' in tag.get_text(strip=True))
#     manufacturer_part_number = None
#     if mfg_part_num_tag:
#         # Assuming the number is right after the text or in a sibling/child tag
#         # This will need specific inspection
#         mfg_part_num_text = mfg_part_num_tag.get_text(strip=True)
#         mfg_match = re.search(r'Manufacturer Part Number\s*([A-Za-z0-9-]+)', mfg_part_num_text)
#         if mfg_match:
#             manufacturer_part_number = mfg_match.group(1)
#         else:
#             # Fallback if the number is in a sibling, e.g., <p>Mfg Part No:</p> <span>12345</span>
#             next_sibling = mfg_part_num_tag.find_next_sibling()
#             if next_sibling:
#                 manufacturer_part_number = next_sibling.get_text(strip=True)
#     print(f"  Manufacturer Part Number: {manufacturer_part_number}")

#     # --- Extract Product Description ---
#     # Look for a div/section with a clear heading or class for product description
#     description_heading = soup.find('h3', string='Product Description') # Common heading
#     product_description = None
#     if description_heading:
#         description_para = description_heading.find_next_sibling('p') # Assuming a paragraph after heading
#         if description_para:
#             product_description = description_para.get_text(strip=True)
#     if not product_description: # Fallback: try common product description containers
#         desc_div = soup.find('div', class_='product-description') # Common class name
#         if desc_div:
#             product_description = desc_div.get_text(strip=True)
#     print(f"  Description: {product_description[:100]}..." if product_description else "  Description: N/A")

#     # --- Extract Troubleshooting ---
#     troubleshooting_heading = soup.find('h3', string='Troubleshooting')
#     troubleshooting_text = None
#     if troubleshooting_heading:
#         troubleshooting_para = troubleshooting_heading.find_next_sibling('p') # Or a div/ul
#         if troubleshooting_para:
#             troubleshooting_text = troubleshooting_para.get_text(strip=True)
#     if not troubleshooting_text: # Fallback: try common troubleshooting containers
#         troubleshoot_div = soup.find('div', class_='troubleshooting-info')
#         if troubleshoot_div:
#             troubleshooting_text = troubleshoot_div.get_text(strip=True)
#     print(f"  Troubleshooting: {troubleshooting_text[:100]}..." if troubleshooting_text else "  Troubleshooting: N/A")

#     # Update Part table with extracted details
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     try:
#         cursor.execute(
#             """
#             UPDATE Part SET
#                 manufacturer_part_number = COALESCE(%s, manufacturer_part_number),
#                 description = COALESCE(%s, description)
#             WHERE id = %s;
#             """,
#             (manufacturer_part_number, product_description, part_id)
#         )
#         conn.commit()
#         print(f"  Updated Part {part_id} with detailed info.")
#     except Exception as e:
#         conn.rollback()
#         print(f"  Error updating part {part_id}: {e}")
#     finally:
#         cursor.close()
#         conn.close()

#     # --- Extract Compatibility Information ---
#     # This is the most complex part and often requires careful regex or parsing.
#     # Look for text like "This part works with X models, including..." or a dedicated compatibility table.
#     # Example snippet: "Manufactured by Bosch for Bosch, Thermador"
#     compatibility_info_section = soup.find('div', class_='compatibility-section') # Common class
#     if not compatibility_info_section:
#         compatibility_info_section = soup.find(lambda tag: 'This part works with' in tag.get_text())

#     if compatibility_info_section:
#         compatibility_text = compatibility_info_section.get_text()
#         print(f"  Potential compatibility text: {compatibility_text[:100]}...")

#         # Regex to find model numbers within the text. Model numbers usually have a specific pattern (e.g., alphanumeric with dashes)
#         # This regex `[A-Z0-9-]+` is a common pattern, but might need refinement.
#         found_model_numbers = re.findall(r'[A-Z0-9-]{5,}', compatibility_text) # At least 5 chars, alphanumeric with dashes
#         print(f"  Attempting to extract models for compatibility: {found_model_numbers}")

#         # For each found model number, try to insert/get its ID and then link it.
#         # This will be refined. For now, we're just extracting the model numbers.
#         for model_num in set(found_model_numbers): # Use set to avoid duplicates
#             # Need to get model_id first. This means the model must have been scraped from main/model pages.
#             # For robust linking, we'd query the DB for the model_id
#             conn = get_db_connection()
#             cursor = conn.cursor()
#             try:
#                 cursor.execute("SELECT id FROM Model WHERE model_number = %s;", (model_num,))
#                 model_result = cursor.fetchone()
#                 if model_result:
#                     model_id = model_result[0]
#                     insert_part_compatibility(part_id, model_id)
#                     print(f"    Linked Part {part_id} to Model {model_id} ({model_num})")
#                 else:
#                     print(f"    Model '{model_num}' not found in DB for compatibility linking. Will add later if found via model scraping.")
#                     # In a real scenario, you might queue this model number for scraping
#                     # or handle it as a new model if it's not found elsewhere.
#             except Exception as e:
#                 print(f"    Error linking compatibility for {model_num}: {e}")
#             finally:
#                 cursor.close()
#                 conn.close()
#     else:
#         print("  No clear compatibility section found.")

#     # --- Extract Installation Guides ---
#     # Look for links or sections explicitly for guides, manuals, videos.
#     # Example: link.find_all('a', href=re.compile(r'\.(pdf|mp4|doc)')) or links with 'guide' in text
#     guide_links = []
#     # Find all links on the page that might be guides
#     for link in soup.find_all('a', href=True):
#         href = link['href']
#         link_text = link.get_text(strip=True).lower()
#         if any(keyword in link_text for keyword in ['guide', 'manual', 'instructions', 'video', 'how to', 'fix', 'install']) or \
#            any(ext in href for ext in ['.pdf', '.mp4', '.mov', '.doc', '.docx']):
#             full_guide_url = urljoin(part_url, href) # Use part_url for relative links
#             guide_title = link_text.capitalize() if link_text else "Unnamed Guide"
#             guide_type = 'Installation' if 'install' in link_text else 'Troubleshooting' if 'trouble' in link_text else 'Guide'
#             guide_links.append({
#                 'title': guide_title,
#                 'guide_url': full_guide_url,
#                 'type': guide_type,
#                 'part_id': part_id,
#                 'model_id': None # Could be filled if guide is specifically for a model
#             })
#             print(f"  Found potential guide: {guide_title} - {full_guide_url}")

#     for guide_data in guide_links:
#         insert_or_update_guide(guide_data)


def scrape_model_detail_page(model_id, model_url, appliance_type_id):
    """
    Scrapes a model's detail page to find associated parts and more model details.
    This will be implemented fully after basic part scraping is robust.
    """
    print(f"\nScraping model detail page for model ID {model_id}: {model_url}")
    # Placeholder for future implementation
    # This page would list parts associated with the model,
    # which can be used to augment or cross-reference our 'Part' table
    # and confirm/create 'PartCompatibility' entries.
    pass


# --- Main Scraper Orchestration ---

def run_scraper(appliance_type_name):
    print(f"\n--- Starting Scraper for {appliance_type_name} ---")

    appliance_type_url = APPLIANCE_URLS.get(appliance_type_name)
    if not appliance_type_url:
        print(f"Error: No URL defined for appliance type '{appliance_type_name}'.")
        return

    # Queues for deeper scraping
    part_category_urls_to_scrape = [] # (category_name, url)
    model_urls_to_scrape = []         # (model_number, description, url)
    part_detail_urls_to_scrape = []   # (part_id, url)

    # 1. Insert/Get ApplianceType ID
    appliance_type_id = insert_or_get_appliance_type(appliance_type_name)
    if not appliance_type_id:
        print(f"Failed to get or create appliance type ID for {appliance_type_name}. Aborting.")
        return

    # 2. Scrape the main appliance page
    temp_part_categories, temp_models_data, temp_brands_data = scrape_main_appliance_page(
        appliance_type_name, appliance_type_url, appliance_type_id
    )
    part_category_urls_to_scrape.extend(temp_part_categories)
    model_urls_to_scrape.extend(temp_models_data)


    # 3. Process extracted Brands
    print("\n--- Processing Brands ---")
    brand_ids = {} # {brand_name: brand_id}
    for brand_name in temp_brands_data:
        brand_id = insert_or_get_brand(brand_name)
        if brand_id:
            brand_ids[brand_name] = brand_id

    # 4. Process extracted Models (initial insertion/update)
    print("\n--- Processing Models (initial) ---")
    model_ids = {} # {model_number: model_id}
    for model_number, model_text, model_url in model_urls_to_scrape:
        # Fetch the model page to get brand name
        soup = fetch_page(model_url)
        inferred_brand_id = None
        if soup:
            heading = soup.find('h1', class_='title-main')
            if heading:
                heading_text = heading.get_text(strip=True)
                match = re.search(r'\b([A-Za-z]+)\s+Refrigerator', heading_text)
                if match:
                    brand_name_from_heading = match.group(1).strip()
                    print(f"  Inferred brand from heading: {brand_name_from_heading}")
                    # Insert/get brand ID
                    inferred_brand_id = brand_ids.get(brand_name_from_heading)
                    if not inferred_brand_id:
                        brand_id = insert_or_get_brand(brand_name_from_heading)
                        if brand_id:
                            brand_ids[brand_name_from_heading] = brand_id
                            inferred_brand_id = brand_id
        
        model_data = {
            'model_number': model_number,
            'appliance_type_id': appliance_type_id,
            'brand_id': inferred_brand_id,
            'description': model_text, # Use the full text as initial description
            'model_page_url': model_url
        }
        model_id = insert_or_update_model(model_data)
        if model_id:
            model_ids[model_number] = model_id
            # Later: scrape_model_detail_page(model_id, model_url, appliance_type_id)

    # 5. Process Part Categories and get part URLs for detail scraping
    print("\n--- Processing Part Categories (fetching product listings) ---")
    for category_name, category_url in part_category_urls_to_scrape:
        parts_from_category = scrape_part_category_page(category_url, appliance_type_id, category_name)
        part_detail_urls_to_scrape.extend(parts_from_category)

    # 6. Scrape individual Part Detail Pages
    # print("\n--- Processing Individual Part Detail Pages ---")
    # for part_id, part_url in part_detail_urls_to_scrape:
    #     scrape_part_detail_page(part_id, part_url)

    print(f"\n--- Finished full scraping for {appliance_type_name} ---")

if __name__ == "__main__":
    # IMPORTANT:
    # 1. Ensure your PostgreSQL server is running.
    # 2. Ensure your database is initialized (run `python db_init.py` if you haven't recently).
    # 3. Ensure your .env file has all PG_DB_NAME, PG_DB_USER, PG_DB_PASSWORD, etc.

    # Run for Refrigerator
    # run_scraper("Refrigerator")

    # Run for Dishwasher (uncomment after running Refrigerator successfully)
    run_scraper("Dishwasher")