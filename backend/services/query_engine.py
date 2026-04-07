"""
Query Engine — intent-first pipeline with structured responses.

Flow:
  User Question → classify_intent() → Route:
    ├── summary     → handle_summary()          [deterministic, no LLM]
    ├── columns     → handle_columns()           [deterministic, no LLM]
    ├── chart       → handle_chart()             [deterministic, no LLM]
    ├── insight     → handle_insight_query()      [deterministic, no LLM]
    ├── aggregation → handle_aggregation()        [deterministic, no LLM]
    └── analytical  → LLM query engine           [LLM, with fallback]
"""

import re
import pandas as pd
import traceback
from services.data_service import get_dataframe, get_data_summary, get_dataset
from services.llm_service import call_llm_json, QUERY_SYSTEM, is_llm_available
from services.intent_classifier import classify_intent, extract_column_mentions
from services.deterministic_handlers import (
    handle_summary, handle_columns, handle_chart, handle_insight_query,
    handle_category_analysis,
)
from services.suggestion_service import get_smart_follow_ups


def execute_query(dataset_id: str, question: str, conversation_history: list[dict] = None) -> dict:
    """Process a natural language question against the dataset."""
    df = get_dataframe(dataset_id)
    if df is None:
        return _error("Dataset not found. Please upload a file first.")

    ds = get_dataset(dataset_id)

    # ── Step 1: Classify intent ──────────────────────────────────
    classification = classify_intent(question)
    intent = classification["intent"]
    entities = classification["entities"]

    # Extract column mentions from the question
    column_names = [c["name"] for c in ds.get("columns_info", [])]
    column_mentions = extract_column_mentions(question, column_names)

    print(f"[QueryEngine] intent={intent}, columns_mentioned={column_mentions}, entities={entities}")

    # ── Step 2: Route to handler ─────────────────────────────────
    if intent == "summary":
        result = handle_summary(df, ds)
        result["response_type"] = "summary"
        result["title"] = "Dataset Summary"
    
    elif intent == "columns":
        result = handle_columns(df, ds)
        result["response_type"] = "summary"
        result["title"] = "Column Information"
    
    elif intent == "chart":
        result = handle_chart(df, question, entities, column_mentions)
        result["response_type"] = "chart"
        result["title"] = result.get("chart_config", {}).get("title", "Visualization") if result.get("chart_config") else "Visualization"
    
    elif intent == "insight":
        result = handle_insight_query(df)
        result["response_type"] = "insight"
        result["title"] = "Key Findings"
    
    elif intent == "category_analysis":
        result = handle_category_analysis(df, question, column_mentions)
        result["response_type"] = "analysis"
        result["title"] = result.get("_title", "Category Analysis")
    else:
        # Always try rule-based aggregation FIRST, even for "analytical" intent!
        result = _handle_aggregation(df, ds, question, column_mentions)
        
        # If rule-based processing fails entirely, then we fallback to LLM
        if result.get("response_type") == "fallback":
            result = _handle_analytical(df, ds, question, conversation_history)

    # Globally apply smart suggestions based on query intent
    result["follow_ups"] = get_smart_follow_ups(df, question.lower())
    return result


# ── Aggregation handler (rule-based, no LLM) ─────────────────────

def _handle_aggregation(df: pd.DataFrame, ds: dict, question: str, column_mentions: list[str]) -> dict:
    """Handle count/total/average/top/bottom queries directly using Pandas."""
    q_lower = question.lower()
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    mentioned_num = [c for c in column_mentions if c in num_cols]
    mentioned_cat = [c for c in column_mentions if c in cat_cols]

    # Explicit Direct Query Overrides
    if "most used payment mode" in q_lower or "frequent payment mode" in q_lower:
        pm_col = next((c for c in df.columns if "payment" in c.lower() and "mode" in c.lower()), "PaymentMode")
        if pm_col in df.columns:
            vc = df[pm_col].value_counts()
            return _make_response(
                answer=f"The most frequent **{pm_col}** is **{vc.index[0]}** with **{vc.iloc[0]:,}** occurrences.",
                response_type="analysis",
                title=f"Most Frequent {pm_col}",
                follow_ups=get_smart_follow_ups(df, q_lower)
            )

    # Detect metric context WITHOUT random column fallback
    value_col = None
    if "profit" in q_lower or "margin" in q_lower or "loss" in q_lower:
        value_col = next((c for c in num_cols if "profit" in c.lower()), mentioned_num[0] if mentioned_num else None)
    elif "revenue" in q_lower or "sales" in q_lower or "amount" in q_lower:
        value_col = next((c for c in num_cols if any(w in c.lower() for w in ["sale", "revenue", "amount"])), mentioned_num[0] if mentioned_num else None)
    elif "quantity" in q_lower or "qty" in q_lower:
        value_col = next((c for c in num_cols if "quantity" in c.lower() or "qty" in c.lower()), mentioned_num[0] if mentioned_num else None)
    else:
        value_col = mentioned_num[0] if mentioned_num else None

    # Fallback to defaults IF specific combinations are requested (e.g. "highest category", default to Amount)
    group_col = mentioned_cat[0] if mentioned_cat else None
    if group_col and not value_col and ("highest" in q_lower or "top" in q_lower or "best" in q_lower):
        value_col = next((c for c in num_cols if any(w in c.lower() for w in ["sale", "revenue", "amount"])), None)

    if not value_col:
        if group_col and any(w in q_lower for w in ["most", "frequent", "used"]):
            vc = df[group_col].value_counts()
            top_val = vc.index[0]
            top_count = vc.iloc[0]
            return _make_response(
                answer=f"The most frequent **{group_col}** is **{top_val}** with **{top_count:,}** occurrences.",
                response_type="analysis",
                title=f"Most Frequent {group_col}",
                follow_ups=get_smart_follow_ups(df, q_lower),
            )

        return _make_response(
            answer="I couldn't identify a valid measure (e.g., Amount, Profit, Quantity) to compute. Please explicitly name the column.",
            response_type="fallback",
            title="Measure Needed",
            follow_ups=get_smart_follow_ups(df, q_lower),
        )

    # 1. SCALAR CALCULATIONS (No Chart)
    # Loss-making / Profitable checks
    if "loss" in q_lower:
        loss_count = df[df[value_col] < 0].shape[0]
        return _make_response(
            answer=f"There are **{loss_count:,}** loss-making transactions in this dataset based on {value_col}.",
            response_type="analysis",
            title="Loss Analysis",
            follow_ups=get_smart_follow_ups(df, q_lower),
        )
    if "profitable" in q_lower:
        profit_count = df[df[value_col] > 0].shape[0]
        return _make_response(
            answer=f"There are **{profit_count:,}** profitable transactions in this dataset based on {value_col}.",
            response_type="analysis",
            title="Profitability Analysis",
            follow_ups=get_smart_follow_ups(df, q_lower),
        )

    # Detect operation
    operation = "sum"  # default fallback for short queries like "revenue?"
    if any(w in q_lower for w in ["avg", "average", "mean"]):
        operation = "mean"
    elif any(w in q_lower for w in ["top", "highest", "best", "max"]):
        operation = "top"
    elif any(w in q_lower for w in ["bottom", "lowest", "least", "worst", "min"]):
        operation = "bottom"
    elif any(w in q_lower for w in ["count", "how many"]):
        operation = "count"

    # Auto-grouping hierarchy for top/bottom ranking if no explicit group
    if operation in ("top", "bottom") and not group_col:
        for fallback in ["Category", "Sub-Category", "Region"]:
            actual_col = next((c for c in cat_cols if c.lower() == fallback.lower()), None)
            if actual_col:
                group_col = actual_col
                break

    if operation == "count":
        total_val = df.shape[0] if not group_col else len(df[group_col].dropna().unique())
        return _make_response(
            answer=f"The total count is **{total_val:,}**.",
            response_type="analysis",
            title="Count Analysis",
            follow_ups=get_smart_follow_ups(df, q_lower),
        )

    # Scalar vs Grouped Execution
    if operation in ("sum", "mean") and not group_col:
        stat_val = df[value_col].sum() if operation == "sum" else df[value_col].mean()
        action_name = "total" if operation == "sum" else "average"
        return _make_response(
            answer=f"The {action_name} {value_col} across the dataset is **{stat_val:,.2f}**.",
            response_type="analysis",
            title=f"{action_name.capitalize()} {value_col}",
            follow_ups=get_smart_follow_ups(df, q_lower),
        )

    # Grouped / Vector logic (top/bottom or grouped sum/mean)
    n_match = re.search(r'\b(?:top|bottom)\s+(\d+)', q_lower)
    n = int(n_match.group(1)) if n_match else 5
    is_bottom = (operation == "bottom")
    direction = "Lowest" if is_bottom else "Highest"

    color_palette = [
        "rgba(6, 182, 212, 0.8)", "rgba(139, 92, 246, 0.8)",
        "rgba(244, 114, 182, 0.8)", "rgba(34, 197, 94, 0.8)",
    ]

    if group_col:
        if operation == "mean":
            agg = df.groupby(group_col)[value_col].mean().sort_values(ascending=is_bottom).head(n)
            title = f"Average {value_col} by {group_col}"
        else: # top, bottom, sum -> all sum aggregated vectors
            agg = df.groupby(group_col)[value_col].sum().sort_values(ascending=is_bottom).head(n)
            title = f"{direction} {n} {group_col} by {value_col}" if operation in ("top", "bottom") else f"{value_col} by {group_col}"
            
        answer = f"📊 **{title}:**\n\n"
        for rank, (label, val) in enumerate(agg.items(), 1):
            answer += f"{rank}. **{label}**: {val:,.2f}\n"
    else:
        # Safety fallback if auto-grouping failed
        sorted_df = df.sort_values(by=value_col, ascending=is_bottom).head(n)
        label_col = ds.get("id_column") or (cat_cols[-1] if cat_cols else df.columns[0])
        title = f"{direction} {n} Items by {value_col}"
        
        answer = f"📊 **{title}:**\n\n"
        agg = pd.Series(dtype=float)
        for rank, (_, row) in enumerate(sorted_df.iterrows(), 1):
            label = str(row[label_col])
            val = row[value_col]
            answer += f"{rank}. **{label}**: {val:,.2f}\n"
            agg[label] = val

    chart_config = {
        "chart_type": "bar",
        "labels": [str(x) for x in agg.index.tolist()],
        "datasets": [{
            "label": value_col,
            "data": [round(x, 2) for x in agg.values.tolist()],
            "backgroundColor": color_palette[0],
            "borderColor": color_palette[0].replace("0.8", "1"),
            "borderWidth": 2,
        }],
        "title": title,
    }

    # Build data table
    data_table = [{"Rank": i + 1, "Entity": str(label), value_col: round(val, 2)}
                  for i, (label, val) in enumerate(agg.items())]

    return _make_response(
        answer=answer,
        response_type="analysis",
        title=title,
        chart_config=chart_config,
        data_table=data_table,
        follow_ups=[
            f"Show me {'top' if is_bottom else 'bottom'} {n} by {value_col}",
            "Give me a summary",
            "What else?"
        ],
    )


# ── Analytical (LLM) handler ─────────────────────────────────────

def _handle_analytical(df: pd.DataFrame, ds: dict, question: str, conversation_history: list[dict] = None) -> dict:
    """Handle complex analytical questions via LLM text-only (no code execution)."""

    if not is_llm_available():
        return _analytical_fallback(df, ds, question)

    data_summary = get_data_summary(ds["id"])

    # Build conversation context
    history_text = ""
    if conversation_history:
        history_lines = []
        for msg in conversation_history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_lines.append(f"{role}: {content}")
        history_text = "\n".join(history_lines)

    # Safe prompt — only asks for text answer, no code
    prompt = f"""Dataset Information:
{data_summary}

{f'Conversation history:{chr(10)}{history_text}{chr(10)}' if history_text else ''}
User question: {question}

IMPORTANT: Answer ONLY based on the data summary above. Do NOT fabricate or hallucinate any data values.
If the information is not available in the dataset, say "This information is not present in the dataset."
Provide a clear, concise answer in markdown format with follow-up suggestions.
Return JSON: {{"answer": "...", "follow_ups": ["q1", "q2", "q3"]}}
"""

    llm_result = call_llm_json(prompt, QUERY_SYSTEM)

    if not llm_result or not isinstance(llm_result, dict):
        return _analytical_fallback(df, ds, question)

    answer = llm_result.get("answer", "I analyzed the data but couldn't form a clear answer.")
    follow_ups = llm_result.get("follow_ups", [])

    return _make_response(
        answer=answer,
        response_type="analysis",
        title="Analysis Result",
        follow_ups=follow_ups[:3],
    )


def _analytical_fallback(df: pd.DataFrame, ds: dict, question: str) -> dict:
    """Fallback for analytical questions when LLM is unavailable."""
    column_names = [c["name"] for c in ds.get("columns_info", [])]
    mentions = extract_column_mentions(question, column_names)
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()

    mentioned_num = [c for c in mentions if c in num_cols]
    if mentioned_num:
        col = mentioned_num[0]
        stats = df[col].describe()
        answer = (
            f"Here's what I can tell you about **{col}** without the AI engine:\n\n"
            f"• **Total records:** {stats['count']:.0f}\n"
            f"• **Average:** {stats['mean']:,.2f}\n"
            f"• **Range:** {stats['min']:,.2f} → {stats['max']:,.2f}\n"
            f"• **Standard deviation:** {stats['std']:.2f}\n\n"
            f"For deeper analysis, configure your Gemini API key."
        )
        table = df[[col]].describe().reset_index().to_dict(orient="records")
        return _make_response(
            answer=answer,
            response_type="fallback",
            title=f"Quick Stats: {col}",
            follow_ups=[f"Show me a chart of {col}", f"Top 5 by {col}", "Give me a summary"],
            data_table=table,
        )

    # Generic fallback — actionable suggestion card
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    suggestions = [
        "📊 Give me a summary of this dataset",
        "📋 What columns are available?",
    ]
    if num_cols:
        suggestions.append(f"🏆 Show me top 5 by {num_cols[0]}")
    if num_cols and cat_cols:
        suggestions.append(f"📈 Show me {num_cols[0]} by {cat_cols[0]}")
    suggestions.append("🔍 What are the key insights?")

    return _make_response(
        answer=(
            "I can't answer that specific question without the AI engine, "
            "but here are some things I **can** help with right now:"
        ),
        response_type="fallback",
        title="Try These Instead",
        follow_ups=[s.split(" ", 1)[1] if " " in s else s for s in suggestions],
    )


# ── Helpers ───────────────────────────────────────────────────────

def _make_response(answer, response_type="analysis", title="", chart_config=None, follow_ups=None, data_table=None):
    return {
        "answer": answer,
        "response_type": response_type,
        "title": title,
        "chart_config": chart_config,
        "follow_ups": follow_ups or [],
        "data_table": data_table,
    }


def _error(msg: str) -> dict:
    return _make_response(msg, response_type="fallback", title="Error")


def _build_chart_config(result, chart_info: dict, df: pd.DataFrame) -> dict | None:
    """Convert LLM chart suggestion + query result into a Chart.js config."""
    try:
        chart_type = chart_info.get("type", "bar")
        title = chart_info.get("title", "")
        label_col = chart_info.get("label_column", "")
        value_cols = chart_info.get("value_columns", [])

        color_palette = [
            "rgba(6, 182, 212, 0.8)", "rgba(139, 92, 246, 0.8)",
            "rgba(244, 114, 182, 0.8)", "rgba(34, 197, 94, 0.8)",
            "rgba(251, 191, 36, 0.8)", "rgba(239, 68, 68, 0.8)",
        ]

        if isinstance(result, pd.Series):
            result_df = result.reset_index()
            result_df.columns = ["label", "value"] if len(result_df.columns) == 2 else result_df.columns
        elif isinstance(result, pd.DataFrame):
            result_df = result.copy()
        else:
            return None

        if len(result_df) == 0:
            return None

        result_df = result_df.head(15)

        if label_col and label_col in result_df.columns:
            labels = result_df[label_col].astype(str).tolist()
        elif "label" in result_df.columns:
            labels = result_df["label"].astype(str).tolist()
        else:
            labels = result_df.iloc[:, 0].astype(str).tolist()

        datasets = []
        numeric_cols = result_df.select_dtypes(include=["number"]).columns.tolist()

        if value_cols:
            for i, vc in enumerate(value_cols):
                if vc in result_df.columns:
                    datasets.append({
                        "label": vc,
                        "data": result_df[vc].fillna(0).tolist(),
                        "backgroundColor": color_palette[i % len(color_palette)],
                        "borderColor": color_palette[i % len(color_palette)].replace("0.8", "1"),
                        "borderWidth": 2,
                    })
        elif numeric_cols:
            for i, nc in enumerate(numeric_cols[:3]):
                datasets.append({
                    "label": nc,
                    "data": result_df[nc].fillna(0).tolist(),
                    "backgroundColor": color_palette[i % len(color_palette)],
                    "borderColor": color_palette[i % len(color_palette)].replace("0.8", "1"),
                    "borderWidth": 2,
                })

        if not datasets:
            return None

        if chart_type in ("pie", "doughnut") and datasets:
            datasets[0]["backgroundColor"] = color_palette[:len(labels)]

        return {
            "chart_type": chart_type, "labels": labels,
            "datasets": datasets, "title": title,
        }
    except Exception:
        return None
