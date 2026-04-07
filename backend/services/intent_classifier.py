"""
Intent Classifier — keyword-based routing for user queries.

Classifies questions into 5 intents WITHOUT using the LLM:
  summary    → dataset overview, describe, summarize
  columns    → column listing, schema, fields
  chart      → visualization requests (bar, pie, plot, graph)
  insight    → patterns, trends, anomalies, interesting findings
  analytical → everything else (falls through to LLM)
"""

import re

# ── Keyword patterns per intent ────────────────────────────────────
# Order matters: more specific patterns first to avoid false matches

_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("summary", [
        r"\bsummar",          # summary, summarize, summarise
        r"\boverview\b",
        r"\bdescribe\b",
        r"\bdescription\b",
        r"\btell me about\b",
        r"\bwhat is this data\b",
        r"\bdata\s*set\s*info",
        r"\bhow many rows\b",
        r"\bshape\b",
        r"\bhead\b",
        r"\bpreview\b",
        r"\bfirst\s+\d+\s+rows\b",
    ]),
    ("columns", [
        r"\bcolumns?\b",
        r"\bfields?\b",
        r"\bschema\b",
        r"\bwhat data\b",
        r"\bdata types?\b",
        r"\bvariables?\b",
        r"\battributes?\b",
        r"\blist.*(column|field)",
        r"\bwhat.*available\b",
    ]),
    ("chart", [
        r"\bchart\b",
        r"\bplot\b",
        r"\bgraph\b",
        r"\bvisuali[sz]",
        r"\bbar\s*(chart|graph)?\b",
        r"\bpie\s*(chart|graph)?\b",
        r"\bline\s*(chart|graph)?\b",
        r"\bhistogram\b",
        r"\bscatter\b",
        r"\bdoughnut\b",
        r"\bshow\s+me\b",
        r"\bdraw\b",
        r"\bdisplay\b",
    ]),
    ("insight", [
        r"\binsight",
        r"\binteresting\b",
        r"\bpattern",
        r"\btrend",
        r"\banomali",
        r"\boutlier",
        r"\bnotable\b",
        r"\bkey\s*(finding|takeaway)",
        r"\bstand\s*out\b",
        r"\bhighlight",
    ]),
    ("category_analysis", [
        r"\bbest\s+category\b",
        r"\bworst\s+category\b",
        r"\btop\s+categor",
        r"\bbottom\s+categor",
        r"\bwhich\s+category\b",
        r"\bcategory\s+perform",
        r"\bperform.*category\b",
        r"\bmost\s+profitable\b",
        r"\bleast\s+profitable\b",
        r"\bbest\s+performing\b",
        r"\bworst\s+performing\b",
        r"\bhighest\s+profit\b",
        r"\blowest\s+profit\b",
        r"\bbest\b.*\bby\s+(profit|sales|revenue|amount)\b",
        r"\bworst\b.*\bby\s+(profit|sales|revenue|amount)\b",
        r"\bcategory\s+breakdown\b",
        r"\bcompare\s+categor",
        r"\bcategory\s+comparison\b",
    ]),
    ("aggregation", [
        r"\btop\s+\d+",
        r"\bhighest\b",
        r"\blowest\b",
        r"\bmost\b",
        r"\bleast\b",
        r"\blargest\b",
        r"\bsmallest\b",
        r"\bbiggest\b",
        r"\bmaximum\b",
        r"\bminimum\b",
        r"\bmax\b",
        r"\bmin\b",
        r"\baverage\b",
        r"\bmean\b",
        r"\btotal\b",
        r"\bsum\b",
        r"\bhow\s+many\b",
        r"\bcount\b",
        r"\bloss-making\b",
        r"\blosses\b",
        r"\bprofitable\b",
        r"\bprofits\b",
        r"\bgroup\s*by\b",
        r"\brank\b",
        r"\bsort\b",
        r"\border\s*by\b",
        r"\bbottom\s+\d+",
        r"\bcompare\b",
    ]),
]


def classify_intent(question: str) -> dict:
    """
    Classify a user question into an intent + extracted entities.

    Returns:
        {
            "intent": "summary" | "columns" | "chart" | "insight" | "analytical",
            "entities": {
                "columns_mentioned": [...],   # column names found in the query
                "chart_type": "bar"|"pie"|... # if explicitly requested
            }
        }
    """
    q_lower = question.lower().strip()

    # 1. Match intent by keyword patterns
    intent = "analytical"  # default fallback
    for candidate_intent, patterns in _INTENT_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, q_lower):
                intent = candidate_intent
                break
        if intent != "analytical":
            break

    # 2. Extract entities
    entities = {
        "columns_mentioned": [],
        "chart_type": None,
    }

    # Detect chart type if mentioned
    chart_type_map = {
        r"\bbar\b": "bar",
        r"\bline\b": "line",
        r"\bpie\b": "pie",
        r"\bdoughnut\b": "doughnut",
        r"\bscatter\b": "scatter",
        r"\bhistogram\b": "bar",
    }
    for pattern, ctype in chart_type_map.items():
        if re.search(pattern, q_lower):
            entities["chart_type"] = ctype
            break

    return {"intent": intent, "entities": entities}


# ── Strict semantic synonyms for column matching ─────────
# Maps business terms to exact column target names.

TERM_MAPPING = {
    "revenue": "Amount",
    "sales": "Amount",
    "profit": "Profit",
    "quantity": "Quantity",
}

def extract_column_mentions(question: str, column_names: list[str]) -> list[str]:
    """
    Find which dataset columns are mentioned in the question.
    
    Strategy (in priority order):
      1. Strict mapping of business terms to target columns (e.g. sales -> Amount)
      2. Exact substring match (case-insensitive)
      3. Partial/fuzzy match ("cat" → finds "Category" column)
    """
    q_lower = question.lower()
    found = []

    # 1. Strict mapping
    for term, mapped_col in TERM_MAPPING.items():
        if re.search(rf'\b{term}\b', q_lower):
            for col in column_names:
                if mapped_col.lower() == col.lower() and col not in found:
                    found.append(col)

    # 2. Exact substring match — sort by length (longest first)
    for col in sorted(column_names, key=len, reverse=True):
        if col.lower() in q_lower and col not in found:
            found.append(col)

    if found:
        return found

    # 3. Partial match: check if any word in the question is a substring of a column name
    words = re.findall(r'\b[a-zA-Z]{3,}\b', q_lower)
    for word in words:
        if len(word) >= 4:  # only words 4+ chars
            for col in column_names:
                if word in col.lower() and col not in found:
                    found.append(col)

    return found
