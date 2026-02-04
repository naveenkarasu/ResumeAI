import { useState, useCallback } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { sendMessage, getSuggestions } from '../api/chat';
import type { Message, ChatRequest } from '../types';

interface UseChatOptions {
  mode?: 'chat' | 'email' | 'tailor' | 'interview';
  jobDescription?: string;
  useVerification?: boolean;
}

export function useChat(options: UseChatOptions = {}) {
  const { mode = 'chat', jobDescription, useVerification = false } = options;

  const [messages, setMessages] = useState<Message[]>([]);

  // Suggestions query
  const { data: suggestions = [] } = useQuery({
    queryKey: ['suggestions', mode],
    queryFn: () => getSuggestions(mode),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Send message mutation
  const mutation = useMutation({
    mutationFn: (message: string) => {
      const request: ChatRequest = {
        message,
        mode,
        job_description: jobDescription,
        use_verification: useVerification,
      };
      return sendMessage(request);
    },
    onMutate: (message) => {
      // Add user message immediately
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: message,
        timestamp: new Date(),
        mode,
      };
      setMessages((prev) => [...prev, userMessage]);
    },
    onSuccess: (response) => {
      // Add assistant response
      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.response,
        citations: response.citations,
        timestamp: new Date(),
        mode: response.mode,
        grounding_score: response.grounding_score,
        processing_time_ms: response.processing_time_ms,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    },
    onError: (error) => {
      // Add error message
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Something went wrong'}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    },
  });

  const sendChatMessage = useCallback(
    (message: string) => {
      mutation.mutate(message);
    },
    [mutation]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    sendMessage: sendChatMessage,
    clearMessages,
    isLoading: mutation.isPending,
    error: mutation.error,
    suggestions,
  };
}
