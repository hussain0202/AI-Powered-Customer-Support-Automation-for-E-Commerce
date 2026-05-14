"""
Generates the project report DOCX.
Run: python generate_report.py
"""

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

doc = Document()

# ── Page margins ──────────────────────────────────────────────────────────────
for section in doc.sections:
    section.top_margin    = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin   = Cm(2.5)
    section.right_margin  = Cm(2.5)

# ── Colour palette ────────────────────────────────────────────────────────────
DARK_BLUE   = RGBColor(0x1A, 0x37, 0x6C)   # headings
ACCENT_BLUE = RGBColor(0x27, 0x6E, 0xC6)   # sub-headings / accents
LIGHT_GRAY  = RGBColor(0xF2, 0xF4, 0xF8)   # table header bg
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
BLACK       = RGBColor(0x1A, 0x1A, 0x1A)
GREEN       = RGBColor(0x1E, 0x88, 0x55)
CODE_BG     = RGBColor(0xF0, 0xF0, 0xF0)


# ── Helper: shade a table cell ────────────────────────────────────────────────
def shade_cell(cell, hex_color: str):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    tcPr.append(shd)


def set_cell_border(cell, **kwargs):
    """kwargs: top, bottom, left, right — each a dict(sz, val, color)"""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        params = kwargs.get(edge, {})
        if params:
            tag = OxmlElement(f"w:{edge}")
            tag.set(qn("w:val"),   params.get("val",   "single"))
            tag.set(qn("w:sz"),    str(params.get("sz", 6)))
            tag.set(qn("w:color"), params.get("color", "auto"))
            tcBorders.append(tag)
    tcPr.append(tcBorders)


# ── Helper: styled paragraph ──────────────────────────────────────────────────
def add_paragraph(text="", bold=False, italic=False, size=11,
                  color=None, align=WD_ALIGN_PARAGRAPH.LEFT,
                  space_before=0, space_after=6):
    p   = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after  = Pt(space_after)
    if text:
        run = p.add_run(text)
        run.bold   = bold
        run.italic = italic
        run.font.size  = Pt(size)
        run.font.color.rgb = color or BLACK
    return p


def add_heading(text, level=1, space_before=14):
    size_map = {1: 20, 2: 14, 3: 12}
    col_map  = {1: DARK_BLUE, 2: ACCENT_BLUE, 3: DARK_BLUE}
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after  = Pt(4)
    run = p.add_run(text)
    run.bold = True
    run.font.size  = Pt(size_map.get(level, 12))
    run.font.color.rgb = col_map.get(level, DARK_BLUE)
    if level == 1:
        # underline rule
        pPr = p._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"),   "single")
        bottom.set(qn("w:sz"),    "6")
        bottom.set(qn("w:space"), "4")
        bottom.set(qn("w:color"), "1A376C")
        pBdr.append(bottom)
        pPr.append(pBdr)
    return p


def add_bullet(text, indent=0, bold_prefix=None):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent   = Inches(0.3 + indent * 0.2)
    p.paragraph_format.space_before  = Pt(2)
    p.paragraph_format.space_after   = Pt(2)
    if bold_prefix:
        run = p.add_run(bold_prefix)
        run.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = BLACK
        p.add_run(" " + text).font.size = Pt(11)
    else:
        run = p.add_run(text)
        run.font.size = Pt(11)
    return p


def add_code_block(lines):
    """Monospace grey block for code / flow diagrams."""
    for line in lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(0)
        p.paragraph_format.left_indent  = Inches(0.3)
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"),   "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"),  "F0F0F0")
        p._p.get_or_add_pPr().append(shd)
        run = p.add_run(line if line else " ")
        run.font.name = "Courier New"
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)


def styled_table(headers, rows, col_widths=None):
    n_cols = len(headers)
    tbl    = doc.add_table(rows=1 + len(rows), cols=n_cols)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.style = "Table Grid"

    # Header row
    hdr = tbl.rows[0]
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        shade_cell(cell, "1A376C")
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p   = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        run.bold = True
        run.font.size      = Pt(11)
        run.font.color.rgb = WHITE

    # Data rows
    for r_idx, row_data in enumerate(rows):
        bg = "F2F4F8" if r_idx % 2 == 0 else "FFFFFF"
        for c_idx, cell_text in enumerate(row_data):
            cell = tbl.rows[r_idx + 1].cells[c_idx]
            shade_cell(cell, bg)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            parts = cell_text.split("**")
            for j, part in enumerate(parts):
                if not part:
                    continue
                run = p.add_run(part)
                run.font.size = Pt(10)
                run.bold = (j % 2 == 1)
                run.font.color.rgb = BLACK

    # Column widths
    if col_widths:
        for row in tbl.rows:
            for i, w in enumerate(col_widths):
                row.cells[i].width = Inches(w)
    return tbl


# ══════════════════════════════════════════════════════════════════════════════
# COVER PAGE
# ══════════════════════════════════════════════════════════════════════════════
doc.add_paragraph()
doc.add_paragraph()
doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("AI-Powered Customer Support Automation")
run.bold = True
run.font.size = Pt(26)
run.font.color.rgb = DARK_BLUE

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("for E-Commerce")
run.bold = True
run.font.size = Pt(22)
run.font.color.rgb = ACCENT_BLUE

doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Project Technical Report")
run.font.size = Pt(14)
run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
run.italic = True

doc.add_paragraph()
doc.add_paragraph()

for label, value in [
    ("Course",   "NLP & Large Language Models"),
    ("Platform", "Python · Streamlit · Groq API (Llama 3.3 70B)"),
    ("Database", "SQLite + ChromaDB Vector Store"),
]:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p.add_run(f"{label}: ")
    r1.bold = True
    r1.font.size = Pt(12)
    r1.font.color.rgb = DARK_BLUE
    r2 = p.add_run(value)
    r2.font.size = Pt(12)
    r2.font.color.rgb = BLACK

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# 1. PROJECT OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
add_heading("1. Project Overview", level=1, space_before=4)
add_paragraph(
    "This project delivers a fully functional AI-powered customer support chatbot "
    "for a Pakistani e-commerce store. Customers interact with the system through a "
    "browser-based chat interface built with Streamlit. The system classifies every "
    "customer message, retrieves relevant data from a structured database or a semantic "
    "knowledge base, and generates natural language responses using the Groq API "
    "(Llama 3.3 70B). The entire pipeline degrades gracefully — if the LLM is "
    "unavailable, structured template responses are returned automatically.",
    size=11, space_after=8
)

add_heading("Key Achievements", level=2)
achievements = [
    ("Intent Classification",       "20+ customer intents recognised using sentence-transformers cosine similarity"),
    ("Multi-turn Dialogue",          "Slot filling, topic-switch detection, and reference resolution across turns"),
    ("SQL Retrieval",                "Live queries against SQLite for orders, products, pricing, inventory, discounts"),
    ("RAG Knowledge Base",           "ChromaDB vector store for policy and FAQ retrieval"),
    ("Hybrid Retrieval",             "Order facts + policy text merged and passed to LLM in one response"),
    ("Groq LLM Integration",         "Llama 3.3 70B via Groq API with graceful template fallback"),
    ("Pagination",                   "Offset-based pagination — 'show me more' advances the result window"),
    ("Conversation Memory",          "Entity extraction from history, dead-end detection, help menu"),
    ("Data Cleaning",                "Automated DB cleaning: null statuses, invalid discounts, bad payments"),
    ("Smart Product Matching",       "Two-pass LIKE + fuzzy token_set_ratio with disambiguation list"),
]
styled_table(
    ["Feature", "Description"],
    [[a, b] for a, b in achievements],
    col_widths=[2.2, 4.1]
)

doc.add_paragraph()

# ══════════════════════════════════════════════════════════════════════════════
# 2. SYSTEM ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════════
add_heading("2. System Architecture", level=1)
add_paragraph(
    "The system is organised into six layers. Each layer has a single responsibility "
    "and passes its output to the next. Failures at any layer trigger a fallback "
    "at the layer below.",
    size=11, space_after=8
)

add_code_block([
    "  User Message (Browser)",
    "       |",
    "  [app.py]  ─── Streamlit UI, session state, chat rendering",
    "       |",
    "  [sentiment.py]  ─── TextBlob polarity: Positive / Neutral / Negative",
    "       |",
    "  [session_manager.py]  ─── Central Orchestrator (THE BRAIN)",
    "       |",
    "  ┌────┴────────────────────────────────────────┐",
    "  │                    │                        │",
    "  [SQL Path]      [RAG Path]           [Hybrid Path]",
    "  SQLite DB        ChromaDB              SQL + RAG",
    "  queries          vector search         merged context",
    "  │                    │                        │",
    "  └─────────────┬──────┘────────────────────────┘",
    "                |",
    "          [llm_client.py]",
    "          Groq API  ──  Llama 3.3 70B",
    "          (fallback: template strings)",
    "                |",
    "         Final Response → Browser",
])

doc.add_paragraph()

# ══════════════════════════════════════════════════════════════════════════════
# 3. CORE COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════
add_heading("3. Core Components", level=1)

# 3.1
add_heading("3.1  app.py — Streamlit UI Layer", level=2)
add_paragraph(
    "The entry point. Streamlit renders the browser chat interface and persists "
    "three objects across messages using session_state:",
    size=11, space_after=4
)
add_bullet("chat_history — every message shown in the chat window")
add_bullet("conversation_state — slot values, active intent, page counter, entity context")
add_bullet("semantic_classifier — the sentence-transformer model (loaded once at startup)")
add_paragraph(
    "On every user submission, app.py calls process_user_message(), receives a "
    "response, appends both turns to chat_history, persists to SQLite, and rerenders. "
    "The sidebar displays the Question Guide — 10 collapsible categories of sample "
    "questions using st.expander().",
    size=11, space_after=8
)

# 3.2
add_heading("3.2  session_manager.py — The Brain", level=2)
add_paragraph(
    "Every message passes through process_user_message() which runs the following "
    "sequence of steps:",
    size=11, space_after=6
)

steps = [
    ("Step 0",   "Hard Reset",            "If user types cancel/reset, wipe all state"),
    ("Step 0.5", "Pagination Shortcut",   "If message = more/next AND last intent was pageable → fetch next page, skip classifier"),
    ("Step 0.6", "Category List",         "If message asks for categories → return live DB list, skip classifier"),
    ("Step 0.7", "History Hydration",     "Scan last 20 messages for order IDs and budgets; inject into state"),
    ("Step 1",   "Reference Resolution",  "Replace 'its price' → actual product name, 'my order' → actual order ID"),
    ("Step 2",   "Intent Classification", "sentence-transformers cosine similarity against 20+ intent examples"),
    ("Step 3",   "Continuation Check",    "If message is 'yes/okay/sure' → reuse last intent"),
    ("Step 4",   "Topic Switch",          "While slot-filling, if user shifts topic with >75% confidence → reset, new intent"),
    ("Step 5",   "Slot Filling",          "Ask for missing required values one at a time; pre-fill from context if possible"),
    ("Step 6",   "Retrieval & Response",  "Route to SQL / RAG / Hybrid / Static based on intent"),
    ("Step 7",   "Dead-end Detection",    "After 2 consecutive unknown responses → show capability help menu"),
]
styled_table(
    ["Step", "Name", "What It Does"],
    [[s, n, d] for s, n, d in steps],
    col_widths=[0.8, 1.7, 3.8]
)
doc.add_paragraph()

# 3.3
add_heading("3.3  Intent Classification — semantic_intent_classifier.py", level=2)
add_paragraph(
    "The SemanticClassifier loads the all-MiniLM-L6-v2 model from sentence-transformers "
    "at startup. For every message it:",
    size=11, space_after=4
)
add_bullet("Converts the resolved message into a 384-dimensional embedding vector")
add_bullet("Compares it to pre-computed vectors for all intent example sentences using cosine similarity")
add_bullet("Returns the intent with the highest similarity score")
add_bullet("Falls back to 'unknown' if the top score is below the confidence threshold")

add_paragraph("Supported intents:", size=11, bold=True, space_before=6, space_after=2)
intents = [
    ["order_tracking", "product_search", "pricing_query", "inventory_query"],
    ["product_recommendation", "product_availability", "discount_offer", "refund_return"],
    ["cancel_order", "payment", "payment_issue", "general_faq"],
    ["shipping", "security_privacy", "account_help", "store_location"],
    ["business_hours", "greeting", "gratitude", "unknown"],
]
styled_table(
    ["Intent Group 1", "Intent Group 2", "Intent Group 3", "Intent Group 4"],
    intents,
    col_widths=[1.6, 1.6, 1.6, 1.6]
)
doc.add_paragraph()

# 3.4
add_heading("3.4  Slot Filling — Required Information Collection", level=2)
add_paragraph(
    "Certain intents require specific information before a database query can run. "
    "The system asks for one missing value at a time and waits for the user's reply.",
    size=11, space_after=6
)
styled_table(
    ["Intent", "Required Slots"],
    [
        ["order_tracking",       "order_id"],
        ["product_recommendation","budget, category"],
        ["refund_return",        "order_id, refund_reason"],
        ["payment_issue",        "order_id, payment_issue_description"],
        ["pricing_query",        "product_name"],
        ["product_availability", "product_name"],
        ["cancel_order",         "order_id"],
        ["inventory_query",      "category"],
    ],
    col_widths=[2.5, 3.8]
)
add_paragraph(
    "If the value is already in the session context (e.g., order_id was mentioned "
    "3 messages ago), the slot is pre-filled silently — no question is asked.",
    size=11, space_before=6, space_after=8
)

# ══════════════════════════════════════════════════════════════════════════════
# 4. RETRIEVAL STRATEGIES
# ══════════════════════════════════════════════════════════════════════════════
add_heading("4. Retrieval Strategies", level=1)
add_paragraph(
    "Once all required slots are filled, rag_router.py assigns one of four retrieval "
    "strategies based on the classified intent.",
    size=11, space_after=8
)

styled_table(
    ["Strategy", "Intents", "Data Source"],
    [
        ["**SQL Retrieval**",    "order_tracking, product_search, pricing_query,\ninventory_query, product_recommendation,\ndiscount_offer, product_availability", "SQLite database"],
        ["**Semantic Search**",  "general_faq, shipping, security_privacy,\naccount_help, store_location, business_hours,\ntechnical_support", "ChromaDB vector store"],
        ["**Hybrid Retrieval**", "refund_return, cancel_order, payment,\npayment_issue", "SQLite + ChromaDB merged"],
        ["**Static Generation**","greeting, gratitude, unknown, complaint,\nescalation", "Template handlers"],
    ],
    col_widths=[1.6, 3.0, 1.7]
)
doc.add_paragraph()

# 4.1 SQL
add_heading("4.1  SQL Retrieval Path", level=2)
add_paragraph(
    "Queries the SQLite database (database/support.db) using parameterised SQL. "
    "All results are paginated with LIMIT 5 OFFSET (page × 5). Key functions:",
    size=11, space_after=4
)
add_bullet("track_order(order_id) — exact match on order_id primary key")
add_bullet("get_matching_products(query) — two-pass product search:")
add_bullet("  Pass 1: LIKE '%query%' substring match, ordered by rating DESC", indent=1)
add_bullet("  Pass 2 (fallback): fuzzy token_set_ratio matching against all 955 product names", indent=1)
add_bullet("  Result: 1 match = show directly | multiple = disambiguation list | 0 = ask to rephrase", indent=1)
add_bullet("get_products_by_category(category) — exact LOWER(category) = LOWER(?) match (prevents 'mens' matching inside 'womens')")
add_bullet("get_products_under_budget(budget, category) — price filter + category + paginated")
add_bullet("get_discounted_products() — ordered by discount_percent DESC")
doc.add_paragraph()

# 4.2 RAG
add_heading("4.2  Semantic Search (RAG) Path", level=2)
add_paragraph("Five sub-steps:", size=11, bold=True, space_after=4)
add_bullet("Query Enrichment (query_enricher.py) — combines user message + active product/category + keywords from last 2 turns")
add_bullet("Embedding — enriched query converted to 384-dim vector via sentence-transformers")
add_bullet("Vector Search (retriever.py) — ChromaDB returns top-K chunks by L2 distance")
add_bullet("Filtering (context_builder.py) — drops chunks with L2 > 1.2, joins remainder with --- separators")
add_bullet("Generation (rag_response_generator.py) — LLM first; template fallback if LLM returns None")
doc.add_paragraph()

# 4.3 Hybrid
add_heading("4.3  Hybrid Retrieval Path", level=2)
add_paragraph(
    "Used when the customer needs both their personal order facts AND the relevant "
    "store policy in the same response (e.g., refund request, cancellation).",
    size=11, space_after=4
)
add_code_block([
    "  SQL Section:",
    "    Order ORD12345 is currently Shipped",
    "    Product: Leather Handbag | Total: PKR 2,199",
    "",
    "  ---",
    "",
    "  Cancellation Policy (from ChromaDB):",
    "    Orders can be cancelled within 24 hours of placement...",
    "",
    "  Both sections passed together to Groq LLM as rag_context.",
    "  LLM writes one coherent response combining personal facts + policy.",
])
doc.add_paragraph()

# 4.4 Static
add_heading("4.4  Static Generation Path", level=2)
add_paragraph(
    "For intents that need no data retrieval, response_generator.py contains "
    "context-aware handlers:",
    size=11, space_after=4
)
add_bullet("handle_greeting() — generic on turn 1; references active product/category on subsequent turns")
add_bullet("handle_unknown() — suggests 'type help' if no context; references active context if set")
add_bullet("handle_cancel_order() — status-aware: different message for delivered vs. in-progress vs. already-cancelled")
add_bullet("Dead-end detection: after 2 consecutive unknown responses, build_help_menu() shows full capability list")
doc.add_paragraph()

# ══════════════════════════════════════════════════════════════════════════════
# 5. LLM INTEGRATION
# ══════════════════════════════════════════════════════════════════════════════
add_heading("5. LLM Integration — Groq API (Llama 3.3 70B)", level=1)

add_paragraph(
    "llm_client.py wraps the Groq SDK. It is called from all three retrieval paths "
    "(RAG, Hybrid, and as an upgrade from SQL-formatted responses where applicable).",
    size=11, space_after=6
)

styled_table(
    ["Component", "Detail"],
    [
        ["Model",           "llama-3.3-70b-versatile"],
        ["Context Window",  "128,000 tokens — comfortably fits system prompt + RAG context + 6-turn history"],
        ["Temperature",     "0.7 — balanced between consistent and natural responses"],
        ["Max Tokens",      "1,024 output tokens per response"],
        ["Client Pattern",  "Singleton — initialised once from GROQ_API_KEY in .env"],
        ["Failure Handling","Any exception returns None; callers fall back to template strings"],
        ["Message Format",  "System prompt → chat history (last 6 turns) → final user turn with RAG context prepended"],
    ],
    col_widths=[2.0, 4.3]
)

doc.add_paragraph()
add_heading("Message Structure Sent to Groq API", level=2)
add_code_block([
    "  messages = [",
    "    { role: system,    content: <store persona + instructions> },",
    "    { role: user,      content: <user turn from history> },",
    "    { role: assistant, content: <bot turn from history> },",
    "    ... (up to 6 history turns) ...",
    "    { role: user,      content: '[Relevant Information]",
    "                                 <SQL data or RAG chunks>",
    "                                 Customer question: <user message>' }",
    "  ]",
])
doc.add_paragraph()

# ══════════════════════════════════════════════════════════════════════════════
# 6. CONVERSATION MEMORY
# ══════════════════════════════════════════════════════════════════════════════
add_heading("6. Conversation Memory System", level=1)
add_paragraph(
    "conversation_memory.py provides three cross-turn memory utilities:",
    size=11, space_after=6
)
styled_table(
    ["Utility", "What It Does"],
    [
        ["extract_entities_from_history()", "Scans last 20 user messages for order IDs (hex / ORD+digits) and budget amounts. Injects discovered values into session context automatically."],
        ["get_conversation_summary()",       "Formats the last 5 turns as compact text (assistant turns truncated to 150 chars). Injected into RAG responses for multi-turn coherence."],
        ["is_dead_end() / increment_unknown()", "Tracks _consecutive_unknown counter. After 2 consecutive unknown responses, shows the capability help menu and resets the counter."],
    ],
    col_widths=[2.3, 4.0]
)
doc.add_paragraph()

# ══════════════════════════════════════════════════════════════════════════════
# 7. DATABASE SCHEMA
# ══════════════════════════════════════════════════════════════════════════════
add_heading("7. Database Schema (SQLite)", level=1)
styled_table(
    ["Table", "Rows", "Key Columns", "Purpose"],
    [
        ["products",   "955",     "product_id, product_name, category, price_pkr, rating", "Product catalog"],
        ["inventory",  "955",     "product_id, stock_quantity, availability",               "Stock levels"],
        ["orders",     "~401K",   "order_id, product_name, category, order_status, order_total", "Customer orders"],
        ["payments",   "~575K",   "order_id, payment_method, amount",                       "Payment records"],
        ["discounts",  "~12.3K",  "product_name, original_price, discounted_price, discount_percent", "Active offers"],
        ["chat_logs",  "dynamic", "user_query, bot_response, sentiment, intent",            "Conversation history"],
    ],
    col_widths=[1.2, 0.7, 2.8, 1.6]
)
doc.add_paragraph()

# ══════════════════════════════════════════════════════════════════════════════
# 8. DATA CLEANING APPLIED
# ══════════════════════════════════════════════════════════════════════════════
add_heading("8. Data Cleaning Applied to Database", level=1)
add_paragraph(
    "The following cleaning operations were applied directly to the SQLite database "
    "to ensure data quality before use in queries and responses.",
    size=11, space_after=6
)
styled_table(
    ["Table", "Issue", "Fix Applied", "Rows"],
    [
        ["orders",    "order_status = NULL",                  "Set to 'N/A'",                        "11"],
        ["orders",    "order_status = literal \\n",            "Set to 'N/A' (matched by hex 5C6E)",  "2"],
        ["orders",    "order_status = 'refund'",              "Normalised to 'refunded'",             "4,083"],
        ["orders",    "order_status = 'cod' (payment method)","Normalised to 'processing'",           "879"],
        ["orders",    "order_status = 'pending_paypal'",      "Normalised to 'pending'",              "5"],
        ["orders",    "category = literal \\n (junk rows)",    "Rows deleted",                        "7,156"],
        ["discounts", "discounted_price >= original_price",   "Invalid rows deleted",                 "577"],
        ["discounts", "discount_percent <= 0 or >= 100",      "Invalid rows deleted",                 "7"],
        ["payments",  "amount <= 0",                          "Invalid records deleted",              "9,693"],
    ],
    col_widths=[1.1, 2.3, 2.0, 0.7]
)
doc.add_paragraph()

# ══════════════════════════════════════════════════════════════════════════════
# 9. COMPLETE MESSAGE FLOW
# ══════════════════════════════════════════════════════════════════════════════
add_heading("9. Complete Message Flow — End to End", level=1)
add_paragraph(
    "The following walkthrough shows exactly what happens when a customer asks "
    "'I want shoes under PKR 5,000':",
    size=11, space_after=6
)
add_code_block([
    "  Turn 1 — User: 'I want shoes under 5000'",
    "  ─────────────────────────────────────────",
    "  [sentiment]       → Neutral",
    "  [Step 0.5]        → 'shoes' is not a 'more' request → skip",
    "  [Step 0.6]        → no 'categor' keyword → skip",
    "  [Step 0.7]        → no entities in history → skip",
    "  [resolve_ref]     → message unchanged",
    "  [classifier]      → intent: product_recommendation, score: 0.87",
    "  [slot check]      → needs: budget, category",
    "  [extract_budget]  → '5000' found ✅",
    "  [extract_category]→ 'shoes' has no DB category match ❌",
    "  [returns]         → 'Please specify a category (type list categories...)'",
    "",
    "  Turn 2 — User: 'Mens Footwear'",
    "  ─────────────────────────────────────────",
    "  [slot fill mode]  → fuzzy_match_category('Mens Footwear')",
    "                       Pass 1: 'mens footwear' in DB categories → MATCH ✅",
    "  [rag_router]      → product_recommendation → sql_retrieval",
    "  [sql_retriever]   → get_products_under_budget(",
    "                         budget=5000, category='Mens Footwear',",
    "                         limit=5, offset=0)",
    "  [format_response] → markdown product list with prices and ratings",
    "  [app.py]          → renders response, saves state",
    "",
    "  Turn 3 — User: 'show me more'",
    "  ─────────────────────────────────────────",
    "  [Step 0.5]        → 'more' + last_intent=product_recommendation",
    "                       → _handle_pagination() → page 2, offset=5",
    "  [classifier]      → NOT CALLED (shortcut fired)",
    "  [sql_retriever]   → get_products_under_budget(... offset=5)",
    "  [app.py]          → renders page 2 results",
])
doc.add_paragraph()

# ══════════════════════════════════════════════════════════════════════════════
# 10. TECHNOLOGIES
# ══════════════════════════════════════════════════════════════════════════════
add_heading("10. Technologies & Libraries", level=1)
styled_table(
    ["Library / Tool", "Role in Project"],
    [
        ["Python 3.12",               "Core language"],
        ["Streamlit",                 "Browser-based chat UI, session state management, sidebar"],
        ["sentence-transformers",     "all-MiniLM-L6-v2 — intent classification and document embeddings"],
        ["ChromaDB",                  "Persistent vector store for knowledge base chunks"],
        ["SQLite (sqlite3)",          "Structured storage for products, orders, payments, discounts"],
        ["Groq SDK",                  "API client for Llama 3.3 70B inference"],
        ["rapidfuzz",                 "Fuzzy product name matching (token_set_ratio, WRatio)"],
        ["TextBlob",                  "Sentiment analysis — polarity scoring of user messages"],
        ["python-dotenv",             "Loads GROQ_API_KEY from .env file"],
        ["pandas / matplotlib",       "Executive dashboard — charts and data analysis in Tab 2"],
        ["PyTorch",                   "Underlying runtime for sentence-transformers"],
    ],
    col_widths=[2.3, 4.0]
)
doc.add_paragraph()

# ══════════════════════════════════════════════════════════════════════════════
# 11. PROPOSAL IMPLEMENTATION STATUS
# ══════════════════════════════════════════════════════════════════════════════
add_heading("11. Project Proposal — Implementation Status", level=1)
styled_table(
    ["Proposed Feature", "Status", "Implementation Detail"],
    [
        ["Automated query classification",   "Implemented",         "sentence-transformers cosine similarity, 20+ intents"],
        ["Intent recognition",               "Implemented",         "SemanticClassifier with confidence scoring"],
        ["Contextual response generation",   "Implemented",         "RAG + Groq LLM + template fallback"],
        ["Human escalation",                 "Partially implemented","Dead-end help menu after repeated unknowns (no live handoff)"],
        ["Multilingual support",             "Not implemented",     "English only; translation layer not added"],
        ["Pre-trained LLMs",                 "Implemented",         "Llama 3.3 70B (stronger than proposed GPT-3)"],
        ["Dialogue management",              "Implemented",         "Custom slot-filling engine in session_manager.py"],
        ["Knowledge base integration",       "Implemented",         "ChromaDB with FAQ and policy documents"],
        ["Python",                           "Implemented",         "Python 3.12 throughout"],
        ["Hugging Face Transformers",        "Implemented",         "sentence-transformers (built on HuggingFace)"],
        ["Flask / FastAPI UI",               "Replaced",            "Streamlit chosen — simpler, sufficient for demo"],
    ],
    col_widths=[2.2, 1.5, 2.6]
)
doc.add_paragraph()

# ══════════════════════════════════════════════════════════════════════════════
# 12. SYSTEM LIMITATIONS
# ══════════════════════════════════════════════════════════════════════════════
add_heading("12. Limitations & Future Improvements", level=1)
styled_table(
    ["Limitation", "Suggested Improvement"],
    [
        ["No actual human handoff",            "Integrate a ticketing system (e.g., Zendesk API) when dead-end is detected"],
        ["English only",                       "Add a translation layer (e.g., Helsinki-NLP models) before intent classification"],
        ["No model fine-tuning",               "Fine-tune Llama on domain-specific e-commerce chat logs"],
        ["Product names are very long",        "Add a product name normalisation step to clean up catalog entries"],
        ["Static knowledge base",              "Auto-sync ChromaDB when FAQ documents are updated"],
        ["No user authentication",             "Add login so order history can be personalised per customer"],
    ],
    col_widths=[2.5, 3.8]
)
doc.add_paragraph()

# ══════════════════════════════════════════════════════════════════════════════
# SAVE
# ══════════════════════════════════════════════════════════════════════════════
out_path = "AI_Customer_Support_Project_Report.docx"
doc.save(out_path)
print(f"Report saved: {out_path}")
