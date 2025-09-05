# README.md

# Email Chat Analysis System

This repository contains a Python-based asynchronous WebSocket application designed to interact with Gmail, analyze email content using AI, and provide summarized answers to user queries via a WebSocket chat interface. The system consists of a **Python WebSocket server**, a **bridge client** that connects to the Gmail API, and a **front-end chat client**.

***

## Components

### 1. `server.py` — WebSocket Server and AI Processing Backend

- Implements a WebSocket server on `ws://localhost:9000` using `websockets` Python library.
- Listens for user queries from clients about Gmail emails.
- Converts natural language questions into Gmail search queries using an AI model (`gemini-2.0-flash`).
- Fetches relevant emails from Gmail using Gmail API with OAuth2 authentication.
- Filters out promotional emails and processes non-promotional ones.
- Sends email metadata (date, subject, body) to AI-driven functions to extract structured details.
- Uses Google Generative AI (`gemini_agent.py`) to:
  - Build Gmail queries.
  - Extract details from emails.
  - Summarize emails relevant to user questions.
  - Extract expenses from summaries.
- Calls MCP tools (math operations) asynchronously based on extracted financial data.
- Maintains state across multiple async iterations, with a reset after each full query cycle.
- Responds with a summarized answer back to the WebSocket client.

### 2. `client_bridge.py` — Bridge Client Between Browser and Server

- Runs a WebSocket client connected to the server at `ws://localhost:9000`.
- Acts as a bridge between a browser WebSocket client (`ws://localhost:8000`) and the server.
- Handles messages from the browser client:
  - Forwards queries to the server.
  - Receives server replies and sends them back to the browser.
- Performs Gmail API OAuth2 authentication and uses Google API client to fetch emails.
- Filters emails to exclude promotional content using regex.
- Extracts full email bodies (supports multi-part emails) and forwards email details (date, subject, body) to the server.
- Receives and sends processing acknowledgments for email tasks.
- Supports clean exit by forwarding "exit" messages to the server and closing WebSocket connections.

### 3. `client.html` — Browser WebSocket Chat Interface (Basic)

- Provides a simple web UI for chatting with the backend over WebSocket (`ws://localhost:8000`).
- Users type queries that are sent to the bridge client.
- Messages and server responses are displayed live.
- Provides “Send” and “Exit” buttons for interaction.
- The bridge client `client_bridge.py` serves as intermediary between browser and server.

### 4. `gemini_agent.py` — Google Gemini AI Integration

- Uses Google Generative AI Gemini models to generate content and extract structured data.
- Contains helper functions to:
  - Extract details like amounts, dates, keywords from email bodies.
  - Build Gmail search queries from user questions.
  - Produce summary answers to Gmail query results.
  - Extract expense data from summaries and replace placeholders with totals.

### 5. `calculator.py` — MCP (Math Computation Protocol) Server Client

- Defines a set of math tools and resources as asynchronous MCP tools (e.g., add, subtract, power, factorial).
- Used by the server to perform computations on extracted numerical data from email summaries.
- Provides demonstration of tool integration with the system's AI output.

***

## Environment and Dependencies

- Python 3.10+ recommended
- Libraries (listed in `requirements.txt`):
  - `websockets`
  - `fastapi`
  - `uvicorn`
  - `google-api-python-client`
  - `google-auth-oauthlib`
  - `google-generativeai`
  - `mcp`
  - `python-dotenv`
  - `Pillow`
  - `pywinauto`
  - `pywin32`
  - plus others as per `requirements.txt`
- Google API OAuth2 credentials: `credentials.json` required for Gmail API
- `.env` file with `GEMINI_API_KEY` for Google Gemini AI

***

## How to Run

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Prepare Google API credentials:**

- Obtain `credentials.json` for OAuth2 from Google Cloud Console (Gmail API enabled).
- Place in project root.
- On first run, OAuth2 flow will generate a `token.json` for Gmail API access.

3. **Set Gemini API key:**

- Add `GEMINI_API_KEY=your_api_key` to `.env` file (create if missing).

4. **Start the MCP Server Client (math tools):**

```bash
python calculator.py
```

5. **Start the WebSocket Server:**

```bash
python server.py
```

6. **Start the Bridge Client:**

```bash
python client_bridge.py
```

7. **Open the Browser Interface:**

- Open `client.html` in a modern browser.
- Connects to bridge client on `ws://localhost:8000`.

8. **Chat with the system:**
- Type natural language Gmail queries (e.g., "Show me my Amazon orders this year").
- The backend will fetch emails, analyze them, perform computations, and respond with summarized answers.

9. **Exit chat:**

- Click the `Exit` button in the web interface to close the connection cleanly.

***

## Summary of Data Flow

```
Browser <--> client.html (WebSocket UI)
   ||
   \/
Bridge WebSocket client (client_bridge.py, ws://localhost:8000)
   ||
   \/
Server WebSocket (server.py, ws://localhost:9000)
   ||
   \/
Gmail API + Google Gemini AI + MCP Tools
```

- Queries flow from the UI to the server via the bridge.
- Emails are fetched and processed by the server.
- Results, including AI summarization and computed values, are sent back to users.

***

## Code Notes

- The server maintains state per interaction and resets for each new user query.
- Connection resets and reconnections are handled with asyncio and websockets in an async-friendly way.
- Detailed debug print statements and error handling are integrated for easier tracing.
- Promotional emails filtered by regex for better relevance.
- AI assists in generating structured data and summaries from unstructured email content.
- MCP tools allow extensible computational capabilities on extracted data from emails.

***

This system showcases a full chat-enabled Gmail email analysis application integrating asynchronous Python websockets, Gmail API, and advanced AI text generation.

[1](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/29028422/53d93f56-7bf2-4a18-84c9-09b4fbc3ec26/client.html)
[2](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/29028422/7454e721-6f61-4a82-8cf5-fdf02d7fbf11/client_bridge.py)
[3](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/29028422/e89cceeb-9d52-4659-ae67-0c8ad231422d/calculator.py)
[4](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/29028422/254832f7-f526-4a47-b691-d540aed295dd/gemini_agent.py)
[5](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/29028422/e75374ae-3a6c-4191-9994-8bb5fef4653d/requirements.txt)
[6](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/29028422/aa075973-c971-4c31-afd0-aba441bed957/server.py)