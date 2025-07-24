# backend/scripts/db_init.py

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from app.core.config import settings

def create_database_and_tables():
    """
    Connects to PostgreSQL, ensures the database exists,
    and creates or verifies the application's tables.
    """
    sys_conn = None
    app_conn = None
    try:
        # Connect to the default 'postgres' database to manage the application database
        sys_conn = psycopg2.connect(
            dbname=set,
            user=settings.PG_DB_USER,
            password=settings.PG_DB_PASSWORD,
            host=settings.PG_DB_HOST,
            port=settings.PG_DB_PORT
        )
        # Required for CREATE DATABASE command to run outside a transaction
        sys_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        sys_cursor = sys_conn.cursor()

        # Check if database exists; create it if not
        sys_cursor.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"), [settings.PG_DB_NAME])
        if not sys_cursor.fetchone():
            print(f"Creating database '{settings.PG_DB_NAME}'...")
            sys_cursor.execute(sql.SQL(f"CREATE DATABASE {settings.PG_DB_NAME} OWNER {settings.PG_DB_USER}"))
            print(f"Database '{settings.PG_DB_NAME}' created.")
        else:
            print(f"Database '{settings.PG_DB_NAME}' already exists.")

        sys_cursor.close()
        sys_conn.close()

        # Now connect to the application database to create/update tables
        app_conn = psycopg2.connect(
            dbname=settings.PG_DB_NAME,
            user=settings.PG_DB_USER,
            password=settings.PG_DB_PASSWORD,
            host=settings.PG_DB_HOST,
            port=settings.PG_DB_PORT
        )
        app_cursor = app_conn.cursor()

        print("Creating tables if they do not exist...")

        # SQL statements for table creation
        tables_sql = [
            """
            CREATE TABLE IF NOT EXISTS ApplianceType (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Brand (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                logo_url TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Model (
                id SERIAL PRIMARY KEY,
                model_number VARCHAR(200) UNIQUE NOT NULL,
                appliance_type_id INTEGER REFERENCES ApplianceType(id),
                brand_id INTEGER REFERENCES Brand(id),
                description TEXT,
                model_page_url TEXT
            );
            """,
            """
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
                name_embedding VECTOR(1536),
                description_embedding VECTOR(1536)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS PartCompatibility (
                part_id INTEGER REFERENCES Part(id) ON DELETE CASCADE,
                model_id INTEGER REFERENCES Model(id) ON DELETE CASCADE,
                PRIMARY KEY (part_id, model_id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS InstallationGuide (
                id SERIAL PRIMARY KEY,
                part_id INTEGER REFERENCES Part(id) ON DELETE SET NULL,
                model_id INTEGER REFERENCES Model(id) ON DELETE SET NULL,
                title VARCHAR(255) NOT NULL,
                guide_text TEXT,
                guide_url TEXT,
                type VARCHAR(50) NOT NULL,
                guide_text_embedding VECTOR(1536)
            );
            """
        ]

        for sql_statement in tables_sql:
            app_cursor.execute(sql_statement)

        app_conn.commit()
        print("All tables created/verified successfully.")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        if app_conn:
            app_conn.rollback()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if sys_conn:
            sys_conn.close()
        if app_conn:
            app_conn.close()

if __name__ == "__main__":
    # Ensure environment variables are loaded for settings to work
    create_database_and_tables()