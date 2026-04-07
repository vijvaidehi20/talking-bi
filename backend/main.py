import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import UPLOAD_DIR, PORT
from models.schemas import (
    QueryRequest, QueryResponse, UploadResponse,
    DatasetInfo, ChartConfig, InsightItem, ChartBuildRequest,
)
from services.data_service import save_and_parse, get_dataset, get_dataframe
from services.query_engine import execute_query
from services.insight_engine import generate_insights
from services.dashboard_service import generate_dashboard
from services.deterministic_handlers import build_interactive_chart

app = FastAPI(title="Talking BI", version="1.0.0")

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory chat history ────────────────────────────────────────
_chat_history: dict[str, list[dict]] = {}  # dataset_id -> list of messages


def _get_history(dataset_id: str) -> list[dict]:
    return _chat_history.setdefault(dataset_id, [])


def _add_message(dataset_id: str, role: str, content: str, **extra):
    msg = {"role": role, "content": content, **extra}
    _get_history(dataset_id).append(msg)
    # Keep last 50 messages per dataset
    if len(_chat_history[dataset_id]) > 50:
        _chat_history[dataset_id] = _chat_history[dataset_id][-50:]
    return msg


@app.post("/api/upload", response_model=UploadResponse)
async def upload_dataset(file: UploadFile = File(...)):
    """Upload a CSV or Excel file for analysis."""
    allowed = {".csv", ".xlsx", ".xls"}
    suffix = Path(file.filename or "file.csv").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}. Use CSV or Excel.")

    file_path = UPLOAD_DIR / (file.filename or "upload.csv")
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        ds = save_and_parse(file_path, file.filename or "upload.csv")
        insights_raw = generate_insights(ds["id"])

        dataset_info = DatasetInfo(
            id=ds["id"],
            filename=ds["filename"],
            row_count=ds["row_count"],
            column_count=ds["column_count"],
            columns=ds["columns_info"],
            preview=ds["preview"],
        )

        insights = []
        for ins in insights_raw:
            chart = None
            if ins.get("chart_config"):
                chart = ChartConfig(**ins["chart_config"])
            insights.append(InsightItem(
                text=ins["text"],
                category=ins["category"],
                impact_score=ins["impact_score"],
                chart_config=chart,
            ))

        # Clear any old chat history for this dataset
        _chat_history[ds["id"]] = []

        return UploadResponse(dataset=dataset_info, insights=insights)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.post("/api/query", response_model=QueryResponse)
async def query_dataset(req: QueryRequest):
    """Ask a natural language question about the dataset."""
    ds = get_dataset(req.dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    # Save user message to history
    _add_message(req.dataset_id, "user", req.question)

    # Get full history for context
    history = _get_history(req.dataset_id)

    result = execute_query(req.dataset_id, req.question, history)

    # Save AI response to history
    _add_message(req.dataset_id, "ai", result["answer"])

    chart = None
    if result.get("chart_config"):
        chart = ChartConfig(**result["chart_config"])

    return QueryResponse(
        answer=result["answer"],
        response_type=result.get("response_type", "analysis"),
        title=result.get("title", ""),
        chart_config=chart,
        follow_ups=result.get("follow_ups", []),
        data_table=result.get("data_table"),
    )


@app.get("/api/history/{dataset_id}")
async def get_chat_history(dataset_id: str):
    """Get chat history for a dataset."""
    return {"messages": _get_history(dataset_id)}


@app.get("/api/datasets/{dataset_id}")
async def get_dataset_info(dataset_id: str):
    """Get metadata for an uploaded dataset."""
    ds = get_dataset(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return DatasetInfo(
        id=ds["id"],
        filename=ds["filename"],
        row_count=ds["row_count"],
        column_count=ds["column_count"],
        columns=ds["columns_info"],
        preview=ds["preview"],
    )


@app.get("/api/datasets/{dataset_id}/preview")
async def get_dataset_preview(dataset_id: str):
    """Get first N rows of the dataset."""
    ds = get_dataset(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return {"preview": ds["preview"]}


@app.get("/api/dashboard/{dataset_id}")
async def get_dashboard(dataset_id: str):
    """Get auto-generated dashboard data for a dataset."""
    ds = get_dataset(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return generate_dashboard(dataset_id)


@app.post("/api/chart/build", response_model=ChartConfig)
async def build_chart(req: ChartBuildRequest):
    """Build a deterministic interactive chart from UI parameters."""
    df = get_dataframe(req.dataset_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
        
    chart_dict = build_interactive_chart(
        df=df,
        x_axis=req.x_axis,
        y_axis=req.y_axis,
        agg_func=req.aggregation,
        chart_type=req.chart_type
    )
    if not chart_dict:
        raise HTTPException(status_code=400, detail="Invalid chart configuration.")
        
    return ChartConfig(**chart_dict)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
