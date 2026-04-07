import { useState, useEffect, useCallback } from 'react';
import {
  Chart as ChartJS, CategoryScale, LinearScale,
  BarElement, LineElement, PointElement, ArcElement,
  Title, Tooltip, Legend, Filler,
} from 'chart.js';
import { Bar, Line, Pie, Doughnut, Scatter } from 'react-chartjs-2';
import { buildChart } from '../utils/api';

ChartJS.register(
  CategoryScale, LinearScale, BarElement, LineElement,
  PointElement, ArcElement, Title, Tooltip, Legend, Filler
);

const chartComponents = { bar: Bar, line: Line, pie: Pie, doughnut: Doughnut, scatter: Scatter };

export default function ChartPanel({ dataset }) {
  const numCols = dataset?.columns?.filter((c) => ["int64", "float64"].includes(c.dtype)) || [];
  const catCols = dataset?.columns?.filter((c) => ["object", "category"].includes(c.dtype)) || [];

  const [xAxis, setXAxis] = useState(catCols[0]?.name || '');
  const [yAxis, setYAxis] = useState(numCols[0]?.name || '');
  const [agg, setAgg] = useState('sum');
  const [chartType, setChartType] = useState('bar');
  
  const [chartConfig, setChartConfig] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchChart = useCallback(async () => {
    if (!dataset || !xAxis || !yAxis) return;
    setLoading(true);
    try {
      const config = await buildChart({
        dataset_id: dataset.id,
        x_axis: xAxis,
        y_axis: yAxis,
        aggregation: agg,
        chart_type: chartType,
      });
      setChartConfig(config);
    } catch (e) {
      console.error("Failed to build chart", e);
    } finally {
      setLoading(false);
    }
  }, [dataset, xAxis, yAxis, agg, chartType]);

  useEffect(() => {
    fetchChart();
  }, [fetchChart]);

  // CSS mappings
  const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
  const textColor = isDark ? '#94a3b8' : '#64748b';
  const titleColor = isDark ? '#f1f5f9' : '#1e293b';
  const gridColor = isDark ? 'rgba(99, 115, 146, 0.04)' : 'rgba(0, 0, 0, 0.03)';
  const tooltipBg = isDark ? 'rgba(17, 24, 39, 0.95)' : 'rgba(255, 255, 255, 0.95)';

  const renderChart = () => {
    if (loading && !chartConfig) return <div className="chart-placeholder">Loading chart...</div>;
    if (!chartConfig) return <div className="chart-placeholder">Select columns to build a chart</div>;

    const ChartComponent = chartComponents[chartConfig.chart_type] || Bar;
    const data = {
      labels: chartConfig.labels || [],
      datasets: (chartConfig.datasets || []).map((ds) => ({
        ...ds,
        tension: chartConfig.chart_type === 'line' ? 0.4 : undefined,
        fill: chartConfig.chart_type === 'line' ? 'origin' : undefined,
        borderRadius: chartConfig.chart_type === 'bar' ? 6 : undefined,
        backgroundColor: (context) => {
          const chart = context.chart;
          const { ctx, chartArea } = chart;
          if (!chartArea) return ds.backgroundColor;
          if (chartConfig.chart_type === 'bar' || chartConfig.chart_type === 'line') {
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

    const options = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, labels: { color: textColor } },
        title: { display: !!chartConfig.title, text: chartConfig.title || '', color: titleColor, font: { size: 14 } },
        tooltip: { backgroundColor: tooltipBg, titleColor: titleColor, bodyColor: textColor },
      },
      scales: ['pie', 'doughnut'].includes(chartConfig.chart_type) ? {} : {
        x: { ticks: { color: textColor }, grid: { color: gridColor }, border: { display: false } },
        y: { ticks: { color: textColor }, grid: { color: gridColor }, border: { display: false } },
      },
    };

    return <ChartComponent data={data} options={options} />;
  };

  if (!dataset) return null;

  return (
    <div className="chart-section">
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>🏗️ Chart Builder</span>
        <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={fetchChart}>
          Refresh
        </button>
      </div>

      <div style={{ padding: '12px 16px', background: 'var(--bg-card)', borderBottom: '1px solid var(--border-subtle)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>X-Axis (Category)</label>
          <select value={xAxis} onChange={e => setXAxis(e.target.value)} style={{ padding: '6px', borderRadius: '4px', background: 'var(--bg-main)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
            {catCols.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
          </select>
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Y-Axis (Metrics)</label>
          <select value={yAxis} onChange={e => setYAxis(e.target.value)} style={{ padding: '6px', borderRadius: '4px', background: 'var(--bg-main)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
            {numCols.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
          </select>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Aggregation</label>
          <select value={agg} onChange={e => setAgg(e.target.value)} style={{ padding: '6px', borderRadius: '4px', background: 'var(--bg-main)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
            <option value="sum">Sum</option>
            <option value="average">Average</option>
            <option value="count">Count</option>
          </select>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Chart Type</label>
          <select value={chartType} onChange={e => setChartType(e.target.value)} style={{ padding: '6px', borderRadius: '4px', background: 'var(--bg-main)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
            <option value="bar">Bar Chart</option>
            <option value="doughnut">Donut Chart</option>
            <option value="pie">Pie Chart</option>
            <option value="line">Line Chart</option>
          </select>
        </div>
      </div>

      <div className="chart-container" style={{ position: 'relative' }}>
        {loading && <div style={{ position: 'absolute', top: 12, right: 12, fontSize: '12px', color: 'var(--accent-cyan)' }}>Updating...</div>}
        <div style={{ width: '100%', height: '260px' }}>
          {renderChart()}
        </div>
      </div>
    </div>
  );
}
