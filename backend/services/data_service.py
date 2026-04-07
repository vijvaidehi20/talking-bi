import uuid
import pandas as pd
from pathlib import Path
from config import UPLOAD_DIR

# In-memory dataset store
_datasets: dict[str, dict] = {}

# loads dataset
def save_and_parse(file_path: Path, original_filename: str) -> dict:
    """Parse an uploaded CSV/Excel file and store it in memory."""
    dataset_id = str(uuid.uuid4())[:8]

    suffix = Path(original_filename).suffix.lower()
    if suffix in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, engine="openpyxl")
    else:
        df = pd.read_csv(file_path)

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]

    # Build column profile
    columns_info = []
    for col in df.columns:
        col_info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isnull().sum()),
            "unique_count": int(df[col].nunique()),
            "sample_values": [
                str(v) for v in df[col].dropna().head(5).tolist()
            ],
        }
        # Add numeric stats
        if pd.api.types.is_numeric_dtype(df[col]):
            col_info["min"] = float(df[col].min()) if not df[col].isnull().all() else None
            col_info["max"] = float(df[col].max()) if not df[col].isnull().all() else None
            col_info["mean"] = float(df[col].mean()) if not df[col].isnull().all() else None
        columns_info.append(col_info)

    # Preview rows
    preview = df.head(5).fillna("").to_dict(orient="records")

    # Store
    _datasets[dataset_id] = {
        "id": dataset_id,
        "filename": original_filename,
        "df": df,
        "columns_info": columns_info,
        "row_count": len(df),
        "column_count": len(df.columns),
        "preview": preview,
    }

    return _datasets[dataset_id]


def get_dataset(dataset_id: str) -> dict | None:
    return _datasets.get(dataset_id)


def get_dataframe(dataset_id: str) -> pd.DataFrame | None:
    ds = _datasets.get(dataset_id)
    return ds["df"] if ds else None


def get_data_summary(dataset_id: str) -> str:
    """Build a structured text summary for LLM context (RAG grounding)."""
    ds = _datasets.get(dataset_id)
    if not ds:
        return ""

    df = ds["df"]
    lines = [
        f"Dataset: {ds['filename']}",
        f"Rows: {ds['row_count']}, Columns: {ds['column_count']}",
        "",
        "Columns:",
    ]

    for col in ds["columns_info"]:
        stat_parts = [f"  - {col['name']} (type: {col['dtype']}, unique: {col['unique_count']}, nulls: {col['null_count']})"]
        if "mean" in col and col.get("mean") is not None:
            stat_parts.append(f"    range: {col['min']:.2f} – {col['max']:.2f}, mean: {col['mean']:.2f}")
        stat_parts.append(f"    samples: {col['sample_values'][:3]}")
        lines.extend(stat_parts)

    # Add a few sample rows
    lines.append("")
    lines.append("Sample rows (first 3):")
    for row in ds["preview"][:3]:
        lines.append(f"  {row}")

    return "\n".join(lines)


def get_column_names(dataset_id: str) -> list[str]:
    """Return the list of column names for a dataset."""
    ds = _datasets.get(dataset_id)
    return [c["name"] for c in ds["columns_info"]] if ds else []

def _is_id_column(df: pd.DataFrame, col: str) -> bool:
    """Detect if a column is a unique identifier (ID)."""
    col_lower = col.lower()
    if "order id" in col_lower or col_lower.endswith("id") or col_lower in ["id", "uuid", "index"]:
        return True
    
    unique_count = df[col].nunique()
    if unique_count == len(df) and len(df) > 10:
        return True
    
    return False

def get_safe_categorical(df: pd.DataFrame) -> list[str]:
    """Return columns suitable for X-axis categories (low cardinality, not IDs)."""
    cat_cols = []
    for col in df.select_dtypes(include=["object", "category"]).columns:
        if not _is_id_column(df, col) and "paymentmode" not in col.lower() and "payment mode" not in col.lower():
            # Prefer low-cardinality categorical
            if df[col].nunique() < 100:
                cat_cols.append(col)
                
    # Priority: 1. Category 2. Sub-Category 3. Region
    def rank_cat(c):
        cl = c.lower()
        if "sub-category" in cl or "subcategory" in cl: return 1
        if "category" in cl: return 0
        if "region" in cl: return 2
        return 99
        
    cat_cols.sort(key=rank_cat)
    
    # fallback to any text if empty
    if not cat_cols:
        for col in df.select_dtypes(include=["object", "category"]).columns:
            if not _is_id_column(df, col):
                cat_cols.append(col)
    
    return cat_cols

def get_safe_numeric(df: pd.DataFrame) -> list[str]:
    """Return columns suitable for Y-axis metrics (numeric, continuous, not IDs)."""
    num_cols = []
    for col in df.select_dtypes(include=["number"]).columns:
        if not _is_id_column(df, col):
            num_cols.append(col)
    return num_cols

def get_primary_metric_cols(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """Identify the consistent sales/revenue and profit columns."""
    safe_num = get_safe_numeric(df)
    
    def _find(keywords):
        for col in safe_num:
            if any(kw in col.lower() for kw in keywords):
                return col
        return None
        
    sales_col = _find(["sale", "revenue", "amount", "total"]) or (safe_num[0] if safe_num else None)
    profit_col = _find(["profit", "margin", "gain"]) or (safe_num[1] if len(safe_num) > 1 else None)
    
    return sales_col, profit_col
