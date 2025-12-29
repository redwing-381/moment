/**
 * Moment Dashboard - Chart
 * Risk trend chart using Chart.js
 */

import { state, el } from './state.js';

// Initialize risk chart
export function initChart() {
  const ctx = el.riskChart?.getContext('2d');
  if (!ctx) return;

  state.chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        data: [],
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      scales: {
        y: {
          beginAtZero: true,
          max: 1,
          grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false },
          ticks: { color: '#6b7280', callback: v => `${(v * 100).toFixed(0)}%` }
        },
        x: { display: false }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1f2937',
          titleColor: '#f3f4f6',
          bodyColor: '#9ca3af',
          borderColor: '#374151',
          borderWidth: 1,
          displayColors: false,
          callbacks: { label: ctx => `Risk: ${(ctx.raw * 100).toFixed(0)}%` }
        }
      },
      animation: { duration: 0 }
    }
  });
}

// Update chart with new data
export function updateChart(trend) {
  if (!trend || !state.chart) return;

  state.chart.data.labels = trend.map((_, i) => i);
  state.chart.data.datasets[0].data = trend.map(r => r.risk_score);

  const avg = trend.reduce((a, r) => a + r.risk_score, 0) / trend.length;
  const color = avg >= 0.6 ? '#ef4444' : avg >= 0.4 ? '#f59e0b' : '#10b981';
  state.chart.data.datasets[0].borderColor = color;
  state.chart.data.datasets[0].backgroundColor = color.replace(')', ', 0.1)').replace('rgb', 'rgba');

  state.chart.update();
}

// Update chart colors for theme
export function updateChartTheme(darkMode) {
  if (!state.chart) return;
  
  const gridColor = darkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';
  const tickColor = darkMode ? '#6b7280' : '#64748b';
  
  state.chart.options.scales.y.grid.color = gridColor;
  state.chart.options.scales.y.ticks.color = tickColor;
  state.chart.options.plugins.tooltip.backgroundColor = darkMode ? '#1f2937' : '#ffffff';
  state.chart.options.plugins.tooltip.titleColor = darkMode ? '#f3f4f6' : '#1e293b';
  state.chart.options.plugins.tooltip.bodyColor = darkMode ? '#9ca3af' : '#64748b';
  state.chart.options.plugins.tooltip.borderColor = darkMode ? '#374151' : '#e2e8f0';
  state.chart.update();
}
