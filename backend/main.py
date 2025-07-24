# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import uvicorn

# --- VERY IMPORTANT: Ensure this import path is correct ---
from app.api import chat as chat_router # This imports the router from app/api/chat.py

# Import config for client and settings
from app.core.config import settings, openai_client

# Load environment variables
load_dotenv()

app = FastAPI(title="PartSelect Chat Agent Backend")

# --- CORS Configuration ---
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CRITICAL: Include the chat router ---
# This line tells your FastAPI app about the endpoints defined in chat_router.py
app.include_router(chat_router.router)


# You can define a root endpoint for health check or info (this should still work)
@app.get("/")
async def root():
    return {"message": "PartSelect Chat Agent API is running!"}

# --- Run the FastAPI application ---
if __name__ == "__main__":
    # ... (health checks for API keys and DB credentials) ...
    uvicorn.run(app, host="0.0.0.0", port=8000)