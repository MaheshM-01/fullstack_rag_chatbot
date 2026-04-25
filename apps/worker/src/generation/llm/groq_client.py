
"""
GROQ CLIENT
===========
WHAT:  Wrapper around Groq API for LLM text generation.
       Supports both normal and streaming responses.

WHY:   Groq gives free access to Llama3-70b — fast and accurate.
       Wrapper abstracts API details from chain.py.
       If we switch LLM provider later, only this file changes.

WHERE: Called by src/generation/chain.py
       chain.py → groq_client.generate(prompt) → answer string
       chain.py → groq_client.stream(prompt)   → token generator

WHEN:  After context retrieved from ChromaDB.
       Final step before sending answer back to user.

HOW GROQ API WORKS:
       1. Send: model name + messages (role + content)
       2. Groq runs Llama3 on their hardware (very fast — custom chips)
       3. Receive: generated text tokens
       
       Messages format (same as OpenAI):
       [
         {"role": "system", "content": "You are helpful..."},
         {"role": "user",   "content": "What is gold loan rate?"}
       ]
"""

import time
from typing import Generator, Optional
from groq import Groq
from src.config import settings


class GroqLLMClient:
    """
    WHAT: Groq API client wrapper for text generation.

    WHY WRAPPER CLASS:
      Handles: API initialization, retry logic, error handling,
               rate limit management, streaming.
      chain.py gets clean simple interface:
        llm.generate(prompt) → "The interest rate is 12%..."
        llm.stream(prompt)   → token by token generator

    USAGE:
      llm = GroqLLMClient()
      
      # Normal (wait for full response)
      answer = llm.generate("What is gold loan rate?")
      
      # Streaming (token by token — for chat UI)
      for token in llm.stream("What is gold loan rate?"):
          print(token, end="", flush=True)
    """

    def __init__(self):
        """
        WHAT: Initialize Groq client with API key from settings.

        WHY validate key format:
          Groq keys start with "gsk_"
          Catch wrong key early (at startup) not late (at user request)
          Better error message than cryptic API error.
        """

        # Validate API key exists and looks correct
        if not settings.groq_api_key:
            raise ValueError(
                "❌ GROQ_API_KEY is missing!\n"
                "   Add it to your .env file:\n"
                "   GROQ_API_KEY=gsk_your_key_here\n"
                "   Get free key: https://console.groq.com"
            )

        if not settings.groq_api_key.startswith("gsk_"):
            raise ValueError(
                "❌ GROQ_API_KEY looks wrong!\n"
                "   Groq keys start with 'gsk_'\n"
                "   Check your .env file."
            )

        # Initialize Groq client
        # WHY: Client object manages HTTP connection to Groq API
        #      Reuse same client for all requests (efficient)
        self.client = Groq(api_key=settings.groq_api_key)
        self.model  = settings.groq_model_name

        print(f"✅ Groq client ready!")
        print(f"   Model: {self.model}")
        print(f"   Free tier: 14,400 req/day | 30 req/min")

    # ============================================================
    # NORMAL GENERATION (full response at once)
    # ============================================================
    def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        retry_count: int = 3,
    ) -> str:
        """
        WHAT: Send prompt to Groq, get complete answer as string.

        WHY temperature=0.1 (not 0):
          temperature=0   → completely deterministic, robotic answers
          temperature=0.1 → tiny creativity, more natural language
          temperature=1.0 → very creative, but inaccurate for facts
          
          For RAG (fact-based answers) → keep LOW (0.0 to 0.3)
          We use 0.1 = accurate but natural sounding ✅

        WHY max_tokens=1024:
          1024 tokens ≈ 750 words ≈ one full page of text
          Enough for detailed answers without wasting quota.
          Groq free tier has daily token limits — be efficient.

        WHY retry_count=3:
          Groq has rate limits (30 req/min).
          If we hit limit → wait and retry automatically.
          3 retries = handles temporary rate limit spikes.

        WHY messages format (not plain text):
          Groq/OpenAI API uses "chat" format with roles:
          
          system role: "You are helpful assistant" 
            → Sets LLM behavior/persona for entire conversation
          
          user role: the actual prompt with context + question
            → What the user is asking

          WHY split into system + user:
            System message optimized differently by LLM internally
            Better instruction following than single big prompt

        Args:
            prompt:      Full prompt string (from templates.py)
            max_tokens:  Max response length in tokens
            temperature: Creativity level (0=deterministic, 1=creative)
            retry_count: Number of retries on rate limit error

        Returns:
            Generated answer as string
        """

        # Build messages in Groq/OpenAI chat format
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a precise and helpful AI assistant. "
                    "Follow all instructions in the user message exactly. "
                    "Be accurate, concise, and answer directly first. "
                    "Then provide short citations when asked."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # Retry loop — handles rate limits gracefully
        for attempt in range(retry_count):
            try:
                print(f"   🤖 Calling Groq API (attempt {attempt + 1})...")

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=False,    # Normal mode — wait for full response
                )

                # Extract answer text from response
                # response.choices[0] = first (and only) completion
                # .message.content = the actual text generated
                answer = response.choices[0].message.content

                # Log token usage (helpful for monitoring free tier limits)
                usage = response.usage
                print(f"   ✅ Groq response received!")
                print(f"   📊 Tokens used: "
                      f"prompt={usage.prompt_tokens} | "
                      f"completion={usage.completion_tokens} | "
                      f"total={usage.total_tokens}")

                return answer.strip()

            except Exception as e:
                error_msg = str(e).lower()

                # Rate limit hit → wait and retry
                # WHY 60 seconds: Groq rate limit window is 1 minute
                if "rate limit" in error_msg or "429" in error_msg:
                    wait_time = 60 * (attempt + 1)  # 60s, 120s, 180s
                    print(f"   ⚠️  Rate limit hit! "
                          f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue

                # Authentication error → wrong API key
                elif "401" in error_msg or "authentication" in error_msg:
                    raise ValueError(
                        "❌ Groq authentication failed!\n"
                        "   Check your GROQ_API_KEY in .env file.\n"
                        "   Get key: https://console.groq.com"
                    )

                # Other errors → raise immediately (no retry)
                else:
                    raise RuntimeError(
                        f"❌ Groq API error: {e}\n"
                        f"   Model: {self.model}"
                    )

        # All retries exhausted
        raise RuntimeError(
            f"❌ Groq API failed after {retry_count} attempts.\n"
            f"   You may have hit the daily limit (14,400 req/day).\n"
            f"   Try again tomorrow or check https://console.groq.com"
        )

    # ============================================================
    # STREAMING GENERATION (token by token)
    # ============================================================
    def stream(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> Generator[str, None, None]:
        """
        WHAT: Stream answer token by token as they're generated.

        WHY STREAMING:
          User experience comparison:

          Normal:    [sending...] → [5 second wait] → [full answer appears]
                     User stares at blank screen ❌

          Streaming: [sending...] → "The" → " interest" → " rate" → " is" → ...
                     Answer appears word by word like ChatGPT ✅

        HOW GENERATORS WORK:
          Instead of returning ONE big string,
          this function YIELDS small pieces one at a time.

          Caller (chain.py or FastAPI):
            for token in llm.stream(prompt):
                print(token, end="")   # Print each token as it arrives
                # or send to frontend via WebSocket

        WHY yield (generator) not return (list):
          return list: Wait for ALL tokens, then return everything
                       = same as no streaming ❌
          
          yield:       Return each token IMMEDIATELY as Groq sends it
                       = true streaming, no waiting ✅

        Args:
            prompt:      Full prompt string
            max_tokens:  Max response length
            temperature: Creativity level

        Yields:
            Individual text tokens as strings
            e.g., "The", " interest", " rate", " is", " 12%"...
        """

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a precise and helpful AI assistant. "
                    "Follow all instructions in the user message exactly. "
                    "Be accurate, concise, and answer directly first. "
                    "Then provide short citations when asked."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        print(f"   🌊 Starting Groq stream...")

        try:
            # stream=True → Groq sends tokens as they're generated
            response_stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,    # ← Streaming mode!
            )

            # Iterate over chunks as they arrive from Groq
            for chunk in response_stream:

                # Each chunk has choices list
                # choices[0].delta.content = new token text
                # delta = "what's new in this chunk"
                token = chunk.choices[0].delta.content

                # Some chunks are empty (metadata chunks)
                # Skip those, only yield actual text
                if token is not None:
                    yield token

        except Exception as e:
            error_msg = str(e).lower()

            if "rate limit" in error_msg or "429" in error_msg:
                yield "\n\n⚠️ Rate limit reached. Please wait a moment and try again."
            elif "401" in error_msg:
                yield "\n\n❌ API authentication error. Check your GROQ_API_KEY."
            else:
                yield f"\n\n❌ Error: {str(e)}"

    # ============================================================
    # UTILITY
    # ============================================================
    def get_available_models(self) -> list:
        """
        WHAT: Returns list of available Groq models.
        WHY:  Useful for admin UI or debugging.
        
        Free tier models (as of 2024):
          llama3-70b-8192    → Best quality (recommended)
          llama3-8b-8192     → Fastest, less accurate
          mixtral-8x7b-32768 → Biggest context window
          gemma-7b-it        → Google's model
        """
        try:
            models = self.client.models.list()
            return [m.id for m in models.data]
        except Exception:
            # Return known free models if API call fails
            return [
                "llama3-70b-8192",
                "llama3-8b-8192",
                "mixtral-8x7b-32768",
                "gemma-7b-it"
            ]
