# PartSelect Chat Agent

## 🌟 Project Overview

This project implements an AI-powered chatbot for the PartSelect e-commerce website, specializing in Refrigerator and Dishwasher parts. The chatbot's primary function is to provide product information, check part compatibility, offer installation guidance, and assist with troubleshooting appliance issues. It leverages a custom knowledge base (PostgreSQL database with scraped data and vector embeddings), real-time web search capabilities, and the Deepseek/OpenAI Large Language Models (LLMs) to provide accurate and helpful responses.

The agent is designed to remain focused on its specific use case (Refrigerator and Dishwasher parts), avoiding irrelevant queries.

## ✨ Features

* **Intelligent Conversational Agent:** Powered by Deepseek AI for natural language understanding and generation.
* **Database Integration (PostgreSQL):** Stores comprehensive data on Refrigerator and Dishwasher parts, models, brands, and guides.
* **Semantic Search (PGVector + OpenAI Embeddings):** Finds relevant information even from vague or natural language queries by understanding their meaning.
* **Web Search Fallback:** If internal database lookups or semantic searches don't yield results, the agent can perform real-time searches on the PartSelect website and summarize findings.
* **Tool Use / Function Calling:** The LLM intelligently decides when to query the database or perform web searches based on user intent.
* **Conversational Memory:** Maintains context across multiple turns for a more fluid interaction.
* **Responsive Chat UI (React):** A modern, user-friendly chat interface built with React, styled to align with PartSelect's branding.
* **Organized Backend (FastAPI):** A clean, modular Python backend using FastAPI for efficient API handling.
* **Markdown Formatting:** Agent responses are formatted using Markdown for enhanced readability in the chat interface.

## 🚀 Getting Started

Follow these steps to set up and run the PartSelect Chat Agent on your local machine.

### Prerequisites

Before you begin, ensure you have the following installed:

* **Git:** For cloning the repository.
* **Node.js & npm (or Yarn):** For the React frontend.
    * [Download Node.js (includes npm)](https://nodejs.org/en/download/)
* **Python 3.9+:** For the FastAPI backend.
    * [Python Downloads](https://www.python.org/downloads/)
* **PostgreSQL:** The database server.
    * [PostgreSQL Downloads](https://www.postgresql.org/download/)
    * **Important:** Remember the password you set for the `postgres` superuser during installation.
* **OpenAI API Key:** Required for generating embeddings for semantic search.
    * [Create OpenAI Account & API Key](https://platform.openai.com/account/api-keys)
* **Deepseek API Key:** Required for the main chat LLM.
    * [Create Deepseek Account & API Key](https://platform.deepseek.com/platform/console/apiKeys)

### Step-by-Step Setup

#### 1. Clone the Repository

```bash
git clone [https://github.com/khushalid/partselect-chat-agent.git](https://github.com/khushalid/partselect-chat-agent.git) # Replace with your repo URL
cd partselect-chat-agent
````

#### 2\. Backend Setup

Navigate into the `backend` directory:

```bash
cd backend
```

##### 2.1. Create and Activate Python Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies.

```bash
python -m venv venv
```

  * **On macOS/Linux:**
    ```bash
    source venv/bin/activate
    ```
  * **On Windows (Command Prompt):**
    ```bash
    venv\Scripts\activate.bat
    ```
  * **On Windows (PowerShell):**
    ```bash
    .\venv\Scripts\Activate.ps1
    ```

##### 2.2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

##### 2.3. Configure Environment Variables (`.env` file)

Create a file named `.env` in the `backend/` directory. **DO NOT commit this file to Git.**

```env
# backend/.env

# --- Deepseek API Configuration ---
DEEPSEEK_API_KEY="sk-YOUR_DEEPSEEK_API_KEY_HERE"
DEEPSEEK_BASE_URL="[https://api.deepseek.com/v1](https://api.deepseek.com/v1)" # Standard Deepseek API base URL
DEEPSEEK_MODEL="deepseek-reasoner" # Or deepseek-chat, or another suitable Deepseek model

# --- OpenAI API Configuration (for Embeddings) ---
OPENAI_API_KEY="sk-YOUR_OPENAI_API_KEY_HERE"
OPENAI_EMBEDDING_MODEL="text-embedding-ada-002" # Common OpenAI embedding model

# --- PostgreSQL Database Credentials ---
PG_DB_NAME="partselect_db"
PG_DB_USER="partselect_user"
PG_DB_PASSWORD="your_secure_db_password" # Set a strong password here
PG_DB_HOST="localhost"
PG_DB_PORT="5432" # Default PostgreSQL port
```

**Replace placeholder values** (`sk-YOUR_DEEPSEEK_API_KEY_HERE`, `sk-YOUR_OPENAI_API_KEY_HERE`, `your_secure_db_password`) with your actual keys and chosen password.

##### 2.4. Set up PostgreSQL Database

You need to create the database and a user for the application, and enable the `pgvector` extension.

1.  **Connect to PostgreSQL as superuser:**
    Open your terminal (make sure your Python virtual environment is **deactivated** for `psql` usage, or use a separate terminal) and run:

    ```bash
    psql -U postgres
    ```

    Enter the `postgres` superuser password you set during PostgreSQL installation.

2.  **Create Database and User:**

    ```sql
    CREATE DATABASE partselect_db;
    CREATE USER partselect_user WITH PASSWORD 'your_secure_db_password'; -- Use the same password as in .env
    GRANT ALL PRIVILEGES ON DATABASE partselect_db TO partselect_user;
    \q -- Exit psql
    ```

3.  **Enable `pgvector` Extension:**
    Re-connect to your new database using your new user:

    ```bash
    psql -U partselect_user -d partselect_db
    ```

    Enable the extension:

    ```sql
    CREATE EXTENSION IF NOT EXISTS vector;
    \q -- Exit psql
    ```

##### 2.5. Initialize Database Schema

Now, run the Python script to create all the necessary tables in your `partselect_db`.
(Ensure your Python virtual environment is **activated** for this step).

```bash
python scripts/db_init.py
```

You should see messages confirming database and table creation.

##### 2.6. Scrape Data from PartSelect.com

This step populates your database with Refrigerator and Dishwasher part, model, and guide information. This can take a significant amount of time (tens of minutes to hours) due to polite delays between requests.

```bash
python scripts/scraper.py
```

This script will print its progress to the console.

##### 2.7. Generate Embeddings for Semantic Search

After scraping, generate vector embeddings for part names, descriptions, and guide texts. This requires the OpenAI API. This step can also take a long time.

```bash
python scripts/embed_data.py
```

Monitor the console for progress and any API errors.

#### 3\. Frontend Setup

Navigate back to the root of your project, then into the `frontend` directory:

```bash
cd ..
cd frontend
```

##### 3.1. Install JavaScript Dependencies

```bash
npm install # or yarn install
```

#### 4\. Run the Application

You'll need two separate terminal windows for this: one for the backend and one for the frontend.

##### 4.1. Start Backend (API Server)

In your first terminal:

```bash
cd backend
source venv/bin/activate # or .\venv\Scripts\Activate.ps1 for Windows
uvicorn main:app --reload --port 8000
```

The backend server should start on `http://127.0.0.1:8000`.

##### 4.2. Start Frontend (React Dev Server)

In your second terminal:

```bash
cd frontend
npm start
```

The React development server should start, and your browser should automatically open `http://localhost:3000`.

## 🤖 Usage

Once both the frontend and backend servers are running, open your browser to `http://localhost:3000`.

You can now interact with the chatbot by typing messages in the input field. Try asking:

  * "What is PS11752778?"
  * "Does PS16746057 work with LFSS2612TF0?"
  * "How do I install part PS11752778?"
  * "My Whirlpool fridge ice maker isn't working."
  * "What is a part that helps with refrigerator drawers?" (Tests semantic search)
  * "Find me a filter for a Samsung dishwasher." (Tests web search if not in DB)
  * "Tell me about car parts." (Tests scope confinement)

## 📁 Project Structure

```
.
├── backend/                  # FastAPI Python backend
│   ├── .env                  # Environment variables (local, .gitignore'd)
│   ├── requirements.txt      # Python dependencies
│   ├── main.py               # FastAPI application entry point
│   ├── app/                  # Python package for core application logic
│   │   ├── __init__.py
│   │   ├── api/              # API routers (e.g., chat endpoint)
│   │   │   ├── __init__.py
│   │   │   └── chat.py
│   │   ├── services/         # Business logic, DB & external API interactions
│   │   │   ├── __init__.py
│   │   │   ├── db_service.py     # Database query functions
│   │   │   └── web_search.py     # PartSelect web search utility
│   │   └── core/             # Core configurations, LLM setup, tool definitions
│   │       ├── __init__.py
│   │       ├── config.py         # Centralized settings & LLM client init
│   │       └── tools.py          # LLM tool definitions (functions it can call)
│   ├── scripts/              # One-off or utility scripts
│   │   ├── __init__.py
│   │   ├── db_init.py            # Database schema initialization
│   │   ├── embed_data.py         # Generates and stores vector embeddings
│   │   ├── scraper.py            # Web scraper for initial data population
│   │   └── test_embeddings.py    # Script to test embedding functionality
│   └── venv/                 # Python virtual environment (ignored)
├── frontend/                 # React.js web application
│   ├── public/               # Public assets
│   ├── src/                  # React source code
│   │   ├── App.js                # Main application component
│   │   ├── App.css               # Global CSS styles
│   │   ├── components/           # Reusable UI components
│   │   │   ├── Message.js            # Renders individual chat messages
│   │   │   ├── Message.css           # Styling for Message component
│   │   │   ├── MessageInput.js       # Input field and send button
│   │   │   └── MessageList.js        # Displays list of messages
│   │   └── index.js              # Entry point for React app
│   ├── package.json          # Node.js dependencies
│   └── yarn.lock / package-lock.json
└── README.md                 # This file
```

## 🛠️ Extensibility & Customization

  * **Adding More Appliance Types/Data:** Modify `scripts/scraper.py` and `scripts/embed_data.py` to target new sections of PartSelect.com, and update your database schema (`scripts/db_init.py`) if needed.
  * **Enhancing LLM Capabilities:**
      * **New Tools:** Define new functions in `app/services/db_service.py` or create new service modules, and add their definitions to `app/core/tools.py`. Update `app/api/chat.py`'s `available_functions` mapping.
      * **Prompt Engineering:** Refine the `system_message_content` in `app/api/chat.py` to better guide the LLM's behavior, tool use, and response formatting.
      * **LLM Model:** Change `DEEPSEEK_MODEL` in `.env` to experiment with different Deepseek models or other OpenAI-compatible models.
  * **Improving UI:**
      * Modify CSS files (`App.css`, `Message.css`) for visual aesthetics.
      * Implement rich content rendering in `frontend/src/components/Message.js` (e.g., dedicated product cards with images, structured troubleshooting steps) by sending structured JSON from the backend instead of just plain text.
  * **Advanced Features:**
      * Implement more sophisticated conversational memory (e.g., summarization of old turns).
      * Add user authentication and session management.
      * Integrate with other PartSelect systems (e.g., order history, cart).

## 🐛 Troubleshooting

  * **`403 Forbidden` during scraping (`scripts/scraper.py`) or web search (`app/services/web_search.py`):**
    * **Symptom:** You might see `Error fetching ...: 403 Client Error: Forbidden` or `Network or HTTP error ... 403 Forbidden`.
    * **Cause:** Websites often block automated requests that don't look like they're coming from a standard web browser. This is typically due to a detected `User-Agent` string or missing other browser-like HTTP headers.
    * **Solution:**
        1.  **Get Your Browser's User-Agent:**
            * Open your web browser (Chrome, Firefox, Edge, Safari).
            * Search Google for "my user agent" or visit a site like [https://www.whatismybrowser.com/detect/what-is-my-user-agent](https://www.whatismybrowser.com/detect/what-is-my-user-agent).
            * **Copy the entire string** displayed as your "User Agent." This will be a long string containing browser and OS details.
        2.  **Update `HEADERS` in Scraper Files:**
            * Open `backend/scripts/scraper.py` and locate the `HEADERS` dictionary.
            * Open `backend/app/services/web_search.py` and locate the `HEADERS` dictionary.
            * **Replace the `User-Agent` value** in both files with the string you copied from your browser.
                ```python
                # Example:
                HEADERS = {
                    'User-Agent': 'PASTE_YOUR_COPIED_USER_AGENT_STRING_HERE',
                    # ... other headers ...
                }
                ```
        3.  **Consider Other Headers (Already in Code):** The provided code already includes other common browser headers (`Accept`, `Accept-Language`, etc.). These also help mimic a real browser. If the issue persists, ensure these are present as shown in the provided code snippets.
        4.  **Increase Delay:** If the `403` error still occurs, you might be hitting rate limits. Increase the `delay` argument in `fetch_page` within `backend/scripts/scraper.py` (e.g., from `3` to `5` or `10` seconds). Similarly, `EMBEDDING_API_DELAY_SECONDS` in `.env` can be increased for embedding processes if needed.
  * **`403 Forbidden` during scraping/web search:**
      * Update `User-Agent` in `backend/scripts/scraper.py` and `backend/app/services/web_search.py` with your current browser's user agent.
      * Increase `time.sleep()` delays in `scraper.py`, `embed_data.py`, and `web_search.py`.
  * **`404 Not Found` for API endpoints:**
      * Ensure all `__init__.py` files are present in all subdirectories of `backend/app/`.
      * Verify `app.include_router(chat_router.router)` is present in `backend/main.py`.
      * Check import paths in all Python files after refactoring.
      * Ensure `uvicorn` is run from the `backend/` directory (`uvicorn main:app`).
  * **`Object of type Decimal is not JSON serializable`:**
      * Ensure database query functions in `app/services/db_service.py` convert `Decimal` types to `float` (or `str`) before returning.
  * **`Model not found` / `invalid_request_error` from LLM API:**
      * Double-check `DEEPSEEK_MODEL` or `OPENAI_EMBEDDING_MODEL` names in `.env` and `app/core/config.py` against official documentation.
      * Verify your `DEEPSEEK_API_KEY` and `OPENAI_API_KEY` are correct and have access to the specified models.
  * **Empty Chatbot Responses / `finish_reason='length'`:**
      * Increase `LLM_MAX_TOKENS_FIRST_CALL` and `LLM_MAX_TOKENS_SUBSEQUENT_CALLS` in `backend/.env` and `app/core/config.py`. The LLM might be running out of tokens for its internal reasoning.
  * **Database connection errors:**
      * Verify `PG_DB_NAME`, `PG_DB_USER`, `PG_DB_PASSWORD`, `PG_DB_HOST`, `PG_DB_PORT` in your `backend/.env` match your PostgreSQL setup.
      * Ensure your PostgreSQL server is running.
  * **UI not reflecting CSS changes:**
      * Perform a hard refresh (`Ctrl + Shift + R` or `Cmd + Shift + R`) in your browser.
      * Disable browser cache in Developer Tools (Network tab).
      * Ensure CSS files are correctly linked in `App.js` and `Message.js`.

-----
