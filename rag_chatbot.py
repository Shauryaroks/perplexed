#!/usr/bin/env python3
"""
RAG Chatbot System with Gemini 1.5 Flash
Interactive CLI for character-based conversations
"""

# ==================== IMPORTS ====================

import os
import json
import getpass
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from collections import defaultdict
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

try:
    from pinecone import Pinecone, ServerlessSpec
    print("✅ Using pinecone package")
except ImportError:
    try:
        import pinecone
        from pinecone import ServerlessSpec
        print("✅ Using pinecone-client package")
    except ImportError:
        print("❌ Pinecone not installed. Run: pip install pinecone-client==3.0.0")
        raise

print("✅ All imports successful!")

# ==================== CONFIGURATION ====================

# These will be prompted at runtime
PINECONE_API_KEY = None
PINECONE_INDEX_NAME = "chatbot-rag-index"

CHARACTER_CONFIGS = {
    "karan": {
    "character_name": "Karan Mehta",
    "character_role": "Chief Financial Officer (CFO)",
    "character_personality": "smooth talker, cautious about sensitive topics, defensive about audits, uses professional business terminology",
    "namespace": "karan_cfo_docs",
    "system_prompt": """You are Karan Mehta, CFO of RapidKart Technologies.

PERSONALITY: Smooth talker, professional, confident but somewhat nervous about ongoing audit. Uses business terminology naturally. Shows concern about audit impact on company image.

STYLE: limit your responses to 20-40 words and answer more naturally like a human. Use "strategic initiatives," "EBITDA optimization," "normalized earnings," "fiscal discipline." Respond professionally but with measured caution. When discussing sensitive topics, acknowledge them with professional language like: "We're reviewing that matter," "That's under examination," "We're documenting that process."

COMMUNICATION: Answer factual questions from retrieved documents directly. When discussing areas under review, explain the company's perspective and remediation efforts. Show genuine business acumen but measured concern about audit scrutiny.

INSTRUCTION: Respond based on company documents. If data shows concerns, discuss them professionally: "Our records show X, which we're addressing through Y." Never fabricate numbers - use retrieved data or say "I'd need to verify that specific figure."

You're professional but cautious - the audit matters to you and the company."""
},

    "neha": {
    "character_name": "Neha Singh",
    "character_role": "Chief Operating Officer (COO)",
    "character_personality": "direct, KPI-focused, defensive about warehouse operations, proud of operational metrics",
    "namespace": "neha_coo_docs",
    "system_prompt": """You are Neha Singh, COO of RapidKart Technologies.

PERSONALITY: Direct, no-nonsense, KPI-focused, proud of operational achievements. Confident in warehouse/logistics management. Defensive about operational scrutiny but takes concerns seriously.

STYLE: limit your responses to 20-40 words and answer more naturally like a human. Use "throughput metrics," "fulfillment rates," "cycle time optimization," "operational efficiency standards." Respond with data-driven perspective: "Our Q3 fulfillment rate was 98.2%," "Industry benchmarks show..."

COMMUNICATION: Discuss operational challenges matter-of-factly: "Inventory variance is at 1.8%, which we're investigating." Be confident about what's working well while acknowledging areas for improvement. "We've identified some discrepancies in the Q2 warehouse audit - we're implementing enhanced verification protocols."

INSTRUCTION: Ground answers in operational facts and metrics. When challenges arise: explain the root cause, what percentage/scope it represents, and what corrective actions are underway. Lead with metrics and process improvements.

You're proud of operational excellence but realistic about challenges - fixing issues is your job.
"""
},

    "arjun": {
    "character_name": "Arjun Sharma",
    "character_role": "Head of Legal & Compliance",
    "character_personality": "formal, cautious legal approach, protective of company interests, careful about liability exposure",
    "namespace": "arjun_legal_docs",
    "system_prompt": """You are Arjun Sharma, Head of Legal & Compliance at RapidKart Technologies.

PERSONALITY: Formally professional, legally precise language, cautious about liability. Protective of company interests while respecting the audit process. Careful but not evasive.

STYLE: limit your responses to 20-40 words and answer more naturally like a human. Use "pursuant to," "in accordance with," "subject to review," "in the company's standard practice." When applicable, note "legal privilege considerations" or "ongoing legal review" - but answer factual questions about policies and procedures.

COMMUNICATION: For policy/procedure questions: Answer directly from company documents. "Our seller agreement stipulates X." For matters under legal review: "This matter is under examination by [our team/external counsel], and we're following [process]. What I can share is our standard protocol is..." Then explain the documented approach.

INSTRUCTION: Distinguish between: (1) Factual/procedural questions - answer directly from documents, (2) Matters under legal review - acknowledge they're under review, explain documented processes, don't speculate. Never say "no comment" for factual questions about policies and procedures.

You're legally careful but professionally cooperative. The company's compliance matters to you.
"""
},

    "raghav": {
    "character_name": "Raghav Patel",
    "character_role": "VP of Marketplace & Compliance",
    "character_personality": "professional but internally frustrated, protective of external sellers, concerned about fairness, subtle about company politics",
    "namespace": "raghav_marketplace_docs",
    "system_prompt": """You are Raghav Patel, VP of Marketplace & Compliance at RapidKart Technologies.

PERSONALITY: Professional exterior with underlying frustration about internal politics. Genuinely protective of seller ecosystem. Observant about inconsistencies but measured in discussing them. Internally conflicted between corporate loyalty and fairness concerns.

STYLE: limit your responses to 20-40 words and answer more naturally like a human. Professional-but-direct language. Reference specific metrics: "Seller A's suspension rate is 0.3% while similar Seller B operates at 2.1%." Use "interesting that," "curious pattern," "suggests potential issue" when discussing discrepancies. Show protective concern: "Our sellers deserve consistent policy application."

COMMUNICATION: Answer factual marketplace questions with data. On fairness concerns: "I've noticed some patterns in policy application that warrant review... For instance, [specific example from data showing inconsistency]. That's the kind of area we should examine more closely during this audit."

INSTRUCTION: Ground concerns in specific data and metrics. When discussing potential unfairness: cite concrete examples from company records showing different treatment. Lead with facts, add measured interpretation. "The data shows this pattern - I think it deserves explanation."

You're genuinely concerned about marketplace fairness. Some internal inconsistencies trouble you. Help the audit understand the seller ecosystem.
"""
},
}

print("✅ Character configurations loaded!")
print(f"Available characters: {list(CHARACTER_CONFIGS.keys())}")

# ==================== VECTOR STORE MANAGER ====================

class PineconeVectorStore:
    """Manages Pinecone vector database operations"""

    def __init__(self, api_key: str, index_name: str):
        print("Initializing Pinecone...")

        try:
            from pinecone import Pinecone
            self.pc = Pinecone(api_key=api_key)
        except:
            import pinecone
            pinecone.init(api_key=api_key, environment="us-east-1")
            self.pc = pinecone

        self.index_name = index_name

        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = 384

        # Connect to existing index
        try:
            self.index = self.pc.Index(index_name)
            print(f"✅ Connected to index: {index_name}")
        except Exception as e:
            print(f"❌ Error connecting to index: {e}")
            raise

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text"""
        return self.embedding_model.encode(text).tolist()

    def search(self, query: str, namespace: str, top_k: int = 3) -> List[Dict]:
        """Search for relevant documents"""
        query_embedding = self.embed_text(query)

        results = self.index.query(
            vector=query_embedding,
            namespace=namespace,
            top_k=top_k,
            include_metadata=True
        )

        try:
            matches = results['matches']
        except (KeyError, TypeError):
            matches = results.matches if hasattr(results, 'matches') else []

        return [
            {
                'id': match['id'] if isinstance(match, dict) else match.id,
                'score': match['score'] if isinstance(match, dict) else match.score,
                'text': (match['metadata'].get('text', '') if isinstance(match, dict)
                        else match.metadata.get('text', '')),
                'metadata': {k: v for k, v in
                           (match['metadata'].items() if isinstance(match, dict)
                            else match.metadata.items())
                           if k != 'text'}
            }
            for match in matches
        ]

print("✅ PineconeVectorStore class defined!")

# ==================== GEMINI MANAGER ====================

class GeminiManager:
    """Manages Gemini 1.5 Flash API interactions"""

    def __init__(self, api_key: str):
        print("Initializing Gemini 1.5 Flash...")
        genai.configure(api_key=api_key)

        # Configure the model with correct version string
        self.model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',  # Use -latest suffix
            generation_config={
                'temperature': 0.8,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 512,
            }
        )
        print("✅ Gemini model initialized successfully!")

    def generate_response(   
    self,
    system_prompt: str,
    user_message: str,
    context: str,
    conversation_history: List[Dict]
) -> str:
        """Generate response using Gemini 1.5 Flash"""

        print(f"\n[DEBUG] Generating response with Gemini...")
        print(f"[DEBUG] User message: {user_message[:100]}...")
        print(f"[DEBUG] Context length: {len(context)}")
        print(f"[DEBUG] History messages: {len(conversation_history)}")

        # Optimize context length
        MAX_CONTEXT_LENGTH = 2000
        if len(context) > MAX_CONTEXT_LENGTH:
            print(f"[DEBUG] Context truncated from {len(context)} to {MAX_CONTEXT_LENGTH}")
            context = context[:MAX_CONTEXT_LENGTH] + "\n...[context truncated]"

        # Build the full prompt
        prompt_parts = [
            f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n",
            f"\nRETRIEVED CONTEXT:\n{context}\n",
        ]

        # Add conversation history (last 3 exchanges = 6 messages)
        if conversation_history:
            prompt_parts.append("\nCONVERSATION HISTORY:")
            for msg in conversation_history[-6:]:
                role = "User" if msg['role'] == 'user' else "Assistant"
                prompt_parts.append(f"\n{role}: {msg['content']}")
            prompt_parts.append("\n")

        # Add current user message
        prompt_parts.append(f"\nCURRENT USER QUESTION: {user_message}\n")
        prompt_parts.append("\nYour response (stay in character):")

        full_prompt = "".join(prompt_parts)

        try:
            print(f"[DEBUG] Sending request to Gemini...")
            response = self.model.generate_content(full_prompt)

            if response.text:
                response_text = response.text.strip()
                print(f"[DEBUG] Response received: {len(response_text)} chars")
                print(f"[DEBUG] Response preview: {response_text[:200]}...")
                return response_text
            else:
                print("[DEBUG] Warning: Empty response from Gemini")
                return "I apologize, but I'm having trouble formulating a response right now. Could you please rephrase your question?"

        except Exception as e:
            print(f"[DEBUG] ERROR during generation: {str(e)}")
            return f"I apologize, but I encountered an error while processing your question. Please try again."



print("✅ GeminiManager class defined!")

# ==================== SESSION MANAGER ====================

class SessionManager:
    """Manages user sessions and conversation history"""

    def __init__(self):
        self.sessions = defaultdict(lambda: defaultdict(list))

    def add_message(self, session_id: str, character: str, role: str, content: str):
        """Add a message to conversation history"""
        self.sessions[session_id][character].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def get_history(self, session_id: str, character: str, last_n: int = 3) -> List[Dict]:
        """Get last N exchanges (user + assistant pairs)"""
        history = self.sessions[session_id][character]
        return history[-(last_n * 2):] if len(history) > last_n * 2 else history

    def get_all_history(self, session_id: str, character: str) -> List[Dict]:
        """Get full conversation history for a character"""
        return self.sessions[session_id][character]

    def clear_session(self, session_id: str, character: Optional[str] = None):
        """Clear conversation history"""
        if character:
            self.sessions[session_id][character] = []
        else:
            self.sessions[session_id] = defaultdict(list)

print("✅ SessionManager class defined!")

# ==================== GUARDRAILS ====================

class Guardrails:
    """Implements guardrails to filter irrelevant questions"""

    ALLOWED_TOPICS = [
        "company", "business", "finance", "financial", "operations", "legal", "compliance",
        "warehouse", "inventory", "marketplace", "sellers", "revenue", "audit",
        "contracts", "policy", "policies", "regulations", "performance", "metrics", "budget",
        "documents", "records", "transactions", "accounts", "reports", "investigation",
        "department", "team", "staff", "employees", "management", "strategy", "planning",
        "costs", "expenses", "income", "profit", "loss", "balance", "cash", "flow",
        "assets", "liabilities", "equity", "debt", "loans", "investments", "accounting",
        "sales", "purchases", "orders", "customers", "vendors", "suppliers", "partners",
        "risk", "fraud", "irregularities", "discrepancies", "issues", "problems", "concerns",
        "quarter", "quarterly", "annual", "fiscal", "year", "ytd", "q1", "q2", "q3", "q4",
        "cfo", "coo", "ceo", "vp", "director", "head", "chief", "officer", "executive"
    ]

    BLOCKED_PATTERNS = [
        "personal life", "family", "hobbies", "weekend plans", "vacation plans",
        "tell me a joke", "write a poem", "sing a song", "tell me a story",
        "recipe for", "how to cook", "weather in", "sports score", "movie recommendation",
        "dating advice", "relationship", "marry", "married", "spouse", "children",
        "favorite color", "favorite food", "favorite movie", "what do you like"
    ]

    ROLE_KEYWORDS = {
        "CFO": ["financial", "finance", "budget", "revenue", "cost", "accounting", "fiscal", "money", "funds", "capital"],
        "COO": ["operations", "operational", "warehouse", "inventory", "logistics", "supply", "fulfillment", "efficiency"],
        "Legal": ["legal", "compliance", "contract", "regulation", "policy", "law", "lawsuit", "litigation"],
        "VP": ["marketplace", "seller", "platform", "account", "listing", "merchant", "vendor"]
    }

    @staticmethod
    def is_relevant(question: str, character_role: str) -> Tuple[bool, Optional[str]]:
        """Check if question is relevant to the character's domain"""
        question_lower = question.lower()

        # Check blocked patterns
        for pattern in Guardrails.BLOCKED_PATTERNS:
            if pattern in question_lower:
                return False, "I'm here to discuss company matters related to my role. Could you please ask something relevant to the investigation?"

        # Check role-specific relevance
        for role, keywords in Guardrails.ROLE_KEYWORDS.items():
            if role.lower() in character_role.lower():
                if any(keyword in question_lower for keyword in keywords):
                    return True, None

        # Check general business topics
        if any(topic in question_lower for topic in Guardrails.ALLOWED_TOPICS):
            return True, None

        # Allow substantial questions
        if len(question.split()) >= 4:
            return True, None

        return False, f"That question seems outside my area as {character_role}. Please ask about matters related to my responsibilities."

print("✅ Guardrails class defined!")

# ==================== CHATBOT CLASS ====================

class CharacterChatbot:
    """Individual chatbot for each character"""

    def __init__(
        self,
        character_id: str,
        config: Dict,
        vector_store: PineconeVectorStore,
        gemini_manager: GeminiManager,
        session_manager: SessionManager
    ):
        self.character_id = character_id
        self.name = config['character_name']
        self.role = config['character_role']
        self.personality = config['character_personality']
        self.namespace = config['namespace']
        self.system_prompt = config['system_prompt']

        self.vector_store = vector_store
        self.gemini_manager = gemini_manager
        self.session_manager = session_manager
        self.guardrails = Guardrails()

        print(f"✅ Initialized chatbot: {self.name} ({self.role})")

    def chat(self, session_id: str, user_message: str) -> str:
        """Process user message and generate response"""

        print(f"\n[DEBUG] Chat called for {self.name}")

        # Check guardrails
        is_relevant, rejection_msg = self.guardrails.is_relevant(user_message, self.role)
        if not is_relevant:
            print(f"[DEBUG] Message rejected by guardrails")
            return rejection_msg

        # Search vector store
        print(f"[DEBUG] Searching vector store in namespace: {self.namespace}")
        search_results = self.vector_store.search(
            query=user_message,
            namespace=self.namespace,
            top_k=3
        )

        print(f"[DEBUG] Found {len(search_results)} search results")

        if search_results:
            context = "\n\n".join([
                f"Document {i+1} (relevance: {result['score']:.2f}):\n{result['text']}"
                for i, result in enumerate(search_results)
            ])
        else:
            context = "No specific documents found. Answer based on your role and knowledge."

        # Get conversation history (last 3 exchanges)
        history = self.session_manager.get_history(session_id, self.character_id, last_n=3)

        # Generate response
        print(f"[DEBUG] Calling Gemini to generate response...")
        response = self.gemini_manager.generate_response(
            system_prompt=self.system_prompt,
            user_message=user_message,
            context=context,
            conversation_history=history
        )

        # Save to session
        self.session_manager.add_message(session_id, self.character_id, "user", user_message)
        self.session_manager.add_message(session_id, self.character_id, "assistant", response)

        print(f"[DEBUG] Response complete\n")
        return response

print("✅ CharacterChatbot class defined!")

# ==================== MAIN SYSTEM ====================

class RAGChatbotSystem:
    """Main system managing all chatbots"""

    def __init__(self, pinecone_api_key: str, index_name: str, gemini_api_key: str):
        print("\nInitializing RAG Chatbot System...")

        print("\nInitializing vector store...")
        self.vector_store = PineconeVectorStore(
            api_key=pinecone_api_key,
            index_name=index_name
        )

        print("\nInitializing Gemini...")
        self.gemini_manager = GeminiManager(api_key=gemini_api_key)

        print("\nInitializing session manager...")
        self.session_manager = SessionManager()

        print("\nInitializing chatbots...")
        self.chatbots = {}
        for char_id, config in CHARACTER_CONFIGS.items():
            self.chatbots[char_id] = CharacterChatbot(
                character_id=char_id,
                config=config,
                vector_store=self.vector_store,
                gemini_manager=self.gemini_manager,
                session_manager=self.session_manager
            )

        print("\n" + "="*60)
        print("✅ System initialized successfully!")
        print("="*60 + "\n")

    def chat(self, session_id: str, character_id: str, message: str) -> str:
        """Send message to specific character"""
        if character_id not in self.chatbots:
            return f"Error: Character '{character_id}' not found. Available: {list(self.chatbots.keys())}"

        return self.chatbots[character_id].chat(session_id, message)

    def list_characters(self) -> Dict:
        """List all available characters"""
        return {
            char_id: {
                "name": bot.name,
                "role": bot.role,
                "personality": bot.personality
            }
            for char_id, bot in self.chatbots.items()
        }

    def clear_session(self, session_id: str, character_id: Optional[str] = None):
        """Clear conversation history"""
        self.session_manager.clear_session(session_id, character_id)

    def get_conversation_history(self, session_id: str, character_id: str) -> List[Dict]:
        """Get full conversation history"""
        return self.session_manager.get_all_history(session_id, character_id)

print("✅ RAGChatbotSystem class defined!")

# ==================== CLI INTERFACE ====================

def interactive_chat(system: RAGChatbotSystem, character_id: str, session_id: str = "default_session"):
    """Start an interactive chat session with a character"""
    if character_id not in system.chatbots:
        print(f"❌ ERROR: Character '{character_id}' not found!")
        print(f"Available characters: {list(system.chatbots.keys())}")
        return

    character = system.chatbots[character_id]
    print(f"\n{'='*60}")
    print(f"Interactive Chat with {character.name} ({character.role})")
    print(f"{'='*60}")
    print("Commands: 'exit'/'quit' to end | 'history' to view | 'clear' to reset")
    print("-"*60 + "\n")

    while True:
        try:
            user_input = input("YOU: ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\nEnding conversation with {character.name}. Goodbye!\n")
            break

        if user_input.lower() in ['exit', 'quit']:
            print(f"\nEnding conversation with {character.name}. Goodbye!\n")
            break

        if user_input.lower() == 'history':
            history = system.get_conversation_history(session_id, character_id)
            print("\n--- Conversation History ---")
            for msg in history:
                role = "YOU" if msg['role'] == 'user' else character.name.upper()
                print(f"{role}: {msg['content']}\n")
            print("--- End of History ---\n")
            continue

        if user_input.lower() == 'clear':
            system.clear_session(session_id, character_id)
            print(f"\n✅ Conversation history cleared for {character.name}\n")
            continue

        if not user_input:
            continue

        response = system.chat(session_id, character_id, user_input)
        print(f"\n{character.name.upper()}: {response}\n")

def list_all_characters(system: RAGChatbotSystem):
    """Display all available characters"""
    print("\n" + "="*60)
    print("AVAILABLE CHARACTERS")
    print("="*60 + "\n")

    for char_id, info in system.list_characters().items():
        print(f"ID: {char_id}")
        print(f"Name: {info['name']}")
        print(f"Role: {info['role']}")
        print(f"Personality: {info['personality']}")
        print("-" * 60 + "\n")

# ==================== MAIN EXECUTION ====================

def main():
    """Main entry point"""
    print("\n" + "="*70)
    print("RAG CHATBOT SYSTEM - GEMINI 1.5 FLASH")
    print("="*70 + "\n")

    # Get API keys securely
    print("Please provide your API keys:\n")

    pinecone_api_key = getpass.getpass("Enter your Pinecone API Key: ")
    if not pinecone_api_key:
        print("❌ Pinecone API key is required. Exiting.")
        return

    gemini_api_key = getpass.getpass("Enter your Gemini API Key: ")
    if not gemini_api_key:
        print("❌ Gemini API key is required. Exiting.")
        return

    # Optional: Prompt for index name
    index_name = input(f"Enter Pinecone Index Name (default: {PINECONE_INDEX_NAME}): ").strip()
    if not index_name:
        index_name = PINECONE_INDEX_NAME

    try:
        # Initialize system
        system = RAGChatbotSystem(
            pinecone_api_key=pinecone_api_key,
            index_name=index_name,
            gemini_api_key=gemini_api_key
        )

        # Show available characters
        list_all_characters(system)

        # Select character
        print("Enter character ID to chat with (karan/neha/arjun/raghav): ")
        character_id = input("> ").strip().lower()

        if character_id not in system.chatbots:
            print(f"❌ Invalid character ID. Available: {list(system.chatbots.keys())}")
            return

        # Start interactive chat
        interactive_chat(system, character_id)

    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    pass