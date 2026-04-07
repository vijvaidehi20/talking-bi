import pandas as pd
from services.data_service import get_dataframe, get_data_summary
from services.llm_service import call_llm_json, INSIGHT_SYSTEM, is_llm_available


def generate_insights(dataset_id: str) -> list[dict]:
    """Auto-generate ranked insights for a dataset."""
    df = get_dataframe(dataset_id)
    if df is None:
        return []

    data_summary = get_data_summary(dataset_id)

    # Also generate basic statistical insights directly
    stat_insights = _generate_stat_insights(df)

    # Use LLM for deeper insights (only if available)
    if not is_llm_available():
        return _fallback_insights(df)

    # Use LLM for deeper insights
    prompt = f"""Analyze this dataset and generate the most valuable insights:

{data_summary}

Additional statistics:
{stat_insights}

Generate 4-6 insights ranked by impact score.
"""

    llm_result = call_llm_json(prompt, INSIGHT_SYSTEM)

    if not llm_result or not isinstance(llm_result, list):
        # Fall back to stat-only insights
        return _fallback_insights(df)

    # Process and build chart configs
    insights = []
    for item in llm_result[:6]:
        chart_config = None
        chart_info = item.get("chart", {})

        if chart_info and chart_info.get("type", "none") != "none":
            chart_config = _build_insight_chart(df, chart_info)

        insights.append({
            "text": item.get("text", ""),
            "category": item.get("category", "summary"),
            "impact_score": min(1.0, max(0.0, float(item.get("impact_score", 0.5)))),
            "chart_config": chart_config,
        })

    # Sort by impact score
    insights.sort(key=lambda x: x["impact_score"], reverse=True)
    return insights


def _generate_stat_insights(df: pd.DataFrame) -> str:
    """Generate basic statistical summaries to help the LLM."""
    lines = []
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    if numeric_cols:
        desc = df[numeric_cols].describe().to_string()
        lines.append(f"Numeric summary:\n{desc}")

    # Categorical columns - top values
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    for col in cat_cols[:5]:
        top = df[col].value_counts().head(5)
        lines.append(f"\nTop values in '{col}': {dict(top)}")

    # Correlations
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr()
        high_corr = []
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                val = corr.iloc[i, j]
                if abs(val) > 0.5:
                    high_corr.append(f"{corr.columns[i]} ↔ {corr.columns[j]}: {val:.2f}")
        if high_corr:
            lines.append(f"\nNotable correlations: {'; '.join(high_corr)}")

    return "\n".join(lines)


def _fallback_insights(df: pd.DataFrame) -> list[dict]:
    """Generate rich insights without LLM, with DYNAMIC impact scoring."""
    insights = []
    color_palette = [
        "rgba(6, 182, 212, 0.8)", "rgba(139, 92, 246, 0.8)",
        "rgba(244, 114, 182, 0.8)", "rgba(34, 197, 94, 0.8)",
        "rgba(251, 191, 36, 0.8)", "rgba(239, 68, 68, 0.8)",
    ]

    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    # ── 1. Dataset overview (always present) ──────────────────────
    null_pct = (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100 if len(df) > 0 else 0
    size_score = min(0.65, 0.4 + (len(df) / 10000) * 0.25)

    null_msg = f"The data is clean with no missing values." if null_pct == 0 else f"About {null_pct:.1f}% of values are missing — worth investigating."
    insights.append({
        "text": f"Your dataset has {len(df):,} records across {len(df.columns)} columns — "
                f"{len(num_cols)} are numeric (good for calculations) and "
                f"{len(cat_cols)} are categorical (good for grouping). {null_msg}",
        "category": "summary",
        "impact_score": round(size_score, 2),
        "chart_config": None,
    })

    # ── 2. Numeric distribution insights (score by variation) ────
    for col in num_cols[:3]:
        mean_val = df[col].mean()
        std_val = df[col].std()
        min_val = df[col].min()
        max_val = df[col].max()
        cv = abs(std_val / mean_val) if mean_val != 0 else 0
        score = min(0.85, 0.5 + cv * 0.15)

        # Human-readable spread description
        ratio = max_val / min_val if min_val > 0 else 0
        if cv > 1.0:
            spread = f"Values vary widely — the lowest is {min_val:,.0f} and the highest is {max_val:,.0f}" + (f", about {ratio:.0f}× higher" if ratio > 2 else "") + f". The typical value is around {mean_val:,.0f}, but there's significant spread."
        elif cv > 0.3:
            spread = f"Values show moderate variation, ranging from {min_val:,.0f} to {max_val:,.0f} with a typical value around {mean_val:,.0f}."
        else:
            spread = f"Values are fairly consistent, clustering around {mean_val:,.0f} (range: {min_val:,.0f} to {max_val:,.0f})."

        insights.append({
            "text": f"{col}: {spread}",
            "category": "distribution",
            "impact_score": round(score, 2),
            "chart_config": None,
        })

    # ── 3. Category breakdown with chart ─────────────────────────
    for col in cat_cols[:1]:
        vc = df[col].value_counts().head(6)
        n_unique = df[col].nunique()
        if n_unique <= 2:
            score = 0.55
        elif n_unique <= 10:
            score = 0.8
        else:
            score = 0.65

        top_item = vc.index[0]
        top_count = vc.iloc[0]
        top_pct = (top_count / len(df)) * 100
        insights.append({
            "text": f"There are {n_unique} different {col} values. "
                    f"'{top_item}' is the most common, appearing {top_count} times ({top_pct:.0f}% of records). "
                    f"Other notable values: {', '.join(str(x) for x in vc.index[1:3])}.",
            "category": "comparison",
            "impact_score": round(score, 2),
            "chart_config": {
                "chart_type": "doughnut",
                "labels": vc.index.tolist(),
                "datasets": [{"label": col, "data": vc.values.tolist(), "backgroundColor": color_palette[:len(vc)]}],
                "title": f"Distribution of {col}",
            },
        })

    # ── 4. Cross-column aggregation (highest impact) ─────────────
    if num_cols and cat_cols:
        nc, cc = num_cols[0], cat_cols[0]
        agg = df.groupby(cc)[nc].sum().sort_values(ascending=False).head(8)
        if len(agg) > 1:
            top_share = agg.iloc[0] / agg.sum() if agg.sum() > 0 else 0
            score = min(0.92, 0.6 + top_share * 0.3)

            if top_share > 0.5:
                dominance = f"'{agg.index[0]}' dominates with {top_share:.0%} of total {nc}."
            elif top_share > 0.25:
                dominance = f"'{agg.index[0]}' leads with {top_share:.0%} of total, followed by '{agg.index[1]}'."
            else:
                dominance = f"{nc} is fairly evenly distributed across {cc} values."

            insights.append({
                "text": f"When we group {nc} by {cc}, {dominance} "
                        f"The range goes from {agg.iloc[-1]:,.0f} ({agg.index[-1]}) to {agg.iloc[0]:,.0f} ({agg.index[0]}).",
                "category": "comparison",
                "impact_score": round(score, 2),
                "chart_config": {
                    "chart_type": "bar",
                    "labels": agg.index.tolist(),
                    "datasets": [{"label": f"Total {nc}", "data": agg.values.tolist(),
                                  "backgroundColor": color_palette[0],
                                  "borderColor": color_palette[0].replace("0.8", "1"), "borderWidth": 2}],
                    "title": f"{nc} by {cc}",
                },
            })

    # ── 5. Correlation insight ───────────────────────────────────
    if len(num_cols) >= 2:
        corr = df[num_cols].corr()
        best_pair = None
        best_corr = 0
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                val = abs(corr.iloc[i, j])
                if val > best_corr:
                    best_corr = val
                    best_pair = (corr.columns[i], corr.columns[j], corr.iloc[i, j])
        if best_pair and best_corr > 0.4:
            direction = "increase together" if best_pair[2] > 0 else "move in opposite directions"
            strength = "strong" if best_corr > 0.7 else "moderate"
            score = min(0.9, 0.5 + best_corr * 0.4)
            insights.append({
                "text": f"There's a {strength} relationship between {best_pair[0]} and {best_pair[1]} — "
                        f"they tend to {direction} (correlation: {best_pair[2]:.2f}). "
                        f"This could be useful for predictions or deeper analysis.",
                "category": "trend",
                "impact_score": round(score, 2),
                "chart_config": None,
            })

    insights.sort(key=lambda x: x["impact_score"], reverse=True)
    return insights


def _build_insight_chart(df: pd.DataFrame, chart_info: dict) -> dict | None:
    """Build a Chart.js config for an insight's suggested visualization."""
    try:
        chart_type = chart_info.get("type", "bar")
        title = chart_info.get("title", "")
        label_col = chart_info.get("label_column", "")
        value_cols = chart_info.get("value_columns", [])

        color_palette = [
            "rgba(6, 182, 212, 0.8)",
            "rgba(139, 92, 246, 0.8)",
            "rgba(244, 114, 182, 0.8)",
            "rgba(34, 197, 94, 0.8)",
            "rgba(251, 191, 36, 0.8)",
            "rgba(239, 68, 68, 0.8)",
        ]

        # Aggregate data if needed
        if label_col and label_col in df.columns and value_cols:
            valid_value_cols = [vc for vc in value_cols if vc in df.columns]
            if not valid_value_cols:
                return None

            agg_df = df.groupby(label_col)[valid_value_cols].sum().head(10).reset_index()
            labels = agg_df[label_col].astype(str).tolist()

            datasets = []
            for i, vc in enumerate(valid_value_cols):
                datasets.append({
                    "label": vc,
                    "data": agg_df[vc].fillna(0).tolist(),
                    "backgroundColor": color_palette[i % len(color_palette)],
                    "borderColor": color_palette[i % len(color_palette)].replace("0.8", "1"),
                    "borderWidth": 2,
                })

            if chart_type in ("pie", "doughnut") and datasets:
                datasets[0]["backgroundColor"] = color_palette[:len(labels)]

            return {
                "chart_type": chart_type,
                "labels": labels,
                "datasets": datasets,
                "title": title,
            }

        return None
    except Exception:
        return None
