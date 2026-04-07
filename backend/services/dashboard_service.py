"""
Dashboard Service — generates KPIs, auto-charts, and insights for the dashboard tab.
Pure Pandas, no LLM dependency.
"""

import pandas as pd
from services.data_service import (
    get_dataframe, get_dataset, get_safe_categorical, get_safe_numeric, get_primary_metric_cols
)

COLOR_PALETTE = [
    "rgba(6, 182, 212, 0.8)",    # cyan
    "rgba(139, 92, 246, 0.8)",   # violet
    "rgba(244, 114, 182, 0.8)",  # pink
    "rgba(34, 197, 94, 0.8)",    # green
    "rgba(251, 191, 36, 0.8)",   # amber
    "rgba(239, 68, 68, 0.8)",    # red
    "rgba(59, 130, 246, 0.8)",   # blue
    "rgba(168, 85, 247, 0.8)",   # purple
]


def generate_dashboard(dataset_id: str) -> dict:
    """Generate complete dashboard data for a dataset."""
    df = get_dataframe(dataset_id)
    ds = get_dataset(dataset_id)
    if df is None or ds is None:
        return {"kpis": [], "charts": [], "insights": []}

    num_cols = get_safe_numeric(df)
    cat_cols = get_safe_categorical(df)

    return {
        "kpis": _generate_kpis(df, num_cols, cat_cols),
        "charts": _generate_charts(df, num_cols, cat_cols),
        "insights": _generate_business_insights(df, num_cols, cat_cols),
    }


def _generate_kpis(df: pd.DataFrame, num_cols: list, cat_cols: list) -> list:
    """Generate 4 KPI cards: Total Sales, Total Profit, Average Order Value, Total Orders."""
    
    sales_col, profit_col = get_primary_metric_cols(df)
    
    kpis = []
    
    # 1. Total Sales (sum of Amount)
    total_sales = df[sales_col].sum() if sales_col else 0
    kpis.append({"label": "Total Sales", "value": f"${total_sales:,.0f}" if sales_col else "N/A", "icon": "💰", "change": None})
    
    # 2. Total Profit
    total_profit = df[profit_col].sum() if profit_col else 0
    kpis.append({"label": "Total Profit", "value": f"${total_profit:,.0f}" if profit_col else "N/A", "icon": "🏆", "change": None})
    
    # 3. Average Order Value
    avg_order = df[sales_col].mean() if sales_col else 0
    kpis.append({"label": "Average Order Value", "value": f"${avg_order:,.2f}" if sales_col else "N/A", "icon": "📈", "change": None})
    
    # 4. Total Orders
    kpis.append({"label": "Total Orders", "value": f"{len(df):,}", "icon": "📦", "change": None})

    return kpis


def _generate_charts(df: pd.DataFrame, num_cols: list, cat_cols: list) -> list:
    """Auto-generate exactly 6 specific analytical charts for the dashboard."""
    charts = []

    sales_col, profit_col = get_primary_metric_cols(df)
    if not num_cols:
        return charts

    # Fallbacks if columns are missing
    metric = sales_col or num_cols[0]
    metric_2 = profit_col or (num_cols[1] if len(num_cols) > 1 else metric)
    
    cat1 = cat_cols[0] if cat_cols else df.columns[0]
    cat2 = cat_cols[1] if len(cat_cols) > 1 else cat1

    # 1. Category Contribution (Donut Chart) -> % total Amount by Category
    agg1 = df.groupby(cat1)[metric].sum().sort_values(ascending=False).head(8)
    charts.append({
        "id": "chart_1",
        "title": f"Contribution by {cat1}",
        "chart_type": "doughnut",
        "labels": agg1.index.astype(str).tolist(),
        "datasets": [{
            "label": metric,
            "data": [round(x, 2) for x in agg1.values.tolist()],
            "backgroundColor": COLOR_PALETTE[:len(agg1)],
            "borderWidth": 2,
        }],
    })

    # 2. Sub-Category Breakdown (Bar Chart)
    agg2 = df.groupby(cat2)[metric].sum().sort_values(ascending=False).head(10)
    charts.append({
        "id": "chart_2",
        "title": f"{metric} by {cat2}",
        "chart_type": "bar",
        "labels": agg2.index.astype(str).tolist(),
        "datasets": [{
            "label": metric,
            "data": [round(x, 2) for x in agg2.values.tolist()],
            "backgroundColor": COLOR_PALETTE[0],
            "borderColor": COLOR_PALETTE[0].replace("0.8", "1"),
            "borderWidth": 2,
        }],
    })

    # 3. Top 10 Orders / Products (Bar Chart)
    id_col = cat_cols[-1] if cat_cols else df.columns[0] # Try to use the most granular categorical
    top10 = df.nlargest(10, metric)
    charts.append({
        "id": "chart_3",
        "title": f"Top 10 by {metric}",
        "chart_type": "bar",
        "labels": top10[id_col].astype(str).tolist(),
        "datasets": [{
            "label": metric,
            "data": [round(x, 2) for x in top10[metric].tolist()],
            "backgroundColor": COLOR_PALETTE[1],
            "borderColor": COLOR_PALETTE[1].replace("0.8", "1"),
            "borderWidth": 2,
        }],
    })

    # 4. Category Comparison (Grouped Bar)
    agg4 = df.groupby(cat1)[[metric, metric_2]].sum().sort_values(by=metric, ascending=False).head(8)
    # Ensure they are distinct, else plot something else
    if metric == metric_2 and len(num_cols) > 1:
        metric_2 = num_cols[1]
        agg4 = df.groupby(cat1)[[metric, metric_2]].sum().sort_values(by=metric, ascending=False).head(8)

    charts.append({
        "id": "chart_4",
        "title": f"{metric} & {metric_2} by {cat1}",
        "chart_type": "bar",
        "labels": agg4.index.astype(str).tolist(),
        "datasets": [
            {
                "label": metric,
                "data": [round(x, 2) for x in agg4[metric].tolist()],
                "backgroundColor": COLOR_PALETTE[0],
                "borderColor": COLOR_PALETTE[0].replace("0.8", "1"),
                "borderWidth": 2,
            },
            {
                "label": metric_2,
                "data": [round(x, 2) for x in agg4[metric_2].tolist()],
                "backgroundColor": COLOR_PALETTE[3], # Greenish contrast
                "borderColor": COLOR_PALETTE[3].replace("0.8", "1"),
                "borderWidth": 2,
            }
        ],
    })

    # 5. Distribution Chart (Histogram-like Bar)
    # Binning the metric into 15 bins
    import numpy as np
    counts, bin_edges = np.histogram(df[metric].dropna(), bins=15)
    bin_labels = [f"{int(bin_edges[i])}-{int(bin_edges[i+1])}" for i in range(len(bin_edges)-1)]
    charts.append({
        "id": "chart_5",
        "title": f"Distribution of {metric}",
        "chart_type": "bar",
        "labels": bin_labels,
        "datasets": [{
            "label": "Frequency",
            "data": counts.tolist(),
            "backgroundColor": COLOR_PALETTE[4],
            "borderColor": COLOR_PALETTE[4].replace("0.8", "1"),
            "borderWidth": 2,
            "barPercentage": 1.0,
            "categoryPercentage": 1.0, # makes it look like a histogram
        }],
    })

    # 6. Trend / Cumulative Chart (Line)
    # Using simple observation ordering since we don't assume a date column is present natively
    trend_data = df[metric].sort_values().reset_index(drop=True)
    # Sub-sample to ~40 points to avoid overloading line charts
    step = max(1, len(trend_data) // 40)
    sampled = trend_data.iloc[::step].head(40)
    charts.append({
        "id": "chart_6",
        "title": f"{metric} Trend (Ordered)",
        "chart_type": "line",
        "labels": list(range(len(sampled))),
        "datasets": [{
            "label": metric,
            "data": [round(x, 2) for x in sampled.tolist()],
            "borderColor": COLOR_PALETTE[6],  # Blue
            "backgroundColor": COLOR_PALETTE[6].replace("0.8", "0.2"),
            "fill": True,
            "tension": 0.4,
            "borderWidth": 3,
        }],
    })

    return charts[:6]


def _generate_business_insights(df: pd.DataFrame, num_cols: list, cat_cols: list) -> list:
    """Generate top 5 business-quality insights."""
    insights = []

    if not num_cols or not cat_cols:
        return [{"text": f"Dataset contains {len(df):,} records across {len(df.columns)} columns.", "type": "info"}]

    sales_col, profit_col = get_primary_metric_cols(df)
    
    # If a generic fallback is needed
    if not profit_col: profit_col = num_cols[0]
    if not sales_col: sales_col = num_cols[0]
        
    cc = cat_cols[0]
    
    agg = df.groupby(cc)[profit_col].sum().sort_values(ascending=False)

    # 1. Most profitable category
    if len(agg) > 0:
        best = agg.index[0]
        total = agg.sum()
        best_share = (agg.iloc[0] / total * 100) if total != 0 else 0
        insights.append({
            "text": f"**Most Profitable:** **{best}** is the top-performing {cc}, "
                    f"generating **{best_share:.0f}%** of total {profit_col}.",
            "type": "positive",
        })

    # 2. Least profitable category
    if len(agg) > 1:
        worst = agg.index[-1]
        worst_share = (agg.iloc[-1] / agg.sum() * 100) if agg.sum() != 0 else 0
        insights.append({
            "text": f"**Least Profitable:** **{worst}** contributes just **{worst_share:.0f}%** "
                    f"to {profit_col}, ranking last among {cc}s.",
            "type": "warning",
        })

    # 3. Highest order
    top_order = df.nlargest(1, sales_col).iloc[0]
    insights.append({
        "text": f"**Highest Order:** The top single transaction yielded **${top_order[sales_col]:,.0f}** "
                f"in {sales_col} (from {cc} *{top_order[cc]}*).",
        "type": "info",
    })

    # 4. Anomaly (Outliers)
    q1 = df[sales_col].quantile(0.25)
    q3 = df[sales_col].quantile(0.75)
    iqr = q3 - q1
    outliers = ((df[sales_col] < q1 - 1.5 * iqr) | (df[sales_col] > q3 + 1.5 * iqr)).sum()
    if outliers > 0:
        insights.append({
            "text": f"**Anomaly Detected:** Found **{outliers} outliers** in {sales_col} "
                    f"({(outliers/len(df))*100:.1f}% of data) performing significantly different from average.",
            "type": "warning",
        })
    else:
        insights.append({
            "text": f"**Stability:** No significant anomalies detected in {sales_col}.",
            "type": "positive",
        })

    # 5. High variance
    std_dev = df[sales_col].std()
    mean = df[sales_col].mean()
    cv = std_dev / mean if mean != 0 else 0
    if cv > 1:
        insights.append({
            "text": f"**High Variance:** The {sales_col} metric fluctuates significantly "
                    f"(StdDev = ${std_dev:,.0f} vs Mean = ${mean:,.0f}). This suggests inconsistent performance.",
            "type": "warning",
        })
    else:
        insights.append({
            "text": f"**Low Variance:** The {sales_col} metric is relatively stable "
                    f"with consistent performance across the dataset.",
            "type": "positive",
        })

    return insights[:5]
