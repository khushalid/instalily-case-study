# backend/db_init.py
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import os

load_dotenv() # Load your .env file

DB_NAME = os.getenv("PG_DB_NAME", "partselect_db")
DB_USER = os.getenv("PG_DB_USER", "partselect_user")
DB_PASSWORD = os.getenv("PG_DB_PASSWORD", "your_secure_password") # IMPORTANT: Use your actual password
DB_HOST = os.getenv("PG_DB_HOST", "localhost")
DB_PORT = os.getenv("PG_DB_PORT", "5432")

def create_database_and_tables():
    conn = None
    try:
        # Connect to default 'postgres' database to create the new database
        sys_conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER, # Use the user you created, or 'postgres' superuser
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        sys_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT) # Required for CREATE DATABASE
        cursor = sys_conn.cursor()

        # Check if database exists, create if not
        cursor.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"), [DB_NAME])
        exists = cursor.fetchone()
        if not exists:
            print(f"Creating database {DB_NAME}...")
            cursor.execute(sql.SQL(f"CREATE DATABASE {DB_NAME} OWNER {DB_USER}"))
            print(f"Database {DB_NAME} created.")
        else:
            print(f"Database {DB_NAME} already exists.")

        cursor.close()
        sys_conn.close()

        # Now connect to the newly created/existing database to create tables
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        print("Creating tables...")

        # ApplianceType Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ApplianceType (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL
            );
        """)

        # Brand Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Brand (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                logo_url TEXT
            );
        """)

        # Model Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Model (
                id SERIAL PRIMARY KEY,
                model_number VARCHAR(200) UNIQUE NOT NULL,
                appliance_type_id INTEGER REFERENCES ApplianceType(id),
                brand_id INTEGER REFERENCES Brand(id),
                description TEXT,
                model_page_url TEXT
            );
        """)

        # Part Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Part (
                id SERIAL PRIMARY KEY,
                part_number VARCHAR(200) UNIQUE NOT NULL,
                manufacturer_part_number VARCHAR(200),
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price_usd NUMERIC(10, 2),
                availability_status VARCHAR(50),
                image_url TEXT,
                product_page_url TEXT,
                appliance_type_id INTEGER REFERENCES ApplianceType(id),
                category VARCHAR(255),
                name_embedding VECTOR(1536),           -- NEW: Embedding for part name
                description_embedding VECTOR(1536)     -- NEW: Embedding for part description
            );
        """)

        # PartCompatibility Table (Many-to-Many between Part and Model)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS PartCompatibility (
                part_id INTEGER REFERENCES Part(id) ON DELETE CASCADE,
                model_id INTEGER REFERENCES Model(id) ON DELETE CASCADE,
                PRIMARY KEY (part_id, model_id)
            );
        """)

        # InstallationGuide Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS InstallationGuide (
                id SERIAL PRIMARY KEY,
                part_id INTEGER REFERENCES Part(id) ON DELETE SET NULL, -- Can be null if guide is for a model, not a specific part
                model_id INTEGER REFERENCES Model(id) ON DELETE SET NULL, -- Can be null if guide is for a specific part, not a model
                title VARCHAR(255) NOT NULL,
                guide_text TEXT,
                guide_url TEXT,
                type VARCHAR(50) NOT NULL, -- e.g., 'Installation', 'Troubleshooting', 'Repair'
                guide_text_embedding VECTOR(1536)
            );
        """)

        conn.commit()
        print("Tables created/verified successfully.")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # IMPORTANT: Before running this, ensure your .env file in the backend/ directory
    # has the PG_DB_NAME, PG_DB_USER, PG_DB_PASSWORD, PG_DB_HOST, PG_DB_PORT variables set.
    create_database_and_tables()