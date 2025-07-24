# backend/embed_data.py

import psycopg2
from dotenv import load_dotenv
import os
import time
from openai import OpenAI # Or deepseek client if they have one specifically for embeddings
from app.services.db_service import get_db_connection # Reuse existing DB connection logic

load_dotenv()

# --- OpenAI Embedding Client Configuration ---
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable not set for embeddings.")

# Initialize OpenAI client for embeddings
embedding_client = OpenAI(
    api_key=openai_api_key,
)

# Use OpenAI's recommended embedding model
EMBEDDING_MODEL = "text-embedding-ada-002" # This is a very common and effective embedding model

def get_embedding(text, model=EMBEDDING_MODEL):
    text = text.replace("\n", " ")
    try:
        if not text.strip(): # API might reject empty strings
            print("Warning: Attempted to get embedding for empty text. Returning None.")
            return None
        
        response = embedding_client.embeddings.create(input=[text], model=model)
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding for text: '{text[:50]}...': {e}")
        print(f"Please ensure your OPENAI_API_KEY is correct and you have access to '{model}' model.")
        return None

def embed_and_update_parts():
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, name, description FROM Part WHERE name_embedding IS NULL OR description_embedding IS NULL;")
        parts_to_embed = cursor.fetchall()

        print(f"Found {len(parts_to_embed)} parts to embed.")

        for part_id, name, description in parts_to_embed:
            print(f"Embedding part ID: {part_id}")
            name_embedding = get_embedding(name)
            description = description if description else "N/A"
            description_embedding = get_embedding(description) # Use description for detailed embedding

            if name_embedding and description_embedding:
                # PGVector expects a list of floats
                cursor.execute(
                    "UPDATE Part SET name_embedding = %s, description_embedding = %s WHERE id = %s;",
                    (name_embedding, description_embedding, part_id)
                )
                conn.commit()
                print(f"  Embedded and updated part {part_id}.")
            else:
                print(f"  Skipping part {part_id} due to embedding failure for name or description.")
            time.sleep(0.1) # Be polite to the API

    except Exception as e:
        conn.rollback()
        print(f"Error embedding parts: {e}")
    finally:
        cursor.close()
        conn.close()

def embed_and_update_guides():
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, guide_text FROM InstallationGuide WHERE guide_text_embedding IS NULL;")
        guides_to_embed = cursor.fetchall()

        print(f"Found {len(guides_to_embed)} guides to embed.")

        for guide_id, guide_text in guides_to_embed:
            print(f"Embedding guide ID: {guide_id}")
            if guide_text: # Ensure text is not None or empty
                guide_embedding = get_embedding(guide_text)

                if guide_embedding:
                    cursor.execute(
                        "UPDATE InstallationGuide SET guide_text_embedding = %s WHERE id = %s;",
                        (guide_embedding, guide_id)
                    )
                    conn.commit()
                    print(f"  Embedded and updated guide {guide_id}.")
                else:
                    print(f"  Skipping guide {guide_id} due to embedding failure.")
            else:
                print(f"  Skipping guide {guide_id} because text content is empty.")
            time.sleep(0.1) # Be polite to the API

    except Exception as e:
        conn.rollback()
        print(f"Error embedding guides: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("Starting embedding process...")
    embed_and_update_parts()
    embed_and_update_guides()
    print("Embedding process complete.")