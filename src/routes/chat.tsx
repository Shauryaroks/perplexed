// src/routes/chat.tsx
import { Conversation, ConversationContent, ConversationScrollButton } from '@/components/ui/shadcn-io/ai/conversation';
import { createRoute } from '@tanstack/react-router'
import type { RootRoute } from '@tanstack/react-router'
import { Loader } from '@/components/ui/shadcn-io/ai/loader'
import { Message, MessageAvatar, MessageContent } from '@/components/ui/shadcn-io/ai/message';
import {
  PromptInput,
  PromptInputButton,
  PromptInputModelSelect,
  PromptInputModelSelectContent,
  PromptInputModelSelectItem,
  PromptInputModelSelectTrigger,
  PromptInputModelSelectValue,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputToolbar,
  PromptInputTools,
} from '@/components/ui/shadcn-io/ai/prompt-input';
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from '@/components/ui/shadcn-io/ai/reasoning';
import { Source, Sources, SourcesContent, SourcesTrigger } from '@/components/ui/shadcn-io/ai/source';
import { Button } from '@/components/ui/button';
import { PaperclipIcon, RotateCcwIcon } from 'lucide-react';
import { nanoid } from 'nanoid';
import { type FormEventHandler, useCallback, useEffect, useState } from 'react';
import { ModeToggle } from '@/components/mode-toggle';
import { Card } from '@/components/ui/card';
import { SelectionPopover } from '@/components/selection_popover';
// import z from 'zod';
import { Input } from '@/components/ui/input';

// ============ CONSTANTS ============
const API_BASE_URL = 'http://localhost:8000';

type ChatMessage = {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  reasoning?: string;
  sources?: Array<{ title: string; url: string }>;
  isStreaming?: boolean;
  character?: string;
};

// ============ CHANGE 1: UPDATE MODELS ARRAY ============
// BEFORE: GPT-4o, Claude, Gemini, Llama
// AFTER: Karan (CFO), Neha (COO), Arjun (Legal), Raghav (VP)
const models = [
  { id: 'karan', name: 'Karan Mehta', role: 'CFO' },
  { id: 'neha', name: 'Neha Singh', role: 'COO' },
  { id: 'arjun', name: 'Arjun Sharma', role: 'Legal Head' },
  { id: 'raghav', name: 'Raghav Patel', role: 'VP Marketplace' }
];

function Chat() {
  // ============ ORIGINAL STATE ============
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: nanoid(),
      content: "Hello! I'm your AI assistant. I can help you with coding questions, explain concepts, and provide guidance on web development topics. What would you like to know?",
      role: 'assistant',
      timestamp: new Date(),
      sources: [
        { title: "Getting Started Guide", url: "#" },
        { title: "API Documentation", url: "#" }
      ]
    }
  ]);

  const [inputValue, setInputValue] = useState('');
  const [selectedModel, setSelectedModel] = useState(models[0].id);
  const [isTyping, setIsTyping] = useState(false);
//  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);

  // Scratchpad state
  const [data, setData] = useState<string[]>([]);
  const [passPhraseForm, setPassPhrase] = useState("");

  // ============ CHANGE 2: ADD BACKEND STATE ============
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [initState, setInitState] = useState({ geminiKey: '', isInitializing: false });
  const [error, setError] = useState<string | null>(null);

  // ============ CHANGE 3: ADD INITIALIZATION FUNCTION ============
  const handleInitialize = useCallback(async (geminiKey: string) => {
    setInitState(prev => ({ ...prev, isInitializing: true }));
    setError(null);

    try {
      // Step 1: Initialize system with Gemini API key
      const initResponse = await fetch(`${API_BASE_URL}/initialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gemini_api_key: geminiKey })
      });

      if (!initResponse.ok) {
        const errorData = await initResponse.json();
        throw new Error(errorData.detail || 'Failed to initialize');
      }

      console.log('✅ System initialized');

      // Step 2: Create a new session
      const sessionResponse = await fetch(`${API_BASE_URL}/sessions`, {
        method: 'POST'
      });

      if (!sessionResponse.ok) {
        throw new Error('Failed to create session');
      }

      const sessionData = await sessionResponse.json();
      setSessionId(sessionData.session_id);
      setIsInitialized(true);
      console.log('✅ Session created:', sessionData.session_id);

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(`Initialization failed: ${message}`);
      console.error('Initialization error:', err);
    } finally {
      setInitState(prev => ({ ...prev, isInitializing: false }));
    }
  }, []);

  // ============ CHANGE 4: UPDATE handleSubmit (REPLACE ENTIRE FUNCTION) ============
  const handleSubmit: FormEventHandler<HTMLFormElement> = useCallback(async (event) => {
    event.preventDefault();

    if (!inputValue.trim() || isTyping || !sessionId || !isInitialized) return;

    // Add user message to UI
    const userMessage: ChatMessage = {
      id: nanoid(),
      content: inputValue.trim(),
      role: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    try {
      // Send message to backend
      const response = await fetch(`${API_BASE_URL}/chat/${selectedModel}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.content,
          session_id: sessionId
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Chat failed');
      }

      const data = await response.json();

      // Add assistant response to UI
      const assistantMessage: ChatMessage = {
        id: data.id,
        content: data.content,
        role: 'assistant',
        timestamp: new Date(data.timestamp),
        character: selectedModel
      };

      setMessages(prev => [...prev, assistantMessage]);
      setError(null);

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(`Chat error: ${message}`);

      // Show error message in chat
      const errorMessage: ChatMessage = {
        id: nanoid(),
        content: `Error: ${message}`,
        role: 'assistant',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }

  }, [inputValue, sessionId, isInitialized, selectedModel]);

  // ============ CHANGE 5: REPLACE handleReset ============
  const handleReset = useCallback(async () => {
    if (!sessionId) return;

    try {
      await fetch(`${API_BASE_URL}/history/${sessionId}/${selectedModel}`, {
        method: 'DELETE'
      });

      setMessages([
        {
          id: nanoid(),
          content: "Conversation cleared. What would you like to know?",
          role: 'assistant',
          timestamp: new Date(),
        }
      ]);
      setInputValue('');
      setIsTyping(false);
      // removed setStreamingMessageId(null) because streaming state is commented out
    } catch (err) {
      console.error('Failed to clear history:', err);
    }
  }, [sessionId, selectedModel]);

  // ============ SCRATCHPAD FUNCTIONS (UNCHANGED) ============
  function saveScratchPad(d: string[]) {
    localStorage.setItem("scratchpad-length", d.length.toString());
    for (let i = 0; i < d.length; i++) {
      localStorage.setItem(`scratchpad-${i}`, d[i]);
    }
  }

  function loadScratchPad(): string[] {
    const output = [];
    const length = parseInt(localStorage.getItem("scratchpad-length") ?? '0');
    for (let i = 0; i < length; i++) {
      const item = localStorage.getItem(`scratchpad-${i}`)
      if (item) output.push(item);
    }
    return output;
  }

  // ============ CHANGE 6: ADD INITIALIZATION USEEFFECT ============
  // Load scratchpad on mount
  useEffect(() => {
    setData(loadScratchPad());
  }, []);

  // Initialize backend connection on component mount
  useEffect(() => {
    const initChat = async () => {
      const savedKey = localStorage.getItem('gemini_api_key');

      if (savedKey) {
        // Auto-initialize with saved key
        await handleInitialize(savedKey);
      }
    };

    initChat();
  }, [handleInitialize]);

  // ============ CHANGE 7: SHOW INITIALIZATION SCREEN IF NOT READY ============
  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-slate-900 to-slate-800">
        <Card className="w-96 p-8">
          <h2 className="text-2xl font-bold mb-4">Initialize Chat System</h2>
          <p className="text-sm text-gray-400 mb-4">Enter your Gemini API Key to start</p>

          <Input
            type="password"
            placeholder="Enter Gemini API Key"
            value={initState.geminiKey}
            onChange={(e) => setInitState(prev => ({ ...prev, geminiKey: e.target.value }))}
            className="mb-4"
            disabled={initState.isInitializing}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                if (initState.geminiKey) {
                  handleInitialize(initState.geminiKey);
                  localStorage.setItem('gemini_api_key', initState.geminiKey);
                }
              }
            }}
          />

          {error && (
            <div className="text-red-500 text-sm mb-4 p-2 bg-red-100 rounded">
              {error}
            </div>
          )}

          <Button
            onClick={() => {
              if (initState.geminiKey) {
                handleInitialize(initState.geminiKey);
                localStorage.setItem('gemini_api_key', initState.geminiKey);
              }
            }}
            disabled={initState.isInitializing || !initState.geminiKey}
            className="w-full"
          >
            {initState.isInitializing ? 'Initializing...' : 'Start Chat'}
          </Button>
        </Card>
      </div>
    );
  }

  // ============ MAIN UI (UNCHANGED EXCEPT FOR ERROR DISPLAY) ============
  return (
    <div className="flex h-screen w-full flex-col overflow-hidden rounded-xl border bg-background shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b bg-muted/50 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="size-2 rounded-full bg-green-500" />
            <span className="font-medium text-sm">AI Assistant</span>
          </div>
          <div className="h-4 w-px bg-border" />
          <span className="text-muted-foreground text-xs">
            {models.find(m => m.id === selectedModel)?.name}
          </span>
        </div>
        <form className="w-1/2 flex gap-2" onSubmit={(e) => {
          e.preventDefault();
          alert("Correct passphrase, preceed to next level\n" + passPhraseForm)
        }}>
          <Input
            value={passPhraseForm}
            onChange={(e) => setPassPhrase(e.target.value.toLowerCase())}
            placeholder='Enter passphrase to unlock next level'
            required
          />
          <Button type="submit">Unlock</Button>
        </form>
        <div className="flex gap-4">
          <ModeToggle />
          <Button
            variant="ghost"
            size="sm"
            onClick={handleReset}
            className="h-8 px-2"
          >
            <RotateCcwIcon className="size-4" />
            <span className="ml-1">Reset</span>
          </Button>
        </div>
      </div>

      {/* Error Display (NEW) */}
      {error && (
        <div className="bg-red-100 border-b border-red-300 text-red-800 px-4 py-2 text-sm">
          {error}
        </div>
      )}

      {/* Conversation Area */}
      <Conversation className="flex-1">
        <SelectionPopover data={data} addData={(n) => {
          const x = [...data, n];
          setData(x);
          saveScratchPad(x);
        }} />
        <div className="flex h-full">
          <ConversationContent className="space-y-4">
            {messages.map((message) => (
              <div key={message.id} className="space-y-3">
                <Message from={message.role}>
                  <MessageContent>
                    {message.isStreaming && message.content === '' ? (
                      <div className="flex items-center gap-2">
                        <Loader size={14} />
                        <span className="text-muted-foreground text-sm">Thinking...</span>
                      </div>
                    ) : (
                      message.content
                    )}
                  </MessageContent>
                  <MessageAvatar
                    src={message.role === 'user' ? 'https://github.com/dovazencot.png' : 'https://github.com/vercel.png'}
                    name={message.role === 'user' ? 'User' : 'AI'}
                  />
                </Message>

                {/* Reasoning */}
                {message.reasoning && (
                  <div className="ml-10">
                    <Reasoning isStreaming={message.isStreaming} defaultOpen={false}>
                      <ReasoningTrigger />
                      <ReasoningContent>{message.reasoning}</ReasoningContent>
                    </Reasoning>
                  </div>
                )}

                {/* Sources */}
                {message.sources && message.sources.length > 0 && (
                  <div className="ml-10">
                    <Sources>
                      <SourcesTrigger count={message.sources.length} />
                      <SourcesContent>
                        {message.sources.map((source, index) => (
                          <Source key={index} href={source.url} title={source.title} />
                        ))}
                      </SourcesContent>
                    </Sources>
                  </div>
                )}
              </div>
            ))}
          </ConversationContent>
          <Card className="sm:w-1/2 flex flex-col items-center p-4 border-none bg-secondary rounded-none w-full">
            <div className="text-5xl">Scratch Pad</div>
            {data.map((item, i) => <div key={i} className="flex flex-col gap-4 bg-background p-4 w-full">
              <div>{item}</div>
              <div className="flex justify-between"><div></div><button onClick={() => {
                const n = data.slice();
                n.splice(i, 1);
                setData(n);
                saveScratchPad(n);
              }} className="bg-muted hover:bg-muted/50 p-4 pt-2 pb-2">Delete</button></div>
            </div>)}
          </Card>
        </div>
        <ConversationScrollButton />
      </Conversation>

      {/* Input Area */}
      <div className="border-t p-4">
        <PromptInput onSubmit={handleSubmit}>
          <PromptInputTextarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask me anything about development, coding, or technology..."
            disabled={isTyping || !isInitialized}
          />
          <PromptInputToolbar>
            <PromptInputTools>
              <PromptInputButton disabled={isTyping || !isInitialized}>
                <PaperclipIcon size={16} />
              </PromptInputButton>
              <PromptInputModelSelect
                value={selectedModel}
                onValueChange={setSelectedModel}
                disabled={isTyping || !isInitialized}
              >
                <PromptInputModelSelectTrigger>
                  <PromptInputModelSelectValue />
                </PromptInputModelSelectTrigger>
                <PromptInputModelSelectContent>
                  {models.map((model) => (
                    <PromptInputModelSelectItem key={model.id} value={model.id}>
                      {model.name}
                    </PromptInputModelSelectItem>
                  ))}
                </PromptInputModelSelectContent>
              </PromptInputModelSelect>
            </PromptInputTools>
            <PromptInputSubmit
              disabled={!inputValue.trim() || isTyping || !isInitialized}
              status={isTyping ? 'streaming' : 'ready'}
            />
          </PromptInputToolbar>
        </PromptInput>
      </div>
    </div>
  );
}

// broaden the generic to avoid cross-file RootRoute generic mismatches
export default (parentRoute: RootRoute<any>) =>
  createRoute({
    path: '/chat',
    component: Chat,
    getParentRoute: () => parentRoute,
  })
