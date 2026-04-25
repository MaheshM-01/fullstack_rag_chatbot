
import httpx
import json

BASE_URL = "http://localhost:8000"

print("=" * 55)
print("TEST 1: Health Check")
print("=" * 55)
r = httpx.get(f"{BASE_URL}/health")
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")

print("\n" + "=" * 55)
print("TEST 2: Ingest File")
print("=" * 55)
with open("test_doc.txt", "rb") as f:
    r = httpx.post(
        f"{BASE_URL}/ingest/file",
        files={"file": ("test_doc.txt", f, "text/plain")},
        params={"namespace": "default"}
    )
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")

print("\n" + "=" * 55)
print("TEST 3: Chat")
print("=" * 55)
r = httpx.post(
    f"{BASE_URL}/chat",
    json={
        "question": "What is the gold loan interest rate?",
        "namespace": "default",
        "chat_history": []
    },
    timeout=30
)
print(f"Status: {r.status_code}")
result = r.json()
print(f"Answer: {result['answer']}")
print(f"Sources: {result['sources']}")

print("\n" + "=" * 55)
print("TEST 4: Streaming Chat")
print("=" * 55)
print("Streaming: ", end="")
with httpx.stream(
    "POST",
    f"{BASE_URL}/chat/stream",
    json={"question": "What plans are available?"},
    timeout=30
) as r:
    for chunk in r.iter_text():
        print(chunk, end="", flush=True)

print("\n\n" + "=" * 55)
print("TEST 5: Stats")
print("=" * 55)
r = httpx.get(f"{BASE_URL}/stats")
print(f"Response: {r.json()}")

print("\n✅ All API endpoints working!")