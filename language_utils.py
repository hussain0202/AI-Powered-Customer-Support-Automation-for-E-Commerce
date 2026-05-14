def detect_language_simple(text: str) -> str:
    """
    Simulates multilingual support detection without requiring external APIs.
    Checks for common Portuguese keywords relevant to the Olist dataset.
    """
    query = text.lower()
    
    portuguese_keywords = [
        "quanto", "tempo", "demora", "entrega", "onde", "está", "pedido", 
        "obrigado", "bom", "dia", "boa", "tarde", "noite", "cancelar", 
        "reembolso", "produto"
    ]
    
    # If any portuguese keywords are isolated in the text
    if any(word in query.split() for word in portuguese_keywords):
        return "Portuguese"
        
    return "English"
