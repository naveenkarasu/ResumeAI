// Chat API functions

import { post, get, del } from './client';
import type { ChatRequest, ChatResponse } from '../types';

export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  return post<ChatResponse, ChatRequest>('/chat', request);
}

export async function getSuggestions(mode: string = 'chat'): Promise<string[]> {
  return get<string[]>(`/chat/suggestions?mode=${mode}`);
}

export async function getChatHistory(sessionId: string = 'default'): Promise<unknown[]> {
  return get<unknown[]>(`/chat/history?session_id=${sessionId}`);
}

export async function clearChatHistory(sessionId: string = 'default'): Promise<{ success: boolean; message: string }> {
  return del<{ success: boolean; message: string }>(`/chat/history?session_id=${sessionId}`);
}
