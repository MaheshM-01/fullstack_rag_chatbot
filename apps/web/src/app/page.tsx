'use client';

import { CSSProperties, FormEvent, useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
import {
  clearAuthToken,
  clearUser,
  getAuthToken,
  getUser,
  saveAuthToken,
  saveUser,
} from '@/lib/storage';
import type { AuthUser, ChatMessage, ChatSession, WorkerStats } from '@/types/api';

type AuthMode = 'login' | 'register';
type FlashMessage = { type: 'success' | 'error'; text: string } | null;

const STACK_GAP: CSSProperties = { display: 'grid', gap: '12px' };

function formatTime(value?: string) {
  if (!value) return '';
  return new Date(value).toLocaleString();
}

export default function HomePage() {
  const [mounted, setMounted] = useState(false);
  const [token, setToken] = useState('');
  const [user, setUser] = useState<AuthUser | null>(null);

  const [authMode, setAuthMode] = useState<AuthMode>('login');
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');
  const [authForm, setAuthForm] = useState({
    name: '',
    email: '',
    password: '',
  });

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState('');
  const [question, setQuestion] = useState('');
  const [namespace, setNamespace] = useState('default');
  const [topK, setTopK] = useState(5);

  const [stats, setStats] = useState<WorkerStats | null>(null);
  const [docFlash, setDocFlash] = useState<FlashMessage>(null);
  const [docLoading, setDocLoading] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [urlInput, setUrlInput] = useState('');

  const isAuthenticated = Boolean(token && user);

  const selectedSession = useMemo(
    () => sessions.find((session) => session.id === selectedSessionId) || null,
    [selectedSessionId, sessions],
  );

  useEffect(() => {
    setMounted(true);
    const savedToken = getAuthToken();
    const savedUser = getUser<AuthUser>();
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(savedUser);
    }
  }, []);

  useEffect(() => {
    if (!token) return;
    void refreshSessions(token);
    void refreshStats(token);
  }, [token]);

  async function refreshSessions(authToken: string) {
    try {
      const nextSessions = await api.getSessions(authToken);
      setSessions(nextSessions);

      if (!nextSessions.length) {
        setSelectedSessionId('');
        setMessages([]);
        return;
      }

      const currentSelection = nextSessions.find((s) => s.id === selectedSessionId);
      const sessionToLoad = currentSelection || nextSessions[0];

      if (!currentSelection) setSelectedSessionId(sessionToLoad.id);
      await loadMessages(authToken, sessionToLoad.id);
    } catch (error: any) {
      setChatError(error.message || 'Failed to load chat sessions');
    }
  }

  async function refreshStats(authToken: string) {
    try {
      const nextStats = await api.getStats(authToken);
      setStats(nextStats);
    } catch (error: any) {
      setDocFlash({ type: 'error', text: error.message || 'Failed to load knowledge-base stats' });
    }
  }

  async function loadMessages(authToken: string, sessionId: string) {
    const nextMessages = await api.getMessages(authToken, sessionId);
    setMessages(nextMessages);
  }

  async function handleAuthSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthLoading(true);
    setAuthError('');

    try {
      const payload =
        authMode === 'register'
          ? {
              name: authForm.name.trim() || undefined,
              email: authForm.email.trim(),
              password: authForm.password,
            }
          : {
              email: authForm.email.trim(),
              password: authForm.password,
            };

      const response = authMode === 'register' ? await api.register(payload) : await api.login(payload);

      setToken(response.token);
      setUser(response.user);
      saveAuthToken(response.token);
      saveUser(response.user);

      setAuthForm({ name: '', email: '', password: '' });
    } catch (error: any) {
      setAuthError(error.message || 'Authentication failed');
    } finally {
      setAuthLoading(false);
    }
  }

  function handleLogout() {
    setToken('');
    setUser(null);
    setSessions([]);
    setSelectedSessionId('');
    setMessages([]);
    setQuestion('');
    clearAuthToken();
    clearUser();
  }

  async function handleSessionClick(sessionId: string) {
    if (!token) return;
    setSelectedSessionId(sessionId);
    setChatError('');
    try {
      await loadMessages(token, sessionId);
    } catch (error: any) {
      setChatError(error.message || 'Failed to load messages');
    }
  }

  async function handleDeleteSession(sessionId: string) {
    if (!token) return;
    try {
      await api.deleteSession(token, sessionId);
      await refreshSessions(token);
    } catch (error: any) {
      setChatError(error.message || 'Failed to delete session');
    }
  }

  async function handleSendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;

    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) return;

    setChatLoading(true);
    setChatError('');

    const optimisticUserMessage: ChatMessage = {
      id: `temp-user-${Date.now()}`,
      role: 'user',
      content: trimmedQuestion,
      createdAt: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticUserMessage]);
    setQuestion('');

    try {
      const response = await api.askQuestion(token, {
        question: trimmedQuestion,
        namespace,
        topK,
        sessionId: selectedSessionId || undefined,
      });

      const assistantMessage: ChatMessage = {
        id: `temp-assistant-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        createdAt: new Date().toISOString(),
        sources: response.sources || [],
        chunksUsed: response.chunks_used,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setSelectedSessionId(response.sessionId);

      const nextSessions = await api.getSessions(token);
      setSessions(nextSessions);
    } catch (error: any) {
      setChatError(error.message || 'Failed to send message');
    } finally {
      setChatLoading(false);
    }
  }

  async function handleFileUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !uploadFile) return;

    setDocLoading(true);
    setDocFlash(null);

    try {
      const result = await api.ingestFile(token, uploadFile, namespace);
      setDocFlash({
        type: 'success',
        text: `${result.file_name || uploadFile.name} ingested with ${result.chunks_created || 0} chunks`,
      });
      setUploadFile(null);
      await refreshStats(token);
    } catch (error: any) {
      setDocFlash({ type: 'error', text: error.message || 'File ingestion failed' });
    } finally {
      setDocLoading(false);
    }
  }

  async function handleUrlIngest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !urlInput.trim()) return;

    setDocLoading(true);
    setDocFlash(null);

    try {
      const result = await api.ingestUrl(token, {
        url: urlInput.trim(),
        namespace,
      });
      setDocFlash({
        type: 'success',
        text: `${result.file_name || 'URL'} ingested with ${result.chunks_created || 0} chunks`,
      });
      setUrlInput('');
      await refreshStats(token);
    } catch (error: any) {
      setDocFlash({ type: 'error', text: error.message || 'URL ingestion failed' });
    } finally {
      setDocLoading(false);
    }
  }

  if (!mounted) return null;

  if (!isAuthenticated) {
    return (
      <main className="app-shell">
        <section
          className="panel panel-strong fade-up"
          style={{
            maxWidth: 980,
            margin: '20px auto',
            display: 'grid',
            gridTemplateColumns: 'minmax(0, 1fr) minmax(300px, 360px)',
            gap: 18,
            padding: 20,
          }}
        >
          <div>
            <p
              className="title-font"
              style={{ margin: 0, letterSpacing: '0.11em', color: 'var(--accent-strong)', fontSize: 12 }}
            >
              AI KNOWLEDGE ASSISTANT
            </p>
            <h1 className="title-font" style={{ margin: '8px 0 10px', fontSize: 'clamp(1.8rem, 4vw, 2.9rem)' }}>
              End-to-End RAG Chatbot
            </h1>
            <p style={{ marginTop: 0, color: 'var(--text-muted)', lineHeight: 1.6 }}>
              LLM orchestration with FastAPI, NestJS, and Next.js. Upload documents, ask contextual questions, and review
              chat sessions with source citations.
            </p>
            <div style={{ ...STACK_GAP, marginTop: 16 }}>
              <div className="panel" style={{ padding: 14 }}>
                <strong className="title-font">System Snapshot</strong>
                <p style={{ margin: '8px 0 0', color: 'var(--text-muted)' }}>
                  Worker is ready. Sign in to test backend flows, ingest documents, and validate end-to-end behavior.
                </p>
              </div>
              <div className="panel" style={{ padding: 14 }}>
                <strong className="title-font">API Base URL</strong>
                <p style={{ margin: '8px 0 0', color: 'var(--text-muted)' }}>
                  {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001/api'}
                </p>
              </div>
            </div>
          </div>

          <form className="panel" style={{ padding: 18, display: 'grid', gap: 12 }} onSubmit={handleAuthSubmit}>
            <h2 className="title-font" style={{ margin: 0 }}>
              {authMode === 'login' ? 'Login' : 'Create Account'}
            </h2>

            {authMode === 'register' ? (
              <div>
                <div className="label">Name (optional)</div>
                <input
                  className="input"
                  value={authForm.name}
                  onChange={(event) => setAuthForm((prev) => ({ ...prev, name: event.target.value }))}
                  placeholder="Your name"
                />
              </div>
            ) : null}

            <div>
              <div className="label">Email</div>
              <input
                className="input"
                type="email"
                value={authForm.email}
                onChange={(event) => setAuthForm((prev) => ({ ...prev, email: event.target.value }))}
                required
              />
            </div>

            <div>
              <div className="label">Password</div>
              <input
                className="input"
                type="password"
                value={authForm.password}
                onChange={(event) => setAuthForm((prev) => ({ ...prev, password: event.target.value }))}
                required
                minLength={6}
              />
            </div>

            {authError ? <div className="message message-error">{authError}</div> : null}

            <button className="button button-primary" disabled={authLoading} type="submit">
              {authLoading ? 'Please wait...' : authMode === 'login' ? 'Login' : 'Register'}
            </button>

            <button
              className="button button-secondary"
              type="button"
              onClick={() => setAuthMode((prev) => (prev === 'login' ? 'register' : 'login'))}
            >
              {authMode === 'login' ? 'Need an account? Register' : 'Have an account? Login'}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="panel panel-strong fade-up" style={{ padding: 16 }}>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'space-between', flexWrap: 'wrap' }}>
          <div>
            <p className="title-font" style={{ margin: 0, letterSpacing: '0.1em', fontSize: 12, color: 'var(--accent-strong)' }}>
              RAG OPS CONSOLE
            </p>
            <h1 className="title-font" style={{ margin: '6px 0 2px', fontSize: 'clamp(1.4rem, 2.4vw, 2rem)' }}>
              Welcome, {user?.name || user?.email}
            </h1>
            <p style={{ margin: 0, color: 'var(--text-muted)' }}>
              Namespace: <strong>{namespace}</strong> | Top-K: <strong>{topK}</strong>
            </p>
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <div className="panel" style={{ padding: '8px 12px', minWidth: 150 }}>
              <div className="label">Total Chunks</div>
              <div className="title-font" style={{ fontSize: 22 }}>
                {stats?.total_chunks ?? 0}
              </div>
            </div>
            <button className="button button-secondary" onClick={() => token && void refreshStats(token)} type="button">
              Refresh Stats
            </button>
            <button className="button button-danger" onClick={handleLogout} type="button">
              Logout
            </button>
          </div>
        </div>
      </header>

      <section className="dashboard-grid fade-up">
        <aside style={{ ...STACK_GAP }}>
          <section className="panel" style={{ padding: 14 }}>
            <h2 className="title-font" style={{ marginTop: 0, marginBottom: 10 }}>
              Chat Sessions
            </h2>
            <div style={{ maxHeight: 260, overflowY: 'auto', display: 'grid', gap: 8 }}>
              {!sessions.length ? <p style={{ color: 'var(--text-muted)', margin: 0 }}>No sessions yet.</p> : null}
              {sessions.map((session) => {
                const isSelected = session.id === selectedSessionId;
                return (
                  <div
                    key={session.id}
                    className="panel"
                    style={{
                      padding: 10,
                      borderColor: isSelected ? 'var(--accent-strong)' : 'var(--line)',
                      background: isSelected ? 'rgba(230, 106, 70, 0.12)' : 'rgba(255,255,255,0.7)',
                    }}
                  >
                    <button
                      style={{ background: 'transparent', border: 0, width: '100%', textAlign: 'left', cursor: 'pointer' }}
                      onClick={() => void handleSessionClick(session.id)}
                      type="button"
                    >
                      <strong className="title-font" style={{ display: 'block' }}>
                        {session.title || 'Untitled Session'}
                      </strong>
                      <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{formatTime(session.updatedAt)}</span>
                    </button>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 6 }}>
                      <button
                        className="button button-secondary"
                        style={{ padding: '5px 12px', fontSize: 12 }}
                        onClick={() => void handleDeleteSession(session.id)}
                        type="button"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="panel" style={{ padding: 14, display: 'grid', gap: 10 }}>
            <h2 className="title-font" style={{ margin: 0 }}>
              Retrieval Settings
            </h2>
            <div>
              <div className="label">Namespace</div>
              <input className="input" value={namespace} onChange={(e) => setNamespace(e.target.value || 'default')} />
            </div>
            <div>
              <div className="label">Top-K (1-20)</div>
              <input
                className="input"
                type="number"
                min={1}
                max={20}
                value={topK}
                onChange={(e) => setTopK(Math.max(1, Math.min(20, Number(e.target.value) || 1)))}
              />
            </div>
          </section>

          <section className="panel" style={{ padding: 14, display: 'grid', gap: 12 }}>
            <h2 className="title-font" style={{ margin: 0 }}>
              Knowledge Base
            </h2>

            <form style={{ display: 'grid', gap: 8 }} onSubmit={handleFileUpload}>
              <div className="label">Upload File (pdf/txt/docx/doc)</div>
              <input type="file" onChange={(event) => setUploadFile(event.target.files?.[0] || null)} />
              <button className="button button-primary" disabled={docLoading || !uploadFile} type="submit">
                Upload + Ingest
              </button>
            </form>

            <form style={{ display: 'grid', gap: 8 }} onSubmit={handleUrlIngest}>
              <div className="label">Ingest from URL</div>
              <input
                className="input"
                type="url"
                placeholder="https://example.com/docs"
                value={urlInput}
                onChange={(event) => setUrlInput(event.target.value)}
              />
              <button className="button button-secondary" disabled={docLoading || !urlInput.trim()} type="submit">
                Ingest URL
              </button>
            </form>

            {docFlash ? (
              <div className={`message ${docFlash.type === 'error' ? 'message-error' : 'message-success'}`}>
                {docFlash.text}
              </div>
            ) : null}
          </section>
        </aside>

        <section className="panel panel-strong" style={{ padding: 14, display: 'grid', gridTemplateRows: '1fr auto', minHeight: 560 }}>
          <div style={{ overflowY: 'auto', paddingRight: 4 }}>
            <h2 className="title-font" style={{ marginTop: 2 }}>
              {selectedSession ? selectedSession.title : 'New Conversation'}
            </h2>
            <p style={{ color: 'var(--text-muted)', marginTop: -4 }}>
              Ask domain questions based on uploaded docs. Sources are shown under assistant messages.
            </p>

            {!messages.length ? (
              <div className="panel" style={{ padding: 14 }}>
                <p style={{ margin: 0, color: 'var(--text-muted)' }}>
                  No chat yet. Ask a question to start a new session.
                </p>
              </div>
            ) : null}

            <div style={{ display: 'grid', gap: 10 }}>
              {messages.map((message) => (
                <article
                  key={message.id}
                  className="panel"
                  style={{
                    padding: 12,
                    borderColor: message.role === 'user' ? 'rgba(230,106,70,0.5)' : 'rgba(35,120,90,0.45)',
                    background:
                      message.role === 'user' ? 'rgba(230,106,70,0.08)' : 'rgba(35,120,90,0.09)',
                  }}
                >
                  <p className="title-font" style={{ margin: '0 0 4px' }}>
                    {message.role === 'user' ? 'You' : 'Assistant'}
                  </p>
                  <p style={{ margin: 0, whiteSpace: 'pre-wrap', lineHeight: 1.55 }}>{message.content}</p>

                  {message.role === 'assistant' && message.sources?.length ? (
                    <div style={{ marginTop: 10, display: 'grid', gap: 6 }}>
                      <strong className="title-font" style={{ fontSize: 13 }}>
                        Sources ({message.chunksUsed ?? message.sources.length})
                      </strong>
                      {message.sources.map((source, index) => (
                        <div
                          key={`${source.file}-${index}`}
                          style={{ padding: '8px 10px', borderRadius: 10, border: '1px dashed var(--line)', fontSize: 13 }}
                        >
                          <strong>{source.file}</strong>
                          {source.page ? ` | Page ${source.page}` : ''}
                          {typeof source.score === 'number' ? ` | Score ${source.score}` : ''}
                          {source.preview ? (
                            <p style={{ margin: '5px 0 0', color: 'var(--text-muted)' }}>{source.preview}</p>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : null}

                  <p style={{ margin: '8px 0 0', color: 'var(--text-muted)', fontSize: 12 }}>
                    {formatTime(message.createdAt)}
                  </p>
                </article>
              ))}
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--line)', paddingTop: 10, marginTop: 10 }}>
            {chatError ? <div className="message message-error">{chatError}</div> : null}
            <form style={{ display: 'grid', gap: 8 }} onSubmit={handleSendMessage}>
              <textarea
                className="textarea"
                placeholder="Ask something from your uploaded documents..."
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                maxLength={1000}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <small style={{ color: 'var(--text-muted)' }}>{question.length}/1000</small>
                <button className="button button-primary" disabled={chatLoading || !question.trim()} type="submit">
                  {chatLoading ? 'Thinking...' : 'Send'}
                </button>
              </div>
            </form>
          </div>
        </section>
      </section>
    </main>
  );
}
