# API Reference

Base URL (NestJS): `http://localhost:3001/api`  
Base URL (Worker): `http://localhost:8000`

## Auth (NestJS)

### `POST /auth/register`

Request:
```json
{
  "email": "user@example.com",
  "password": "secret123",
  "name": "User Name"
}
```

Response:
```json
{
  "message": "Registration successful",
  "token": "jwt-token",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name"
  }
}
```

### `POST /auth/login`

Request:
```json
{
  "email": "user@example.com",
  "password": "secret123"
}
```

Response shape is same as register.

## System (NestJS)

### `GET /health`
- Public health check for backend service

## Chat (NestJS, JWT required)

### `POST /chat`

Headers:
- `Authorization: Bearer <token>`

Request:
```json
{
  "question": "What is the interest rate?",
  "sessionId": "optional-session-uuid",
  "namespace": "default",
  "topK": 5
}
```

Response:
```json
{
  "sessionId": "uuid",
  "answer": "Answer text...",
  "sources": [
    {
      "file": "gold_loan.pdf",
      "page": "3",
      "score": 0.84
    }
  ],
  "chunks_used": 3,
  "question": "What is the interest rate?"
}
```

### `GET /chat/sessions`
- Returns latest active sessions for authenticated user

### `GET /chat/sessions/:id/messages`
- Returns full message timeline for a session

### `DELETE /chat/sessions/:id`
- Soft deletes a session (`isActive=false`)

## Documents (NestJS, JWT required)

### `POST /documents/upload`

Content type:
- `multipart/form-data`

Fields:
- `file`: `.pdf | .txt | .docx | .doc`
- `namespace` (optional, default `default`)

### `POST /documents/url`

Request:
```json
{
  "url": "https://example.com/docs",
  "namespace": "default"
}
```

### `GET /documents/stats`
- Proxies worker stats payload

## Worker Endpoints (FastAPI)

### `GET /health`
- Worker service health

### `GET /stats`
- Chroma collection stats

### `POST /ingest/file`
- Multipart file ingestion

### `POST /ingest/url`
- URL ingestion

### `POST /chat`
- Non-streaming RAG response

### `POST /chat/stream`
- Streaming token output

### `DELETE /reset`
- Wipe all vectors from collection

### `DELETE /namespace/{namespace}`
- Delete vectors in one namespace
