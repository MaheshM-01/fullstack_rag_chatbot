
from src.generation.llm.groq_client import GroqLLMClient

print("=" * 50)
print("TEST 1: Normal Generation")
print("=" * 50)

llm = GroqLLMClient()

answer = llm.generate(
    "In one sentence, what is a gold loan?"
)
print(f"Answer: {answer}")

print("\n" + "=" * 50)
print("TEST 2: Streaming Generation")
print("=" * 50)

print("Streaming answer: ", end="")
for token in llm.stream("In one sentence, what is RAG in AI?"):
    print(token, end="", flush=True)

print("\n\n✅ Groq client working!")