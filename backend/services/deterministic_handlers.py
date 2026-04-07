"""
Deterministic Handlers — pure pandas logic, no LLM required.

Each handler returns the standard response shape:
  { "answer": str, "chart_config": dict|None, "follow_ups": list, "data_table": list|None }
"""
# summary handler, columns handler, stats handler
import pandas as pd
from services.data_service import get_safe_categorical, get_safe_numeric

# ── Shared color palette ───────────────────────────────────────────
COLOR_PALETTE = [
    "rgba(6, 182, 212, 0.8)",    # cyan
    "rgba(139, 92, 246, 0.8)",   # violet
    "rgba(244, 114, 182, 0.8)",  # pink
    "rgba(34, 197, 94, 0.8)",    # green
    "rgba(251, 191, 36, 0.8)",   # amber
    "rgba(239, 68, 68, 0.8)",    # red
]


def _make_response(answer, chart_config=None, follow_ups=None, data_table=None, df=None):
    follow_ups = follow_ups or []
    
    # Filter vague follow_ups
    follow_ups = [f for f in follow_ups if f not in ("What else?", "Give me a summary", "Show me a chart of this", "Show me a chart")]
    
    # Contextual Chart Suggestions Ensure Reality
    if df is not None:
        num_cols = get_safe_numeric(df)
        cat_cols = get_safe_categorical(df)
        if num_cols and cat_cols:
            n1 = num_cols[0]
            c1 = cat_cols[0]
            sugs = [f"Show {n1} by {c1}", f"Total {n1}", f"Best performing {c1} by {n1}"]
            
            for s in sugs[:3]:
                if s not in follow_ups:
                    follow_ups.append(s)

    return {
        "answer": answer,
        "chart_config": None,  # BLIND CHART GENERATION DISABLED
        "follow_ups": follow_ups,
        "data_table": data_table,
    }


# ── SUMMARY handler ───────────────────────────────────────────────

def handle_summary(df: pd.DataFrame, dataset_info: dict) -> dict:
    """Generate a full dataset summary using only pandas."""
    num_cols = get_safe_numeric(df)
    cat_cols = get_safe_categorical(df)
    date_cols = df.select_dtypes(include=["datetime"]).columns.tolist()

    total_nulls = int(df.isnull().sum().sum())
    null_pct = (total_nulls / (len(df) * len(df.columns))) * 100 if len(df) > 0 else 0

    lines = [
        f"📊 **Dataset Summary: {dataset_info.get('filename', 'data')}**",
        f"",
        f"• **Rows:** {len(df):,}  |  **Columns:** {len(df.columns)}",
        f"• **Numeric columns ({len(num_cols)}):** {', '.join(num_cols[:6])}" + (" ..." if len(num_cols) > 6 else ""),
        f"• **Categorical columns ({len(cat_cols)}):** {', '.join(cat_cols[:6])}" + (" ..." if len(cat_cols) > 6 else ""),
    ]

    if date_cols:
        lines.append(f"• **Date columns ({len(date_cols)}):** {', '.join(date_cols)}")

    lines.append(f"• **Missing values:** {total_nulls:,} ({null_pct:.1f}%)")

    # Numeric highlights
    if num_cols:
        lines.append(f"\n**Numeric Highlights:**")
        for col in num_cols[:4]:
            lines.append(
                f"  - {col}: min={df[col].min():.2f}, max={df[col].max():.2f}, "
                f"avg={df[col].mean():.2f}, std={df[col].std():.2f}"
            )

    # Top categories
    if cat_cols:
        lines.append(f"\n**Top Categories:**")
        for col in cat_cols[:2]:
            top3 = df[col].value_counts().head(3)
            items = ", ".join(f"{k} ({v})" for k, v in top3.items())
            lines.append(f"  - {col}: {items}")

    answer = "\n".join(lines)

    # Build a summary chart — column type distribution
    type_counts = {"Numeric": len(num_cols), "Categorical": len(cat_cols), "Date": len(date_cols)}
    type_counts = {k: v for k, v in type_counts.items() if v > 0}

    chart_config = None
    if num_cols and cat_cols:
        # Show top category value counts as a bar chart
        top_col = cat_cols[0]
        vc = df[top_col].value_counts().head(8)
        chart_config = {
            "chart_type": "bar",
            "labels": vc.index.tolist(),
            "datasets": [{
                "label": f"Count by {top_col}",
                "data": vc.values.tolist(),
                "backgroundColor": COLOR_PALETTE[0],
                "borderColor": COLOR_PALETTE[0].replace("0.8", "1"),
                "borderWidth": 2,
            }],
            "title": f"Distribution of {top_col}",
        }

    # Data preview table
    data_table = df.head(5).fillna("").to_dict(orient="records")

    return _make_response(
        answer=answer,
        chart_config=chart_config,
        follow_ups=[
            f"What are the top 5 values in {num_cols[0]}?" if num_cols else "What patterns do you see?",
            f"Show me a chart of {cat_cols[0]}" if cat_cols else "What columns are available?",
            "Are there any outliers in the data?",
        ],
        data_table=data_table,
    )


# ── COLUMNS handler ───────────────────────────────────────────────

def handle_columns(df: pd.DataFrame, dataset_info: dict) -> dict:
    """List all columns with types, uniqueness, and sample values."""
    lines = [f"📋 **Columns in {dataset_info.get('filename', 'dataset')}** ({len(df.columns)} total):\n"]

    table_rows = []
    for col_info in dataset_info.get("columns_info", []):
        name = col_info["name"]
        dtype = col_info["dtype"]
        uniq = col_info["unique_count"]
        nulls = col_info["null_count"]
        samples = col_info.get("sample_values", [])[:3]

        type_icon = "🔢" if "int" in dtype or "float" in dtype else "📝" if "object" in dtype else "📅"
        lines.append(f"{type_icon} **{name}** — {dtype}, {uniq} unique, {nulls} nulls")
        if samples:
            lines.append(f"   _samples: {', '.join(str(s) for s in samples)}_")

        table_rows.append({
            "Column": name,
            "Type": dtype,
            "Unique": uniq,
            "Nulls": nulls,
            "Sample": ", ".join(str(s) for s in samples),
        })

    return _make_response(
        answer="\n".join(lines),
        follow_ups=[
            "Give me a summary of this dataset",
            f"Show me the distribution of {dataset_info['columns_info'][0]['name']}" if dataset_info.get("columns_info") else "Describe the data",
            "What are the key insights?",
        ],
        data_table=table_rows,
    )


# ── CHART handler ─────────────────────────────────────────────────

def handle_chart(df: pd.DataFrame, question: str, entities: dict, column_mentions: list[str]) -> dict:
    """Build a chart deterministically from the question and data."""
    num_cols = get_safe_numeric(df)
    cat_cols = get_safe_categorical(df)
    chart_type = entities.get("chart_type") or "bar"

    # Try to figure out what to plot from column mentions
    mentioned_num = [c for c in column_mentions if c in num_cols]
    mentioned_cat = [c for c in column_mentions if c in cat_cols]

    label_col = None
    value_col = None

    # Strategy: pick the best label (categorical) and value (numeric) columns
    if mentioned_cat and mentioned_num:
        label_col = mentioned_cat[0]
        value_col = mentioned_num[0]
    elif mentioned_cat and num_cols:
        label_col = mentioned_cat[0]
        value_col = num_cols[0]
    elif mentioned_num and cat_cols:
        label_col = cat_cols[0]
        value_col = mentioned_num[0]
    elif cat_cols and num_cols:
        label_col = cat_cols[0]
        value_col = num_cols[0]
    elif num_cols:
        # No categorical — show distribution of first numeric col
        value_col = num_cols[0]

    if not value_col:
        return _make_response(
            answer="I couldn't determine what to chart. Please specify a column name, e.g., 'Show me a chart of Sales by Region'.",
            follow_ups=["What columns are available?", "Give me a summary"],
            df=df,
        )

    # Build chart data
    if label_col:
        agg = df.groupby(label_col)[value_col].sum().sort_values(ascending=False).head(12)
        labels = agg.index.astype(str).tolist()
        data = agg.values.tolist()
        title = f"Total {value_col} Across {label_col}"
        answer = f"Here's a **{chart_type} chart** of **{value_col}** grouped by **{label_col}**."

        # For few categories, use pie/doughnut
        if len(labels) <= 6 and chart_type == "bar":
            chart_type = "doughnut"

        bg_colors = COLOR_PALETTE[:len(labels)] if chart_type in ("pie", "doughnut") else COLOR_PALETTE[0]

        chart_config = {
            "chart_type": chart_type,
            "labels": labels,
            "datasets": [{
                "label": value_col,
                "data": data,
                "backgroundColor": bg_colors,
                "borderColor": COLOR_PALETTE[0].replace("0.8", "1") if isinstance(bg_colors, str) else [c.replace("0.8", "1") for c in bg_colors],
                "borderWidth": 2,
            }],
            "title": title,
        }

        table_data = [{"label": l, value_col: round(v, 2)} for l, v in zip(labels, data)]
    else:
        # Histogram-style: show value distribution
        labels = [f"Row {i+1}" for i in range(min(20, len(df)))]
        data = df[value_col].head(20).fillna(0).tolist()
        title = f"Distribution of Transactions by {value_col}"
        answer = f"Here's the distribution of **{value_col}** (first 20 values)."

        chart_config = {
            "chart_type": "bar",
            "labels": labels,
            "datasets": [{
                "label": value_col,
                "data": data,
                "backgroundColor": COLOR_PALETTE[0],
                "borderColor": COLOR_PALETTE[0].replace("0.8", "1"),
                "borderWidth": 2,
            }],
            "title": title,
        }
        table_data = None

    follow_ups = []
    if label_col and len(num_cols) > 1:
        other_num = [c for c in num_cols if c != value_col][:2]
        follow_ups = [f"Show me {c} by {label_col}" for c in other_num]
    follow_ups.append("Give me a summary of this dataset")

    return _make_response(
        answer=answer,
        chart_config=chart_config,
        follow_ups=["Show me a chart of this", "Give me a summary", "What else?"],
        data_table=table_data,
        df=df,
    )


# ── INSIGHT handler (deterministic portion) ────────────────────────

def handle_insight_query(df: pd.DataFrame) -> dict:
    """Provide advanced insights using pandas logic."""
    num_cols = get_safe_numeric(df)
    cat_cols = get_safe_categorical(df)

    lines = ["🔍 **Key Findings:**\n"]

    # 1. Highest-variance numeric column
    if num_cols:
        cv_scores = {}
        for col in num_cols:
            mean = df[col].mean()
            if mean != 0:
                cv_scores[col] = abs(df[col].std() / mean)
        if cv_scores:
            most_varied = max(cv_scores, key=cv_scores.get)
            lines.append(f"📈 **Most variable column:** {most_varied} (coefficient of variation: {cv_scores[most_varied]:.2f})")

    # 2. Null hotspots
    null_counts = df.isnull().sum()
    high_null = null_counts[null_counts > 0].sort_values(ascending=False)
    if len(high_null) > 0:
        top_null = high_null.head(3)
        items = ", ".join(f"{col} ({cnt} nulls)" for col, cnt in top_null.items())
        lines.append(f"⚠️ **Missing data:** {items}")

    # 3. Correlations
    if len(num_cols) >= 2:
        corr = df[num_cols].corr()
        pairs = []
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                val = corr.iloc[i, j]
                if abs(val) > 0.6:
                    direction = "positive" if val > 0 else "negative"
                    pairs.append((corr.columns[i], corr.columns[j], val, direction))
        if pairs:
            pairs.sort(key=lambda x: abs(x[2]), reverse=True)
            for c1, c2, val, direction in pairs[:3]:
                lines.append(f"🔗 **Strong {direction} correlation:** {c1} ↔ {c2} ({val:.2f})")

    # 4. Top category by numeric total (Revenue vs Profit comparison)
    if cat_cols and num_cols:
        cc = cat_cols[0]
        from services.data_service import get_primary_metric_cols
        sales_col, profit_col = get_primary_metric_cols(df)
        
        nc = sales_col or num_cols[0]
        agg_rev = df.groupby(cc)[nc].sum().sort_values(ascending=False)
        
        if len(agg_rev) > 0:
            top_rev_cat = agg_rev.index[0]
            lines.append(f"🏆 **Top {cc} by {nc}:** {top_rev_cat} ({agg_rev.iloc[0]:,.2f})")
            
            if profit_col and profit_col != nc:
                agg_prof = df.groupby(cc)[profit_col].sum().sort_values(ascending=False)
                if len(agg_prof) > 0:
                    top_prof_cat = agg_prof.index[0]
                    if top_rev_cat != top_prof_cat:
                        lines.append(f"💡 **Key Insight:** **{top_rev_cat}** generates the highest {nc}, while **{top_prof_cat}** delivers the highest {profit_col}.")
                    else:
                        lines.append(f"💡 **Key Insight:** **{top_rev_cat}** dominates across both {nc} and {profit_col}.")

    answer = "\n".join(lines) if len(lines) > 1 else "No notable patterns found in the data."

    # Build a chart for the most impactful finding
    chart_config = None
    if cat_cols and num_cols:
        cc, nc = cat_cols[0], num_cols[0]
        agg = df.groupby(cc)[nc].sum().sort_values(ascending=False).head(8)
        chart_config = {
            "chart_type": "bar",
            "labels": agg.index.tolist(),
            "datasets": [{
                "label": f"Total {nc}",
                "data": agg.values.tolist(),
                "backgroundColor": COLOR_PALETTE[0],
                "borderColor": COLOR_PALETTE[0].replace("0.8", "1"),
                "borderWidth": 2,
            }],
            "title": f"{nc} by {cc}",
        }

    return _make_response(
        answer=answer,
        chart_config=chart_config,
        follow_ups=[
            "Show me a chart",
            "What are the top categories?",
            "Any interesting insights?"
        ],
        df=df,
    )


# ── INTERACTIVE CHART BUILDER ─────────────────────────────────────

def build_interactive_chart(df: pd.DataFrame, x_axis: str, y_axis: str, agg_func: str, chart_type: str) -> dict:
    """Build a completely deterministic chart from explicit user parameters."""
    if x_axis not in df.columns or y_axis not in df.columns:
        return {}

    # Aggregation
    if agg_func == "sum":
        agg = df.groupby(x_axis)[y_axis].sum().sort_values(ascending=False).head(15)
    elif agg_func == "average":
        agg = df.groupby(x_axis)[y_axis].mean().sort_values(ascending=False).head(15)
    elif agg_func == "count":
        agg = df.groupby(x_axis)[y_axis].count().sort_values(ascending=False).head(15)
    else:
        agg = df.groupby(x_axis)[y_axis].sum().sort_values(ascending=False).head(15)

    labels = agg.index.astype(str).tolist()
    data = agg.values.tolist()
    title = f"{agg_func.capitalize()} of {y_axis} by {x_axis}"

    bg_colors = COLOR_PALETTE[:len(labels)] if chart_type in ("pie", "doughnut") else COLOR_PALETTE[0]

    return {
        "chart_type": chart_type,
        "labels": labels,
        "datasets": [{
            "label": y_axis,
            "data": [round(x, 2) for x in data],
            "backgroundColor": bg_colors,
            "borderColor": COLOR_PALETTE[0].replace("0.8", "1") if isinstance(bg_colors, str) else [c.replace("0.8", "1") for c in bg_colors],
            "borderWidth": 2,
        }],
        "title": title,
    }


# ── CATEGORY ANALYSIS handler ─────────────────────────────────────

def handle_category_analysis(df: pd.DataFrame, question: str, column_mentions: list[str]) -> dict:
    """Handle queries asking 'which category is best' etc."""
    num_cols = get_safe_numeric(df)
    cat_cols = get_safe_categorical(df)

    if not cat_cols:
        return _make_response(
            answer="No categorical columns found in the dataset to analyze.",
            follow_ups=["Give me a summary", "What columns are available?"],
            df=df,
        )

    if not num_cols:
        return _make_response(
            answer="No numeric columns found to measure category performance.",
            follow_ups=["Give me a summary", "What columns are available?"],
        )

    # Pick which numeric column to measure by
    mentioned_num = [c for c in column_mentions if c in num_cols]
    mentioned_cat = [c for c in column_mentions if c in cat_cols]

    # Detect if user wants profit, sales, etc.
    if any(w in q_lower for w in ["profit", "margin", "gain"]):
        value_col = next((c for c in num_cols if "profit" in c.lower() or "margin" in c.lower()), mentioned_num[0] if mentioned_num else num_cols[0])
    elif any(w in q_lower for w in ["sales", "revenue", "amount", "income"]):
        value_col = next((c for c in num_cols if any(w in c.lower() for w in ["sale", "revenue", "amount", "income"])), mentioned_num[0] if mentioned_num else num_cols[0])
    else:
        value_col = mentioned_num[0] if mentioned_num else num_cols[0]

    group_col = mentioned_cat[0] if mentioned_cat else cat_cols[0]

    # Compute aggregations
    agg = df.groupby(group_col)[value_col].agg(["sum", "mean", "count"]).reset_index()
    agg.columns = [group_col, "Total", "Average", "Count"]
    agg = agg.sort_values("Total", ascending=False)

    best = agg.iloc[0]
    worst = agg.iloc[-1]
    grand_total = agg["Total"].sum()

    # Determine if user asked about best or worst
    is_worst = bool(re.search(r'\b(worst|least|lowest|bottom|weakest|poorest)\b', q_lower))

    focus = worst if is_worst else best
    focus_label = "Worst" if is_worst else "Best"

    # Build human-readable answer
    share_pct = (focus["Total"] / grand_total * 100) if grand_total > 0 else 0
    performance = "underperforming" if is_worst else "strong performance"

    lines = [
        f"## 🏆 {focus_label} Performing {group_col}: **{focus[group_col]}**\n",
        f"**{focus[group_col]}** has a total {value_col} of **{focus['Total']:,.2f}**, "
        f"accounting for **{share_pct:.1f}%** of all {value_col} — indicating {performance}.\n",
        f"### Category Breakdown\n",
    ]

    for _, row in agg.iterrows():
        row_share = (row["Total"] / grand_total * 100) if grand_total > 0 else 0
        bar = "█" * max(1, int(row_share / 5))
        marker = " ← best" if row[group_col] == best[group_col] and not is_worst else ""
        marker = " ← worst" if row[group_col] == worst[group_col] and is_worst else marker
        lines.append(
            f"- **{row[group_col]}**: {row['Total']:,.2f} ({row_share:.1f}%) {bar}{marker}"
        )

    lines.append(f"\n> **Key takeaway:** {best[group_col]} leads with {(best['Total'] / grand_total * 100):.0f}% market share, "
                  f"while {worst[group_col]} trails at {(worst['Total'] / grand_total * 100):.0f}%.")

    answer = "\n".join(lines)

    # Chart
    chart_agg = agg.head(10)
    chart_config = {
        "chart_type": "bar",
        "labels": chart_agg[group_col].tolist(),
        "datasets": [{
            "label": f"Total {value_col}",
            "data": [round(x, 2) for x in chart_agg["Total"].tolist()],
            "backgroundColor": COLOR_PALETTE[0],
            "borderColor": COLOR_PALETTE[0].replace("0.8", "1"),
            "borderWidth": 2,
        }],
        "title": f"Performance of {value_col} Across {group_col}",
    }

    # Data table
    data_table = [
        {group_col: row[group_col], f"Total {value_col}": round(row["Total"], 2),
         f"Avg {value_col}": round(row["Average"], 2), "Count": int(row["Count"]),
         "Share %": f"{(row['Total'] / grand_total * 100):.1f}%"}
        for _, row in agg.iterrows()
    ]

    other_metric = "Profit" if value_col != "Profit" and "Profit" in num_cols else (num_cols[1] if len(num_cols) > 1 else num_cols[0])

    return _make_response(
        answer=answer,
        chart_config=chart_config,
        follow_ups=[
            f"{'Best' if is_worst else 'Worst'} category by {value_col}",
            f"Compare categories by {other_metric}",
            f"Top 5 by {value_col}",
        ],
        data_table=data_table,
    )

