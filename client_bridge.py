import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import requests
import base64
import re
import asyncio
import websockets
import google.generativeai as genai
from dotenv import load_dotenv

import json
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

BROWSER_PORT = 8000
SERVER_URI = "ws://localhost:9000"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/contacts.readonly"
]

def authenticate_gmail():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def get_gmail_profile():
    service = authenticate_gmail()
    creds = service._http.credentials

    response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {creds.token}"}
    )

    if response.status_code == 200:
        data = response.json()
        return {
            "email": data.get("email"),
            "first_name": data.get("given_name"),
            "last_name": data.get("family_name"),
            "full_name": data.get("name"),
        }
    else:
        raise Exception(f"Error fetching profile: {response.text}")

def get_subject_and_snippet(message):
    headers = message["payload"]["headers"]
    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
    snippet = message.get("snippet", "")
    return subject.lower(), snippet.lower()

def is_promotional(subject, snippet):
    PROMO_REGEX = re.compile(
    r"(offer|sale|deal|limited time|hurry|exclusive|off|cheap\d+% off)",
    re.IGNORECASE
)
    text = subject + " " + snippet
    return bool(PROMO_REGEX.search(text))

def remove_quotes(text: str) -> str:
    quotes = ['"', "'", "“", "”", "‘", "’", "`"]
    for q in quotes:
        text = text.replace(q, "")
    return text

async def bridge_handler(browser_ws):
    async with websockets.connect(SERVER_URI) as server_ws:
        async for msg in browser_ws:
            max_results = 28  # Limit to check only 20 emails
            print(f"[BROWSER] {msg}")
            if msg.lower() == "exit":
                await server_ws.send("exit")
                break

            # forward to server
            await server_ws.send(msg)

            # wait for server response
            query = await server_ws.recv()
            query = remove_quotes(query)
            print(f"[SERVER] {query}")
            
            service = authenticate_gmail()
            print(f"Fetching emails with query: {query}")
            
            try:
                # Initial request
                results = service.users().messages().list(
                    userId="me", q=query, maxResults=1
                ).execute()
    
                messages = results.get("messages", [])
                next_page_token = results.get("nextPageToken")
    
                collected_snippets = []
                total_checked = 0
                total_nonpromo = 0
    
                while messages and total_nonpromo < max_results:
                    for msg in messages:
                        total_checked += 1
    
                        # Fetch full message
                        msg_data = service.users().messages().get(
                            userId="me", id=msg["id"], format="full"
                        ).execute()
    
                        headers = {h['name']: h['value'] for h in msg_data.get('payload', {}).get('headers', [])}
                        date = headers.get('Date', '')
                        subject = headers.get('Subject', '')
                        snippet_preview = msg_data.get("snippet", "")
    
                        # Check promotion filter
                        if is_promotional(subject, snippet_preview):
                            print(f"[{total_checked}] Skipping promotional mail: {subject}")
                            continue
    
                        total_nonpromo += 1
                        print(f"[{total_checked}] Keeping genuine mail: {subject}")
    
                        # Extract email body
                        body = ""
                        payload = msg_data.get("payload", {})
                        if "parts" in payload:
                            for part in payload["parts"]:
                                if part["mimeType"] in ["text/plain", "text/html"]:
                                    data = part["body"].get("data")
                                    if data:
                                        body += base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                        else:
                            data = payload.get("body", {}).get("data")
                            if data:
                                body += base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    
                        # Extract structured details from email body
                        await server_ws.send(date)
                        await server_ws.send(subject)
                        await server_ws.send(body)
                        try:
                            junk = await asyncio.wait_for(server_ws.recv(), timeout=5)
                        except asyncio.TimeoutError:
                            junk = None  # Or handle the timeout accordingly
                        print(junk)
                        #details = get_details_from_email_body(body, user_query)
    
                        if total_nonpromo >= max_results:
                            break
    
                    # Get next page if available
                    if total_nonpromo < max_results and next_page_token:
                        results = service.users().messages().list(
                            userId="me", q=query, maxResults=1, pageToken=next_page_token
                        ).execute()
                        messages = results.get("messages", [])
                        next_page_token = results.get("nextPageToken")
                    else:
                        break
    
                print(f"✅ Processed {total_checked} emails, kept {total_nonpromo} genuine ones.")
                await server_ws.send("Done")
                try:
                    junk = await asyncio.wait_for(server_ws.recv(), timeout=5)
                except asyncio.TimeoutError:
                    junk = None  # Or handle the timeout accordingly
                print(junk)
                await server_ws.send("How is it Going?")
                #print(collected_snippets)
                
                #await server_ws.send(collected_snippets)
                try:
                    summarized_email = await asyncio.wait_for(server_ws.recv(), timeout=20)
                except asyncio.TimeoutError:
                    summarized_email = None  # Or handle the timeout accordingly
                
                print("Server:", summarized_email)
                # send back to browser
                await browser_ws.send(summarized_email)

                
                
            except Exception as e:
                print(f"Error fetching emails: {str(e)}")

async def main():
    async with websockets.serve(bridge_handler, "localhost", BROWSER_PORT):
        print(f"Bridge started on ws://localhost:{BROWSER_PORT}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
