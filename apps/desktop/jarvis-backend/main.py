"""
Jarvis AI Backend - Local AI Server
A simple local AI server for the Jarvis desktop app.
This provides a real backend without depending on Hermes.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("jarvis-backend")

# App configuration
APP_NAME = "Jarvis"
APP_VERSION = "1.0.0"
DEFAULT_MODEL = "local"
DEFAULT_PORT = 8765

# FastAPI app
app = FastAPI(title="Jarvis AI Backend", version=APP_VERSION)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: str
    model: Optional[str] = None
    agent_name: Optional[str] = None
    provider: Optional[str] = None  # "local", "openai", "anthropic", "gemini"

class ChatResponse(BaseModel):
    response: str
    session_id: str
    model: str
    timestamp: str

class StatusResponse(BaseModel):
    name: str
    version: str
    status: str
    model: str
    timestamp: str
    provider: str

# In-memory session storage (replace with SQLite later)
sessions: dict[str, list[dict]] = {}

# Mock AI responses (replace with real LLM later)
MOCK_RESPONSES = [
    "Hello! I'm {name}. How can I help you today?",
    "That's an interesting question. Let me think about it...",
    "I understand what you're saying. Tell me more about it.",
    "Great! I'm {name} and I'm here to help with anything you need.",
    "I've noted that down. Is there anything else you'd like to discuss?",
    "Thanks for sharing that with me. How can I assist further?",
]

def get_response(message: str, name: str, style: str, provider: str = "local", openai_key: str = "", anthropic_key: str = "", gemini_key: str = "") -> str:
    """Generate response using real AI API or fallback to mock."""
    import time
    time.sleep(1.0)
    
    # Use provided keys (from settings) instead of environment variables
    openai_key = openai_key or os.getenv("OPENAI_API_KEY", "")
    anthropic_key = anthropic_key or os.getenv("ANTHROPIC_API_KEY", "")
    gemini_key = gemini_key or os.getenv("GEMINI_API_KEY", "")
    
    # Try OpenAI
    if openai_key:
        try:
            import httpx
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": message}],
                    "max_tokens": 100,
                },
                headers={"Authorization": f"Bearer {openai_key}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OpenAI API error: {e}")
    
    # Try Anthropic
    if anthropic_key:
        try:
            import httpx
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 100,
                    "messages": [{"role": "user", "content": message}]
                },
                headers={
                    "x-api-key": anthropic_key,
                    "Content-Type": "application/json",
                    "Anthropic-Version": "2023-06-01"
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data["content"][0]["text"]
        except Exception as e:
            logger.warning(f"Anthropic API error: {e}")
    
    # Try Google Gemini
    if gemini_key:
        try:
            import httpx
            response = httpx.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
                json={
                    "contents": [{"parts": [{"text": message}]}]
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.warning(f"Gemini API error: {e}")
    
    # Fallback to mock response
    if style == "friendly":
        response = MOCK_RESPONSES[0]
    elif style == "professional":
        response = "Thank you for your message. I understand your request."
    elif style == "casual":
        response = "Hey! Got your message. What's up?"
    else:
        response = MOCK_RESPONSES[0]
    
    response = response.replace("{name}", name)
    return response
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Jarvis AI Backend shutting down")

@app.get("/", response_model=StatusResponse)
async def root():
    """Get app status."""
    return StatusResponse(
        name=APP_NAME,
        version=APP_VERSION,
        status="running",
        model=DEFAULT_MODEL,
        timestamp=datetime.now().isoformat()
    )

@app.get("/api/status")
async def status():
    """Get backend status."""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "model": DEFAULT_MODEL,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat messages."""
    try:
        # Initialize session if needed
        if request.session_id not in sessions:
            sessions[request.session_id] = []
        
        # Add user message
        user_message = {"role": "user", "content": request.message, "timestamp": datetime.now().isoformat()}
        sessions[request.session_id].append(user_message)
        
        # Determine provider (use request provider or default to "local")
        provider = request.provider or "local"
        
        # Generate response using the selected provider
        response = get_response(
            message=request.message,
            name=request.agent_name or APP_NAME,
            style="friendly",
            provider=provider,
            openai_key=os.getenv("OPENAI_API_KEY", ""),
            anthropic_key=os.getenv("ANTHROPIC_API_KEY", ""),
            gemini_key=os.getenv("GEMINI_API_KEY", ""),
        )
        
        # Add assistant response
        assistant_message = {"role": "assistant", "content": response, "timestamp": datetime.now().isoformat()}
        sessions[request.session_id].append(assistant_message)
        
        return ChatResponse(
            response=response,
            session_id=request.session_id,
            model=f"{provider}-model",
            timestamp=datetime.now().isoformat(),
            provider=provider,
        )
    
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
async def list_sessions():
    """List all sessions."""
    return {
        "sessions": [
            {"id": sid, "message_count": len(msgs), "updated": msgs[-1]["timestamp"] if msgs else None}
            for sid, msgs in sessions.items()
        ]
    }

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"id": session_id, "messages": sessions[session_id]}

# OAuth endpoints for Google and OpenAI
@app.get("/api/oauth/{provider}/start")
async def oauth_start(provider: str):
    """Start OAuth flow for a provider."""
    if provider not in OAUTH_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    
    config = OAUTH_CONFIGS[provider]
    
    # Generate state for CSRF protection
    state = str(uuid.uuid4())
    oauth_states[state] = {
        "provider": provider,
        "redirect_to": "http://localhost:5174",
    }
    
    # Build authorization URL
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": config["scope"],
        "state": state,
    }
    
    auth_url = f"{config['auth_url']}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
    
    return {"auth_url": auth_url, "state": state}

@app.get("/api/oauth/{provider}/callback")
async def oauth_callback(provider: str, code: str = None, error: str = None, state: str = None):
    """Handle OAuth callback from provider."""
    if error:
        return {"error": error}
    
    if not code or not state:
        return {"error": "Missing code or state"}
    
    # Verify state
    if state not in oauth_states:
        return {"error": "Invalid state"}
    
    # Exchange code for token
    config = OAUTH_CONFIGS.get(provider)
    if not config:
        return {"error": f"Unsupported provider: {provider}"}
    
    try:
        import httpx
        response = httpx.post(
            config["token_url"],
            data={
                "code": code,
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "redirect_uri": config["redirect_uri"],
                "grant_type": "authorization_code",
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return {"error": f"Token exchange failed: {response.text}"}
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now().timestamp() + expires_in
        
        # Store token
        oauth_tokens[provider] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
        }
        
        # Get user info
        user_info = None
        if provider == "google":
            info_response = httpx.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )
            if info_response.status_code == 200:
                user_info = info_response.json()
        
        return {
            "success": True,
            "access_token": access_token,
            "user_info": user_info,
            "redirect_to": "http://localhost:5174",
        }
    
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return {"error": str(e)}

@app.post("/api/oauth/{provider}/refresh")
async def oauth_refresh(provider: str):
    """Refresh OAuth token."""
    if provider not in oauth_tokens:
        raise HTTPException(status_code=404, detail="Token not found")
    
    token_data = oauth_tokens[provider]
    
    if token_data["expires_at"] > datetime.now().timestamp():
        # Token still valid, return it
        return {"access_token": token_data["access_token"]}
    
    # Refresh token
    config = OAUTH_CONFIGS.get(provider)
    if not config:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    
    try:
        import httpx
        response = httpx.post(
            config["token_url"],
            data={
                "refresh_token": token_data["refresh_token"],
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "grant_type": "refresh_token",
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return {"error": "Token refresh failed", "details": response.text}
        
        token_data = response.json()
        new_access_token = token_data.get("access_token")
        new_refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        
        # Update stored token
        token_data["access_token"] = new_access_token
        if new_refresh_token:
            token_data["refresh_token"] = new_refresh_token
        token_data["expires_at"] = datetime.now().timestamp() + expires_in
        
        return {"access_token": new_access_token}
    
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return {"error": str(e)}

@app.post("/api/oauth/{provider}/revoke")
async def oauth_revoke(provider: str):
    """Revoke OAuth token."""
    if provider in oauth_tokens:
        del oauth_tokens[provider]
    return {"success": True}

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id in sessions:
        del sessions[session_id]
    return {"success": True}

@app.post("/api/sessions/{session_id}/clear")
async def clear_session(session_id: str):
    """Clear a session's messages."""
    if session_id in sessions:
        sessions[session_id] = []
    return {"success": True}

# WebSocket endpoint for real-time communication
@app.websocket("/ws")
async def websocket_endpoint(websocket):
    """Handle WebSocket connections."""
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            session_id = data.get("session_id", str(uuid.uuid4()))
            
            # Get response
            response = get_response(message, "Jarvis", "friendly")
            
            await websocket.send_json({
                "type": "response",
                "response": response,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            })
    
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await websocket.close()

# API key configuration (for future use with cloud AI)
# Store API keys securely - load from environment variables
import os
from pathlib import Path

# API keys loaded from .env file or environment
API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY", ""),
    "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
    "gemini": os.getenv("GEMINI_API_KEY", ""),
}

# Check if any API keys are configured
HAS_API_KEYS = any(bool(key) for key in API_KEYS.values())

# OAuth configuration (for Google Gemini)
OAUTH_CONFIGS = {
    "google": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8765/callback/google"),
        "scope": "https://www.googleapis.com/auth/cloud-platform https://www.googleapis.com/auth/generativeai",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
    }
}

# In-memory OAuth token storage (replace with database later)
oauth_tokens = {}  # {provider: {access_token, refresh_token, expires_at, user_email}}

# OAuth state for CSRF protection
oauth_states = {}  # {state: {provider, redirect_to}}

if __name__ == "__main__":
    logger.info(f"Starting {APP_NAME} AI Backend on port {DEFAULT_PORT}")
    logger.info(f"API Keys configured: {HAS_API_KEYS}")
    uvicorn.run(
        "jarvis_backend:app",
        host="0.0.0.0",
        port=DEFAULT_PORT,
        reload=True,
        log_level="info"
    )
