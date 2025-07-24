# backend/test_embeddings.py

import psycopg2
import json
import os
from dotenv import load_dotenv
from openai import OpenAI # Assuming Deepseek API compatibility
from db_service import get_db_connection # Reuse your DB connection

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
EMBEDDING_MODEL = "text-embedding-ada-002" 

def get_embedding(text: str, model: str = EMBEDDING_MODEL):
    """Generates an embedding for the given text using the Deepseek API."""
    text = text.replace("\n", " ")
    try:
        if not text.strip():
            print("Warning: Attempted to get embedding for empty text.")
            return None
        response = embedding_client.embeddings.create(input=[text], model=model)
        return response.data[0].embedding
    except Exception as e:
        print(f"ERROR: Failed to get embedding for query '{text[:50]}...'. Error: {e}")
        return None

def find_similar_parts(query_embedding, limit: int = 5):
    """
    Performs a vector similarity search for parts based on a query embedding.
    Uses cosine distance (smaller distance = more similar).
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor()

        # Search against description_embedding first, then name_embedding
        # using the <-> operator for cosine distance
        cursor.execute(
            """
            SELECT
                id,
                part_number,
                name,
                description,
                (description_embedding <=> %s) AS desc_distance,
                (name_embedding <=> %s) AS name_distance
            FROM
                Part
            WHERE
                description_embedding IS NOT NULL OR name_embedding IS NOT NULL
            ORDER BY
                LEAST(COALESCE(description_embedding <=> %s, 1.0), COALESCE(name_embedding <=> %s, 1.0)) ASC
            LIMIT %s;
            """,
            (json.dumps(query_embedding), json.dumps(query_embedding), # For description_embedding <=> %s
             json.dumps(query_embedding), json.dumps(query_embedding), # For name_embedding <=> %s
             limit)
        )
        results = cursor.fetchall()

        parts = []
        for row in results:
            part = {
                "id": row[0],
                "part_number": row[1],
                "name": row[2],
                "description": row[3],
                "desc_distance": row[4],
                "name_distance": row[5]
            }
            parts.append(part)
        return parts
    except psycopg2.Error as e:
        print(f"Database error during similarity search for parts: {e}")
        return []
    finally:
        if conn: cursor.close(); conn.close()

def find_similar_guides(query_embedding, limit: int = 3):
    """
    Performs a vector similarity search for installation guides based on a query embedding.
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                title,
                guide_text,
                (guide_text_embedding <=> %s) AS distance,
                type
            FROM
                InstallationGuide
            WHERE
                guide_text_embedding IS NOT NULL
            ORDER BY
                distance ASC
            LIMIT %s;
            """,
            (json.dumps(query_embedding), limit)
        )
        results = cursor.fetchall()

        guides = []
        for row in results:
            guide = {
                "id": row[0],
                "title": row[1],
                "guide_text_snippet": row[2][:200] + "..." if row[2] and len(row[2]) > 200 else row[2], # Snippet
                "distance": row[3],
                "type": row[4]
            }
            guides.append(guide)
        return guides
    except psycopg2.Error as e:
        print(f"Database error during similarity search for guides: {e}")
        return []
    finally:
        if conn: cursor.close(); conn.close()


if __name__ == "__main__":
    print("--- Testing Semantic Search Capabilities ---")

    test_queries = [
        "What keeps my vegetables fresh in the fridge?",
        "My dishwasher is leaking water from the bottom.",
        "How do I replace a refrigerator ice maker?",
        "part that makes cold water",
        "noisy freezer fan"
    ]

    for query in test_queries:
        print(f"\nQUERY: '{query}'")
        query_embedding = get_embedding(query)

        if query_embedding:
            print("  Searching for similar parts...")
            similar_parts = find_similar_parts(query_embedding, limit=3)
            if similar_parts:
                for part in similar_parts:
                    print(f"    Part: {part['name']} (PS#: {part['part_number']}) - Distance: {part['desc_distance']:.4f}")
                    # print(f"      Description: {part['description'][:100]}...") # Uncomment for full description snippet
            else:
                print("    No similar parts found.")

            print("  Searching for similar guides...")
            similar_guides = find_similar_guides(query_embedding, limit=2)
            if similar_guides:
                for guide in similar_guides:
                    print(f"    Guide: {guide['title']} (Type: {guide['type']}) - Distance: {guide['distance']:.4f}")
                    # print(f"      Snippet: {guide['guide_text_snippet']}") # Uncomment for guide text snippet
            else:
                print("    No similar guides found.")
        else:
            print("  Could not generate embedding for query.")

    print("\n--- Test Complete ---")