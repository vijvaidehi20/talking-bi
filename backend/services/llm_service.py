import json
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL

# Configure Gemini (only if API key is available)
_model = None
if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel(GEMINI_MODEL)
    except Exception:
        _model = None


def is_llm_available() -> bool:
    return _model is not None


def call_llm(prompt: str, system_instruction: str = "") -> str:
    """Send a prompt to Gemini and return the text response."""
    if not is_llm_available():
        return "Error: LLM not configured. Please set GEMINI_API_KEY in .env file."
    try:
        full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        response = _model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error communicating with LLM: {str(e)}"


def call_llm_json(prompt: str, system_instruction: str = "") -> dict | list | None:
    """Send a prompt and parse the response as JSON."""
    raw = call_llm(prompt, system_instruction)

    # Strip markdown code fences if present
    cleaned = raw
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1]
    if "```" in cleaned:
        cleaned = cleaned.split("```", 1)[0]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start:end])
            except json.JSONDecodeError:
                pass
        # Try array
        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start:end])
            except json.JSONDecodeError:
                pass
        return None


# ── Prompt Templates ──────────────────────────────────────────────

QUERY_SYSTEM = """You are a data analyst assistant. You help users explore and understand their datasets.
You have access to a pandas DataFrame called `df`. You must answer questions by generating Python/pandas code to query the data.

RULES:
1. Always respond in valid JSON with this exact structure:
{
  "code": "pandas code that produces the result (assign final result to `result` variable)",
  "answer": "natural language answer to display to the user",
  "chart": {
    "type": "bar|line|pie|doughnut|scatter|none",
    "title": "chart title",
    "label_column": "column name for labels/x-axis",
    "value_columns": ["column name(s) for values/y-axis"]
  },
  "follow_ups": ["suggested follow-up question 1", "question 2", "question 3"]
}
2. The 'code' field must be valid Python that works on a pandas DataFrame named `df`.
3. Always assign the final result to a variable named `result`.
4. If a chart is appropriate, specify chart config. Use "none" for chart type if no chart fits.
5. Generate 2-3 contextual follow-up questions the user might ask next.
6. Keep answers concise but insightful.
"""

INSIGHT_SYSTEM = """You are a data analyst. Analyze the dataset and generate the most valuable insights.
For each insight, provide:
- A clear, concise text description
- A category (trend, outlier, distribution, comparison, summary)
- An impact score from 0.0 to 1.0 (how significant/actionable is this insight)
- A chart configuration if the insight benefits from visualization

Respond with valid JSON array:
[
  {
    "text": "insight description",
    "category": "category",
    "impact_score": 0.85,
    "chart": {
      "type": "bar|line|pie|doughnut|scatter",
      "title": "chart title",
      "label_column": "column for labels",
      "value_columns": ["column(s) for values"]
    }
  }
]

Generate 4-6 insights, ranked by impact_score (highest first).
Focus on: key distributions, top/bottom values, correlations, notable patterns, summary statistics.
"""

FOLLOWUP_SYSTEM = """Based on the conversation so far, suggest 3 natural follow-up questions the user
might want to ask about their data. Return a JSON array of strings."""
