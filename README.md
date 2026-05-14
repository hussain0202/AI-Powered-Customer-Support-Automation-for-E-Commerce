# E-Commerce AI Support Platform

An intelligent, multi-layered customer support system built on the Olist Brazilian E-Commerce Dataset. It combines a Groq-powered LLM, a RAG pipeline backed by ChromaDB, semantic intent classification, and a real SQLite product/order database into a single Streamlit web application.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Running the App](#running-the-app)
- [How the AI Pipeline Works](#how-the-ai-pipeline-works)
- [Dashboard & Tabs](#dashboard--tabs)
- [Testing the LLM](#testing-the-llm)
- [Utility Scripts](#utility-scripts)
- [Dataset](#dataset)

---

## Overview

Traditional e-commerce support requires human agents to handle thousands of repetitive queries daily — order status, refunds, product availability, payments. This platform automates the full support lifecycle using:

- **Semantic intent detection** via sentence embeddings (no keyword matching)
- **Real database queries** against a 100k+ order dataset for factual answers
- **RAG (Retrieval-Augmented Generation)** to ground LLM responses in policy documents
- **Groq LLM** (`llama-3.3-70b-versatile`) for natural, context-aware replies
- **Multi-turn slot filling** to collect required information step-by-step
- **Persistent user sessions** with login, chat history, and support ticket tracking

---

## Architecture

```
User Message
     │
     ▼
┌─────────────────────────────────────────────────┐
│              session_manager.py                  │
│  1. Reference Resolution & Context Injection     │
│  2. Semantic Intent Classification               │
│  3. Multi-turn Slot Filling (e.g. ask order ID) │
│  4. Route to correct retrieval strategy          │
└──────────┬──────────────┬───────────────────────┘
           │              │
    ┌──────▼──────┐ ┌─────▼──────────────────────┐
    │ sql_retrieval│ │  semantic_search /          │
    │             │ │  hybrid_retrieval            │
    │ SQLite DB   │ │                              │
    │ orders      │ │  ChromaDB (vector store)     │
    │ products    │ │  + SQL facts                 │
    │ inventory   │ │        │                     │
    │ payments    │ │        ▼                     │
    │ discounts   │ │  Groq LLM (llama-3.3-70b)   │
    └──────┬──────┘ └─────┬────────────────────────┘
           │              │
           └──────┬───────┘
                  ▼
           Final Response
```

### Retrieval Strategies

| Strategy | When used | LLM involved |
|---|---|---|
| `sql_retrieval` | Product search, pricing, recommendations, order tracking, discounts | No — formatted SQL result |
| `semantic_search` | General FAQ, shipping, account, technical support | Yes — ChromaDB chunks → Groq |
| `hybrid_retrieval` | Cancel order, refunds, payments, payment issues | Yes — SQL facts + policy → Groq |

---

## Features

### AI Assistant
- **Semantic intent classification** — `all-MiniLM-L6-v2` sentence embeddings compared against labelled examples; no brittle keyword rules
- **28 intent categories** — order tracking, product search, recommendations, pricing, discounts, refunds, cancellations, payments, complaints, raise ticket, human escalation, and more
- **Multi-turn slot filling** — bot asks follow-up questions sequentially (e.g. asks for order ID before tracking, asks for budget before recommending)
- **Context memory** — remembers active order ID, category, budget, and product across turns
- **Pagination** — "show me more" loads the next page of product results without re-asking
- **Reference resolution** — resolves pronouns and context references ("that one", "same category")
- **Topic switching** — mid-flow intent change detected and handled gracefully

### LLM & RAG Pipeline
- **Groq LLM** (`llama-3.3-70b-versatile`) generates all policy and FAQ responses
- **ChromaDB** vector store indexes six knowledge base documents (FAQ, shipping, refunds, payments, account help, technical support)
- **Hybrid retrieval** merges live SQL data with retrieved policy context before sending to the LLM
- **Query enrichment** — user query is expanded with conversation context before retrieval
- **Fallback toggle** — sidebar button enables/disables static template fallback when the LLM is unavailable; when disabled, a clear error message is shown instead of a silent fallback

### Order & Product Management
- Real order tracking against 100k+ Olist orders
- Actual DB writes for cancellations (`order_status → cancelled`) and refunds (`order_status → refunded`)
- Two-pass fuzzy product search — LIKE substring match first, `RapidFuzz` token-set-ratio fallback
- Disambiguation list shown when multiple products match a partial name
- Budget-filtered recommendations with category filtering
- Discounted products, inventory queries, payment methods — all live from SQLite

### Support Tickets
- Dedicated `raise_ticket` intent with step-by-step slot filling (issue type menu → description)
- Six issue types: Payment Problem, Delivery Issue, Damaged/Wrong Item, Order Cancellation Issue, Complaint, Other
- Tickets stored in `support_tickets` table and linked to the logged-in user
- Automatic ticket creation for payment issues, complaints, technical support, and human escalation flows

### User Authentication & Persistent Sessions
- Register and login with username or email
- Passwords hashed with PBKDF2-SHA256 (100,000 iterations + random salt)
- 30-day browser cookie sessions — no re-login required after page refresh
- Per-user chat history and support ticket history stored in SQLite
- Logout invalidates the session token in the database

### Dashboard & Analytics
- **Executive Dashboard** — order status distribution, monthly volume trend, delayed vs on-time pie chart, top 10 product categories
- **Support Insights** — average review score, delay rate, problematic product categories, review score distribution, recent chat logs, support ticket overview with breakdown by type
- **My Account tab** — personal profile, full chat history, full ticket history for the logged-in user
- Chat logs exportable as CSV

### Sidebar
- Collapsible question guide — 11 intent categories with example questions
- Collapsible FAQ panel — 54 questions and answers across 9 categories, loaded live from `faq.json`
- Debug State Panel — live JSON view of conversation state after every message
- LLM Fallback toggle button
- CSV export

---

## Tech Stack

| Component | Technology |
|---|---|
| Web framework | Streamlit 1.57 |
| LLM inference | Groq API — `llama-3.3-70b-versatile` |
| Vector store | ChromaDB 1.5 |
| Embeddings | `sentence-transformers` — `all-MiniLM-L6-v2` |
| Intent classification | Cosine similarity over sentence embeddings |
| Database | SQLite (via Python `sqlite3`) |
| Fuzzy matching | RapidFuzz |
| Sentiment analysis | TextBlob |
| Data processing | Pandas |
| Session cookies | `extra-streamlit-components` CookieManager |
| Password hashing | `hashlib.pbkdf2_hmac` (stdlib) |
| Dataset | Olist Brazilian E-Commerce (Kaggle) |

---

## Project Structure

```
ecommerce_ai_support/
│
├── app.py                        # Streamlit UI — all tabs, sidebar, auth gate
├── auth.py                       # User registration, login, session management
├── login_page.py                 # Login / register UI component
├── session_manager.py            # Central reasoning engine — slot filling, routing, context
├── response_generator.py         # Fallback template response handlers
├── semantic_intent_classifier.py # Sentence-transformer intent classifier
├── sentiment.py                  # TextBlob sentiment analysis
├── context_intelligence.py       # Reference resolution, fuzzy category matching
├── conversation_memory.py        # Chat history entity extraction, dead-end detection
├── database_manager.py           # SQLite CRUD — users, chat_logs, support_tickets, sessions
├── data_loader.py                # Loads Olist CSV datasets into pandas DataFrames
├── runtime_config.py             # Shared runtime flags (LLM fallback toggle)
├── llm_client.py                 # Groq SDK wrapper — builds messages, calls API
│
├── rag/
│   ├── retriever.py              # Initialises ChromaDB and runs semantic search
│   ├── document_loader.py        # Loads .txt files from knowledge_base/
│   ├── text_chunker.py           # Splits documents into overlapping chunks
│   ├── embedding_manager.py      # Generates sentence embeddings for ChromaDB
│   ├── vector_store.py           # ChromaDB add/search operations
│   ├── query_enricher.py         # Expands query with conversation context
│   ├── context_builder.py        # Formats retrieved chunks into context string
│   ├── rag_router.py             # Decides retrieval strategy per intent
│   ├── rag_response_generator.py # Calls LLM with semantic_search context
│   └── hybrid_retriever.py       # Merges SQL facts + policy context → LLM
│
├── database/
│   ├── sql_retriever.py          # All SQL queries (products, orders, inventory, etc.)
│   ├── support.db                # SQLite database (auto-created on first run)
│   └── chroma_db/                # ChromaDB persistent vector store (auto-created)
│
├── knowledge_base/               # Plain-text policy documents indexed by ChromaDB
│   ├── faq.txt
│   ├── shipping_policy.txt
│   ├── refund_policy.txt
│   ├── payment_policy.txt
│   ├── account_help.txt
│   └── technical_support.txt
│
├── faq.json                      # 54 FAQ entries — used by sidebar FAQ panel
├── intent_examples.json          # Labelled examples per intent for classifier
│
├── reset_chromadb.py             # Utility — clears and re-seeds ChromaDB
├── requirements.txt
└── .env                          # GROQ_API_KEY (not committed)
```

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- A [Groq API key](https://console.groq.com/) (free tier available)
- The Olist dataset CSVs (see [Dataset](#dataset))

### 1. Clone and create virtual environment
```bash
git clone <repo-url>
cd ecommerce_ai_support
python -m venv env
# Windows
env\Scripts\activate
# macOS / Linux
source env/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
Create a `.env` file in the project root:
```
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Place the Olist dataset CSVs
Put the following files in a `data/` folder (or wherever `data_loader.py` expects them):
```
olist_orders_dataset.csv
olist_order_reviews_dataset.csv
olist_order_items_dataset.csv
olist_products_dataset.csv
product_category_name_translation.csv
```

---

## Configuration

| File | What to change |
|---|---|
| `.env` | `GROQ_API_KEY` — your Groq API key |
| `llm_client.py` | `MODEL`, `MAX_TOKENS`, `TEMPERATURE`, `_SYSTEM_PROMPT` |
| `intent_examples.json` | Add more example phrases per intent to improve classification accuracy |
| `knowledge_base/*.txt` | Add or edit policy documents; run `reset_chromadb.py` after changes |
| `faq.json` | Add FAQ entries; sidebar FAQ panel reads this file live |

---

## Running the App

```bash
streamlit run app.py
```

The app will:
1. Initialise the SQLite database (creates tables automatically on first run)
2. Load and index knowledge base documents into ChromaDB
3. Load the Olist dataset and pre-compute dashboard insights
4. Open the login page — register an account to get started

### After updating knowledge base files
```bash
python reset_chromadb.py
```
This deletes the existing ChromaDB collection and re-seeds it from the updated `.txt` files.

---

## How the AI Pipeline Works

### Intent Classification
Every message goes through `semantic_intent_classifier.py`, which:
1. Embeds the message using `all-MiniLM-L6-v2`
2. Computes cosine similarity against pre-embedded examples from `intent_examples.json`
3. Returns the intent with the highest similarity score and a confidence level (HIGH / MEDIUM / LOW)

### Slot Filling
For intents that need more information (e.g. order tracking needs an order ID), `session_manager.py` checks `INTENT_SLOT_REQUIREMENTS` and asks follow-up questions one at a time until all slots are filled.

### Response Generation
Once slots are collected, the intent is routed:
- **`sql_retrieval`** — queries SQLite directly, returns formatted data
- **`semantic_search`** — retrieves ChromaDB chunks → builds context → sends to Groq LLM
- **`hybrid_retrieval`** — queries SQLite for facts + retrieves policy from ChromaDB → merges both → sends to Groq LLM

### LLM Fallback Control
A toggle button in the sidebar controls whether a static template response is used when the LLM fails:
- **Fallback ON** (default) — silent fallback to template; always shows a response
- **Fallback OFF** — shows a clear error message if the LLM is unavailable; useful for testing

---

## Dashboard & Tabs

| Tab | Contents |
|---|---|
| **AI Assistant** | Live chat with sentiment badge, intent badge, retrieval strategy badge, and per-message debug panel |
| **Executive Dashboard** | Order status distribution, monthly trend, delayed vs on-time, top 10 product categories |
| **Support Insights** | KPI metrics, problematic categories, review score distribution, recent chat logs, support ticket overview |
| **My Account** | Personal profile, all personal chat history, all personal support tickets |

---

## Testing the LLM

No test script needed — use the live chat and the built-in debug tools:

1. **Retriever badge** — shown below every user message; `semantic_search` or `hybrid_retrieval` means the LLM was called
2. **API Response & RAG Debugging** — expandable panel under each message shows the full `api_payload` including `retrieval_strategy`
3. **Fallback toggle** — set to OFF; if the LLM fails you will see a warning message instead of a silent template fallback
4. **Debug State Panel** — sidebar JSON view of live conversation state
5. **Terminal output** — Groq API errors print to the terminal where Streamlit is running

**Queries that always go through the LLM:**
- *"What is your return policy?"* → `semantic_search`
- *"How long does shipping take?"* → `semantic_search`
- *"I want to cancel order 123456"* → `hybrid_retrieval`
- *"I want a refund for my order"* → `hybrid_retrieval`

---

## Utility Scripts

| Script | Purpose |
|---|---|
| `reset_chromadb.py` | Clears and re-seeds ChromaDB — run after editing knowledge base files |
| `verify_data.py` | Sanity checks the Olist dataset CSV loading |

---

## Dataset

Powered by the [Olist Brazilian E-Commerce Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — 100,000+ real anonymised orders, product listings, customer reviews, and payment records from 2016–2018.

The dataset is used to populate the SQLite `database/support.db` with products, inventory, orders, payments, and discounts — giving the AI assistant real data to query against instead of mock responses.
