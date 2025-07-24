# backend/main.py

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv # New: for loading environment variables
import os                     # New: for accessing environment variables
import uvicorn
from openai import OpenAI     # New: for interacting with Deepseek API
import json

# Import your database service functions
from db_service import (
    get_part_details,
    check_compatibility,
    # get_installation_guide,
    get_installation_guide_by_part,
    get_installation_guide_by_model,
    troubleshoot_appliance,
    semantic_search
)
from web_search_service import perform_partselect_web_search

# Import your tool definitions
from tools_config import DB_TOOLS

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# --- CORS Configuration (Keep as is) ---
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

# --- Initialize Deepseek Client ---
# Get API key and base URL from environment variables
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1") # Default if not set
model = os.getenv("DEEPSEEK_MODEL")
# model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

if not deepseek_api_key:
    raise RuntimeError("DEEPSEEK_API_KEY environment variable not set.")

client = OpenAI(
    api_key=deepseek_api_key,
    base_url=deepseek_base_url,
)

# client = OpenAI(
#     api_key=os.getenv("OPENAI_API_KEY"),
# )

# --- Define a mapping from tool names (as used by LLM) to actual Python functions ---
# This dictionary maps the 'name' in tools_config.py to the function in db_service.py
available_functions = {
    "get_part_details": get_part_details,
    "check_compatibility": check_compatibility,
    # "get_installation_guide": get_installation_guide,
    "get_installation_guide_by_part": get_installation_guide_by_part,  # NEW
    "get_installation_guide_by_model": get_installation_guide_by_model, # NEW
    "troubleshoot_appliance": troubleshoot_appliance,
    "perform_partselect_web_search": perform_partselect_web_search, 
    "semantic_search": semantic_search 
}

MAX_CONVERSATION_MESSAGES = 4

# --- Chat Endpoint (MODIFIED for Function Calling) ---
@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        conversation_history_from_frontend = data.get("messages", [])

        if not conversation_history_from_frontend:
            raise HTTPException(status_code=400, detail="Conversation history cannot be empty.")

        system_message_content = (
            "You are a helpful chat agent for the PartSelect e-commerce website. "
            "Your primary function is to provide product information and assist with customer transactions "
            "**ONLY for Refrigerator and Dishwasher parts and models**. "
            "You have access to specialized tools to look up part details, check compatibility, "
            "retrieve installation guides, troubleshoot appliance issues, perform semantic searches on your database, and search the PartSelect website directly. "
            "**Always use the provided tools when relevant to answer a user's question.** "
            "Do NOT answer questions outside the scope of Refrigerator and Dishwasher parts or general knowledge. "
            "If a question is outside your scope, politely state that you can only assist with Refrigerator and Dishwasher parts. "
            "When providing part numbers or model numbers, mention them explicitly."
            "When asked how to fix an issue, use the 'get_installation_guide' or 'troubleshoot_appliance' tool as appropriate."
            "If a user asks for installation steps for a specific part number, use the 'get_installation_guide' tool with the part number."
            "If a user asks if a part is compatible with a model, use the 'check_compatibility' tool."
            "**PRIORITIZE TOOL USE IN THIS ORDER:** "
            "1. **Exact-match database lookups:** (`get_part_details`, `check_compatibility`, `get_installation_guide`, `troubleshoot_appliance`) if the query contains specific IDs or clear intent. "
            "2. **Semantic database search:** (`semantic_search`) if the query is more natural language, vague, or the exact-match tools fail to find specific results. Use this for symptoms, descriptions, or general part types. "
            "3. **External website search:** (`perform_partselect_web_search`) if semantic search also fails to provide concrete answers or if the user explicitly asks to 'search the website'. "
            "Maintain a friendly and professional tone. Respond concisely and directly."
            "If you retrieve detailed information, summarize it for the user."
            "If a guide is found, provide a direct link to it."
            "If a tool indicates that information was not found (e.g., 'found': false in the tool output), "
            "you MUST try the next prioritized tool. If all internal tools fail, then use 'perform_partselect_web_search'. "
            "When you use `perform_partselect_web_search`, summarize its results for the user and provide direct links. "
            "If after all tools, no answer is found, state that clearly and offer general help."
            "**IMPORTANT:** Format your responses using **Markdown** for clarity. " # NEW Instruction
            "Use headings (`##`), bullet points (`* item`), bold text (`**text**`), and newlines (`\n\n`) to break up information. " # NEW Instruction
            "Ensure lists are properly formatted with bullet points or numbered lists. " # NEW Instruction
            "Always include newlines between paragraphs and distinct sections for readability." # NEW Instruction
        )

        messages = [{"role": "system", "content": system_message_content}]
        filtered_frontend_history = []
        for msg in conversation_history_from_frontend:
            if msg.get("role") == "assistant" and msg.get("content", "").startswith("Hi there!"):
                continue
            filtered_frontend_history.append({"role": msg.get("role"), "content": msg.get("content", "")})

        messages.extend(filtered_frontend_history)
        # Prune older messages if history exceeds limit, always preserving the system prompt
        if len(messages) > MAX_CONVERSATION_MESSAGES:
            # Keep the system message + the most recent MAX_CONVERSATION_MESSAGES - 1 messages
            messages = [messages[0]] + messages[len(messages) - (MAX_CONVERSATION_MESSAGES - 1):]
            print(f"History pruned. Keeping {len(messages)} messages (max {MAX_CONVERSATION_MESSAGES}).")
        # --- End Conversation History Pruning ---


        print(f"\n--- Messages for First Deepseek Call ---")
        print(messages)

        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=messages,
            tools=DB_TOOLS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=2000,
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # --- Tool Orchestration Loop ---
        # This loop allows for sequential tool calls if Deepseek requests them
        # or for a programmatic fallback (like web search) if a tool fails.
        MAX_TOOL_CALL_ITERATIONS = 2 # Prevent infinite loops, allow one primary tool + one fallback tool
        current_iteration = 0
        final_agent_response_content = None

        while tool_calls and current_iteration < MAX_TOOL_CALL_ITERATIONS:
            print(f"\nDeepseek wants to call tools (Iteration {current_iteration + 1}): {tool_calls}")
            
            # Add Deepseek's tool call request to the messages list for history
            messages.append(
                {
                    "role": response_message.role,
                    "content": response_message.content, # This might be None or a short phrase from Deepseek
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        } for tc in tool_calls
                    ]
                }
            )

            tool_outputs_for_llm = [] # Collect outputs for this iteration's tool calls
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args_str = tool_call.function.arguments
                tool_output_data = None

                if function_name not in available_functions:
                    tool_output_data = {"error": f"Tool '{function_name}' is not a recognized function."}
                    print(tool_output_data)
                else:
                    function_to_call = available_functions[function_name]
                    try:
                        function_args = json.loads(function_args_str)
                        print(f"  Calling function: {function_name} with args: {function_args}")
                        tool_output_data = function_to_call(**function_args)
                        print(f"  Tool output: {tool_output_data}")
                    except json.JSONDecodeError:
                        tool_output_data = {"error": f"Invalid JSON arguments from LLM for tool '{function_name}': {function_args_str}"}
                        print(tool_output_data)
                    except Exception as e:
                        tool_output_data = {"error": f"Error executing tool '{function_name}': {e}"}
                        print(tool_output_data)

                tool_outputs_for_llm.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(tool_output_data),
                    }
                )
            
            # Add all tool outputs from this iteration to the messages list
            messages.extend(tool_outputs_for_llm)

            print(f"\n--- Messages for next Deepseek Call (Iteration {current_iteration + 1}) ---")
            print(messages)

            # Make another call to Deepseek with the updated messages
            response = client.chat.completions.create(
                model="deepseek-reasoner",
                messages=messages,
                tools=DB_TOOLS, # Keep tools available for potential follow-up tool calls
                tool_choice="auto",
                temperature=0.7,
                max_tokens=2000,
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls # Check if Deepseek wants to call more tools

            current_iteration += 1
            if not tool_calls: # If no more tool calls requested, we have the final content
                final_agent_response_content = response_message.content

        # After loop, if final_agent_response_content is still None, it means the loop terminated
        # due to max_tool_call_iterations, or Deepseek didn't generate content in the last turn.
        if final_agent_response_content is None:
            final_agent_response_content = response_message.content # Try to get content from last response
            if not final_agent_response_content or final_agent_response_content.strip() == "":
                print("WARNING: Deepseek did not generate content after tool calls. Providing fallback.")
                final_agent_response_content = "I performed a search, but the AI did not generate a specific response based on the results. Please try rephrasing your question or contact support."


        print(f"\n--- Raw Final Deepseek Response Object ---")
        print(response) # Print the very last response object
        print(f"\n--- Final Deepseek Message Content ---")
        print(final_agent_response_content)

        return {"response": final_agent_response_content}

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unhandled error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="An error occurred in the chat endpoint.")
    
# --- Run the FastAPI application (Keep as is) ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)