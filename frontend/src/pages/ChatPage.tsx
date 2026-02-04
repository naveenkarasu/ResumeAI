import { useState, useEffect, useCallback } from 'react';
import { ChatHistory, ChatInput } from '../components/chat';
import { useChat } from '../hooks/useChat';
import { useToast } from '../components/ui';
import { CHAT_MODES } from '../types';

export function ChatPage() {
  const [mode, setMode] = useState<'chat' | 'email' | 'tailor' | 'interview'>('chat');
  const [jobDescription, setJobDescription] = useState('');
  const [showJobInput, setShowJobInput] = useState(false);
  const toast = useToast();

  const currentMode = CHAT_MODES.find((m) => m.id === mode)!;

  const { messages, sendMessage, clearMessages, isLoading, suggestions } = useChat({
    mode,
    jobDescription: currentMode.requiresJobDescription ? jobDescription : undefined,
  });

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + K to clear chat
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        clearMessages();
        toast.info('Chat cleared');
      }
      // Ctrl/Cmd + 1-4 to switch modes
      if ((e.ctrlKey || e.metaKey) && ['1', '2', '3', '4'].includes(e.key)) {
        e.preventDefault();
        const modes = ['chat', 'email', 'tailor', 'interview'] as const;
        const idx = parseInt(e.key) - 1;
        setMode(modes[idx]);
        toast.info(`Switched to ${CHAT_MODES[idx].label} mode`);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [clearMessages, toast]);

  // Show job input when mode requires it
  useEffect(() => {
    if (currentMode.requiresJobDescription && !jobDescription) {
      setShowJobInput(true);
    }
  }, [currentMode.requiresJobDescription, jobDescription]);

  const handleCopyLastResponse = useCallback(() => {
    const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant');
    if (lastAssistant) {
      navigator.clipboard.writeText(lastAssistant.content);
      toast.success('Copied to clipboard');
    }
  }, [messages, toast]);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-gray-900">Chat</h1>
          <p className="text-sm text-gray-500 hidden sm:block">Ask questions about your resume</p>
        </div>

        {/* Mode selector - horizontal scroll on mobile */}
        <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
          {CHAT_MODES.map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                mode === m.id
                  ? 'bg-primary-100 text-primary-700 font-medium'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              title={m.description}
            >
              <span className="mr-1">{m.icon}</span>
              <span className="hidden sm:inline">{m.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Job description input (collapsible on mobile) */}
      {currentMode.requiresJobDescription && (
        <div className="mb-4">
          <button
            onClick={() => setShowJobInput(!showJobInput)}
            className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2 sm:hidden"
          >
            <span>{showJobInput ? '▼' : '▶'}</span>
            Job Description {jobDescription ? '✓' : '(required)'}
          </button>
          <div className={`${showJobInput ? 'block' : 'hidden sm:block'}`}>
            <label className="block text-sm font-medium text-gray-700 mb-2 hidden sm:block">
              Job Description
            </label>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the job description here..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
            />
          </div>
        </div>
      )}

      {/* Chat container */}
      <div className="flex-1 bg-white rounded-lg border border-gray-200 flex flex-col overflow-hidden min-h-0">
        {/* Messages */}
        <ChatHistory messages={messages} isLoading={isLoading} />

        {/* Suggestions */}
        {messages.length === 0 && suggestions.length > 0 && (
          <div className="px-3 md:px-4 pb-3 md:pb-4 flex flex-wrap gap-2">
            {suggestions.slice(0, 4).map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => sendMessage(suggestion)}
                className="px-3 py-1.5 bg-gray-100 text-gray-700 text-xs md:text-sm rounded-full hover:bg-gray-200 transition-colors line-clamp-1"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        {/* Input area */}
        <div className="p-3 md:p-4 border-t border-gray-200">
          <div className="flex gap-2">
            <div className="flex gap-1">
              <button
                onClick={clearMessages}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                title="Clear chat (Ctrl+K)"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
              {messages.length > 0 && (
                <button
                  onClick={handleCopyLastResponse}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Copy last response"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </button>
              )}
            </div>
            <div className="flex-1">
              <ChatInput
                onSend={sendMessage}
                disabled={isLoading || (currentMode.requiresJobDescription && !jobDescription.trim())}
                placeholder={
                  currentMode.requiresJobDescription && !jobDescription.trim()
                    ? 'Enter job description first...'
                    : `${currentMode.description}...`
                }
              />
            </div>
          </div>
          {/* Keyboard shortcut hint */}
          <div className="hidden md:flex gap-4 mt-2 text-xs text-gray-400">
            <span>Enter to send</span>
            <span>Ctrl+K to clear</span>
            <span>Ctrl+1-4 to switch modes</span>
          </div>
        </div>
      </div>
    </div>
  );
}
