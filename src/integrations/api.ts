// API Service for Backend Communication
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: string;
  character: string;
  metadata?: any;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
}

export interface ChatResponse {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: string;
  character: string;
  session_id: string;
}

export interface InitializeRequest {
  gemini_api_key: string;
}

export interface SessionResponse {
  session_id: string;
  characters: string[];
}

class APIService {
  private baseURL: string;
  private sessionId: string | null = null;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  // Initialize RAG system with Gemini API key
  async initialize(geminiApiKey: string): Promise<{ status: string; characters: string[] }> {
    const response = await fetch(`${this.baseURL}/initialize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gemini_api_key: geminiApiKey })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Initialization failed');
    }

    return response.json();
  }

  // Create a new chat session
  async createSession(): Promise<SessionResponse> {
    const response = await fetch(`${this.baseURL}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error('Failed to create session');
    }

    const data = await response.json();
    this.sessionId = data.session_id;
    return data;
  }

  // Send message to specific character
  async sendMessage(
    characterId: string,
    message: string,
    sessionId?: string
  ): Promise<ChatResponse> {
    const sid = sessionId || this.sessionId;
    
    const response = await fetch(`${this.baseURL}/chat/${characterId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message, 
        session_id: sid 
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to send message');
    }

    return response.json();
  }

  // Get conversation history
  async getHistory(sessionId: string, characterId: string): Promise<ChatMessage[]> {
    const response = await fetch(
      `${this.baseURL}/history/${sessionId}/${characterId}`
    );

    if (!response.ok) {
      throw new Error('Failed to fetch history');
    }

    const data = await response.json();
    return data.messages;
  }

  // Clear conversation history
  async clearHistory(sessionId: string, characterId: string): Promise<void> {
    const response = await fetch(
      `${this.baseURL}/history/${sessionId}/${characterId}`,
      { method: 'DELETE' }
    );

    if (!response.ok) {
      throw new Error('Failed to clear history');
    }
  }

  // Get current session ID
  getSessionId(): string | null {
    return this.sessionId;
  }

  // Set session ID manually
  setSessionId(sessionId: string): void {
    this.sessionId = sessionId;
  }
}

// Export singleton instance
export const apiService = new APIService();
