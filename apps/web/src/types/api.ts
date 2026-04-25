export type UserRole = 'user' | 'assistant';

export interface AuthUser {
  id: string;
  email: string;
  name?: string;
  role?: string;
}

export interface AuthResponse {
  token: string;
  message: string;
  user: AuthUser;
}

export interface ChatSource {
  file: string;
  page?: string;
  score?: number;
  preview?: string;
}

export interface ChatResponse {
  answer: string;
  question: string;
  sessionId: string;
  chunks_used: number;
  sources: ChatSource[];
}

export interface ChatSession {
  id: string;
  title: string;
  namespace: string;
  updatedAt: string;
  createdAt: string;
  isActive: boolean;
}

export interface ChatMessage {
  id: string;
  role: UserRole;
  content: string;
  createdAt: string;
  sources?: ChatSource[];
  chunksUsed?: number;
}

export interface WorkerStats {
  status?: string;
  total_chunks?: number;
  collection_name?: string;
  persist_directory?: string;
  embedding_model?: string;
}
