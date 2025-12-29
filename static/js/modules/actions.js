/**
 * Moment Dashboard - Actions
 * Simulation controls and API calls
 */

import { el } from './state.js';
import { send } from './websocket.js';

// Start simulation
export function startSimulation() {
  send({
    action: 'start_simulation',
    event_count: parseInt(el.eventCount?.value || 50),
    attack_percentage: parseInt(el.attackPct?.value || 20),
    duration_seconds: parseInt(el.duration?.value || 10),
    use_ai: el.useAi?.checked || false
  });
}

// Stop simulation
export function stopSimulation() {
  send({ action: 'stop_simulation' });
}

// Reset metrics
export function resetMetrics() {
  send({ action: 'reset_metrics' });
  if (el.btnExport) el.btnExport.disabled = true;
}

// Run attack scenario
export function runScenario(id) {
  send({ 
    action: 'run_scenario', 
    scenario_id: id, 
    use_ai: el.useAi?.checked || false 
  });
}

// Set decision mode
export function setDecisionMode(mode) {
  send({ action: 'set_decision_mode', mode: mode });
}

// Export report
export async function exportReport() {
  try {
    const res = await fetch('/api/export-report');
    const data = await res.json();
    if (data.error) return alert(data.error);

    const win = window.open('', '_blank');
    win.document.write(generateReportHTML(data));
    win.document.close();
    win.print();
  } catch (e) {
    alert('Export failed: ' + e.message);
  }
}

// Generate report HTML
function generateReportHTML(data) {
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <title>Security Report</title>
      <style>
        body { font-family: -apple-system, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }
        h1 { color: #1f2937; border-bottom: 2px solid #6366f1; padding-bottom: 10px; }
        h2 { color: #374151; margin-top: 30px; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
        .stat { background: #f3f4f6; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #6366f1; }
        .stat-label { font-size: 12px; color: #6b7280; }
        .blocked { color: #ef4444; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #e5e7eb; padding: 10px; text-align: left; }
        th { background: #f3f4f6; }
      </style>
    </head>
    <body>
      <h1>Moment - Security Report</h1>
      <p>Generated: ${new Date(data.generated_at).toLocaleString()}</p>
      <div class="stats">
        <div class="stat"><div class="stat-value">${data.summary.total_events}</div><div class="stat-label">Events</div></div>
        <div class="stat"><div class="stat-value blocked">${data.summary.blocked}</div><div class="stat-label">Blocked</div></div>
        <div class="stat"><div class="stat-value">${data.summary.allowed}</div><div class="stat-label">Allowed</div></div>
        <div class="stat"><div class="stat-value">${data.summary.block_rate}%</div><div class="stat-label">Block Rate</div></div>
      </div>
      <h2>Top Risk Actors</h2>
      <table>
        <tr><th>Actor</th><th>Events</th><th>Blocked</th><th>Avg Risk</th></tr>
        ${data.top_risky_actors.map(a => `<tr><td>${a.actor_id}</td><td>${a.events}</td><td>${a.blocked}</td><td>${(a.avg_risk * 100).toFixed(0)}%</td></tr>`).join('')}
      </table>
    </body>
    </html>
  `;
}
