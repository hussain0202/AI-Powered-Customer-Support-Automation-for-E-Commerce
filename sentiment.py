from textblob import TextBlob
import math

def get_sentiment_label(score):
    """Maps a 1-5 numerical score to a sentiment label."""
    if score in [1, 2]:
        return "Negative"
    elif score == 3:
        return "Neutral"
    elif score in [4, 5]:
        return "Positive"
    return "Unknown"

def generate_support_response(sentiment):
    """Generates an empathetic response based on the sentiment label."""
    if sentiment == "Negative":
        return "We're truly sorry to hear that you are unhappy. We are committed to making things right."
    elif sentiment == "Positive":
        return "Thank you for the wonderful feedback! We're thrilled you had a great experience."
    else:
        return "Thank you for reaching out. How else can we assist you today?"

def analyze_sentiment(review_text, review_score=None):
    """
    Hybrid sentiment analyzer using TextBlob and optional numerical score.
    Returns sentiment_label, polarity_score, and a tone_message.
    """
    sentiment_label = "Neutral"
    polarity = 0.0
    
    # 1. Text-based sentiment using TextBlob
    if review_text and isinstance(review_text, str):
        blob = TextBlob(review_text)
        polarity = blob.sentiment.polarity
        
        if polarity > 0.1:
            sentiment_label = "Positive"
        elif polarity < -0.1:
            sentiment_label = "Negative"
        else:
            sentiment_label = "Neutral"
            
    # 2. Score-based fallback
    if review_score is not None and not math.isnan(review_score):
        score_label = get_sentiment_label(int(review_score))
        
        # If the text sentiment was Neutral (weak polarity), we trust the explicit score more
        if -0.2 <= polarity <= 0.2:
            sentiment_label = score_label

    # 3. Generate empathetic tone message
    tone_message = generate_support_response(sentiment_label)
    
    return sentiment_label, polarity, tone_message
