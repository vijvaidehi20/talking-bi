const API_BASE = 'http://localhost:8001';

async function safeFetch(url, options = {}) {
  try {
    const res = await fetch(url, options);
    if (!res.ok) {
      return { error: 'Something went wrong while processing your query.' };
    }
    return await res.json();
  } catch (err) {
    return { error: 'Something went wrong while processing your query.' };
  }
}

export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const data = await safeFetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData,
  });

  if (data.error) throw new Error(data.error);
  return data;
}

export async function queryDataset(datasetId, question, conversationHistory = []) {
  const data = await safeFetch(`${API_BASE}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      dataset_id: datasetId,
      question,
      conversation_history: conversationHistory,
    }),
  });

  if (data.error) throw new Error(data.error);
  return data;
}

export async function getChatHistory(datasetId) {
  const data = await safeFetch(`${API_BASE}/api/history/${datasetId}`);
  if (data.error) return { messages: [] };
  return data;
}

export async function getDashboard(datasetId) {
  const data = await safeFetch(`${API_BASE}/api/dashboard/${datasetId}`);
  if (data.error) throw new Error(data.error);
  return data;
}

export async function buildChart(requestBody) {
  const data = await safeFetch(`${API_BASE}/api/chart/build`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody),
  });

  if (data.error) throw new Error(data.error);
  return data;
}
