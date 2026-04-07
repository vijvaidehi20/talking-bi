import { useState, useEffect } from 'react';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import ReactMarkdown from 'react-markdown';
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement,
  ArcElement, PointElement, LineElement, Tooltip, Legend, Filler,
} from 'chart.js';
import { getDashboard } from '../utils/api';

ChartJS.register(
  CategoryScale, LinearScale, BarElement,
  ArcElement, PointElement, LineElement, Tooltip, Legend, Filler,
);

const isDark = () => document.documentElement.getAttribute('data-theme') !== 'light';

const chartOptions = (title, chartType) => {
  const gridColor = isDark() ? 'rgba(99, 115, 146, 0.04)' : 'rgba(0, 0, 0, 0.03)';
  const textColor = isDark() ? '#94a3b8' : '#64748b';

  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top', labels: { color: textColor, font: { size: 11 }, usePointStyle: true, padding: 16 } },
      tooltip: { backgroundColor: isDark() ? 'rgba(17, 24, 39, 0.95)' : 'rgba(255, 255, 255, 0.95)', titleColor: isDark() ? '#f1f5f9' : '#1e293b', bodyColor: isDark() ? '#94a3b8' : '#475569', borderColor: isDark() ? 'rgba(99, 115, 146, 0.3)' : 'rgba(0, 0, 0, 0.1)', borderWidth: 1, padding: 12, cornerRadius: 8, titleFont: { size: 12, weight: '600' }, bodyFont: { size: 11 } },
    },
    scales: ['pie', 'doughnut'].includes(chartType) ? {} : {
      x: { ticks: { color: textColor, font: { size: 10 } }, grid: { color: gridColor }, border: { display: false } },
      y: { ticks: { color: textColor, font: { size: 10 } }, grid: { color: gridColor }, border: { display: false } },
    },
  };
};

const pieOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'right', labels: { color: 'var(--text-secondary)', font: { size: 11 }, padding: 12, usePointStyle: true } },
  },
};

const ChartComponent = ({ config }) => {
  if (!config) return null;

  const data = {
    labels: config.labels,
    datasets: (config.datasets || []).map((ds) => ({
      ...ds,
      borderRadius: config.chart_type === 'bar' ? 6 : undefined,
      borderSkipped: false,
      barPercentage: config.chart_type === 'bar' ? 0.6 : undefined,
      categoryPercentage: config.chart_type === 'bar' ? 0.8 : undefined,
      tension: config.chart_type === 'line' ? 0.4 : undefined,
      fill: config.chart_type === 'line' ? 'origin' : undefined,
      backgroundColor: (context) => {
        const chart = context.chart;
        const { ctx, chartArea } = chart;
        
        if (!chartArea) return ds.backgroundColor;
        
        if (config.chart_type === 'bar' || config.chart_type === 'line') {
          const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
          const coreColor = typeof ds.backgroundColor === 'string' ? ds.backgroundColor : "rgba(6, 182, 212, 0.8)";
          const fadeColor = coreColor.replace(/[\d.]+\)$/g, '0.1)'); 
          gradient.addColorStop(0, fadeColor);
          gradient.addColorStop(1, coreColor);
          return gradient;
        }
        return ds.backgroundColor;
      }
    })),
  };

  if (config.chart_type === 'doughnut' || config.chart_type === 'pie') {
    return <Doughnut data={data} options={pieOptions} />;
  }
  if (config.chart_type === 'line') {
    return <Line data={data} options={chartOptions(config.title, 'line')} />;
  }
  return <Bar data={data} options={chartOptions(config.title, 'bar')} />;
};

const insightTypeColor = {
  positive: 'var(--accent-green)',
  warning: 'var(--accent-amber)',
  neutral: 'var(--text-secondary)',
  info: 'var(--accent-cyan)',
};

const insightTypeIcon = {
  positive: '✅',
  warning: '⚠️',
  neutral: 'ℹ️',
  info: '📊',
};

export default function Dashboard({ dataset }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!dataset?.id) return;
    setLoading(true);
    setError('');
    getDashboard(dataset.id)
      .then((d) => { setData(d); setLoading(false); })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, [dataset?.id]);

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="typing-indicator">
          <div className="typing-dot"></div>
          <div className="typing-dot"></div>
          <div className="typing-dot"></div>
        </div>
        <p>Generating dashboard...</p>
      </div>
    );
  }

  if (!data) return <div className="dashboard-loading">{error || 'No data available'}</div>;

  return (
    <div className="dashboard">
      {/* KPI Cards */}
      <div className="dashboard-kpis">
        {data.kpis?.map((kpi, i) => (
          <div key={i} className="kpi-card">
            <div className="kpi-icon">{kpi.icon}</div>
            <div className="kpi-info">
              <div className="kpi-value">{kpi.value}</div>
              <div className="kpi-label">{kpi.label}</div>
              {kpi.change && <div className="kpi-change">{kpi.change}</div>}
            </div>
          </div>
        ))}
      </div>

      {/* Charts Grid */}
      <div className="dashboard-charts">
        {data.charts?.map((chart) => (
          <div key={chart.id} className="dashboard-chart-card">
            <div className="dashboard-chart-title">{chart.title}</div>
            <div className="dashboard-chart-container">
              <ChartComponent config={chart} />
            </div>
          </div>
        ))}
      </div>

      {/* Insights */}
      {data.insights?.length > 0 && (
        <div className="dashboard-insights">
          <div className="dashboard-section-title">🔍 Key Business Insights</div>
          {data.insights.map((insight, i) => (
            <div
              key={i}
              className="dashboard-insight-card"
              style={{ borderLeftColor: insightTypeColor[insight.type] || 'var(--accent-cyan)' }}
            >
              <span className="dashboard-insight-icon">
                {insightTypeIcon[insight.type] || '📊'}
              </span>
              <div className="dashboard-insight-text markdown-content">
                <ReactMarkdown>{insight.text}</ReactMarkdown>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
