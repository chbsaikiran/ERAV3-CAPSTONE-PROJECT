import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio
import google.generativeai as genai
from concurrent.futures import TimeoutError
from functools import partial

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from pydantic import BaseModel
#from gmail_utils import fetch_emails_from_query
from gemini_agent import get_details_from_email_body,build_gmail_search_query, summarize_emails_with_query,get_total_expenses_from_emails_with_query,Replace_total_expenses_from_emails_with_query

import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import websockets

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Load environment variables from .env file
load_dotenv()

# Access your API key and initialize Gemini client correctly
api_key = os.getenv("GEMINI_API_KEY")
#client = genai.Client(api_key=api_key)
genai.configure(api_key=api_key)
client = genai.GenerativeModel("gemini-2.0-flash")

max_iterations = 6
last_response = None
iteration = 0
iteration_response = []

async def generate_with_timeout(client, prompt, timeout=10):
    """Generate content with a timeout"""
    print("Starting LLM generation...")
    try:
        # Convert the synchronous generate_content call to run in a thread
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None, 
                lambda: client.generate_content(prompt)
            ),
            timeout=timeout
        )
        print("LLM generation completed")
        return response
    except TimeoutError:
        print("LLM generation timed out!")
        raise
    except Exception as e:
        print(f"Error in LLM generation: {e}")
        raise

def reset_state():
    """Reset all global variables to their initial state"""
    global last_response, iteration, iteration_response
    last_response = None
    iteration = 0
    iteration_response = []

def safe_float(x):
    try:
        return float(x.strip())
    except ValueError:
        return 0.0

async def handle_client(websocket):
    while True:
        async for message in websocket:
            if message.lower() == "exit":
                break
            print(f"[CLIENT] {message}")
            gmail_query = build_gmail_search_query(message)
            # Respond back to client
            await websocket.send(gmail_query)
            collected_snippets = []
            while True:
                date = await websocket.recv()
                if date == "Done":
                    break
                subject = await websocket.recv()
                body = await websocket.recv()
                details = get_details_from_email_body(body, message)
                await websocket.send("ok processed")
                full_snippet = (
                        f"Date: {date}\n"
                        f"Subject: {subject}\n"
                        f"Details: {details}\n"
                    )
                collected_snippets.append(full_snippet)
            await websocket.send("Processing Done")
            #print(f"Received snippets: {collected_snippets}")
            summarized_email = summarize_emails_with_query(message, collected_snippets)
            print(f"Summarized email: {summarized_email}")
            junk = await websocket.recv()
            print
            list_of_numbers = get_total_expenses_from_emails_with_query(summarized_email)
            reset_state()  # Reset at the start of main
            print("Starting main execution...")
            try:
                # Create a single MCP server connection
                print("Establishing connection to MCP server...")
                server_params = StdioServerParameters(
                    command="python",
                    args=["calculator.py"]
                )
        
                async with stdio_client(server_params) as (read, write):
                    print("Connection established, creating session...")
                    async with ClientSession(read, write) as session:
                        print("Session created, initializing...")
                        await session.initialize()
                        
                        # Get available tools
                        print("Requesting tool list...")
                        tools_result = await session.list_tools()
                        tools = tools_result.tools
                        print(f"Successfully retrieved {len(tools)} tools")
        
                        # Create system prompt with available tools
                        print("Creating system prompt...")
                        print(f"Number of tools: {len(tools)}")
                        
                        try:
                            # First, let's inspect what a tool object looks like
                            # if tools:
                            #     print(f"First tool properties: {dir(tools[0])}")
                            #     print(f"First tool example: {tools[0]}")
                            
                            tools_description = []
                            for i, tool in enumerate(tools):
                                try:
                                    # Get tool properties
                                    params = tool.inputSchema
                                    desc = getattr(tool, 'description', 'No description available')
                                    name = getattr(tool, 'name', f'tool_{i}')
                                    
                                    # Format the input schema in a more readable way
                                    if 'properties' in params:
                                        param_details = []
                                        for param_name, param_info in params['properties'].items():
                                            param_type = param_info.get('type', 'unknown')
                                            param_details.append(f"{param_name}: {param_type}")
                                        params_str = ', '.join(param_details)
                                    else:
                                        params_str = 'no parameters'
        
                                    tool_desc = f"{i+1}. {name}({params_str}) - {desc}"
                                    tools_description.append(tool_desc)
                                    print(f"Added description for tool: {tool_desc}")
                                except Exception as e:
                                    print(f"Error processing tool {i}: {e}")
                                    tools_description.append(f"{i+1}. Error processing tool")
                            
                            tools_description = "\n".join(tools_description)
                            print("Successfully created tools description")
                        except Exception as e:
                            print(f"Error creating tools description: {e}")
                            tools_description = "Error loading tools"
                        
                        print("Created system prompt... ")
                        print(list_of_numbers)
        
                        _, function_info = list_of_numbers.split(":", 1)
                        parts = [p.strip() for p in function_info.split("|")]
                        func_name, params = parts[0], parts[1:]
                        print(f"\nDEBUG: Raw function info: {function_info}")
                        print(f"DEBUG: Split parts: {parts}")
                        print(f"DEBUG: Function name: {func_name}")
                        print(f"DEBUG: Raw parameters: {params}")
                        
                        if func_name == "add_list" and params == ['0']:
                            print("No expenses found in the summary.")
                            summarized_email = Replace_total_expenses_from_emails_with_query(summarized_email,"No relevant information found in the emails.")
                            await websocket.send(summarized_email)
                        else :
                            try:
                                # Find the matching tool to get its input schema
                                tool = next((t for t in tools if t.name == func_name), None)
                                if not tool:
                                    print(f"DEBUG: Available tools: {[t.name for t in tools]}")
                                    raise ValueError(f"Unknown tool: {func_name}")
                            
                                print(f"DEBUG: Found tool: {tool.name}")
                                print(f"DEBUG: Tool schema: {tool.inputSchema}")
                            
                                # Prepare arguments according to the tool's input schema
                                arguments = {}
                                schema_properties = tool.inputSchema.get('properties', {})
                                print(f"DEBUG: Schema properties: {schema_properties}")
                            
                                for param_name, param_info in schema_properties.items():
                                    if not params:  # Check if we have enough parameters
                                        raise ValueError(f"Not enough parameters provided for {func_name}")
                                        
                                    value = params  # Get and remove the first parameter
                                    param_type = param_info.get('type', 'string')
                                    
                                    print(f"DEBUG: Converting parameter {param_name} with value {value} to type {param_type}")
                                    
                                    # Convert the value to the correct type based on the schema
                                    if param_type == 'integer':
                                        arguments[param_name] = int(value)
                                    elif param_type == 'number':
                                        arguments[param_name] = float(value)
                                    elif param_type == 'array':
                                        # Handle array input
                                        if isinstance(value, str):
                                            value = value.strip('[]').split(',')
                                        arguments[param_name] = [safe_float(x) for x in value]
                                    else:
                                        arguments[param_name] = str(value)
                            
                                print(f"DEBUG: Final arguments: {arguments}")
                                print(f"DEBUG: Calling tool {func_name}")
                                
                                result = await session.call_tool(func_name, arguments=arguments)
                                print(f"DEBUG: Raw result: {result.content[0].text}")
                                summarized_email = Replace_total_expenses_from_emails_with_query(summarized_email,result.content[0].text)
                                await websocket.send(summarized_email)
                            
                            except Exception as e:
                                print(f"DEBUG: Error details: {str(e)}")
                                print(f"DEBUG: Error type: {type(e)}")
                                import traceback
                                traceback.print_exc()
                                iteration_response.append(f"Error in iteration {iteration + 1}: {str(e)}")
            except Exception as e:
                print(f"Error in main execution: {e}")
                import traceback
                traceback.print_exc()
            finally:
                reset_state()  # Reset at the end of main
            #await websocket.close()

        
        #await websocket.send(f"Server reply: {message.upper()}")

async def main():
    async with websockets.serve(handle_client, "localhost", 9000):
        print("Server started on ws://localhost:9000")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
