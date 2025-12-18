from fastapi import FastAPI, Request
from pydantic import BaseModel
from run_agent import run_agent
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import sys

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to your frontend URL like ["http://localhost:3000"]
    allow_credentials=False,
    allow_methods=["*"],  # allow POST, GET, OPTIONS, etc.
    allow_headers=["*"],
)

# --- Session In-Memory Storage ---
session_store = {}

# --- Request Body Schema ---
class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    reply: str
    session_id: str

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_req: ChatRequest):
    session_id = chat_req.session_id
    message = chat_req.message

    # Initialize session history if not exists
    if session_id not in session_store:
        session_store[session_id] = []

    chat_history = session_store[session_id]

    # Append user message to chat history
    chat_history.append({"sender": "user", "message": message})

    # Run the agent
    reply = run_agent(message, chat_history)

    # Append bot reply to chat history
    chat_history.append({"sender": "bot", "message": reply})

    # Update session
    session_store[session_id] = chat_history

    return ChatResponse(reply=reply, session_id=session_id)


@app.get("/test")
async def hello():
    return {"message": "Hello RAG"}