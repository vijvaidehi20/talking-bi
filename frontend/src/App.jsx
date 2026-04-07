import { useState, useCallback, useEffect } from 'react';
import Header from './components/Header';
import UploadPanel from './components/UploadPanel';
import ChatInterface from './components/ChatInterface';
import ChartPanel from './components/ChartPanel';
import Dashboard from './components/Dashboard';
import { uploadFile, queryDataset, getChatHistory } from './utils/api';

export default function App() {
  const [dataset, setDataset] = useState(null);
  const [insights, setInsights] = useState([]);
  const [messages, setMessages] = useState([]);
  const [chartConfig, setChartConfig] = useState(null);
  const [followUps, setFollowUps] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [theme, setTheme] = useState(() => localStorage.getItem('tbi-theme') || 'dark');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('tbi-theme', theme);
  }, [theme]);

  useEffect(() => {
    if (dataset && dataset.id) {
      getChatHistory(dataset.id).then((history) => {
        if (history && history.messages) {
          setMessages(history.messages);
        }
      }).catch(console.error);
    }
  }, [dataset]);

  const toggleTheme = useCallback(() => {
    setTheme((t) => (t === 'dark' ? 'light' : 'dark'));
  }, []);

  const handleUpload = useCallback(async (file) => {
    const result = await uploadFile(file);
    setDataset(result.dataset);
    setInsights(result.insights || []);
    setMessages([]);
    setChartConfig(null);
    setFollowUps([]);
    setActiveTab('chat');
    return result;
  }, []);

  const handleNewDataset = useCallback(() => {
    setDataset(null);
    setInsights([]);
    setMessages([]);
    setChartConfig(null);
    setFollowUps([]);
    setActiveTab('chat');
  }, []);

  const handleSend = useCallback(async (question) => {
    if (!dataset) return;
    const userMsg = { role: 'user', content: question };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setFollowUps([]);

    try {
      const history = [...messages, userMsg].map((m) => ({
        role: m.role, content: m.content,
      }));
      const result = await queryDataset(dataset.id, question, history);

      const aiMsg = {
        role: 'ai',
        content: result.answer,
        response_type: result.response_type || 'analysis',
        title: result.title || '',
        data_table: result.data_table,
        follow_ups: result.follow_ups || [],
      };
      setMessages((prev) => [...prev, aiMsg]);
      if (result.chart_config) setChartConfig(result.chart_config);
      setFollowUps(result.response_type !== 'fallback' ? (result.follow_ups || []) : []);
    } catch (err) {
      setMessages((prev) => [...prev, {
        role: 'ai',
        content: err.message,
        response_type: 'fallback',
        title: 'Error',
      }]);
    } finally {
      setLoading(false);
    }
  }, [dataset, messages]);

  useEffect(() => {
    const handler = (e) => { if (e.detail && !loading) handleSend(e.detail); };
    window.addEventListener('followup-click', handler);
    return () => window.removeEventListener('followup-click', handler);
  }, [handleSend, loading]);

  /* ── Homepage: no dataset uploaded yet ── */
  if (!dataset) {
    return <UploadPanel onUpload={handleUpload} theme={theme} toggleTheme={toggleTheme} />;
  }

  /* ── Workspace: dataset loaded ── */
  return (
    <>
      <Header
        dataset={dataset}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        theme={theme}
        toggleTheme={toggleTheme}
        onNewDataset={handleNewDataset}
      />
      <main className="main-app">
        {activeTab === 'chat' && (
          <ChatInterface
            messages={messages}
            onSend={handleSend}
            loading={loading}
            followUps={followUps}
            dataset={dataset}
            chartConfig={chartConfig}
          />
        )}

        {activeTab === 'dashboard' && (
          <div className="dashboard-full">
            <Dashboard dataset={dataset} />
          </div>
        )}
      </main>
    </>
  );
}
