# Talking BI Platform

Talking BI is a high-performance, deterministic business intelligence and analytics engine. It allows users to seamlessly upload datasets (CSV or Excel) and derive actionable insights through natural language queries. By combining robust rule-based data processing (via Pandas) with large language model intelligence, the platform guarantees immediate, accurate calculations for core business metrics while offering modern, interactive data visualizations.

## 🚀 Features

- **File Upload:** Instantly upload CSV or Excel datasets for analysis.
- **Natural Language Data Querying:** Ask questions in plain English and receive conversational answers along with data tables and charts.
- **Automated Insights Generator:** Automatically generates key takeaways, impact scores, and corresponding visualizations upon file upload.
- **Auto-generated Dashboards:** Instant BI dashboards built deterministically from your data.
- **Interactive Chart Builder:** Dynamically build and configure interactive charts using Chart.js.
- **Context-Aware Chat History:** Maintains conversation history per dataset for contextual follow-up questions.

## 🛠️ Technology Stack

**Frontend:**
- React 19
- Vite
- Chart.js & React-Chartjs-2 (for interactive data visualizations)
- React Markdown (for rendering text)

**Backend:**
- Python 3
- FastAPI (High-performance API framework)
- Pandas & Numpy (for deterministic data processing and aggregation)
- Groq API (for blazing-fast intent classification and natural language generation)

## 📁 Project Structure

```text
talking-bi/
├── backend/            # FastAPI application and Python logic
│   ├── main.py         # Main API routes
│   ├── config.py       # Configuration and environment variables
│   ├── models/         # Pydantic schemas for structured data
│   ├── services/       # Services (Data, Query Engine, Insights, Dashboard)
│   └── uploads/        # Temporary directory for dataset uploads
├── frontend/           # React frontend application
│   ├── src/            # React components and views
│   ├── package.json    # Frontend dependencies and scripts
│   └── vite.config.js  # Vite configuration
├── .env                # Environment variables (API keys, etc.)
└── .gitignore          # Git ignore configuration
```

## ⚙️ Getting Started

### Prerequisites

- Node.js (v18+ recommended)
- Python 3.9+
- A Groq API Key

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables. Ensure the root `.env` file (or `backend/.env`) has your Groq API Key:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```
5. Start the backend server:
   ```bash
   python main.py
   ```
   *The FastAPI backend will start running on `http://localhost:8000`.*

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
   *The React application will be available at `http://localhost:5173`.*

## 📈 Analytics Approach

Unlike standard LLM agents that attempt to write and run code on the fly to fulfill analytical queries, **Talking BI** enforces strict rule-based workflows. The LLM is used exclusively for *intent classification* and *natural language response drafting*, while calculations, metric aggregations, and chart configurations are handled by deterministic Python code. This avoids hallucinated numbers and ensures maximum reliability for business-critical decision making.
