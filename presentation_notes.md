# 🎤 Presentation Notes: E-Commerce AI Support Platform

## 1. Elevator Pitch
"Hello, I'm presenting our AI Support Platform. We've built a robust, data-driven customer service automation system that handles order tracking, intelligent product recommendations, and real-time sentiment analysis, all integrated directly into a live dashboard for support operations."

## 2. Problem Statement
"E-commerce stores face a massive volume of repetitive inquiries. Customers want to know where their orders are, what they should buy, and they want their complaints heard. Doing this manually creates bottlenecks, lowers customer satisfaction, and burns out human agents."

## 3. Dataset Explanation
"To make this real, we're using the Olist Brazilian E-Commerce dataset. It's a relational database representing over 100,000 real orders, products, and customer reviews. This means our insights and recommendations are grounded in actual historical sales and logistical data."

## 4. AI Concepts Used
"We purposefully kept the system lightweight and interpretable. 
- We use **NLP Sentiment Analysis** via TextBlob to gauge customer frustration in real-time.
- We built a **hybrid recommendation heuristic** that maps English queries to Portuguese product datasets, returning the statistically highest-selling items in matching categories.
- We use **Intent Classification** to intelligently route queries to the correct logical module."

## 5. Architecture Explanation
"The architecture is highly modular. Streamlit serves as the presentation layer. When a user sends a message, our `intent_classifier.py` and `language_utils.py` route the request appropriately. It then calls specific core modules (`chatbot.py`, `recommender.py`, `knowledge_base.py`) which query pandas dataframes in-memory. Finally, `response_generator.py` compiles the context and automatically flags conversations for **Human Escalation** if confidence is low. Everything is asynchronously logged to SQLite."

## 6. Feature Walkthrough
- **Chat Assistant**: "Notice how we can drop an order ID, and the bot instantly pulls logistics data and calculates if the order was delayed."
- **Sentiment & Escalation**: "If I type an angry message or ask for an agent, watch the sentiment badge turn red and an 'Escalated to Human' badge appear."
- **Knowledge Base & Language**: "It handles basic FAQs seamlessly, and detects Portuguese inputs to trigger simulated multilingual responses."
- **Insights Dashboard**: "In the background, the app is aggregating problematic categories—those with the lowest average review scores—giving operations managers an instant hit-list of quality control issues."

## 7. Challenges Faced
"The biggest challenge was language barriers and data sparsity. The dataset is Portuguese, and product descriptions are limited. We overcame this by building a translation mapping layer in `recommender.py` and relying on aggregate numerical review scores when text sentiment was unreliable."

## 8. Future Improvements
"In V2, we plan to implement semantic search. By embedding product descriptions into a Vector Database, we can offer fuzzy searches without relying on exact keyword intersections. We also plan to integrate an LLM for conversational memory."

## 9. Demo Flow
1. Start at the **AI Assistant** tab. Point out the Proposal Alignment Sidebar.
2. Ask a KB question (`"What payment methods are available?"`).
3. Ask for a product recommendation (`"Show me beauty products"`).
4. Demonstrate Portuguese detection (`"Quanto tempo demora a entrega?"`).
5. Express frustration to show sentiment detection and escalation (`"I am angry about my delayed package"`).
6. Input a real order ID (`e481f51cbdc54678b7cc49136f2d6af7`) to show tracking capabilities.
7. Click over to the **Executive Dashboard** and **Support Insights** tabs to highlight the charts and Problematic Categories.

## 10. Potential Evaluator Q&A

**Q: Why not use LangChain or OpenAI?**
**A:** "We followed the KISS principle. By using rule-based routing, Regex, and TextBlob, the system runs completely locally, costs $0 in API credits, has zero latency, and is 100% predictable."

**Q: How does the SQLite integration scale?**
**A:** "Currently it's perfect for local persistence of chat logs. If we moved to production, we would swap the SQLite driver for PostgreSQL, but the modular `database.py` design means the core application logic wouldn't need to change."

**Q: How does the Recommendation Engine actually work without a Vector DB?**
**A:** "It uses a set-intersection technique. It tokenizes the user's query, finds keyword overlaps in the English category translations, maps back to the Portuguese dataset, and ranks products by historical purchase frequency."

## 11. Proposal vs Final Implementation
- **Proposed Models vs Reality**: Proposed GPT/BERT fine-tuning was replaced with lightweight explainable NLP due to project scope, speed, and local hardware constraints. 
- **Real Dataset Priority**: Mock setups were scrapped in favor of integrating the real, massive Olist dataset.
- **Completeness**: The final system is practical, stable, and completely demo-ready while fulfilling all original proposal requirements (Context generation, Knowledge Base, Escalation, Multilingual Support).
