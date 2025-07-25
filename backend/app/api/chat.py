# backend/app/api/chat.py

"""
FastAPI router for handling chat interactions with the LLM agent.
Orchestrates conversation history, tool calling, and responses.
"""

from fastapi import APIRouter, Request, HTTPException
import json

# Import services and tools from their new, organized paths
from app.services.db_service import (
    get_part_details,
    check_compatibility,
    get_installation_guide_by_part,
    get_installation_guide_by_model,
    troubleshoot_appliance,
    semantic_search,
    compare_models,
    compare_parts
)
from app.services.web_search import perform_partselect_web_search
from app.core.tools import DB_TOOLS
from app.core.config import settings, openai_client # Import settings and LLM client

router = APIRouter()

# Mapping of tool names (as defined in tools.py) to their corresponding Python functions
available_functions = {
    "get_part_details": get_part_details,
    "check_compatibility": check_compatibility,
    "get_installation_guide_by_part": get_installation_guide_by_part,
    "get_installation_guide_by_model": get_installation_guide_by_model,
    "troubleshoot_appliance": troubleshoot_appliance,
    "semantic_search": semantic_search,
    "perform_partselect_web_search": perform_partselect_web_search,
    "compare_models": compare_models,
    "compare_parts": compare_parts
}

@router.post("/chat")
async def chat_endpoint(request: Request):
    """
    Handles incoming chat messages, manages conversation history,
    orchestrates LLM calls, tool execution, and returns agent responses.
    """
    try:
        data = await request.json()
        conversation_history_from_frontend = data.get("messages", [])

        if not conversation_history_from_frontend:
            raise HTTPException(status_code=400, detail="Conversation history cannot be empty.")

        # Define the system message content for the LLM's persona and instruction
        system_message_content = (
            "You are a helpful chat agent for the PartSelect e-commerce website. "
            "Your primary function is to provide product information and assist with customer transactions "
            "**ONLY for Refrigerator and Dishwasher parts and models**. "
            "You have access to specialized tools to look up part details, check compatibility, "
            "retrieve installation guides, troubleshoot appliance issues, perform semantic searches on your database, "
            "compare appliance models, **compare appliance parts,** and search the PartSelect website directly. " # NEW Instruction
            "**Always use the provided tools when relevant to answer a user's question.** "
            "Do NOT answer questions outside the scope of Refrigerator and Dishwasher parts or general knowledge. "
            "If a question is outside your scope, politely state that you can only assist with Refrigerator and Dishwasher parts. "
            "When providing part numbers or model numbers, mention them explicitly."
            "When asked how to fix an issue, use the 'get_installation_guide' or 'troubleshoot_appliance' tool as appropriate."
            "If a user asks for installation steps for a specific part number, use the 'get_installation_guide' tool with the part number."
            "If a user asks if a part is compatible with a model, use the 'check_compatibility' tool."
            "If the user asks to compare two models (e.g., 'compare X and Y', 'difference between X and Y'), use the `compare_models` tool."
            "**If the user asks to compare two parts (e.g., 'compare part X and part Y', 'difference between part A and B'), use the `compare_parts` tool.**" # NEW Instruction
            "**PRIORITIZE TOOL USE IN THIS ORDER:** "
            "1. **Direct comparison (Models or Parts):** (`compare_models`, `compare_parts`) if the intent is clearly comparing two entities. " # UPDATED Priority
            "2. **Exact-match database lookups:** (`get_part_details`, `check_compatibility`, `get_installation_guide`, `troubleshoot_appliance`) if the query contains specific IDs or clear intent. "
            "3. **Semantic database search:** (`semantic_search`) if the query is more natural language, vague, or the exact-match tools fail to find specific results. Use this for symptoms, descriptions, or general part types. "
            "4. **External website search:** (`perform_partselect_web_search`) if semantic search also fails to provide concrete answers or if the user explicitly asks to 'search the website'. "
            "Maintain a friendly and professional tone. Respond concisely and directly."
            "If you retrieve detailed information, summarize it for the user."
            "If a guide is found, provide a direct link to it."
            "If a tool indicates that information was not found (e.g., 'found': false in the tool output), "
            "you MUST try the next prioritized tool. If all internal tools fail, then use 'perform_partselect_web_search'. "
            "When you use `perform_partselect_web_search`, summarize its results for the user and provide direct links. "
            "If after all tools, no answer is found, state that clearly and offer general help."
            "**IMPORTANT:** Format your responses using **Markdown** for clarity. "
            "Use headings (`##`), bullet points (`* item`), bold text (`**text**`), and newlines (`\n\n`) to break up information. "
            "Ensure lists are properly formatted with bullet points or numbered lists. "
            "Always include newlines between paragraphs and distinct sections for readability."
        )


        # Initialize messages list with the system prompt
        messages = [{"role": "system", "content": system_message_content}]
        
        # Append filtered conversation history from the frontend
        for msg in conversation_history_from_frontend:
            # Skip initial greeting from agent if it's identical to our system message purpose
            if msg.get("role") == "assistant" and msg.get("content", "").startswith("Hi there! I'm PartSelect's chat agent."):
                continue
            messages.append({"role": msg.get("role"), "content": msg.get("content", "")})

        # Conversation History Pruning: Keep system message + most recent messages
        if len(messages) > settings.MAX_CONVERSATION_MESSAGES:
            messages = [messages[0]] + messages[len(messages) - (settings.MAX_CONVERSATION_MESSAGES - 1):]
            print(f"History pruned. Keeping {len(messages)} messages (max {settings.MAX_CONVERSATION_MESSAGES}).")

        # First call to LLM: Decide on initial action (tool call or direct response)
        response = openai_client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=messages,
            tools=DB_TOOLS,
            tool_choice="auto",
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS_FIRST_CALL,
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # Tool Orchestration Loop: Allows for sequential tool calls or programmatic fallbacks
        current_iteration = 0
        final_agent_response_content = None

        while tool_calls and current_iteration < settings.MAX_TOOL_CALL_ITERATIONS:
            print(f"\nLLM wants to call tools (Iteration {current_iteration + 1}): {tool_calls}")
            
            # Add LLM's tool call request to the messages list for history
            messages.append(
                {
                    "role": response_message.role,
                    "content": response_message.content,
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

            tool_outputs_for_llm = []
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args_str = tool_call.function.arguments
                tool_output_data = None

                if function_name not in available_functions:
                    tool_output_data = {"error": f"Tool '{function_name}' is not recognized."}
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

                # Add the tool's output to the messages list for the next LLM call
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(tool_output_data),
                    }
                )
            
            # Second (or subsequent) LLM call with updated messages (including tool outputs)
            response = openai_client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=messages, # Pass the continually growing conversation history
                tools=DB_TOOLS, # Keep tools available for potential follow-up tool calls
                tool_choice="auto",
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS_SUBSEQUENT_CALLS,
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls # Check if LLM wants to call more tools

            current_iteration += 1
            if not tool_calls: # If no more tool calls requested, LLM is giving a final content response
                final_agent_response_content = response_message.content
                break # Exit loop as we have a final answer

        # Fallback if loop finishes without a direct content response
        if final_agent_response_content is None:
            final_agent_response_content = response_message.content
            if not final_agent_response_content or final_agent_response_content.strip() == "":
                print("WARNING: LLM did not generate content after tool calls. Providing fallback.")
                final_agent_response_content = "I performed a search, but the AI did not generate a specific response based on the results. Please try rephrasing your question or contact support."

        print(f"\n--- Raw Final LLM Response Object ---")
        print(response)
        print(f"\n--- Final LLM Message Content ---")
        print(final_agent_response_content)

        return {"response": final_agent_response_content}

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unhandled error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="An error occurred in the chat endpoint.")