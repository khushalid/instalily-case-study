# backend/db_service.py

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import os
import json
from urllib.parse import quote_plus # New import for URL encoding
from openai import OpenAI

load_dotenv()

# Database Configuration (from .env)
DB_NAME = os.getenv("PG_DB_NAME")
DB_USER = os.getenv("PG_DB_USER")
DB_PASSWORD = os.getenv("PG_DB_PASSWORD")
DB_HOST = os.getenv("PG_DB_HOST")
DB_PORT = os.getenv("PG_DB_PORT")

# --- OpenAI Embedding Client Configuration ---
# Assuming you're now using OpenAI's embedding model
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # Ensure this is set in your .env
# Common OpenAI embedding model
EMBEDDING_MODEL = "text-embedding-ada-002"

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY environment variable not set.")

embedding_client = OpenAI(api_key=OPENAI_API_KEY)

# --- Helper to construct PartSelect search URL ---
def construct_partselect_search_url(query_term: str) -> str:
    """Constructs a URL for searching on PartSelect.com."""
    # Ensure the query term is URL-encoded
    encoded_query = quote_plus(query_term)
    return f"https://www.partselect.com/api/search/?searchterm={encoded_query}"

def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        return None

# --- Database Query Functions (Tools for LLM) ---

def get_part_details(part_number: str) -> dict:
    """
    Retrieves detailed information about a part by its PartSelect number.
    ...
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                p.name, p.description, p.price_usd, p.availability_status,
                p.image_url, p.product_page_url, p.manufacturer_part_number,
                at.name as appliance_type, b.name as brand
            FROM Part p
            LEFT JOIN ApplianceType at ON p.appliance_type_id = at.id
            LEFT JOIN Brand b ON at.id = (SELECT id FROM ApplianceType WHERE name = 'Refrigerator' AND id = p.appliance_type_id)
            WHERE p.part_number = %s;
            """,
            (part_number.upper(),)
        )
        result = cursor.fetchone()
        if result:
            columns = [desc[0] for desc in cursor.description]
            part_details = dict(zip(columns, result))
            if 'price_usd' in part_details and part_details['price_usd'] is not None:
                part_details['price_usd'] = float(part_details['price_usd'])
            return {"found": True, "details": part_details} # Return as dict with 'found' status
        else:
            return {
                "found": False,
                "message": f"Part number {part_number} not found in our database.",
                "suggested_web_search_url": construct_partselect_search_url(part_number)
            }
    except psycopg2.Error as e:
        print(f"Error in get_part_details for {part_number}: {e}")
        return {"found": False, "message": "Database error retrieving part details."}
    finally:
        if conn: cursor.close(); conn.close()

def check_compatibility(part_number: str, model_number: str) -> dict:
    """
    Checks if a given part is compatible with a specific appliance model.
    ...
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor()

        cursor.execute("SELECT id, name FROM Part WHERE part_number = %s;", (part_number.upper(),))
        part_info = cursor.fetchone()
        if not part_info:
            return {
                "compatible": False,
                "reason": f"Part {part_number} not found in our database.",
                "suggested_web_search_url": construct_partselect_search_url(part_number)
            }
        part_id, part_name = part_info[0], part_info[1] # Use part_info to get name for msg

        cursor.execute("SELECT id, description FROM Model WHERE model_number = %s;", (model_number.upper(),))
        model_info = cursor.fetchone()
        if not model_info:
            return {
                "compatible": False,
                "reason": f"Model {model_number} not found in our database.",
                "suggested_web_search_url": construct_partselect_search_url(model_number)
            }
        model_id, model_description = model_info

        cursor.execute(
            "SELECT COUNT(*) FROM PartCompatibility WHERE part_id = %s AND model_id = %s;",
            (part_id, model_id)
        )
        is_compatible = cursor.fetchone()[0] > 0

        if is_compatible:
            return {"compatible": True, "part_number": part_number, "model_number": model_number,
                    "message": f"Part {part_name} ({part_number}) is compatible with model {model_number} ({model_description})."}
        else:
            return {"compatible": False, "part_number": part_number, "model_number": model_number,
                    "message": f"Part {part_name} ({part_number}) is NOT directly listed as compatible with model {model_number} ({model_description}).",
                    "suggested_web_search_url": construct_partselect_search_url(f"{part_number} {model_number}")
            }
    except psycopg2.Error as e:
        print(f"Error in check_compatibility for part {part_number}, model {model_number}: {e}")
        return {"compatible": False, "reason": "Database error during compatibility check."}
    finally:
        if conn: cursor.close(); conn.close()

# def get_installation_guide(part_number: str = None, model_number: str = None, guide_type: str = 'Installation') -> dict:
#     """
#     Retrieves installation or troubleshooting guides for a part or model.
#     ...
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         if not conn: return None
#         cursor = conn.cursor()

#         query_part_id = None
#         if part_number:
#             cursor.execute("SELECT id FROM Part WHERE part_number = %s;", (part_number.upper(),))
#             part_result = cursor.fetchone()
#             if part_result:
#                 query_part_id = part_result[0]
#             else:
#                 return {
#                     "found": False,
#                     "message": f"Part {part_number} not found in our database.",
#                     "suggested_web_search_url": construct_partselect_search_url(part_number)
#                 }

#         query_model_id = None
#         if model_number:
#             cursor.execute("SELECT id FROM Model WHERE model_number = %s;", (model_number.upper(),))
#             model_result = cursor.fetchone()
#             if model_result:
#                 query_model_id = model_result[0]
#             else:
#                 return {
#                     "found": False,
#                     "message": f"Model {model_number} not found in our database.",
#                     "suggested_web_search_url": construct_partselect_search_url(model_number)
#                 }

#         conditions = []
#         params = []

#         if query_part_id:
#             conditions.append("ig.part_id = %s")
#             params.append(query_part_id)
        
#         if query_model_id:
#             conditions.append("ig.model_id = %s")
#             params.append(query_model_id)
        
#         # If specific type requested, filter by it
#         if guide_type and guide_type.lower() in ['installation', 'troubleshooting', 'repair', 'guide']:
#             conditions.append("LOWER(ig.type) = LOWER(%s)")
#             params.append(guide_type)

#         if not conditions:
#             return {
#                 "found": False,
#                 "message": "Please provide a part number, model number, or specific guide type to search for.",
#                 "suggested_web_search_url": construct_partselect_search_url(f"{guide_type} guide") # Generic search
#             }

#         query = """
#             SELECT ig.title, ig.guide_text, ig.guide_url, ig.type
#             FROM InstallationGuide ig
#             WHERE """ + " AND ".join(conditions) + """
#             LIMIT 1;
#         """
        
#         cursor.execute(query, tuple(params))
#         result = cursor.fetchone()

#         if result:
#             columns = [desc[0] for desc in cursor.description]
#             guide = dict(zip(columns, result))
#             return {"found": True, "guide": guide, "message": f"Found a {guide['type']} guide."}
#         else:
#             search_query_term = ""
#             if part_number: search_query_term += part_number
#             if model_number: search_query_term += f" {model_number}" if search_query_term else model_number
#             if guide_type: search_query_term += f" {guide_type} guide" if search_query_term else f"{guide_type} guide"

#             return {
#                 "found": False,
#                 "message": f"No {guide_type} guide found for the provided criteria.",
#                 "suggested_web_search_url": construct_partselect_search_url(search_query_term.strip())
#             }

#     except psycopg2.Error as e:
#         print(f"Error in get_installation_guide: {e}")
#         return {"found": False, "message": "Database error while searching for guide."}
#     finally:
#         if conn: cursor.close(); conn.close()

def troubleshoot_appliance(appliance_type: str, symptom: str) -> dict:
    """
    Suggests common fixes or related parts for a given appliance symptom.
    ...
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor()

        # Find appliance_type_id
        cursor.execute("SELECT id FROM ApplianceType WHERE name = %s;", (appliance_type,))
        appliance_type_id = cursor.fetchone()
        if not appliance_type_id:
            return {
                "found": False,
                "message": f"Appliance type '{appliance_type}' not recognized.",
                "suggested_web_search_url": construct_partselect_search_url(f"{appliance_type} troubleshooting")
            }
        appliance_type_id = appliance_type_id[0]

        search_keywords = symptom.lower().split()
        
        like_conditions = [sql.SQL("LOWER(ig.guide_text) LIKE %s") for _ in search_keywords]
        like_params = [f"%{kw}%" for kw in search_keywords]

        part_name_conditions = [sql.SQL("LOWER(p.name) LIKE %s") for _ in search_keywords]
        part_name_params = [f"%{kw}%" for kw in search_keywords]
        
        query = sql.SQL("""
            SELECT
                ig.title, ig.guide_text, ig.guide_url, p.part_number, p.name as part_name
            FROM InstallationGuide ig
            LEFT JOIN Part p ON ig.part_id = p.id
            WHERE ig.type = 'Troubleshooting'
            AND (p.appliance_type_id = %s OR ig.model_id IN (SELECT id FROM Model WHERE appliance_type_id = %s))
            AND ({})
            LIMIT 3;
        """).format(sql.SQL(' OR ').join(like_conditions + part_name_conditions))
        
        params = [appliance_type_id, appliance_type_id] + like_params + part_name_params

        cursor.execute(query, tuple(params))
        results = cursor.fetchall()

        if results:
            trouble_info = []
            for row in results:
                columns = [desc[0] for desc in cursor.description]
                trouble_info.append(dict(zip(columns, row)))
            return {"found": True, "results": trouble_info, "message": "Found potential solutions."}
        else:
            return {
                "found": False,
                "message": "Could not find specific troubleshooting steps for that symptom.",
                "suggested_web_search_url": construct_partselect_search_url(f"{appliance_type} {symptom} troubleshooting")
            }

    except psycopg2.Error as e:
        print(f"Error in troubleshoot_appliance: {e}")
        return {"found": False, "message": "Database error during troubleshooting search."}
    finally:
        if conn: cursor.close(); conn.close()













# # backend/db_service.py

# import psycopg2
# from psycopg2 import sql
# from dotenv import load_dotenv
# import os
# import json # For handling JSON results, especially for troubleshooting symptoms list

# load_dotenv()

# # Database Configuration (from .env)
# DB_NAME = os.getenv("PG_DB_NAME")
# DB_USER = os.getenv("PG_DB_USER")
# DB_PASSWORD = os.getenv("PG_DB_PASSWORD")
# DB_HOST = os.getenv("PG_DB_HOST")
# DB_PORT = os.getenv("PG_DB_PORT")

# def get_db_connection():
#     """Establishes and returns a database connection."""
#     try:
#         conn = psycopg2.connect(
#             dbname=DB_NAME,
#             user=DB_USER,
#             password=DB_PASSWORD,
#             host=DB_HOST,
#             port=DB_PORT
#         )
#         return conn
#     except psycopg2.Error as e:
#         print(f"Database connection error: {e}")
#         return None

# # --- Database Query Functions (Tools for LLM) ---

# def get_part_details(part_number: str) -> dict:
#     """
#     Retrieves detailed information about a part by its PartSelect number.
#     ...
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         if not conn: return None
#         cursor = conn.cursor()
#         cursor.execute(
#             """
#             SELECT
#                 p.name, p.description, p.price_usd, p.availability_status,
#                 p.image_url, p.product_page_url, p.manufacturer_part_number,
#                 at.name as appliance_type, b.name as brand
#             FROM Part p
#             LEFT JOIN ApplianceType at ON p.appliance_type_id = at.id
#             LEFT JOIN Brand b ON at.id = (SELECT id FROM ApplianceType WHERE name = 'Refrigerator' AND id = p.appliance_type_id)
#             WHERE p.part_number = %s;
#             """,
#             (part_number.upper(),)
#         )
#         result = cursor.fetchone()
#         if result:
#             columns = [desc[0] for desc in cursor.description]
#             part_details = dict(zip(columns, result))
#             # Convert Decimal to float for JSON serialization
#             if 'price_usd' in part_details and part_details['price_usd'] is not None:
#                 part_details['price_usd'] = float(part_details['price_usd'])
#             return part_details
#         return None
#     except psycopg2.Error as e:
#         print(f"Error in get_part_details for {part_number}: {e}")
#         return None
#     finally:
#         if conn: cursor.close(); conn.close()

# def check_compatibility(part_number: str, model_number: str) -> dict:
#     """
#     Checks if a given part is compatible with a specific appliance model.
#     Args:
#         part_number (str): The PartSelect part number.
#         model_number (str): The appliance model number.
#     Returns:
#         dict: Compatibility status and relevant info.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         if not conn: return None
#         cursor = conn.cursor()

#         # First, find the part and model IDs
#         cursor.execute("SELECT id FROM Part WHERE part_number = %s;", (part_number.upper(),))
#         part_id = cursor.fetchone()
#         if not part_id:
#             return {"compatible": False, "reason": f"Part {part_number} not found."}
#         part_id = part_id[0]

#         cursor.execute("SELECT id, description FROM Model WHERE model_number = %s;", (model_number.upper(),))
#         model_info = cursor.fetchone()
#         if not model_info:
#             return {"compatible": False, "reason": f"Model {model_number} not found in our database."}
#         model_id, model_name = model_info

#         # Then, check the PartCompatibility table
#         cursor.execute(
#             "SELECT COUNT(*) FROM PartCompatibility WHERE part_id = %s AND model_id = %s;",
#             (part_id, model_id)
#         )
#         is_compatible = cursor.fetchone()[0] > 0

#         if is_compatible:
#             return {"compatible": True, "part_number": part_number, "model_number": model_number,
#                     "message": f"Part {part_number} is compatible with model {model_number} ({model_name})."}
#         else:
#             # You might want to also return common models for the part, or common parts for the model
#             # if direct compatibility is not found, to provide more context.
#             return {"compatible": False, "part_number": part_number, "model_number": model_number,
#                     "message": f"Part {part_number} is NOT directly listed as compatible with model {model_number} ({model_name}). Please double-check or consider searching for alternatives for this model."}
#     except psycopg2.Error as e:
#         print(f"Error in check_compatibility for part {part_number}, model {model_number}: {e}")
#         return {"compatible": False, "reason": "Database error during compatibility check."}
#     finally:
#         if conn: cursor.close(); conn.close()

def get_installation_guide_by_part(part_number: str, guide_type: str = 'Installation') -> dict:
    """
    Retrieves installation or troubleshooting guides for a specific part.
    Args:
        part_number (str): The PartSelect part number.
        guide_type (str): Type of guide ('Installation', 'Troubleshooting', 'Repair').
    Returns:
        dict: A dictionary of guide details, or None if not found.
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor()

        query = """
            SELECT ig.title, ig.guide_text, ig.guide_url, ig.type
            FROM InstallationGuide ig
            WHERE ig.part_id = (SELECT id FROM Part WHERE part_number = %s)
            AND LOWER(ig.type) = LOWER(%s)
            LIMIT 1;
        """
        cursor.execute(query, (part_number.upper(), guide_type))
        result = cursor.fetchone()

        if result:
            columns = [desc[0] for desc in cursor.description]
            guide = dict(zip(columns, result))
            return {"found": True, "guide": guide, "message": f"Found a {guide['type']} guide for part {part_number}."}
        else:
            return {"found": False, "message": f"No {guide_type} guide found for part {part_number}."}

    except psycopg2.Error as e:
        print(f"Error in get_installation_guide_by_part: {e}")
        return {"found": False, "message": "Database error while searching for part guide."}
    finally:
        if conn: cursor.close(); conn.close()

# --- NEW: get_installation_guide_by_model ---
def get_installation_guide_by_model(model_number: str, guide_type: str = 'Installation') -> dict:
    """
    Retrieves installation or troubleshooting guides for a specific model.
    Args:
        model_number (str): The appliance model number.
        guide_type (str): Type of guide ('Installation', 'Troubleshooting', 'Repair').
    Returns:
        dict: A dictionary of guide details, or None if not found.
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor()

        query = """
            SELECT ig.title, ig.guide_text, ig.guide_url, ig.type
            FROM InstallationGuide ig
            WHERE ig.model_id = (SELECT id FROM Model WHERE model_number = %s)
            AND LOWER(ig.type) = LOWER(%s)
            LIMIT 1;
        """
        cursor.execute(query, (model_number.upper(), guide_type))
        result = cursor.fetchone()

        if result:
            columns = [desc[0] for desc in cursor.description]
            guide = dict(zip(columns, result))
            return {"found": True, "guide": guide, "message": f"Found a {guide['type']} guide for model {model_number}."}
        else:
            return {"found": False, "message": f"No {guide_type} guide found for model {model_number}."}

    except psycopg2.Error as e:
        print(f"Error in get_installation_guide_by_model: {e}")
        return {"found": False, "message": "Database error while searching for model guide."}
    finally:
        if conn: cursor.close(); conn.close()

# def troubleshoot_appliance(appliance_type: str, symptom: str) -> dict:
#     """
#     Suggests common fixes or related parts for a given appliance symptom.
#     This will perform a basic keyword search against troubleshooting guides.
#     Args:
#         appliance_type (str): 'Refrigerator' or 'Dishwasher'.
#         symptom (str): A description of the problem (e.g., 'ice maker not working', 'leaking').
#     Returns:
#         dict: Relevant troubleshooting tips or part suggestions.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         if not conn: return None
#         cursor = conn.cursor()

#         # Find appliance_type_id
#         cursor.execute("SELECT id FROM ApplianceType WHERE name = %s;", (appliance_type,))
#         appliance_type_id = cursor.fetchone()
#         if not appliance_type_id:
#             return {"found": False, "message": f"Appliance type '{appliance_type}' not recognized."}
#         appliance_type_id = appliance_type_id[0]

#         # Basic keyword search on guide text and part names within the specified appliance type
#         # This is a very simple search and can be greatly improved with full-text search,
#         # vector embeddings for semantic search, or more structured troubleshooting data.
#         search_keywords = symptom.lower().split()
        
#         # Build dynamic LIKE conditions for relevant keywords
#         like_conditions = [sql.SQL("LOWER(ig.guide_text) LIKE %s") for _ in search_keywords]
#         like_params = [f"%{kw}%" for kw in search_keywords]

#         # Also search part names associated with the guide
#         part_name_conditions = [sql.SQL("LOWER(p.name) LIKE %s") for _ in search_keywords]
#         part_name_params = [f"%{kw}%" for kw in search_keywords]
        
#         query = sql.SQL("""
#             SELECT
#                 ig.title, ig.guide_text, ig.guide_url, p.part_number, p.name as part_name
#             FROM InstallationGuide ig
#             LEFT JOIN Part p ON ig.part_id = p.id
#             WHERE ig.type = 'Troubleshooting'
#             AND (p.appliance_type_id = %s OR ig.model_id IN (SELECT id FROM Model WHERE appliance_type_id = %s))
#             AND ({}) -- This will be the OR combination of LIKE conditions
#             LIMIT 3; -- Limit results to a few relevant ones
#         """).format(sql.SQL(' OR ').join(like_conditions + part_name_conditions))
        
#         params = [appliance_type_id, appliance_type_id] + like_params + part_name_params

#         cursor.execute(query, tuple(params))
#         results = cursor.fetchall()

#         if results:
#             trouble_info = []
#             for row in results:
#                 columns = [desc[0] for desc in cursor.description]
#                 trouble_info.append(dict(zip(columns, row)))
#             return {"found": True, "results": trouble_info, "message": "Found potential solutions."}
#         else:
#             return {"found": False, "message": "Could not find specific troubleshooting steps for that symptom. Please try rephrasing or check your appliance manual."}

#     except psycopg2.Error as e:
#         print(f"Error in troubleshoot_appliance: {e}")
#         return {"found": False, "message": "Database error during troubleshooting search."}
#     finally:
#         if conn: cursor.close(); conn.close()


# # You can add more specific functions here as needed, e.g.:
# # def get_parts_by_model(model_number: str) -> list: ...
# # def get_models_by_brand(brand_name: str, appliance_type: str) -> list: ...
# # def get_top_selling_parts(appliance_type: str) -> list: ...

# --- NEW: Helper to get embedding for semantic search query ---
def get_query_embedding(text: str) -> list:
    """Generates an embedding for the given text using the OpenAI API."""
    text = text.replace("\n", " ") # Replace newlines for better embeddings
    try:
        if not text.strip():
            print("Warning: Attempted to get embedding for empty query text.")
            return None
        response = embedding_client.embeddings.create(input=[text], model=EMBEDDING_MODEL)
        return response.data[0].embedding
    except Exception as e:
        print(f"ERROR: Failed to get embedding for query '{text[:50]}...'. Error: {e}")
        return None

# --- NEW: Semantic Search Tool Function ---
def semantic_search(query: str, appliance_type: str = None, search_limit: int = 5) -> dict:
    """
    Performs a semantic (vector) search across part descriptions and installation guides
    to find relevant information based on a natural language query.
    Args:
        query (str): The natural language query or symptom.
        appliance_type (str, optional): 'Refrigerator' or 'Dishwasher' to narrow search.
        search_limit (int): Max number of results to return for each category (parts/guides).
    Returns:
        dict: A dictionary containing semantically similar parts and guides.
    """
    query_embedding = get_query_embedding(query)
    if not query_embedding:
        return {"found_semantic": False, "message": "Could not generate embedding for the query.", "suggested_web_search_url": construct_partselect_search_url(query)}

    conn = None
    try:
        conn = get_db_connection()
        if not conn: return {"found_semantic": False, "message": "Database connection error.", "suggested_web_search_url": construct_partselect_search_url(query)}
        cursor = conn.cursor()

        results = {"parts": [], "guides": []}

        # Build conditions for appliance type if provided
        appliance_filter_sql = ""
        appliance_params = []
        if appliance_type:
            cursor.execute("SELECT id FROM ApplianceType WHERE name = %s;", (appliance_type,))
            appliance_id_res = cursor.fetchone()
            if appliance_id_res:
                appliance_id = appliance_id_res[0]
                appliance_filter_sql = " AND p.appliance_type_id = %s"
                appliance_params = [appliance_id]
            else:
                print(f"Warning: Invalid appliance_type '{appliance_type}' for semantic search.")

        # --- Semantic Search for Parts ---
        # Search against description_embedding first, then name_embedding
        cursor.execute(
            f"""
            SELECT
                p.part_number, p.name, p.description, p.product_page_url, p.price_usd,
                (p.description_embedding <=> %s) AS desc_distance,
                (p.name_embedding <=> %s) AS name_distance
            FROM
                Part p
            WHERE
                (p.description_embedding IS NOT NULL OR p.name_embedding IS NOT NULL)
                {appliance_filter_sql}
            ORDER BY
                LEAST(COALESCE(p.description_embedding <=> %s, 1.0), COALESCE(p.name_embedding <=> %s, 1.0)) ASC
            LIMIT %s;
            """,
            (json.dumps(query_embedding), json.dumps(query_embedding), # For <=>
             *(appliance_params), # If appliance_filter_sql is present
             json.dumps(query_embedding), json.dumps(query_embedding), # For LEAST
             search_limit)
        )
        part_results = cursor.fetchall()
        for row in part_results:
            part = {
                "part_number": row[0],
                "name": row[1],
                "description_snippet": row[2][:150] + "..." if row[2] and len(row[2]) > 150 else row[2],
                "product_page_url": row[3],
                "price_usd": float(row[4]) if row[4] else None,
                "overall_distance": min(row[5] or 1.0, row[6] or 1.0) # Take the better distance
            }
            results['parts'].append(part)

        # --- Semantic Search for Guides ---
        guide_appliance_filter_sql = ""
        guide_appliance_params = []
        if appliance_type:
            guide_appliance_filter_sql = " AND (p.appliance_type_id = %s OR m.appliance_type_id = %s)"
            guide_appliance_params = [appliance_id, appliance_id]

        cursor.execute(
            f"""
            SELECT
                ig.title, ig.guide_text, ig.guide_url, ig.type, p.part_number, m.model_number,
                (ig.guide_text_embedding <=> %s) AS distance
            FROM
                InstallationGuide ig
            LEFT JOIN Part p ON ig.part_id = p.id
            LEFT JOIN Model m ON ig.model_id = m.id
            WHERE
                ig.guide_text_embedding IS NOT NULL
                {guide_appliance_filter_sql}
            ORDER BY
                distance ASC
            LIMIT %s;
            """,
            (json.dumps(query_embedding),
             *(guide_appliance_params),
             search_limit)
        )
        guide_results = cursor.fetchall()
        for row in guide_results:
            guide = {
                "title": row[0],
                "guide_text_snippet": row[1][:150] + "..." if row[1] and len(row[1]) > 150 else row[1],
                "guide_url": row[2],
                "type": row[3],
                "part_number": row[4],
                "model_number": row[5],
                "distance": row[6]
            }
            results['guides'].append(guide)

        if results['parts'] or results['guides']:
            return {"found_semantic": True, "results": results, "message": "Found relevant information through semantic search."}
        else:
            return {
                "found_semantic": False,
                "message": "No relevant information found through semantic search in our database.",
                "suggested_web_search_url": construct_partselect_search_url(query)
            }

    except psycopg2.Error as e:
        print(f"Database error during semantic search: {e}")
        return {"found_semantic": False, "message": "Database error during semantic search."}
    except Exception as e:
        print(f"An unexpected error occurred during semantic search: {e}")
        return {"found_semantic": False, "message": "An unexpected error occurred during semantic search."}
    finally:
        if conn: cursor.close(); conn.close()