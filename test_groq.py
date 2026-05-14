"""
Run this to verify your Groq API key is set and working.
Usage: python test_groq.py
"""

import os
import sys

# ── Step 1: Check .env loads ──────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[1] .env loaded")
except ImportError:
    print("[1] python-dotenv not installed — reading env vars directly")

# ── Step 2: Check key exists ──────────────────────────────────────────────────
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("[2] FAIL — GROQ_API_KEY is not set in .env or environment")
    sys.exit(1)

masked = api_key[:8] + "..." + api_key[-4:]
print(f"[2] GROQ_API_KEY found: {masked}")

# ── Step 3: Import Groq SDK ───────────────────────────────────────────────────
try:
    from groq import Groq
    print("[3] groq SDK imported successfully")
except ImportError:
    print("[3] FAIL — groq package not installed. Run: pip install groq")
    sys.exit(1)

# ── Step 4: Create client ─────────────────────────────────────────────────────
try:
    client = Groq(api_key=api_key)
    print("[4] Groq client created")
except Exception as e:
    print(f"[4] FAIL — Could not create client: {e}")
    sys.exit(1)

# ── Step 5: Send a real API call ──────────────────────────────────────────────
print("[5] Sending test message to llama-3.3-70b-versatile ...")
try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant. Reply in one short sentence only."
            },
            {
                "role": "user",
                "content": "What is 2 + 2? Reply in one sentence."
            }
        ],
        max_completion_tokens=50,
        temperature=0,
        stream=False,
    )
    reply = response.choices[0].message.content
    print(f"[5] API response received: {repr(reply)}")
except Exception as e:
    print(f"[5] FAIL — API call failed: {type(e).__name__}: {e}")
    sys.exit(1)

# ── Step 6: Test llm_client wrapper (the actual project module) ───────────────
print("[6] Testing llm_client.generate_response (project wrapper) ...")
try:
    sys.path.insert(0, os.getcwd())
    from llm_client import generate_response
    result = generate_response(
        user_query="What payment methods do you accept?",
        rag_context="We accept Cash on Delivery, JazzCash, and EasyPaisa.",
        intent="payment",
    )
    if result:
        print(f"[6] llm_client response received: {repr(result[:120])}")
    else:
        print("[6] FAIL — generate_response returned None (check logs above)")
        sys.exit(1)
except Exception as e:
    print(f"[6] FAIL — {type(e).__name__}: {e}")
    sys.exit(1)

print()
print("All checks passed. Groq API is configured and working correctly.")
