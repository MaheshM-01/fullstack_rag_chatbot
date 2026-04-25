import type {
  AuthResponse,
  ChatMessage,
  ChatResponse,
  ChatSession,
  WorkerStats,
} from '@/types/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001/api';

function extractErrorMessage(payload: any): string {
  if (!payload) return 'Request failed';
  if (typeof payload === 'string') return payload;

  const directMessage = payload.message;
  if (Array.isArray(directMessage)) return directMessage.join(', ');
  if (typeof directMessage === 'string') return directMessage;
  if (directMessage && typeof directMessage === 'object') {
    if (typeof directMessage.message === 'string') return directMessage.message;
    if (typeof directMessage.workerError === 'string') return directMessage.workerError;
  }

  if (typeof payload.error === 'string') return payload.error;
  if (typeof payload.detail === 'string') return payload.detail;

  return 'Request failed';
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers = new Headers(options.headers || {});
  const isFormData = options.body instanceof FormData;

  if (!isFormData) headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  const text = await response.text();
  let data: any = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { message: text };
    }
  }

  if (!response.ok) {
    throw new Error(extractErrorMessage(data));
  }

  return data as T;
}

export const api = {
  register: (payload: { email: string; password: string; name?: string }) =>
    request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  login: (payload: { email: string; password: string }) =>
    request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  health: () => request<{ status: string; service: string }>('/health', { method: 'GET' }),

  askQuestion: (
    token: string,
    payload: { question: string; sessionId?: string; namespace?: string; topK?: number },
  ) =>
    request<ChatResponse>(
      '/chat',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      token,
    ),

  getSessions: (token: string) =>
    request<ChatSession[]>('/chat/sessions', { method: 'GET' }, token),

  getMessages: (token: string, sessionId: string) =>
    request<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`, { method: 'GET' }, token),

  deleteSession: (token: string, sessionId: string) =>
    request<{ message: string }>(`/chat/sessions/${sessionId}`, { method: 'DELETE' }, token),

  ingestFile: (token: string, file: File, namespace: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('namespace', namespace);
    return request<any>(
      '/documents/upload',
      {
        method: 'POST',
        body: formData,
      },
      token,
    );
  },

  ingestUrl: (token: string, payload: { url: string; namespace?: string }) =>
    request<any>(
      '/documents/url',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      token,
    ),

  getStats: (token: string) =>
    request<WorkerStats>('/documents/stats', { method: 'GET' }, token),
};
