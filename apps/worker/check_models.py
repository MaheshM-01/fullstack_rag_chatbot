
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv(r"C:\first_data_science_proj\RAG -chatbot--ml\.env")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
models = client.models.list()

print("Available Groq Models:")
print("=" * 50)
for model in models.data:
    print(f"  → {model.id}")