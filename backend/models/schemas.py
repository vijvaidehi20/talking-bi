from pydantic import BaseModel
from typing import Optional


class QueryRequest(BaseModel):
    dataset_id: str
    question: str
    conversation_history: list[dict] = []


class ChartConfig(BaseModel):
    chart_type: str  # bar, line, pie, doughnut, scatter
    labels: list[str] = []
    datasets: list[dict] = []
    title: str = ""


class ChartBuildRequest(BaseModel):
    dataset_id: str
    x_axis: str
    y_axis: str
    aggregation: str = "sum"  # sum, average, count
    chart_type: str = "bar"  # bar, line, pie, doughnut


class InsightItem(BaseModel):
    text: str
    category: str  # trend, outlier, distribution, comparison, summary
    impact_score: float  # 0.0 - 1.0
    chart_config: Optional[ChartConfig] = None


class QueryResponse(BaseModel):
    answer: str
    response_type: str = "analysis"  # summary, chart, insight, analysis, fallback
    title: str = ""
    chart_config: Optional[ChartConfig] = None
    follow_ups: list[str] = []
    data_table: Optional[list[dict]] = None


class DatasetInfo(BaseModel):
    id: str
    filename: str
    row_count: int
    column_count: int
    columns: list[dict]  # {name, dtype, sample_values, null_count, unique_count}
    preview: list[dict]  # first 5 rows


class UploadResponse(BaseModel):
    dataset: DatasetInfo
    insights: list[InsightItem] = []
