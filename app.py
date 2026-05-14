import json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime
from pathlib import Path

# Custom Core Modules
import database_manager as db
from database_manager import get_tickets_summary, get_recent_tickets, get_user_chats, get_user_tickets
from auth import get_user_stats, create_session, get_session_user, delete_session
from login_page import show_login_page
import extra_streamlit_components as stx
from sentiment import analyze_sentiment
from data_loader import load_orders, load_reviews, load_order_items, load_products, load_category_translation

# NLP Semantic, State & Response Modules
from semantic_intent_classifier import get_classifier
from response_generator import ResponseGenerator
from session_manager import process_user_message, initialize_state
from rag.retriever import initialize_retriever

# 1. Initialize DB & Global Models (must run before login so users table exists)
db.init_db()
initialize_retriever()
response_router = ResponseGenerator()
semantic_classifier = get_classifier()

# 2. Config & Setup
st.set_page_config(page_title="AI Customer Support", page_icon="🛍️", layout="wide")

# Modern CSS Styling
st.markdown("""
<style>
/* Clean modern UI overrides */
.stButton>button { width: 100%; border-radius: 5px; font-weight: bold; }
.sentiment-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.8em;
    font-weight: bold;
    color: white;
    margin-top: 5px;
    margin-right: 5px;
}
.badge-Positive { background-color: #4CAF50; }
.badge-Neutral { background-color: #9E9E9E; }
.badge-Negative { background-color: #F44336; }
div.stMetric > div {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

# Cookie manager — must be initialised before the auth gate (no caching — it's a widget)
_cookies = stx.CookieManager(key="ai_support_cookies")

# 3. Cached Data Processing for Dashboard
@st.cache_data
def load_all_dashboard_data():
    orders = load_orders()
    reviews = load_reviews()
    items = load_order_items()
    products = load_products()
    translations = load_category_translation()
    return orders, reviews, items, products, translations

@st.cache_data
def calculate_insights():
    orders, reviews, items, products, translations = load_all_dashboard_data()
    most_common_status = orders['order_status'].mode().iloc[0]
    avg_score = reviews['review_score'].mean()
    pos = len(reviews[reviews['review_score'] >= 4])
    neg = len(reviews[reviews['review_score'] <= 2])
    orders['est_date'] = pd.to_datetime(orders['order_estimated_delivery_date'], errors='coerce')
    orders['del_date'] = pd.to_datetime(orders['order_delivered_customer_date'], errors='coerce')
    delivered = orders[orders['order_status'] == 'delivered']
    delayed = len(delivered[delivered['del_date'] > delivered['est_date']])
    total_delivered = len(delivered)
    delay_pct = (delayed / total_delivered * 100) if total_delivered > 0 else 0
    on_time = total_delivered - delayed
    r_i = pd.merge(reviews[['order_id', 'review_score']], items[['order_id', 'product_id']], on='order_id', how='inner')
    r_i_p = pd.merge(r_i, products[['product_id', 'product_category_name']], on='product_id', how='inner')
    r_i_p_t = pd.merge(r_i_p, translations, on='product_category_name', how='inner')
    cat_scores = r_i_p_t.groupby('product_category_name_english')['review_score'].agg(['mean', 'count'])
    problematic = cat_scores[cat_scores['count'] >= 50].sort_values('mean').head(3)
    orders['month_year'] = pd.to_datetime(orders['order_purchase_timestamp'], errors='coerce').dt.strftime('%Y-%m')
    monthly_trend = orders.groupby('month_year').size().sort_index()
    top_10_cats = r_i_p_t['product_category_name_english'].value_counts().head(10)
    return {
        'most_common_status': most_common_status, 'avg_score': avg_score, 'pos': pos, 'neg': neg,
        'delayed': delayed, 'on_time': on_time, 'delay_pct': delay_pct, 'problematic': problematic,
        'monthly_trend': monthly_trend, 'top_10_cats': top_10_cats,
        'status_dist': orders['order_status'].value_counts(), 'score_dist': reviews['review_score'].value_counts().sort_index()
    }

import runtime_config

# 3. Authentication Gate — auto-login from cookie or show login page
_SESSION_COOKIE = "ai_support_session"

if not st.session_state.get("logged_in", False):
    _token = _cookies.get(_SESSION_COOKIE)
    if _token:
        _user = get_session_user(_token)
        if _user:
            st.session_state.logged_in = True
            st.session_state.user = _user
        else:
            # Token expired or invalid — clear it
            _cookies.delete(_SESSION_COOKIE)

if not st.session_state.get("logged_in", False):
    show_login_page()
    st.stop()

# If user just logged in via the form (no cookie yet), create and set one now
if st.session_state.get("logged_in") and not _cookies.get(_SESSION_COOKIE):
    _new_token = create_session(st.session_state.user["id"])
    _cookies.set(_SESSION_COOKIE, _new_token, expires_at=datetime.datetime(2099, 1, 1))

with st.spinner("Initializing Data Engine & AI Models..."):
    insights = calculate_insights()

# 4. Session State Initialization
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "conversation_state" not in st.session_state:
    st.session_state.conversation_state = initialize_state()

# Inject authenticated user_id into conversation state so tickets/chats are attributed
st.session_state.conversation_state["context"]["user_id"] = st.session_state.user["id"]

# Sync fallback setting from session state into the shared runtime config
runtime_config.set_fallback(st.session_state.get("fallback_enabled", True))

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.title("🛍️ AI Support Hub")

    # ── User Profile Card ─────────────────────────────────────────────────────
    user = st.session_state.user
    stats = get_user_stats(user["id"])
    st.markdown(
        f"""
        <div style="background:#f8f9fa; border-radius:10px; padding:12px 14px; margin-bottom:8px;">
            <div style="font-size:1.1rem; font-weight:700;">👤 {user['full_name']}</div>
            <div style="color:#6c757d; font-size:0.8rem;">@{user['username']}</div>
            <div style="color:#6c757d; font-size:0.78rem; margin-top:4px;">📧 {user['email']}</div>
            <hr style="margin:8px 0; border-color:#dee2e6;">
            <div style="display:flex; gap:16px; font-size:0.82rem;">
                <span>💬 <b>{stats['total_chats']}</b> chats</span>
                <span>🎫 <b>{stats['total_tickets']}</b> tickets</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_reset, col_logout = st.columns(2)
    with col_reset:
        if st.button("🔄 Reset Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.conversation_state = initialize_state()
            st.session_state.conversation_state["context"]["user_id"] = user["id"]
            st.rerun()
    with col_logout:
        if st.button("🚪 Logout", use_container_width=True):
            _tok = _cookies.get(_SESSION_COOKIE)
            if _tok:
                delete_session(_tok)
                _cookies.delete(_SESSION_COOKIE)
            for key in ["logged_in", "user", "chat_history", "conversation_state"]:
                st.session_state.pop(key, None)
            st.rerun()

    st.divider()

    # ── Question Guide ────────────────────────────────────────────────────────
    st.markdown("### 💡 What Can I Ask?")
    st.caption("Click any category to expand sample questions.")

    _QUESTION_GUIDE = {
        "📦 Order Tracking": [
            "Where is my order?",
            "Track order ORD12345",
            "What is the status of my order?",
            "Has my package been shipped yet?",
            "When will my order be delivered?",
        ],
        "🛍️ Product Search & Browse": [
            "Show me products in Men's Watches",
            "What products do you have in Electronics?",
            "List all categories",
            "Show me more products",
            "Browse Women's Bags",
        ],
        "💰 Product Recommendations": [
            "Recommend me something under PKR 5,000",
            "I want a watch under 10,000",
            "Suggest budget-friendly electronics",
            "What can I buy under PKR 3,000 in footwear?",
            "Show me more recommendations",
        ],
        "🏷️ Pricing & Availability": [
            "What is the price of Samsung Galaxy S24?",
            "Is the Nike Air Max in stock?",
            "How much does the leather bag cost?",
            "Check availability of Xiaomi Redmi Note",
            "What is the price range for laptops?",
        ],
        "🎁 Discounts & Offers": [
            "Are there any discounts available?",
            "Show me sale items",
            "What products are on offer?",
            "Show discounted products",
            "Show me more deals",
        ],
        "↩️ Refunds & Returns": [
            "I want a refund",
            "How do I return a product?",
            "My item was damaged, I need a refund",
            "What is your return policy?",
            "Can I return after 7 days?",
        ],
        "❌ Cancel Order": [
            "I want to cancel my order",
            "Cancel order ORD12345",
            "How do I cancel a placed order?",
            "Can I cancel after shipping?",
        ],
        "💳 Payments": [
            "What payment methods do you accept?",
            "Do you accept credit cards?",
            "Is cash on delivery available?",
            "I have a payment issue with my order",
            "My payment was deducted but order not placed",
        ],
        "🚚 Shipping & Delivery": [
            "How long does shipping take?",
            "Do you offer free shipping?",
            "What are your delivery charges?",
            "Do you ship across Pakistan?",
            "Can I track my shipment?",
        ],
        "🎫 Raise a Support Ticket": [
            "I want to raise a ticket",
            "Create a support ticket for my issue",
            "I need to report a problem",
            "Open a complaint ticket",
            "Log an issue with my order",
            "Submit a support request",
        ],
        "❓ General & Store Info": [
            "What are your store hours?",
            "How do I contact support?",
            "What is your privacy policy?",
            "Do you have a loyalty program?",
            "How do I create an account?",
        ],
    }

    for category, questions in _QUESTION_GUIDE.items():
        with st.expander(category, expanded=False):
            for q in questions:
                st.markdown(f"- {q}")

    st.divider()

    # ── FAQ Panel ─────────────────────────────────────────────────────────────
    st.markdown("### ❓ Frequently Asked Questions")
    st.caption("Browse common questions and answers. Click any topic to expand.")

    _FAQ_CATEGORIES = {
        "📦 Order Tracking & Status": [
            "how to track my order",
            "order status meanings",
            "order not received",
            "wrong item received",
            "damaged item received",
        ],
        "↩️ Returns & Refunds": [
            "return policy",
            "refund policy",
            "exchange policy",
            "product not as described",
        ],
        "❌ Order Cancellation": [
            "order cancellation",
            "how to cancel after shipping",
            "partial order cancellation",
            "cancellation refund timeline",
        ],
        "💳 Payments": [
            "payment methods",
            "cash on delivery",
            "jazzcash easypaisa",
            "failed payment",
            "payment security",
            "invoice and receipt",
        ],
        "🚚 Shipping & Delivery": [
            "shipping time",
            "free shipping",
            "delivery charges",
            "shipping across pakistan",
            "express delivery",
            "international shipping",
            "delivery not on time",
            "change delivery address",
        ],
        "🛍️ Products & Pricing": [
            "product categories",
            "how to search products",
            "product availability",
            "product reviews",
            "warranty",
            "minimum order",
        ],
        "🎁 Discounts & Offers": [
            "discount codes",
            "bundle deals",
            "gift cards",
        ],
        "🎫 Support Tickets": [
            "how to raise a complaint",
            "support ticket status",
            "human agent",
        ],
        "❓ General & Account": [
            "create account",
            "store hours",
            "loyalty program",
            "privacy policy",
            "data deletion",
            "app download",
            "business account",
        ],
    }

    @st.cache_data
    def _load_faq():
        faq_path = Path(__file__).parent / "faq.json"
        with open(faq_path, "r", encoding="utf-8") as f:
            return json.load(f)

    _faq_data = _load_faq()

    for faq_cat, faq_keys in _FAQ_CATEGORIES.items():
        with st.expander(faq_cat, expanded=False):
            for key in faq_keys:
                answer = _faq_data.get(key)
                if answer:
                    st.markdown(f"**Q: {key.replace('_', ' ').title()}**")
                    st.caption(answer)
                    st.markdown("")

    st.divider()

    # ── Debug Panel ───────────────────────────────────────────────────────────
    with st.expander("🛠️ Debug State Panel", expanded=False):
        st.json(st.session_state.conversation_state)

    st.markdown("### 💾 Export Data")
    chat_df = db.get_all_chats_df()
    if not chat_df.empty:
        csv = chat_df.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Export Chat Logs (CSV)", data=csv, file_name="chat_logs.csv", mime="text/csv")

    # ── LLM Fallback Toggle ───────────────────────────────────────────────────
    fallback_on = st.session_state.get("fallback_enabled", True)
    label = "🟢 Fallback: ON" if fallback_on else "🔴 Fallback: OFF"
    help_text = (
        "ON: If the LLM fails, a static template response is shown.\n"
        "OFF: If the LLM fails, an error message is shown instead."
    )
    if st.button(label, help=help_text, use_container_width=False):
        st.session_state.fallback_enabled = not fallback_on
        runtime_config.set_fallback(not fallback_on)
        st.rerun()

# ==========================================
# MAIN HEADER
# ==========================================
st.title("E-Commerce AI Support Platform")
st.markdown("Professional, context-aware customer service automation powered by the Olist E-commerce Dataset.")
st.divider()

# TABS
tab1, tab2, tab3, tab4 = st.tabs(["💬 AI Assistant", "📈 Executive Dashboard", "🧠 Support Insights", "👤 My Account"])

# ==========================================
# TAB 1: AI ASSISTANT
# ==========================================
with tab1:
    col_chat, col_empty = st.columns([3, 1])
    with col_chat:
        
        # 1. Render Persistent Chat History
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["message"])
                
                if msg["role"] == "user":
                    badges = f"<span class='sentiment-badge badge-{msg.get('sentiment', 'Neutral')}'>Sentiment: {msg.get('sentiment', 'Neutral')}</span> "
                    if msg.get("api_payload"):
                        badges += f"<span class='sentiment-badge badge-Neutral'>Flow: {msg['api_payload'].get('intent', 'N/A')}</span> "
                        if msg['api_payload'].get("retrieval_strategy"):
                            badges += f"<span class='sentiment-badge badge-Neutral'>Retriever: {msg['api_payload'].get('retrieval_strategy')}</span>"
                    st.markdown(badges, unsafe_allow_html=True)
                    
                    if msg.get("api_payload"):
                        with st.expander("API Response & RAG Debugging"):
                            st.json(msg["api_payload"])
                    
                if msg["role"] == "assistant" and msg.get("escalated"):
                    st.markdown("<span class='sentiment-badge badge-Negative'>⚠️ Escalated to Human Agent</span>", unsafe_allow_html=True)

        # 2. Handle New User Input
        if prompt := st.chat_input("How can I help you today?"):
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Sentiment Analysis
            sentiment_label, polarity, tone = analyze_sentiment(prompt)
            sentiment_result = (sentiment_label, polarity, tone)

            # Context-Aware Stateful Pipeline
            with st.spinner("Processing memory & semantic context..."):
                final_response, escalated, new_state, api_payload = process_user_message(
                    user_message=prompt,
                    chat_history=st.session_state.chat_history,
                    conversation_state=st.session_state.conversation_state,
                    semantic_classifier=semantic_classifier,
                    response_router=response_router,
                    sentiment_result=sentiment_result
                )

            # Update Session Architecture
            st.session_state.conversation_state = new_state

            # Append memory logs
            st.session_state.chat_history.append({
                "role": "user",
                "message": prompt,
                "sentiment": sentiment_label,
                "timestamp": timestamp,
                "api_payload": api_payload
            })

            st.session_state.chat_history.append({
                "role": "assistant",
                "message": final_response,
                "escalated": escalated,
                "timestamp": timestamp
            })

            # Save to persistent database (attributed to the logged-in user)
            db.save_chat(
                prompt, final_response, sentiment_label,
                api_payload.get("intent", "unknown"),
                1 if escalated else 0,
                user_id=st.session_state.user["id"],
            )

            # Force immediate re-render to display the appended messages
            st.rerun()

# ==========================================
# TAB 2: EXECUTIVE DASHBOARD
# ==========================================
with tab2:
    st.subheader("Platform Activity Dashboard")
    fig_col1, fig_col2 = st.columns(2)
    with fig_col1:
        st.markdown("**Order Status Distribution**")
        fig1, ax1 = plt.subplots(figsize=(6, 4))
        insights['status_dist'].head(5).plot(kind='bar', ax=ax1, color='#4CAF50')
        ax1.set_ylabel("Number of Orders")
        ax1.tick_params(axis='x', rotation=45)
        st.pyplot(fig1)
        st.markdown("**Delayed vs On-Time Deliveries**")
        fig3, ax3 = plt.subplots(figsize=(6, 4))
        ax3.pie([insights['on_time'], insights['delayed']], labels=['On-Time', 'Delayed'], autopct='%1.1f%%', colors=['#81C784', '#E57373'], startangle=90)
        ax3.axis('equal')
        st.pyplot(fig3)
    with fig_col2:
        st.markdown("**Monthly Order Volume Trend**")
        fig4, ax4 = plt.subplots(figsize=(6, 4))
        insights['monthly_trend'].plot(kind='line', ax=ax4, color='#FF9800', marker='o')
        ax4.set_ylabel("Orders")
        ax4.tick_params(axis='x', rotation=45)
        st.pyplot(fig4)
        st.markdown("**Top 10 Product Categories**")
        fig5, ax5 = plt.subplots(figsize=(6, 4))
        insights['top_10_cats'].sort_values().plot(kind='barh', ax=ax5, color='#2196F3')
        ax5.set_xlabel("Units Sold")
        st.pyplot(fig5)

# ==========================================
# TAB 3: SUPPORT INSIGHTS
# ==========================================
with tab3:
    st.subheader("🧠 Operational & Support Insights")
    st.markdown("Actionable intelligence generated dynamically from historical customer interactions.")
    m1, m2, m3 = st.columns(3)
    m1.metric("Average Review Score", f"{insights['avg_score']:.2f} / 5.0", delta="-0.5 from Target", delta_color="inverse")
    m2.metric("Delayed Delivery Rate", f"{insights['delay_pct']:.1f}%", delta="Critical KPI", delta_color="off")
    m3.metric("Pos/Neg Review Ratio", f"{insights['pos'] / insights['neg'] if insights['neg']>0 else 0:.1f}x", delta="Positive dominant", delta_color="normal")
    st.divider()
    col_prob, col_scores = st.columns(2)
    with col_prob:
        st.error("**🚨 Most Problematic Categories (Lowest Avg Score)**")
        for cat, row in insights['problematic'].iterrows():
            st.markdown(f"- **{cat.replace('_', ' ').title()}**: {row['mean']:.2f} ⭐ ({int(row['count'])} reviews)")
    with col_scores:
        st.info("**⭐ Review Score Distribution**")
        fig2, ax2 = plt.subplots(figsize=(5, 3))
        insights['score_dist'].plot(kind='bar', ax=ax2, color='#9C27B0')
        ax2.set_xlabel("Star Rating")
        ax2.set_ylabel("Review Count")
        ax2.tick_params(axis='x', rotation=0)
        st.pyplot(fig2)
    st.divider()
    st.markdown("### 📝 Recent Chat Logs")
    recent_chats = db.get_recent_chats(5)
    if recent_chats:
        for chat in recent_chats:
            escalation_badge = "⚠️ ESCALATED" if chat[5] else "✅ RESOLVED"
            with st.expander(f"[{chat[3]}] {escalation_badge} - User: {chat[0][:60]}..."):
                st.write(f"**Query:** {chat[0]}")
                st.markdown(f"**Classification:** <span class='sentiment-badge badge-{chat[2]}'>Sentiment: {chat[2]}</span> <span class='sentiment-badge badge-Neutral'>Intent: {chat[4]}</span>", unsafe_allow_html=True)
                st.write(f"**Bot Response:** {chat[1]}")
    else:
        st.write("No recent chat history.")

    st.divider()
    st.markdown("### 🎫 Support Ticket Overview")

    ticket_summary = get_tickets_summary()
    t1, t2, t3 = st.columns(3)
    t1.metric("Total Tickets Raised", ticket_summary["total"])
    t2.metric("Open Tickets", ticket_summary["open"], delta_color="inverse")
    t3.metric("Resolved Tickets", ticket_summary["total"] - ticket_summary["open"])

    if ticket_summary["by_type"]:
        col_ttype, col_trecent = st.columns([1, 2])
        with col_ttype:
            st.markdown("**Tickets by Issue Type**")
            for issue_type, count in ticket_summary["by_type"].items():
                label = issue_type.replace("_", " ").title()
                st.markdown(f"- **{label}**: {count}")

        with col_trecent:
            st.markdown("**Recent Support Tickets**")
            recent_tickets = get_recent_tickets(8)
            if recent_tickets:
                for t in recent_tickets:
                    status_icon = "✅" if t["status"] == "resolved" else "🔴"
                    header = f"{status_icon} Ticket #{t['ticket_id']} — {t['issue_type'].replace('_', ' ').title()} [{t['created_at'][:10]}]"
                    with st.expander(header, expanded=False):
                        st.write(f"**Order ID:** {t['order_id']}")
                        st.write(f"**Status:** {t['status'].title()}")
                        st.write(f"**Description:** {t['description']}")
            else:
                st.write("No support tickets yet.")
    else:
        st.info("No support tickets have been raised yet.")

# ==========================================
# TAB 4: MY ACCOUNT
# ==========================================
with tab4:
    _u = st.session_state.user
    _stats = get_user_stats(_u["id"])

    st.subheader(f"👤 My Account — {_u['full_name']}")
    st.divider()

    # Profile info cards
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Username", f"@{_u['username']}")
    p2.metric("Email", _u["email"])
    p3.metric("Total Chats", _stats["total_chats"])
    p4.metric("Support Tickets", _stats["total_tickets"])

    joined = _u.get("created_at", "")
    if joined:
        st.caption(f"Account created: {joined[:10]}")

    st.divider()

    # ── Personal Chat History ─────────────────────────────────────────────────
    st.markdown("### 💬 My Chat History")
    my_chats = get_user_chats(_u["id"], limit=20)
    if my_chats:
        for chat in my_chats:
            esc_icon = "⚠️ ESCALATED" if chat["escalated"] else "✅"
            sentiment_color = {"Positive": "#4CAF50", "Negative": "#F44336"}.get(chat["sentiment"], "#9E9E9E")
            label = (
                f"{esc_icon} [{chat['created_at'][:16]}] "
                f"— Intent: {(chat['intent'] or 'N/A').replace('_', ' ').title()} "
                f"— {chat['user_query'][:55]}..."
            )
            with st.expander(label, expanded=False):
                st.markdown(
                    f"<span style='background:{sentiment_color};color:white;padding:2px 8px;"
                    f"border-radius:8px;font-size:0.78rem;'>Sentiment: {chat['sentiment']}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**You asked:** {chat['user_query']}")
                st.markdown(f"**Bot replied:** {chat['bot_response']}")
    else:
        st.info("No chat history yet. Start a conversation in the AI Assistant tab.")

    st.divider()

    # ── Personal Ticket History ───────────────────────────────────────────────
    st.markdown("### 🎫 My Support Tickets")
    my_tickets = get_user_tickets(_u["id"], limit=20)
    if my_tickets:
        for t in my_tickets:
            status_icon = "✅" if t["status"] == "resolved" else "🔴"
            with st.expander(
                f"{status_icon} Ticket #{t['ticket_id']} — {t['issue_type'].replace('_', ' ').title()} [{t['created_at'][:10]}]",
                expanded=False,
            ):
                col_a, col_b = st.columns(2)
                col_a.write(f"**Order ID:** {t['order_id']}")
                col_b.write(f"**Status:** {t['status'].title()}")
                st.write(f"**Description:** {t['description']}")
    else:
        st.info("No support tickets raised yet. You can raise one in the AI Assistant tab.")
