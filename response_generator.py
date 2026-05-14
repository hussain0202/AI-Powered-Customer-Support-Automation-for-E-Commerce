
import re
from typing import Any, Dict, Optional

from database.sql_retriever import (
    get_product_price,
    get_available_inventory,
    get_products_under_budget,
    get_products_by_category,
    get_payment_methods,
    get_discounted_products,
    track_order,
    search_products,
    format_products_response,
    format_price_response,
    format_order_response,
)
from database_manager import log_support_ticket


def extract_budget(text: str) -> Optional[float]:
    match = re.search(r"\d+", text.replace(",", ""))
    return float(match.group()) if match else None


def extract_order_id(text: str) -> Optional[str]:
    match = re.search(r"\b\d{6,}\b|\bORD\d+\b", text, re.IGNORECASE)
    return match.group() if match else None


def extract_product_name(text: str) -> str:
    text = text.lower()
    remove_phrases = [
        "what is the price of",
        "price of",
        "how much is",
        "how much does",
        "tell me price of",
        "check price of",
        "is available",
        "available",
    ]

    for phrase in remove_phrases:
        text = text.replace(phrase, "")

    return text.strip()


def extract_category(text: str) -> Optional[str]:
    from context_intelligence import fuzzy_match_category
    return fuzzy_match_category(text)


class ResponseGenerator:
    def generate_response(
        self,
        user_message: str,
        intent: str,
        confidence: str = "MEDIUM",
        conversation_state: Optional[Dict[str, Any]] = None,
        chat_history: Optional[list] = None,
    ) -> str:
        conversation_state = conversation_state or {}
        chat_history = chat_history or []

        handlers = {
            "greeting": self.handle_greeting,
            "goodbye": self.handle_goodbye,
            "gratitude": self.handle_gratitude,
            "pricing_query": self.handle_pricing_query,
            "inventory_query": self.handle_inventory_query,
            "product_recommendation": self.handle_product_recommendation,
            "product_search": self.handle_product_search,
            "product_availability": self.handle_product_availability,
            "payment": self.handle_payment,
            "payment_issue": self.handle_payment_issue,
            "discount_offer": self.handle_discount_offer,
            "order_tracking": self.handle_order_tracking,
            "shipping": self.handle_shipping,
            "refund_return": self.handle_refund_return,
            "cancel_order": self.handle_cancel_order,
            "cart_management": self.handle_cart_management,
            "wishlist": self.handle_wishlist,
            "account_help": self.handle_account_help,
            "technical_support": self.handle_technical_support,
            "complaint": self.handle_complaint,
            "general_faq": self.handle_general_faq,
            "human_escalation": self.handle_human_escalation,
            "unknown": self.handle_unknown,
        }

        handler = handlers.get(intent, self.handle_unknown)

        return handler(
            user_message=user_message,
            conversation_state=conversation_state,
            chat_history=chat_history,
            confidence=confidence,
        )

    def handle_greeting(
        self,
        conversation_state: Dict[str, Any],
        chat_history: list,
        **kwargs,
    ) -> str:
        # Returning user — personalise based on active context
        if chat_history and len(chat_history) >= 2:
            category = conversation_state.get("active_category")
            product = conversation_state.get("active_product")
            if category:
                label = category.replace("_", " ")
                return (
                    f"Welcome back! We were looking at {label} products earlier. "
                    f"Would you like to continue browsing, or is there something else I can help you with?"
                )
            if product:
                return (
                    f"Welcome back! We were discussing {product} earlier. "
                    f"How can I assist you today?"
                )
        return "Hello! Welcome to our E-Commerce store. How can I assist you today?"

    def handle_goodbye(self, **kwargs) -> str:
        return "Thank you for visiting. Have a great day!"

    def handle_gratitude(self, **kwargs) -> str:
        return "You're welcome! I'm happy to help."

    def handle_pricing_query(self, user_message: str, conversation_state: Dict[str, Any], **kwargs) -> str:
        product_name = conversation_state.get("active_product")

        extracted_product = extract_product_name(user_message)

        if extracted_product:
            product_name = extracted_product

        if not product_name:
            conversation_state["active_intent"] = "pricing_query"
            conversation_state["pending_slot"] = "product_name"
            conversation_state["awaiting_user_input"] = True
            return "Please provide the product name so I can check the price."

        matches = get_product_price(product_name)

        if not matches:
            return "I couldn't find that product in our database. Please try another product name."

        if len(matches) == 1:
            conversation_state["active_product"] = matches[0]["product_name"]
            return format_price_response(matches[0])

        lines = [f"I found {len(matches)} products matching **{product_name}**. Which one did you mean?\n"]
        for i, p in enumerate(matches, 1):
            lines.append(f"{i}. **{p['product_name']}** — PKR {p['price_pkr']:,.0f} | Rating: {p.get('rating', 'N/A')}")
        lines.append("\nPlease type the full product name to get the exact price.")
        return "\n".join(lines)

    def handle_inventory_query(self, user_message: str, conversation_state: Dict[str, Any], **kwargs) -> str:
        category = extract_category(user_message) or conversation_state.get("active_category")

        if not category:
            conversation_state["active_intent"] = "inventory_query"
            conversation_state["pending_slot"] = "category"
            conversation_state["awaiting_user_input"] = True
            return "Please specify a category (type 'list categories' to see all available options)."

        products = get_available_inventory(category=category, limit=8)

        if not products:
            return f"I couldn't find in-stock products for {category}. Please try another category."

        conversation_state["active_category"] = category

        return format_products_response(
            products,
            title=f"Available {category.replace('_', ' ')} products:"
        )

    def handle_product_recommendation(self, user_message: str, conversation_state: Dict[str, Any], **kwargs) -> str:
        budget = extract_budget(user_message) or conversation_state.get("active_budget")
        category = extract_category(user_message) or conversation_state.get("active_category")

        if not budget:
            conversation_state["active_intent"] = "product_recommendation"
            conversation_state["pending_slot"] = "budget"
            conversation_state["awaiting_user_input"] = True
            return "Please share your budget."

        conversation_state["active_budget"] = budget

        if not category:
            conversation_state["active_intent"] = "product_recommendation"
            conversation_state["pending_slot"] = "category"
            conversation_state["awaiting_user_input"] = True
            return "Great! What category are you interested in? Electronics, fashion, beauty, gaming, or home appliances?"

        conversation_state["active_category"] = category

        products = get_products_under_budget(
            budget=budget,
            category=category,
            limit=5
        )

        return format_products_response(
            products,
            title=f"Here are recommended {category.replace('_', ' ')} products under PKR {budget:,.0f}:"
        )

    def handle_product_search(self, user_message: str, conversation_state: Dict[str, Any], **kwargs) -> str:
        category = extract_category(user_message)

        if category:
            products = get_products_by_category(category=category, limit=8)
            conversation_state["active_category"] = category

            return format_products_response(
                products,
                title=f"Here are products from {category.replace('_', ' ')}:"
            )

        return "Please tell me what product or category you want to search for."

    def handle_product_availability(self, user_message: str, conversation_state: Dict[str, Any], **kwargs) -> str:
        product_name = extract_product_name(user_message) or conversation_state.get("active_product")

        if not product_name:
            conversation_state["active_intent"] = "product_availability"
            conversation_state["pending_slot"] = "product_name"
            conversation_state["awaiting_user_input"] = True
            return "Please provide the product name so I can check availability."

        results = search_products(product_name, limit=1)

        if not results:
            return "I couldn't find that product in our database. Please try a different name."

        product = results[0]
        conversation_state["active_product"] = product["product_name"]

        stock_label = product.get("availability", "available").replace("_", " ")
        qty = product.get("stock_quantity")
        qty_str = f" ({qty} units in stock)" if qty is not None else ""

        return (
            f"{product['product_name']} — {stock_label}{qty_str}\n"
            f"Price: PKR {product['price_pkr']:,.0f}\n"
            f"Rating: {product.get('rating', 'N/A')}"
        )

    def handle_payment(self, **kwargs) -> str:
        methods = get_payment_methods()

        if not methods:
            return "I couldn't find payment methods in the system."

        return "We currently support these payment methods:\n\n" + "\n".join(
            f"- {method}" for method in methods
        )

    def handle_payment_issue(self, **kwargs) -> str:
        return "Please share your order ID and describe the payment issue, such as failed payment, deducted amount, or declined transaction."

    def handle_discount_offer(self, **kwargs) -> str:
        discounts = get_discounted_products(limit=5)

        if not discounts:
            return "There are currently no discount offers available."

        lines = ["Here are the top discounted products:", ""]

        for item in discounts:
            lines.append(
                f"- {item['product_name']} — PKR {item['discounted_price']:,.0f} "
                f"({item['discount_percent']}% off)"
            )

        return "\n".join(lines)

    def handle_order_tracking(self, user_message: str, conversation_state: Dict[str, Any], **kwargs) -> str:
        order_id = extract_order_id(user_message) or conversation_state.get("active_order_id")

        if not order_id:
            conversation_state["active_intent"] = "order_tracking"
            conversation_state["pending_slot"] = "order_id"
            conversation_state["awaiting_user_input"] = True
            return "Please provide your order ID."

        order = track_order(order_id)

        if order:
            conversation_state["active_order_id"] = order_id
            return format_order_response(order)

        return "I could not find this order ID in our system."

    def handle_shipping(self, **kwargs) -> str:
        return "Shipping time depends on your city and product availability. Usually, orders are delivered within 3–7 working days."

    def handle_refund_return(self, user_message: str, conversation_state: Dict[str, Any], **kwargs) -> str:
        order_id = extract_order_id(user_message) or conversation_state.get("active_order_id")

        if not order_id:
            return "I can help with refunds or returns. Please provide your order ID."

        order = track_order(order_id)
        if not order:
            return f"I couldn't find order {order_id}. Please check the order ID and try again."

        conversation_state["active_order_id"] = order_id
        return (
            f"Order {order_id} details:\n"
            f"  Product: {order['product_name']}\n"
            f"  Status: {order['order_status']}\n"
            f"  Payment Method: {order['payment_method']}\n"
            f"  Total: PKR {order['order_total']:,.0f}\n\n"
            f"Returns are accepted within 7 days of delivery. "
            f"Please describe the reason for your return to proceed."
        )

    def handle_cancel_order(self, user_message: str, conversation_state: Dict[str, Any], **kwargs) -> str:
        order_id = extract_order_id(user_message) or conversation_state.get("active_order_id")

        if not order_id:
            return "Please provide your order ID so I can check whether it can still be cancelled."

        order = track_order(order_id)
        if not order:
            return f"I couldn't find order {order_id}. Please double-check the order ID."

        conversation_state["active_order_id"] = order_id
        status = order["order_status"].lower()

        if status in ("delivered", "completed"):
            return (
                f"Order {order_id} has already been {order['order_status']} and cannot be cancelled.\n"
                f"Product: {order['product_name']}\n"
                f"Total: PKR {order['order_total']:,.0f}\n\n"
                f"You may be eligible for a return instead. Would you like to initiate a refund?"
            )
        if status in ("cancelled", "canceled"):
            return f"Order {order_id} has already been cancelled."

        return (
            f"Order {order_id} is currently {order['order_status']}.\n"
            f"Product: {order['product_name']}\n"
            f"Total: PKR {order['order_total']:,.0f}\n\n"
            f"Please contact our support team to confirm the cancellation request."
        )

    def handle_cart_management(self, **kwargs) -> str:
        return (
            "Cart management is handled through our website and mobile app. "
            "I can help you find products, check prices, check availability, "
            "or recommend items within your budget — just ask!"
        )

    def handle_wishlist(self, **kwargs) -> str:
        return (
            "Wishlist management is available through your account on our website. "
            "I can help you find products, check their availability and price, "
            "or recommend alternatives — just tell me what you are looking for."
        )

    def handle_account_help(self, **kwargs) -> str:
        return (
            "For account-related issues such as login problems, password reset, "
            "or profile updates, please visit our website's Help Center or contact "
            "our support team directly at support@store.com. "
            "I can help you with orders, products, payments, and refunds right here."
        )

    def handle_technical_support(self, user_message: str, conversation_state: Dict[str, Any], **kwargs) -> str:
        order_id = conversation_state.get("active_order_id")
        ticket_id = log_support_ticket(
            order_id=order_id or "N/A",
            issue_type="technical_support",
            description=user_message,
        )
        return (
            f"Your technical issue has been logged as ticket #{ticket_id}. "
            f"Our team will look into it and respond within 24 hours. "
            f"If the issue is urgent, please contact support@store.com directly."
        )

    def handle_complaint(self, user_message: str, conversation_state: Dict[str, Any], **kwargs) -> str:
        order_id = conversation_state.get("active_order_id")
        ticket_id = log_support_ticket(
            order_id=order_id or "N/A",
            issue_type="complaint",
            description=user_message,
        )
        return (
            f"I'm sorry to hear about your experience. Your complaint has been recorded "
            f"as ticket #{ticket_id} and will be reviewed by our team within 24 hours. "
            f"If you'd like to share more details, please go ahead."
        )

    def handle_general_faq(self, **kwargs) -> str:
        return "I can help with FAQs about orders, refunds, shipping, payments, accounts, and products."

    def handle_human_escalation(self, user_message: str, conversation_state: Dict[str, Any], **kwargs) -> str:
        order_id = conversation_state.get("active_order_id")
        ticket_id = log_support_ticket(
            order_id=order_id or "N/A",
            issue_type="human_escalation",
            description=user_message,
        )
        return (
            f"Your request has been escalated to our human support team (ticket #{ticket_id}). "
            f"A representative will contact you shortly. "
            f"For immediate help, please reach us at support@store.com or call 0300-1234567."
        )

    def handle_unknown(self, conversation_state: Dict[str, Any], **kwargs) -> str:
        # Offer a context-aware hint if we know what the user was doing
        category = conversation_state.get("active_category")
        product = conversation_state.get("active_product")
        if category:
            return (
                f"I'm not sure I understood that. We were looking at {category.replace('_', ' ')} products — "
                f"would you like to search, get recommendations, or check prices?"
            )
        if product:
            return (
                f"I'm not sure I understood that. We were discussing {product} — "
                f"would you like to check its price, availability, or something else?"
            )
        return (
            "I'm not entirely sure how to help with that. "
            "Could you rephrase, or type 'help' to see what I can assist you with?"
        )
