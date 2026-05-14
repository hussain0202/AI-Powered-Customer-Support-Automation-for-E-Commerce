# 🛒 E-Commerce AI Support Platform

## 🎯 Problem Statement
E-commerce businesses process thousands of customer queries daily regarding order status, product recommendations, and complaints. Managing this manually is slow, expensive, and scales poorly.

## 💡 Solution Overview
This project is an AI-powered customer support assistant built specifically for E-commerce platforms. It automates:
1. **Order Tracking**: Instantly fetches logistical data for any given order, intelligently detecting delivery delays.
2. **Product Recommendations**: Smartly matches English keyword queries to the native Portuguese datasets, surfacing top-selling items.
3. **Sentiment Analysis**: Automatically detects frustrated customers using NLP and adjusts the bot's empathetic tone.
4. **Actionable Insights**: Generates live operational intelligence (e.g. tracking delayed delivery percentages, identifying problematic product categories).

## 📋 How This Project Matches the Proposal
- **Lightweight Explainable AI**: We used lightweight NLP intent classification heuristics instead of heavy fine-tuned LLMs due to time and deployment constraints, keeping the system local and fast.
- **Real E-Commerce Integration**: The system abandons mock data and successfully integrates real Olist e-commerce datasets for order tracking, product recommendations, reviews, and dynamic analytics.
- **Contextual Responses**: LLM-based generative responses are simulated through a modular context engine that perfectly formats intents, sentiments, and knowledge base lookups.
- **Prototype Features**: The critical requirements of Human Escalation tracking and Multilingual Support (Portuguese detection) are fully implemented as prototype features for demonstration.

## 📊 Dataset Overview
Powered by the [Olist Brazilian E-Commerce Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), featuring over 100k real, anonymized orders, reviews, and product interactions.

## 🧠 AI/ML Concepts Used
- **Natural Language Processing (NLP)**: Uses `TextBlob` for polarity-based sentiment analysis on unstructured text.
- **Search & Recommendation Heuristics**: Set intersection over keyword clusters mapped to historical sales distributions.
- **Data Engineering**: Dynamic in-memory pandas aggregations of normalized schemas (Stars Schema).

## 🏗 System Architecture
- `app.py`: Streamlit-based web interface and routing controller. Features Tabs, Metrics, and Caching.
- `intent_classifier.py`: Categorizes query intent with confidence scoring.
- `response_generator.py`: Combines sentiment tone, dataset lookups, and escalation flags into final contextual responses.
- `knowledge_base.py`: Handles FAQ resolutions.
- `chatbot.py`: Regex-powered order intent extraction and status tracking logic.
- `recommender.py`: Category translation mapper and historical top-seller generator.
- `sentiment.py`: Hybrid sentiment engine (Numerical reviews + NLP text polarity).
- `database.py`: SQLite logging pipeline with CSV export and safe migration capability.

## ✨ Features
- **Modern UI**: Clean Streamlit UI with tabs, metrics, and sidebar widgets.
- **Analytics Dashboard**: Matplotlib visualizations of order flows and product performance.
- **Support Insights**: Calculated metrics showing problematic categories and delay impacts.
- **Export Utility**: One-click CSV export of chat logs.

## 🚀 Installation & Running Locally
1. Clone the repository and navigate to the project directory:
   ```bash
   cd ecommerce_ai_support
   ```
2. Install the required lightweight dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the Streamlit application:
   ```bash
   streamlit run app.py
   ```

## 🗣️ Example Queries to Try
- `Where is order e481f51cbdc54678b7cc49136f2d6af7?`
- `Can you recommend some beauty products?`
- `What payment methods are available?`
- `I am very unhappy with my delivery.`
- `Can I speak to a human agent?`
- `Quanto tempo demora a entrega?`
