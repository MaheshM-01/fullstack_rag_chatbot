const TOKEN_KEY = 'rag-chatbot-token';
const USER_KEY = 'rag-chatbot-user';

export function getAuthToken() {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem(TOKEN_KEY) || '';
}

export function saveAuthToken(token: string) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAuthToken() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
}

export function saveUser(user: unknown) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getUser<T>() {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function clearUser() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(USER_KEY);
}
