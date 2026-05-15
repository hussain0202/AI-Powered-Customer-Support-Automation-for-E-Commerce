import re
import logging
from database.sql_retriever import (
    track_order,
    update_order_status,
    get_product_price,
    get_available_inventory,
    get_products_by_category,
    get_products_under_budget,
    get_discounted_products,
    get_payment_methods,
    get_all_categories,
    format_products_response,
    format_price_response,
    format_order_response,
)

from database_manager import log_support_ticket
from rag.rag_router import determine_strategy
from rag.retriever import retrieve_context
from rag.context_builder import build_context
from rag.rag_response_generator import generate_rag_response
from rag.query_enricher import enrich_query
from rag.hybrid_retriever import retrieve_policy_context, build_hybrid_response

from context_intelligence import resolve_references, fuzzy_match_category, detect_continuation
from conversation_memory import (
    extract_entities_from_history,
    get_conversation_summary,
    is_dead_end,
    increment_unknown,
    reset_unknown,
    build_help_menu,
)

logger = logging.getLogger(__name__)

INTENT_SLOT_REQUIREMENTS = {
    "inventory_query": ["category"],
    "product_recommendation": ["budget", "category"],
    "order_tracking": ["order_id"],
    "refund_return": ["order_id", "refund_reason", "refund_confirmation"],
    "product_availability": ["product_name"],
    "pricing_query": ["product_name"],
    "cancel_order": ["order_id"],
    "payment_issue": ["order_id", "payment_issue_description"],
    "raise_ticket": ["ticket_issue_type", "ticket_description"],
}

FOLLOW_UP_QUESTIONS = {
    "category": "Please specify a category (type 'list categories' to see all available options).",
    "budget": "Please share your budget.",
    "order_id": "Please provide your order ID.",
    "refund_reason": "Please tell me the reason for the return/refund.",
    "refund_confirmation": (
        "Thank you for providing the details. Would you like us to raise a return/refund ticket?\n\n"
        "Our support team will review your request and process it accordingly.\n\n"
        "Please reply **yes** to confirm or **no** to cancel."
    ),
    "product_name": "Please provide the product name.",
    "payment_issue_description": "Please describe the payment issue you are facing.",
    "ticket_issue_type": (
        "What type of issue would you like to report?\n\n"
        "1. Payment Problem\n"
        "2. Delivery Issue\n"
        "3. Damaged / Wrong Item\n"
        "4. Order Cancellation Issue\n"
        "5. Complaint\n"
        "6. Other\n\n"
        "Please type the number or name of your issue type."
    ),
    "ticket_description": "Please describe your issue in detail so we can help you better.",
}

def extract_budget(text: str):
    match = re.search(r'\b\d+(?:,\d+)*\b', text.replace(" ", ""))
    if match:
        return match.group(0).replace(",", "")
    return None

def extract_category(text: str):
    return fuzzy_match_category(text)

def extract_order_id(text: str):
    match = re.search(r'\b[a-f0-9]{32}\b', text, re.IGNORECASE)
    if match: return match.group(0)
    match = re.search(r'\b(?:ORD)?\d{3,}\b', text, re.IGNORECASE)
    if match: return match.group(0)
    return None

def extract_product_name(text: str):
    meaningless = ["tell me", "yes", "no", "okay", "ok", "hmm", "what", "sure", "idk", "help", "nothing"]
    if text.lower().strip() in meaningless:
        return None
    return text.strip()

def extract_confirmation(text: str):
    lower = text.lower().strip()
    yes_words = {"yes", "yeah", "yep", "sure", "ok", "okay", "confirm", "proceed", "please", "go ahead", "create", "raise", "do it", "agree"}
    no_words = {"no", "nope", "nah", "cancel", "nevermind", "never mind", "don't", "do not", "skip", "stop", "reject"}
    if any(w in lower for w in yes_words):
        return "yes"
    if any(w in lower for w in no_words):
        return "no"
    return None

_TICKET_TYPE_MAP = {
    "1": "Payment Problem",
    "2": "Delivery Issue",
    "3": "Damaged / Wrong Item",
    "4": "Order Cancellation Issue",
    "5": "Complaint",
    "6": "Other",
    "payment": "Payment Problem",
    "delivery": "Delivery Issue",
    "damaged": "Damaged / Wrong Item",
    "wrong": "Damaged / Wrong Item",
    "cancellation": "Order Cancellation Issue",
    "cancel": "Order Cancellation Issue",
    "complaint": "Complaint",
    "other": "Other",
}

# Slots that must be answered explicitly via follow-up questions — never extract from the intent trigger message
_NO_PREFILL_SLOTS = {"ticket_issue_type", "ticket_description", "refund_reason", "refund_confirmation"}


def extract_issue_type(text: str):
    lower = text.lower().strip()
    for key, label in _TICKET_TYPE_MAP.items():
        if key in lower:
            return label
    return None  # Only accept explicit number (1-6) or keyword — no fallback

def extract_entity(text: str, slot_name: str):
    if slot_name == "order_id": return extract_order_id(text)
    elif slot_name == "budget": return extract_budget(text)
    elif slot_name == "category": return extract_category(text)
    elif slot_name == "ticket_issue_type": return extract_issue_type(text)
    elif slot_name == "refund_confirmation": return extract_confirmation(text)
    elif slot_name in ["product_name", "refund_reason", "payment_issue_description", "ticket_description"]:
        return extract_product_name(text)
    return None

PAGE_SIZE = 5
PAGEABLE_INTENTS = {"product_recommendation", "inventory_query", "product_search", "discount_offer"}
_MORE_WORDS = {"more", "next", "another", "additional", "else", "further", "others", "rest"}


def _is_more_request(text: str) -> bool:
    words = set(re.sub(r"[^a-z\s]", "", text.lower()).split())
    return bool(words & _MORE_WORDS)


def _is_category_list_request(text: str) -> bool:
    lower = text.lower()
    has_cat = "categor" in lower
    has_list_word = any(w in lower for w in ["list", "show", "what", "all", "give", "see", "which"])
    return has_cat and has_list_word


def _query_sig(intent: str, category, budget) -> str:
    return f"{intent}|{str(category).lower()}|{budget}"


def _handle_pagination(user_message: str, state: dict) -> tuple:
    """Executes the next page of results for the last pageable intent."""
    active_intent = state["last_completed_intent"]
    state["active_intent"] = active_intent

    category = state["context"].get("active_category")
    budget = state["context"].get("active_budget")

    current_sig = _query_sig(active_intent, category, budget)
    page = state["context"].get("_product_page", 0) + 1
    state["context"]["_product_page"] = page
    state["context"]["_last_query_sig"] = current_sig
    offset = page * PAGE_SIZE
    page_label = f" (page {page + 1})"

    if active_intent == "product_recommendation":
        products = get_products_under_budget(budget=budget, category=category, limit=PAGE_SIZE, offset=offset)
        if not products:
            data_response = "No more products found. You've seen all available results."
        else:
            parts = ["Recommended"]
            if category:
                parts.append(category.replace("_", " "))
            parts.append("products")
            if budget:
                parts.append(f"under PKR {budget:,.0f}")
            title = " ".join(parts) + page_label + ":"
            data_response = format_products_response(products, title=title)

    elif active_intent == "inventory_query":
        products = get_available_inventory(category=category, limit=PAGE_SIZE, offset=offset)
        label = category.replace("_", " ") if category else "all categories"
        data_response = (
            format_products_response(products, title=f"In-stock products — {label}{page_label}:")
            if products else "No more products found."
        )

    elif active_intent == "product_search":
        products = get_products_by_category(category=category, limit=PAGE_SIZE, offset=offset) if category else []
        label = category.replace("_", " ") if category else "our catalog"
        data_response = (
            format_products_response(products, title=f"Products from {label}{page_label}:")
            if products else "No more products found."
        )

    elif active_intent == "discount_offer":
        discounts = get_discounted_products(limit=PAGE_SIZE, offset=offset)
        if not discounts:
            data_response = "No more discounted products found. You've seen all available offers."
        else:
            lines = [f"Top discounted products{page_label}:", ""]
            for item in discounts:
                lines.append(
                    f"- {item['product_name']} — PKR {item['discounted_price']:,.0f} "
                    f"(was PKR {item['original_price']:,.0f}, {item['discount_percent']}% off)"
                )
            data_response = "\n".join(lines)

    else:
        data_response = "I'm not sure how to show more for this request."

    state["last_completed_intent"] = active_intent
    api_payload = {
        "intent": active_intent,
        "status": "paginated",
        "page": page,
        "retrieval_strategy": "sql_retrieval",
        "context": state["context"],
    }
    return data_response, False, state, api_payload


def initialize_state():
    """Initializes a fresh conversation state with persistent memory."""
    return {
        "active_intent": None,
        "pending_slot": None,
        "collected_slots": {},
        "last_bot_question": None,
        "awaiting_user_input": False,
        "last_completed_intent": None,
        "context": {
            "active_budget": None,
            "active_product": None,
            "active_category": None,
            "active_order_id": None,
            "last_shown_items": [],
            "_product_page": 0,
            "_last_query_sig": None,
            "_consecutive_unknown": 0,
        }
    }

def reset_workflow(state):
    """Resets active workflow slots but PRESERVES persistent conversational context."""
    return {
        "active_intent": None,
        "pending_slot": None,
        "collected_slots": {},
        "last_bot_question": None,
        "awaiting_user_input": False,
        "last_completed_intent": state.get("last_completed_intent"),
        "context": state.get("context", {})
    }


def process_user_message(user_message: str, chat_history: list, conversation_state: dict, semantic_classifier, response_router, sentiment_result):
    """
    Central Contextual Reasoning Engine handling multi-step slot filling, dialogue memory, RAG, and reference resolution.
    """
    if "context" not in conversation_state:
        conversation_state = initialize_state()

    state = conversation_state.copy()

    # 0. User manually overrides or cancels
    if user_message.lower() in ["cancel", "stop", "start over", "reset"]:
        state = initialize_state()
        return "Conversation reset. How can I help you?", False, state, {"intent": "reset"}

    # 0.5 Pagination shortcut — intercept before classifier so "more"/"next" never misroutes
    if _is_more_request(user_message) and state.get("last_completed_intent") in PAGEABLE_INTENTS:
        return _handle_pagination(user_message, state)

    # 0.6 Category list shortcut — return live category list regardless of active flow
    if _is_category_list_request(user_message):
        categories = get_all_categories()
        cat_list = "\n".join(f"- {c}" for c in categories)
        return (
            f"Here are our available product categories:\n\n{cat_list}\n\n"
            f"Which category would you like to browse?"
        ), False, state, {"intent": "general_faq", "status": "category_list"}

    intent_res = {}

    # 0.7 Hydrate context from chat history for any entities not yet in active state
    hist = extract_entities_from_history(chat_history)
    if hist.get("order_id") and not state["context"].get("active_order_id"):
        state["context"]["active_order_id"] = hist["order_id"]
    if hist.get("budget") and not state["context"].get("active_budget"):
        state["context"]["active_budget"] = float(hist["budget"])

    # 1. CORE INTELLIGENCE: Reference Resolution & Context Injection
    resolved_message = resolve_references(user_message, state["context"])

    # 2. CORE INTELLIGENCE: Continuation Intent Check
    if detect_continuation(resolved_message) and not state["awaiting_user_input"] and state["last_completed_intent"]:
        active_intent = state["last_completed_intent"]
        intent_res = {"intent": active_intent, "confidence": "HIGH", "score": 1.0}
        state["active_intent"] = active_intent
        state["collected_slots"] = {}
        if "category" in INTENT_SLOT_REQUIREMENTS.get(active_intent, []) and state["context"].get("active_category"):
            state["collected_slots"]["category"] = state["context"]["active_category"]

    # 3. Active Slot Filling & Topic Switch Detection
    elif state["awaiting_user_input"] and state["pending_slot"]:
        intent_check = semantic_classifier.predict_intent(resolved_message)
        check_intent = intent_check.get("intent", "unknown")
        check_score = intent_check.get("score", 0.0)

        if check_score > 0.75 and check_intent not in ["unknown", "greeting", "gratitude", state["active_intent"], "general_faq"]:
            logger.info(f"Topic switch detected. Shifting from {state['active_intent']} to {check_intent}")
            state = reset_workflow(state)
            state["active_intent"] = check_intent
            intent_res = intent_check
            if check_intent in INTENT_SLOT_REQUIREMENTS:
                for req_slot in INTENT_SLOT_REQUIREMENTS[check_intent]:
                    val = extract_entity(resolved_message, req_slot)
                    if val: state["collected_slots"][req_slot] = val
        else:
            extracted_value = extract_entity(resolved_message, state["pending_slot"])
            if extracted_value:
                state["collected_slots"][state["pending_slot"]] = extracted_value
                state["pending_slot"] = None
                state["awaiting_user_input"] = False
                intent_res = {"intent": state["active_intent"], "confidence": "HIGH", "score": 1.0}
            else:
                if state["pending_slot"] == "category":
                    categories = get_all_categories()
                    cat_list = "\n".join(f"- {c}" for c in categories)
                    return (
                        f"I couldn't match that to a category. Here are the available ones:\n\n"
                        f"{cat_list}\n\n"
                        f"Please type one of the above."
                    ), False, state, {"intent": state["active_intent"], "status": "slot_retry"}
                return (
                    f"I couldn't detect a valid response. {state['last_bot_question']}"
                ), False, state, {"intent": state["active_intent"], "status": "slot_retry"}
    else:
        # 4. Standard Intent Classification (Using resolved context message)
        intent_res = semantic_classifier.predict_intent(resolved_message)
        active_intent = intent_res.get("intent", "unknown")

        state["active_intent"] = active_intent
        state["collected_slots"] = {}

        # Contextual Pre-filling
        if active_intent in INTENT_SLOT_REQUIREMENTS:
            for req_slot in INTENT_SLOT_REQUIREMENTS[active_intent]:
                # ticket slots must always be answered explicitly — never filled from trigger message
                if req_slot in _NO_PREFILL_SLOTS:
                    continue
                val = extract_entity(resolved_message, req_slot)
                if not val and req_slot == "product_name" and state["context"].get("active_product"):
                    val = state["context"]["active_product"]
                if not val and req_slot == "category" and state["context"].get("active_category"):
                    val = state["context"]["active_category"]
                if not val and req_slot == "budget" and state["context"].get("active_budget"):
                    val = state["context"]["active_budget"]
                if not val and req_slot == "order_id" and state["context"].get("active_order_id"):
                    val = state["context"]["active_order_id"]

                if val: state["collected_slots"][req_slot] = val

    active_intent = state["active_intent"]

    # 5. Iterative Slot Requirement Loop
    if active_intent in INTENT_SLOT_REQUIREMENTS:
        for slot in INTENT_SLOT_REQUIREMENTS[active_intent]:
            if slot not in state["collected_slots"]:
                state["pending_slot"] = slot
                state["awaiting_user_input"] = True
                question = FOLLOW_UP_QUESTIONS.get(slot, f"Please provide your {slot.replace('_', ' ')}.")
                state["last_bot_question"] = question
                return question, False, state, {"intent": active_intent, "status": "slot_filling", "missing": slot}

    # 6. Execution & Context Updating (All slots collected)
    data_response = None
    retrieval_strategy = determine_strategy(active_intent)

    # Context Mapping Layer
    if "category" in state["collected_slots"]:
        state["context"]["active_category"] = state["collected_slots"]["category"]
    if "product_name" in state["collected_slots"]:
        state["context"]["active_product"] = state["collected_slots"]["product_name"]
    if "order_id" in state["collected_slots"]:
        state["context"]["active_order_id"] = state["collected_slots"]["order_id"]

    if retrieval_strategy == "sql_retrieval":
        # --- Pagination offset calculation ---
        if active_intent in PAGEABLE_INTENTS:
            current_sig = _query_sig(
                active_intent,
                state["collected_slots"].get("category") or state["context"].get("active_category"),
                state["collected_slots"].get("budget") or state["context"].get("active_budget"),
            )
            if _is_more_request(user_message) and current_sig == state["context"].get("_last_query_sig"):
                page = state["context"].get("_product_page", 0) + 1
            else:
                page = 0
            state["context"]["_product_page"] = page
            state["context"]["_last_query_sig"] = current_sig
            offset = page * PAGE_SIZE
        else:
            offset = 0

        if active_intent == "order_tracking":
            order_id = state["collected_slots"].get("order_id")
            order = track_order(order_id)
            state["context"]["active_order_id"] = order_id
            data_response = format_order_response(order)

        elif active_intent == "product_availability":
            product_name = state["collected_slots"].get("product_name")
            matches = get_product_price(product_name)
            if not matches:
                data_response = (
                    f"I couldn't find any product matching **{product_name}**. "
                    f"Please try a more specific name."
                )
            elif len(matches) == 1:
                p = matches[0]
                state["context"]["active_product"] = p["product_name"]
                avail = p.get("availability", "N/A")
                stock = p.get("stock_quantity")
                stock_str = f" ({stock} units)" if stock is not None else ""
                data_response = (
                    f"**{p['product_name']}**\n"
                    f"Availability: {avail}{stock_str}\n"
                    f"Price: PKR {p['price_pkr']:,.0f}\n"
                    f"Rating: {p.get('rating', 'N/A')}"
                )
            else:
                lines = [
                    f"I found {len(matches)} products matching **{product_name}**. "
                    f"Which one did you mean?\n"
                ]
                for i, p in enumerate(matches, 1):
                    avail = p.get("availability", "N/A")
                    lines.append(
                        f"{i}. **{p['product_name']}** — PKR {p['price_pkr']:,.0f} "
                        f"| {avail} | Rating: {p.get('rating', 'N/A')}"
                    )
                lines.append("\nPlease type the full product name to get exact details.")
                data_response = "\n".join(lines)

        elif active_intent == "pricing_query":
            product_name = state["collected_slots"].get("product_name")
            matches = get_product_price(product_name)
            if not matches:
                data_response = (
                    f"I couldn't find any product matching **{product_name}**. "
                    f"Please try a more specific name."
                )
            elif len(matches) == 1:
                p = matches[0]
                state["context"]["active_product"] = p["product_name"]
                data_response = format_price_response(p)
            else:
                lines = [
                    f"I found {len(matches)} products matching **{product_name}**. "
                    f"Which one did you mean?\n"
                ]
                for i, p in enumerate(matches, 1):
                    lines.append(
                        f"{i}. **{p['product_name']}** — PKR {p['price_pkr']:,.0f} "
                        f"| Rating: {p.get('rating', 'N/A')}"
                    )
                lines.append("\nPlease type the full product name to get the exact price.")
                data_response = "\n".join(lines)

        elif active_intent == "inventory_query":
            category = state["collected_slots"].get("category") or state["context"].get("active_category")
            products = get_available_inventory(category=category, limit=PAGE_SIZE, offset=offset)
            if category:
                state["context"]["active_category"] = category
            label = category.replace("_", " ") if category else "all categories"
            page_label = f" (page {page + 1})" if page > 0 else ""
            if not products and page > 0:
                data_response = f"No more in-stock products for {label}. You've seen all available items."
            elif not products:
                data_response = (
                    f"No in-stock products found for **{label}**.\n"
                    f"Try a different category — type 'list categories' to see all options."
                )
            else:
                data_response = format_products_response(
                    products, title=f"In-stock products — {label}{page_label}:"
                )

        elif active_intent == "product_search":
            category = extract_category(resolved_message) or state["context"].get("active_category")
            products = get_products_by_category(category=category, limit=PAGE_SIZE, offset=offset) if category else []
            if category:
                state["context"]["active_category"] = category
            label = category.replace("_", " ") if category else "our catalog"
            page_label = f" (page {page + 1})" if page > 0 else ""
            if not products and page > 0:
                data_response = f"No more products for {label}. You've reached the end of the results."
            elif not products:
                data_response = (
                    f"No products found for **{label}**.\n"
                    f"Type 'list categories' to browse other options."
                )
            else:
                data_response = format_products_response(
                    products, title=f"Products from {label}{page_label}:"
                )

        elif active_intent == "product_recommendation":
            raw_budget = state["collected_slots"].get("budget")
            budget = float(raw_budget) if raw_budget else None
            category = state["collected_slots"].get("category") or state["context"].get("active_category")
            if budget:
                state["context"]["active_budget"] = budget
            if category:
                state["context"]["active_category"] = category
            products = get_products_under_budget(budget=budget, category=category, limit=PAGE_SIZE, offset=offset)
            title = f"Recommended {category.replace('_', ' ') if category else ''} products"
            if budget:
                title += f" under PKR {budget:,.0f}"
            if page > 0:
                title += f" (page {page + 1})"
            if not products and page > 0:
                data_response = "No more products found. You've seen all available results."
            elif not products:
                budget_str = f"PKR {budget:,.0f}" if budget else "your budget"
                data_response = (
                    f"No products found for **{category.replace('_', ' ') if category else 'this category'}** "
                    f"within {budget_str}.\n"
                    f"Try increasing your budget or a different category."
                )
            else:
                data_response = format_products_response(products, title=title.strip() + ":")

        elif active_intent == "discount_offer":
            discounts = get_discounted_products(limit=PAGE_SIZE, offset=offset)
            if not discounts and page > 0:
                data_response = "No more discounted products found. You've seen all available offers."
            elif not discounts:
                data_response = "There are currently no active discount offers."
            else:
                page_label = f" (page {page + 1})" if page > 0 else ""
                lines = [f"Top discounted products{page_label}:", ""]
                for item in discounts:
                    lines.append(
                        f"- {item['product_name']} — PKR {item['discounted_price']:,.0f} "
                        f"(was PKR {item['original_price']:,.0f}, {item['discount_percent']}% off)"
                    )
                data_response = "\n".join(lines)

        # payment, cancel_order, refund_return, payment_issue → handled in hybrid_retrieval block below

    elif retrieval_strategy == "semantic_search":
        enriched = enrich_query(resolved_message, state["context"], chat_history)
        retrieved_chunks = retrieve_context(enriched, top_k=5)
        context_str = build_context(retrieved_chunks)
        conv_summary = get_conversation_summary(chat_history)
        data_response = generate_rag_response(resolved_message, context_str, active_intent, conv_summary, chat_history)

    elif retrieval_strategy == "hybrid_retrieval":
        sql_section = None

        if active_intent == "payment":
            methods = get_payment_methods()
            if methods:
                sql_section = "We support the following payment methods:\n\n" + "\n".join(
                    f"- {m}" for m in methods
                )

        elif active_intent == "cancel_order":
            order_id = state["collected_slots"].get("order_id")
            order = track_order(order_id)
            state["context"]["active_order_id"] = order_id
            if not order:
                sql_section = f"I couldn't find order {order_id} in our system. Please check the order ID."
            else:
                status = order["order_status"].lower()
                if status in ("delivered", "completed"):
                    sql_section = (
                        f"Order {order_id} has already been {order['order_status']} and cannot be cancelled.\n"
                        f"Product: {order['product_name']}\n"
                        f"Total: PKR {order['order_total']:,.0f}\n\n"
                        f"You may be eligible for a return instead."
                    )
                elif status in ("cancelled", "canceled"):
                    sql_section = f"Order {order_id} has already been cancelled."
                else:
                    # ── ACTUALLY cancel the order in the database ──────────
                    update_order_status(order_id, "cancelled")
                    sql_section = (
                        f"Order {order_id} has been successfully cancelled.\n"
                        f"Product: {order['product_name']}\n"
                        f"Total: PKR {order['order_total']:,.0f}\n\n"
                        f"The cancellation has been recorded. "
                        f"If a payment was made, a refund will be processed per our refund policy."
                    )

        elif active_intent == "refund_return":
            order_id = state["collected_slots"].get("order_id")
            refund_reason = state["collected_slots"].get("refund_reason", "Not specified")
            confirmation = state["collected_slots"].get("refund_confirmation", "yes")
            order = track_order(order_id)
            state["context"]["active_order_id"] = order_id
            if not order:
                sql_section = f"I couldn't find order {order_id}. Please double-check the order ID."
            elif confirmation == "no":
                sql_section = (
                    f"No problem! Your return/refund request for order {order_id} has been cancelled.\n"
                    f"If you change your mind or need any further assistance, feel free to ask."
                )
            else:
                current_status = order["order_status"].lower()
                if current_status == "refunded":
                    sql_section = (
                        f"Order {order_id} has already been refunded.\n"
                        f"Product: {order['product_name']}\n"
                        f"Total: PKR {order['order_total']:,.0f}"
                    )
                elif current_status in ("cancelled", "canceled"):
                    sql_section = (
                        f"Order {order_id} was already cancelled. "
                        f"If a payment was made, please contact support for refund details."
                    )
                else:
                    ticket_id = log_support_ticket(
                        order_id=order_id,
                        issue_type="refund_return",
                        description=f"Return/Refund Request. Reason: {refund_reason}",
                        user_id=state["context"].get("user_id"),
                    )
                    sql_section = (
                        f"Your return/refund request has been submitted successfully.\n\n"
                        f"**Ticket ID:** #{ticket_id}\n"
                        f"**Reason:** {refund_reason}\n\n"
                        f"Order Details:\n"
                        f"  Product: {order['product_name']}\n"
                        f"  Current Status: {order['order_status']}\n"
                        f"  Payment Method: {order['payment_method']}\n"
                        f"  Total: PKR {order['order_total']:,.0f}\n\n"
                        f"Our support team will review ticket #{ticket_id} and process your return/refund within 24–48 hours. "
                        f"Please save your ticket ID for future reference."
                    )

        elif active_intent == "payment_issue":
            order_id = state["collected_slots"].get("order_id")
            issue_desc = state["collected_slots"].get("payment_issue_description", "Not specified")
            order = track_order(order_id)
            state["context"]["active_order_id"] = order_id
            if not order:
                sql_section = f"I couldn't find order {order_id} in our system."
            else:
                # ── Actually log the ticket in the database ────────────────
                ticket_id = log_support_ticket(
                    order_id=order_id,
                    issue_type="payment_issue",
                    description=issue_desc,
                    user_id=state["context"].get("user_id"),
                )
                sql_section = (
                    f"Payment issue ticket #{ticket_id} has been created for order {order_id}.\n"
                    f"Issue: {issue_desc}\n\n"
                    f"Order Details:\n"
                    f"  Product: {order['product_name']}\n"
                    f"  Status: {order['order_status']}\n"
                    f"  Payment Method: {order['payment_method']}\n"
                    f"  Total: PKR {order['order_total']:,.0f}\n\n"
                    f"Our team will review ticket #{ticket_id} and contact you within 24 hours."
                )

        policy_context = retrieve_policy_context(
            resolved_message, state["context"], chat_history
        )
        data_response = build_hybrid_response(sql_section, policy_context, active_intent, resolved_message, chat_history)

    # 6b. raise_ticket — direct DB write before LLM/static routing
    if active_intent == "raise_ticket" and not data_response:
        issue_type  = state["collected_slots"].get("ticket_issue_type", "General Issue")
        description = state["collected_slots"].get("ticket_description", resolved_message)
        order_id    = state["collected_slots"].get("order_id") or state["context"].get("active_order_id")

        ticket_id = log_support_ticket(
            order_id=order_id or "N/A",
            issue_type=issue_type,
            description=description,
            user_id=state["context"].get("user_id"),
        )

        data_response = (
            f"Your support ticket has been created successfully.\n\n"
            f"**Ticket ID:** #{ticket_id}\n"
            f"**Issue Type:** {issue_type}\n"
            f"**Order ID:** {order_id or 'Not linked'}\n"
            f"**Description:** {description}\n"
            f"**Status:** Open\n\n"
            f"Our support team will review your ticket and respond within 24 hours. "
            f"Please save your ticket ID #{ticket_id} for future reference."
        )

    # 7. Final Output Routing
    if data_response:
        final_response = data_response
    else:
        final_response = response_router.generate_response(
            user_message=resolved_message,
            intent=active_intent,
            confidence=intent_res.get("confidence", "MEDIUM"),
            conversation_state=state["context"],
            chat_history=chat_history,
        )

    # 8. Dead-end detection — offer help menu after repeated unknown responses
    if active_intent == "unknown":
        increment_unknown(state)
        if is_dead_end(state):
            reset_unknown(state)
            final_response = build_help_menu()
    else:
        reset_unknown(state)

    # 9. Human escalation — log ticket and set escalated flag for UI badge
    escalated = False
    if active_intent == "human_escalation":
        order_id = state["context"].get("active_order_id")
        log_support_ticket(
            order_id=order_id or "N/A",
            issue_type="human_escalation",
            description=resolved_message,
            user_id=state["context"].get("user_id"),
        )
        escalated = True

    # Safe Workflow Completion Clear (Preserving Memory)
    state["last_completed_intent"] = active_intent

    # Preserve conversational continuity
    if active_intent not in ["product_recommendation", "inventory_query", "pricing_query", "product_search"]:
        state = reset_workflow(state)

    api_payload = {
        "intent": active_intent,
        "status": "completed",
        "score": intent_res.get("score", 1.0),
        "retrieval_strategy": retrieval_strategy,
        "resolved_message": resolved_message,
        "context": state["context"],
    }

    return final_response, escalated, state, api_payload