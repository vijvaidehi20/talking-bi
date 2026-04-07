import pandas as pd
from services.data_service import get_primary_metric_cols, get_safe_categorical

def get_smart_follow_ups(df: pd.DataFrame, q_lower: str, intent: str = None) -> list[str]:
    """
    Generate 3-4 relevant analytical follow-up suggestions based on user query intent.
    
    Rules:
    - revenue intent (mentions revenue/sales)
    - ranking intent (mentions top/highest/best)
    - fallback to context-aware defaults
    """
    suggestions = []
    
    # 1. Identify key columns
    sales_col, profit_col = get_primary_metric_cols(df)
    cat_cols = get_safe_categorical(df)
    main_cat = cat_cols[0] if cat_cols else "Category"
    
    # 2. Check for "Revenue" intent
    if any(w in q_lower for w in ["revenue", "sales", "amount"]):
        suggestions = [
            f"Show {sales_col or 'revenue'} by {main_cat}",
            f"Top 5 categories by {sales_col or 'revenue'}",
            f"{profit_col or 'Profit'} by {main_cat}",
            "Show loss-making orders"
        ]
    
    # 3. Check for "Ranking" intent
    elif any(w in q_lower for w in ["top", "highest", "best", "most"]):
        suggestions = [
            f"Bottom 5 categories by {sales_col or 'revenue'}",
            f"{sales_col or 'Revenue'} by {main_cat}",
            "Show profit analysis",
            "Give me a summary"
        ]
    
    # 4. Fallback Suggestions
    if not suggestions:
        if sales_col and main_cat:
            suggestions.append(f"Show {sales_col} by {main_cat}")
        if profit_col:
            suggestions.append("Show loss-making orders")
        suggestions.extend(["Give me a summary", "What are the key insights?"])

    # Remove generic filler and ensure exactly 4 unique suggestions (max)
    generic_to_remove = ["What else?", "irrelevant options"]
    final_suggestions = []
    for s in suggestions:
        if s not in final_suggestions and s not in generic_to_remove:
            final_suggestions.append(s)
            
    return final_suggestions[:4]
