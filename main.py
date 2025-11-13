from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()
# Import your RAG system
from rag_chatbot import RAGChatbotSystem

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Backend Configuration ============
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "your_pinecone_key_here")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "chatbot-rag-index")

# ============ Global System Instance ============
rag_system: Optional[RAGChatbotSystem] = None
SESSION_STORE = {}
CONVERSATION_HISTORY = {}

# ============ Pydantic Models ============

class ChatMessage(BaseModel):
    id: str
    content: str
    role: str
    timestamp: str
    character: str
    metadata: Optional[dict] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    id: str
    content: str
    role: str
    timestamp: str
    character: str
    session_id: str

class ConversationHistory(BaseModel):
    session_id: str
    character: str
    messages: List[ChatMessage]

class InitializeRequest(BaseModel):
    gemini_api_key: str  # Only Gemini key from user

# ============ History Management ============

def add_to_history(session_id: str, character_id: str, role: str, content: str):
    """Add message to history, maintaining only last 2 exchanges (4 messages total)"""
    key = f"{session_id}_{character_id}"
    
    if key not in CONVERSATION_HISTORY:
        CONVERSATION_HISTORY[key] = []
    
    CONVERSATION_HISTORY[key].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    
    if len(CONVERSATION_HISTORY[key]) > 4:
        CONVERSATION_HISTORY[key] = CONVERSATION_HISTORY[key][-4:]

def get_history(session_id: str, character_id: str) -> List[dict]:
    """Get conversation history for a character (max 2 exchanges = 4 messages)"""
    key = f"{session_id}_{character_id}"
    return CONVERSATION_HISTORY.get(key, [])

def clear_history(session_id: str, character_id: Optional[str] = None):
    """Clear conversation history for a session"""
    if character_id:
        key = f"{session_id}_{character_id}"
        if key in CONVERSATION_HISTORY:
            del CONVERSATION_HISTORY[key]
    else:
        keys_to_delete = [k for k in CONVERSATION_HISTORY.keys() if k.startswith(f"{session_id}_")]
        for key in keys_to_delete:
            del CONVERSATION_HISTORY[key]

# ============ System Initialization ============

@app.post("/initialize")
async def initialize_system(request: InitializeRequest):
    """Initialize the RAG system with Gemini key from user"""
    global rag_system
    
    try:
        print("Initializing RAG Chatbot System...")
        
        # Validate Gemini key is provided
        if not request.gemini_api_key:
            raise ValueError("Gemini API key is required")
        
        # Initialize RAG system with backend Pinecone key and user-provided Gemini key
        print("###########################################")
        key = request.gemini_api_key
        print("###########################################")
        rag_system = RAGChatbotSystem(
            pinecone_api_key=PINECONE_API_KEY,
            index_name=PINECONE_INDEX_NAME,
            gemini_api_key=key
        )
        
        print("✅ RAG System initialized successfully!")
        return {
            "status": "success",
            "message": "RAG system initialized",
            "characters": list(rag_system.chatbots.keys())
        }
    except Exception as e:
        print(f"❌ Failed to initialize RAG system: {e}")
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")

# ============ Session Management ============

@app.post("/sessions")
async def create_session():
    """Create a new chat session"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not initialized. Call /initialize first.")
    
    session_id = str(uuid.uuid4())
    SESSION_STORE[session_id] = {
        "created_at": datetime.now().isoformat(),
        "characters": list(rag_system.chatbots.keys())
    }
    
    return {
        "session_id": session_id,
        "characters": list(rag_system.chatbots.keys())
    }

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session information"""
    if session_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSION_STORE[session_id]
    return {
        "session_id": session_id,
        "created_at": session['created_at'],
        "characters": session['characters']
    }

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if session_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="Session not found")
    
    clear_history(session_id)
    del SESSION_STORE[session_id]
    return {"message": f"Session {session_id} deleted"}

# ============ Character-Specific Chat Routes ============

@app.post("/chat/karan")
async def chat_karan(request: ChatRequest) -> ChatResponse:
    """Chat with Karan Mehta (CFO)"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    session_id = request.session_id or "default_session"
    character_id = "karan"
    
    try:
        add_to_history(session_id, character_id, "user", request.message)
        
        response_text = rag_system.chat(
            session_id=session_id,
            character_id=character_id,
            message=request.message
        )
        
        add_to_history(session_id, character_id, "assistant", response_text)
        
        return ChatResponse(
            id=str(uuid.uuid4()),
            content=response_text,
            role="assistant",
            timestamp=datetime.now().isoformat(),
            character=character_id,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/chat/neha")
async def chat_neha(request: ChatRequest) -> ChatResponse:
    """Chat with Neha Singh (COO)"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    session_id = request.session_id or "default_session"
    character_id = "neha"
    
    try:
        add_to_history(session_id, character_id, "user", request.message)
        
        response_text = rag_system.chat(
            session_id=session_id,
            character_id=character_id,
            message=request.message
        )
        
        add_to_history(session_id, character_id, "assistant", response_text)
        
        return ChatResponse(
            id=str(uuid.uuid4()),
            content=response_text,
            role="assistant",
            timestamp=datetime.now().isoformat(),
            character=character_id,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/chat/arjun")
async def chat_arjun(request: ChatRequest) -> ChatResponse:
    """Chat with Arjun Sharma (Head of Legal)"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    session_id = request.session_id or "default_session"
    character_id = "arjun"
    
    try:
        add_to_history(session_id, character_id, "user", request.message)
        
        response_text = rag_system.chat(
            session_id=session_id,
            character_id=character_id,
            message=request.message
        )
        
        add_to_history(session_id, character_id, "assistant", response_text)
        
        return ChatResponse(
            id=str(uuid.uuid4()),
            content=response_text,
            role="assistant",
            timestamp=datetime.now().isoformat(),
            character=character_id,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/chat/raghav")
async def chat_raghav(request: ChatRequest) -> ChatResponse:
    """Chat with Raghav Patel (VP of Marketplace and Compliance)"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    session_id = request.session_id or "default_session"
    character_id = "raghav"
    
    try:
        add_to_history(session_id, character_id, "user", request.message)
        
        response_text = rag_system.chat(
            session_id=session_id,
            character_id=character_id,
            message=request.message
        )
        
        add_to_history(session_id, character_id, "assistant", response_text)
        
        return ChatResponse(
            id=str(uuid.uuid4()),
            content=response_text,
            role="assistant",
            timestamp=datetime.now().isoformat(),
            character=character_id,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ============ Conversation History Routes ============

@app.get("/history/{session_id}/{character_id}")
async def get_conversation_history(session_id: str, character_id: str):
    """Get conversation history for a character (last 2 exchanges only)"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    
    if character_id not in rag_system.chatbots:
        raise HTTPException(status_code=404, detail=f"Character '{character_id}' not found")
    
    try:
        history = get_history(session_id, character_id)
        
        return ConversationHistory(
            session_id=session_id,
            character=character_id,
            messages=[
                ChatMessage(
                    id=str(uuid.uuid4()),
                    content=msg['content'],
                    role=msg['role'],
                    timestamp=msg.get('timestamp', datetime.now().isoformat()),
                    character=character_id
                )
                for msg in history
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/history/{session_id}/{character_id}")
async def clear_session_history(session_id: str, character_id: str):
    """Clear conversation history for a character"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    
    if character_id not in rag_system.chatbots:
        raise HTTPException(status_code=404, detail=f"Character '{character_id}' not found")
    
    try:
        clear_history(session_id, character_id)
        return {
            "message": f"History cleared for {character_id} in session {session_id}",
            "remaining_messages": len(get_history(session_id, character_id))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)