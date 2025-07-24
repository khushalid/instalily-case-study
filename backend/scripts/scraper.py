# backend/scripts/scraper.py

"""
Web scraping script to extract Refrigerator and Dishwasher part, model,
and brand information from PartSelect.com and populate the PostgreSQL database.
"""

import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin
from app.core.config import settings # Import settings for configuration

# --- Global Configuration ---
# Headers to mimic a browser for web requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

BASE_URL = "https://www.partselect.com/"

# Mapping for dynamic URL generation based on appliance type
APPLIANCE_URLS = {
    "Refrigerator": urljoin(BASE_URL, "Refrigerator-Parts.htm"),
    "Dishwasher": urljoin(BASE_URL, "Dishwasher-Parts.htm"),
}

def get_db_connection():
    """
    Establishes and returns a database connection using settings from app.core.config.
    """
    return psycopg2.connect(
        dbname=settings.PG_DB_NAME,
        user=settings.PG_DB_USER,
        password=settings.PG_DB_PASSWORD,
        host=settings.PG_DB_HOST,
        port=settings.PG_DB_PORT
    )

def insert_or_get_appliance_type(appliance_name: str) -> int | None:
    """
    Inserts an appliance type into the database if it doesn't already exist,
    and returns its ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO ApplianceType (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id;", (appliance_name,))
        appliance_id = cursor.fetchone()[0]
        conn.commit()
        return appliance_id
    except Exception as e:
        conn.rollback()
        print(f"Error inserting/getting appliance type '{appliance_name}': {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def insert_or_get_brand(brand_name: str) -> int | None:
    """
    Inserts a brand into the database if it doesn't already exist,
    and returns its ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Brand (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id;", (brand_name,))
        brand_id = cursor.fetchone()[0]
        conn.commit()
        return brand_id
    except Exception as e:
        conn.rollback()
        print(f"Error inserting/getting brand '{brand_name}': {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def insert_or_update_model(model_data: dict) -> int | None:
    """
    Inserts a new model or updates an existing one in the database.
    Returns the ID of the inserted/updated model.
    """
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
        print(f"Error inserting/updating model '{model_data.get('model_number')}': {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def insert_or_update_part(part_data: dict) -> int | None:
    """
    Inserts a new part or updates an existing one in the database.
    Returns the ID of the inserted/updated part.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Note: 'installation_guides' and 'troubleshooting_guides' are not columns in the Part table.
        # They should be inserted into the InstallationGuide table.
        cursor.execute(
            """
            INSERT INTO Part (part_number, manufacturer_part_number, name, description, price_usd,
                              availability_status, image_url, product_page_url, appliance_type_id, category)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (part_number) DO UPDATE SET
                manufacturer_part_number = EXCLUDED.manufacturer_part_number,
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                price_usd = EXCLUDED.price_usd,
                availability_status = EXCLUDED.availability_status,
                image_url = EXCLUDED.image_url,
                product_page_url = EXCLUDED.product_page_url,
                appliance_type_id = EXCLUDED.appliance_type_id,
                category = EXCLUDED.category
            RETURNING id;
            """,
            (part_data['part_number'], part_data.get('manufacturer_part_number'), part_data['name'],
             part_data.get('description'), part_data.get('price_usd'), part_data.get('availability_status'),
             part_data.get('image_url'), part_data.get('product_page_url'),
             part_data.get('appliance_type_id'), part_data.get('category'))
        )
        part_id = cursor.fetchone()[0]
        conn.commit()
        return part_id
    except Exception as e:
        conn.rollback()
        print(f"Error inserting/updating part '{part_data.get('part_number')}': {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def insert_part_compatibility(part_id: int, model_id: int):
    """
    Inserts a compatibility record between a part and a model.
    """
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

def insert_or_update_guide(guide_data: dict) -> int | None:
    """
    Inserts a new installation/troubleshooting guide or updates an existing one.
    Returns the ID of the inserted/updated guide.
    """
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
        print(f"Error inserting/updating guide '{guide_data.get('guide_url')}': {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def fetch_page(url: str, retries: int = 3, delay: int = 3) -> BeautifulSoup | None:
    """
    Fetches a URL with retries and a delay to be polite to the server.
    """
    for i in range(retries):
        try:
            print(f"Fetching: {url}")
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

def scrape_main_appliance_page(appliance_type_name: str, appliance_type_url: str, appliance_type_id: int) -> tuple[list, list, set]:
    """
    Scrapes the main appliance type page (e.g., Refrigerator-Parts.htm)
    to extract links to part categories, popular models, and popular brands.
    """
    print(f"\nScraping main page for {appliance_type_name}: {appliance_type_url}")
    soup = fetch_page(appliance_type_url)
    if not soup:
        print(f"Could not fetch main appliance page for {appliance_type_name}")
        return [], [], set()

    part_category_urls = []
    model_urls = []
    brand_names = set()

    # PART CATEGORIES
    print(f"Looking for 'Related {appliance_type_name} Parts' section...")
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

    # POPULAR MODELS
    print(f"Looking for 'Popular {appliance_type_name} Models' section...")
    popular_models_heading = soup.find('h2', id="TopModelsSectionTitle", string=re.compile(f'Popular\s+{appliance_type_name}\s+Models'))
    if popular_models_heading:
        models_list_container = popular_models_heading.find_next_sibling('div', class_='row mb-4')
        if models_list_container:
            models_list_container = models_list_container.find_next_sibling('ul', class_='nf__links')
        if models_list_container:
            for li in models_list_container.find_all('li'):
                link = li.find('a', href=True)
                if link:
                    model_text = link.get_text(strip=True)
                    model_number_match = re.match(r'([A-Z0-9-]+)\s', model_text)
                    model_number = model_number_match.group(1) if model_number_match else model_text.split(' ')[0]
                    full_url = urljoin(BASE_URL, link['href'])
                    model_urls.append((model_number, model_text, full_url))
                    print(f"  Found model: {model_number} - {full_url}")
    else:
        print(f"Could not find 'Popular {appliance_type_name} Models' section using expected selectors.")

    # POPULAR BRANDS
    print(f"Looking for '{appliance_type_name} Brands' section...")
    popular_brands_heading = soup.find('h2', id="ShopByBrand")
    if popular_brands_heading and popular_brands_heading.find('span', string=f'{appliance_type_name} Brands'):
        brands_list_container = popular_brands_heading.find_next_sibling('ul', class_='nf__links')
        if brands_list_container:
            for li in brands_list_container.find_all('li'):
                link = li.find('a', href=True)
                if link:
                    brand_name_full = link.get_text(strip=True)
                    brand_name = brand_name_full.replace(f' {appliance_type_name} Parts', '').strip()
                    if brand_name:
                        brand_names.add(brand_name)
                        print(f"  Found brand: {brand_name}")
    else:
        print(f"Could not find '{appliance_type_name} Brands' section using expected selectors.")

    return part_category_urls, model_urls, brand_names

def scrape_part_category_page(category_url: str, appliance_type_id: int, category_name: str) -> list[tuple[int, str]]:
    """
    Scrapes a part category page to extract individual part details
    and queue them for deeper scraping if necessary.
    """
    print(f"\nScraping part category page: {category_name} ({category_url})")
    soup = fetch_page(category_url)
    if not soup:
        print(f"Could not fetch part category page for {category_name}")
        return []

    part_detail_urls = []
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

        name_link_container = item.find('a', class_='nf__part__detail__title')
        if name_link_container:
            part_name = name_link_container.find('span').get_text(strip=True) if name_link_container.find('span') else name_link_container.get_text(strip=True)
            product_page_url = urljoin(BASE_URL, name_link_container['href'])

        img_container = item.find('div', class_='nf__part__left-col__img')
        if img_container:
            img_tag = img_container.find('img', src=True)
            if img_tag:
                src = img_tag['src']
                if 'srcset' in img_tag.attrs:
                    srcset = img_tag['srcset'].split(',')
                    image_url = next((s.strip().split(' ')[0] for s in srcset if s.strip().endswith(('.webp', '.jpg', '.jpeg', '.png'))), None)
                    if not image_url and src:
                        image_url = src
                elif src:
                    image_url = src

                if image_url and image_url.startswith('/'):
                    image_url = urljoin(BASE_URL, image_url)
        if not image_url:
            print(f"    Warning: No image found for {part_name}. Please inspect HTML for image selector.")

        part_select_num_div = item.find('div', class_='nf__part__detail__part-number')
        if part_select_num_div and 'PartSelect Number' in part_select_num_div.get_text():
            strong_tag = part_select_num_div.find('strong')
            if strong_tag:
                part_number = strong_tag.get_text(strip=True)

        mfg_part_num_divs = item.find_all('div', class_='nf__part__detail__part-number')
        for div in mfg_part_num_divs:
            if 'Manufacturer Part Number' in div.get_text():
                strong_tag = div.find('strong')
                if strong_tag:
                    manufacturer_part_number = strong_tag.get_text(strip=True)
                    break

        price_div = item.find('div', class_='price')
        if price_div:
            price_text = price_div.get_text(strip=True).replace('$', '').replace(',', '')
            try:
                price_usd = float(price_text)
            except ValueError:
                pass

        availability_div = item.find('div', class_='mb-1 mb-sm-2 js-tooltip')
        if availability_div:
            span_tag = availability_div.find('span')
            if span_tag:
                availability_status = span_tag.get_text(strip=True)
        if not availability_status:
             availability_status = "Unknown"

        detail_container = item.find('div', class_='nf__part__detail')
        if detail_container:
            all_part_num_divs = detail_container.find_all('div', class_=re.compile(r'nf__part__detail__part-number'))
            if all_part_num_divs:
                last_part_num_div = all_part_num_divs[-1]
                description_chunks = []
                for sib in last_part_num_div.next_siblings:
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

        troubleshooting_div = item.find('div', class_='nf__part__detail__symptoms')
        if troubleshooting_div:
            troubleshooting_summary = troubleshooting_div.get_text(separator='\n', strip=True)
            troubleshooting_summary = troubleshooting_summary.replace("Fixes these symptoms\n", "").strip()

        installation_div = item.find('div', class_='nf__part__detail__instruction')
        if installation_div:
            main_text_span = installation_div.find('span', class_='d-block')
            if main_text_span:
                installation_instructions_summary = main_text_span.get_text(separator='\n', strip=True)
            else:
                installation_instructions_summary = installation_div.get_text(separator='\n', strip=True)
                installation_instructions_summary = re.sub(r'Installation Instructions|Raymond from [A-Z, ]+|E:15 error code with Watertap|Read more...', '', installation_instructions_summary).strip()

        if part_number and product_page_url and part_name:
            part_data = {
                'part_number': part_number,
                'manufacturer_part_number': manufacturer_part_number,
                'name': part_name,
                'description': product_description_summary,
                'price_usd': price_usd,
                'availability_status': availability_status,
                'image_url': image_url,
                'product_page_url': product_page_url,
                'appliance_type_id': appliance_type_id,
                'category': category_name,
                'installation_instructions_summary': installation_instructions_summary, # Used for Guide table
                'troubleshooting_summary': troubleshooting_summary # Used for Guide table
            }
            part_id = insert_or_update_part(part_data)
            if part_id:
                part_detail_urls.append((part_id, product_page_url))

                if troubleshooting_summary:
                    insert_or_update_guide({
                        'part_id': part_id,
                        'model_id': None,
                        'title': f"Troubleshooting for {part_name}",
                        'guide_text': troubleshooting_summary,
                        'guide_url': product_page_url + "#Troubleshooting",
                        'type': 'Troubleshooting'
                    })

                if installation_instructions_summary:
                    insert_or_update_guide({
                        'part_id': part_id,
                        'model_id': None,
                        'title': f"Installation Instructions for {part_name}",
                        'guide_text': installation_instructions_summary,
                        'guide_url': product_page_url + "#Instructions",
                        'type': 'Installation'
                    })
                
                print(f"    Added/Updated Part: {part_number} - {part_name} - Price: ${price_usd} - Avail: {availability_status}")
            else:
                print(f"    Failed to insert/update Part: {part_number} - {part_name}")
        else:
            print(f"    Skipping item due to missing essential data. Part Name: {part_name}, Part Number: {part_number}, URL: {product_page_url}")

    return part_detail_urls

def scrape_model_detail_page(model_id: int, model_url: str, appliance_type_id: int):
    """
    Placeholder for scraping a model's detail page to find associated parts or
    more comprehensive model-specific information.
    """
    print(f"\nScraping model detail page for model ID {model_id}: {model_url}")
    # This function is a placeholder for future implementation if needed.
    pass


def run_scraper(appliance_type_name: str):
    """
    Orchestrates the scraping process for a given appliance type,
    from main page to category pages, and then to individual part details.
    """
    print(f"\n--- Starting Scraper for {appliance_type_name} ---")

    appliance_type_url = APPLIANCE_URLS.get(appliance_type_name)
    if not appliance_type_url:
        print(f"Error: No URL defined for appliance type '{appliance_type_name}'.")
        return

    part_category_urls_to_scrape = []
    model_urls_to_scrape = []
    part_detail_urls_to_scrape = []

    appliance_type_id = insert_or_get_appliance_type(appliance_type_name)
    if not appliance_type_id:
        print(f"Failed to get or create appliance type ID for {appliance_type_name}. Aborting.")
        return

    temp_part_categories, temp_models_data, temp_brands_data = scrape_main_appliance_page(
        appliance_type_name, appliance_type_url, appliance_type_id
    )
    part_category_urls_to_scrape.extend(temp_part_categories)
    model_urls_to_scrape.extend(temp_models_data)

    print("\n--- Processing Brands ---")
    brand_ids = {}
    for brand_name in temp_brands_data:
        brand_id = insert_or_get_brand(brand_name)
        if brand_id:
            brand_ids[brand_name] = brand_id

    print("\n--- Processing Models (initial) ---")
    model_ids = {}
    for model_number, model_text, model_url in model_urls_to_scrape:
        soup = fetch_page(model_url)
        inferred_brand_id = None
        if soup:
            heading = soup.find('h1', class_='title-main')
            if heading:
                heading_text = heading.get_text(strip=True)
                match = re.search(r'\b([A-Za-z]+)\s+Refrigerator', heading_text) # Regex specific to Refrigerator
                if match:
                    brand_name_from_heading = match.group(1).strip()
                    print(f"  Inferred brand from heading: {brand_name_from_heading}")
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
            'description': model_text,
            'model_page_url': model_url
        }
        model_id = insert_or_update_model(model_data)
        if model_id:
            model_ids[model_number] = model_id
            # Optionally: scrape_model_detail_page(model_id, model_url, appliance_type_id)

    print("\n--- Processing Part Categories (fetching product listings) ---")
    for category_name, category_url in part_category_urls_to_scrape:
        parts_from_category = scrape_part_category_page(category_url, appliance_type_id, category_name)
        part_detail_urls_to_scrape.extend(parts_from_category)

    # Individual Part Detail Pages (currently not in use as details scraped from category page)
    # for part_id, part_url in part_detail_urls_to_scrape:
    #     scrape_part_detail_page(part_id, part_url)

    print(f"\n--- Finished full scraping for {appliance_type_name} ---")

if __name__ == "__main__":
    # Ensure PostgreSQL server is running and database initialized.
    # Ensure .env file has all necessary PG_DB_NAME, PG_DB_USER, PG_DB_PASSWORD etc.
    
    # Example usage:
    run_scraper("Refrigerator")
    run_scraper("Dishwasher") # Run for Dishwasher after Refrigerator