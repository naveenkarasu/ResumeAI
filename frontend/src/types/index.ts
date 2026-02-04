// API Types - matching backend Pydantic models

export interface Citation {
  section: string;
  text: string;
  relevance_score: number;
}

export interface ChatResponse {
  response: string;
  citations: Citation[];
  mode: string;
  grounding_score?: number;
  search_mode?: string;
  processing_time_ms?: number;
}

export interface ChatRequest {
  message: string;
  mode: 'chat' | 'email' | 'tailor' | 'interview';
  job_description?: string;
  use_verification?: boolean;
}

export interface BackendInfo {
  name: string;
  status: string;
  model: string;
  is_active: boolean;
}

export interface SettingsResponse {
  backend: string;
  available_backends: BackendInfo[];
  use_hybrid_search: boolean;
  use_hyde: boolean;
  use_reranking: boolean;
  use_grounding: boolean;
  indexed_documents: number;
  total_chunks: number;
}

export interface StatusResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  uptime_seconds: number;
  rag_initialized: boolean;
  active_backend: string;
  indexed_documents: number;
  last_index_time?: string;
  components: Record<string, string>;
}

export interface SettingsUpdateRequest {
  backend?: string;
  use_hybrid_search?: boolean;
  use_hyde?: boolean;
  use_reranking?: boolean;
  use_grounding?: boolean;
}

// UI Types
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  timestamp: Date;
  mode?: string;
  grounding_score?: number;
  processing_time_ms?: number;
}

export interface ChatMode {
  id: 'chat' | 'email' | 'tailor' | 'interview';
  label: string;
  description: string;
  icon: string;
  requiresJobDescription: boolean;
}

export const CHAT_MODES: ChatMode[] = [
  {
    id: 'chat',
    label: 'Chat',
    description: 'Ask questions about your resume',
    icon: '💬',
    requiresJobDescription: false,
  },
  {
    id: 'email',
    label: 'Email',
    description: 'Generate application emails',
    icon: '✉️',
    requiresJobDescription: true,
  },
  {
    id: 'tailor',
    label: 'Tailor',
    description: 'Get resume tailoring suggestions',
    icon: '✨',
    requiresJobDescription: true,
  },
  {
    id: 'interview',
    label: 'Interview',
    description: 'Interview preparation help',
    icon: '🎤',
    requiresJobDescription: false,
  },
];
